"""Conflict detection service for finding contradictions and agreements between claims.

This is the CORE differentiator: classify the information landscape into
consensus, contested, and unknown buckets based on semantic similarity
and LLM-powered relationship detection.
"""
import json
import logging
import asyncio
from typing import Dict, Any, List, Tuple, Optional

from app.config import settings
from app.services.gemini_client import generate
from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


# ============================================================================
# FUNCTION 1 — Find similar claim pairs
# ============================================================================

async def find_similar_claim_pairs(
    session_id: str,
    similarity_threshold: float = 0.75,
    max_pairs: int = 50,
) -> List[Tuple[Dict[str, Any], Dict[str, Any], float]]:
    """
    Find pairs of claims that are semantically similar.
    
    Args:
        session_id: UUID of the research session
        similarity_threshold: Minimum cosine similarity (0-1)
        max_pairs: Maximum number of pairs to return
    
    Returns:
        List of tuples: (claim_a, claim_b, similarity_score)
        Deduplicates pairs and skips self-matches.
    
    Examples:
        >>> pairs = await find_similar_claim_pairs("session-uuid")
        >>> len(pairs) <= 50
        True
        >>> all(a["id"] != b["id"] for a, b, _ in pairs)
        True
    """
    logger.info(f"Finding similar claim pairs for session {session_id}")
    
    # Fetch all claims for the session
    try:
        from app.db.supabase_client import get_claims_by_session
        claims = await get_claims_by_session(session_id)
    except Exception as e:
        logger.error(f"Failed to fetch claims for session {session_id}: {e}")
        return []
    
    if not claims:
        logger.info("No claims found for session")
        return []
    
    logger.debug(f"Found {len(claims)} claims, searching for similar pairs")
    
    # Build set of unique pairs
    seen_pairs = set()
    pairs = []
    
    for claim_a in claims:
        if len(pairs) >= max_pairs:
            break
        
        # Find similar claims using vector search
        try:
            from app.db.supabase_client import find_similar_claims
            similar_claims = await find_similar_claims(
                claim_a["embedding"],
                threshold=similarity_threshold,
                limit=5
            )
        except Exception as e:
            logger.warning(f"Failed to find similar claims for claim {claim_a.get('id')}: {e}")
            continue
        
        for similar_claim in similar_claims:
            claim_b = similar_claim["claim"]
            similarity = similar_claim["similarity"]
            
            # Skip self-matches
            if claim_a["id"] == claim_b["id"]:
                continue
            
            # Create canonical pair ID (smaller ID first)
            pair_key = tuple(sorted([claim_a["id"], claim_b["id"]]))
            
            # Skip if we've seen this pair
            if pair_key in seen_pairs:
                continue
            
            seen_pairs.add(pair_key)
            pairs.append((claim_a, claim_b, similarity))
            
            if len(pairs) >= max_pairs:
                break
    
    # Mock mode fallback: generate synthetic pairs if needed
    if settings.mock_mode and len(pairs) == 0 and len(claims) >= 2:
        logger.debug("MOCK MODE: Generating synthetic claim pairs")
        # Create pairs from existing claims only if we have NO pairs
        for i in range(min(2, len(claims) - 1)):
            claim_a = claims[i]
            claim_b = claims[i + 1]
            pair_key = tuple(sorted([claim_a["id"], claim_b["id"]]))
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                pairs.append((claim_a, claim_b, 0.85))
    
    logger.info(f"Found {len(pairs)} candidate claim pairs")
    return pairs[:max_pairs]


# ============================================================================
# FUNCTION 2 — Judge a single pair
# ============================================================================

async def judge_pair(
    claim_a: Dict[str, Any],
    claim_b: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Determine the relationship between two claims using LLM.
    
    Args:
        claim_a: First claim dict with id, claim_text, etc.
        claim_b: Second claim dict
    
    Returns:
        Conflict dict if contradiction/disagreement found, None if agreement.
        Conflict dict has keys: claim_a_id, claim_b_id, conflict_type,
        confidence, explanation.
    
    Examples:
        >>> claim_a = {"id": 1, "claim_text": "Earth is flat"}
        >>> claim_b = {"id": 2, "claim_text": "Earth is round"}
        >>> conflict = await judge_pair(claim_a, claim_b)
        >>> conflict is not None
        True
        >>> conflict["conflict_type"] in ["contradiction", "disagreement"]
        True
    """
    claim_a_text = claim_a.get("claim_text", "")
    claim_b_text = claim_b.get("claim_text", "")
    
    logger.debug(
        f"Judging pair: claim {claim_a.get('id')} vs {claim_b.get('id')}"
    )
    
    # Mock mode: return synthetic conflict
    if settings.mock_mode:
        logger.debug("MOCK MODE: Returning synthetic conflict")
        return {
            "claim_a_id": claim_a["id"],
            "claim_b_id": claim_b["id"],
            "conflict_type": "contradiction",
            "confidence": 0.8,
            "explanation": "Mock conflict between two similar claims",
        }
    
    # Real mode: use Gemini to judge
    prompt = f"""You are a fact-comparison engine. Compare the two claims below and determine their relationship.

Claim A: "{claim_a_text}"
Claim B: "{claim_b_text}"

Classify their relationship as EXACTLY ONE of:
- "contradiction": A and B cannot both be true
- "disagreement": A and B differ in emphasis or interpretation
- "agreement": A and B support or reinforce each other

Return ONLY this JSON, no extra text:
{{"relationship": "contradiction",
 "confidence": 0.85,
 "explanation": "one-sentence reason"}}"""
    
    try:
        response = await generate(prompt)
        result = _parse_judgment_json(response)
        
    except (json.JSONDecodeError, ValueError) as e:
        # Retry once with stricter prompt
        logger.warning(f"Initial judgment parse failed: {e}. Retrying...")
        
        strict_prompt = f"""Return ONLY JSON, no markdown, no explanation.

Compare these claims:
A: "{claim_a_text}"
B: "{claim_b_text}"

Format: {{"relationship": "contradiction|disagreement|agreement", "confidence": 0.85, "explanation": "reason"}}"""
        
        try:
            response = await generate(strict_prompt)
            result = _parse_judgment_json(response)
        except Exception as retry_error:
            logger.error(f"Judgment failed after retry: {retry_error}")
            return None
    
    # Process result
    relationship = result.get("relationship", "").lower()
    
    # Agreement → not a conflict, return None
    if relationship == "agreement":
        logger.debug(f"Claims {claim_a['id']} and {claim_b['id']} are in agreement, skipping")
        return None
    
    # Contradiction or disagreement → return conflict dict
    if relationship in ["contradiction", "disagreement"]:
        return {
            "claim_a_id": claim_a["id"],
            "claim_b_id": claim_b["id"],
            "conflict_type": relationship,
            "confidence": result.get("confidence", 0.5),
            "explanation": result.get("explanation", "No explanation provided"),
        }
    
    # Unknown relationship → skip
    logger.warning(f"Unknown relationship '{relationship}' for pair, skipping")
    return None


def _parse_judgment_json(response: str) -> Dict[str, Any]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    response = response.strip()
    
    # Remove markdown code blocks
    if response.startswith("```"):
        lines = response.split("\n")
        # Remove first line if it's ```json or ```
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response = "\n".join(lines).strip()
    
    # Parse JSON
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        # Try to extract JSON from response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            response = response[start:end]
            data = json.loads(response)
        else:
            raise e
    
    # Validate required keys
    if "relationship" not in data:
        raise ValueError("Missing 'relationship' key in judgment")
    
    return data


# ============================================================================
# FUNCTION 3 — Detect all conflicts
# ============================================================================

async def detect_conflicts(session_id: str) -> List[Dict[str, Any]]:
    """
    Detect all conflicts between claims in a session.
    
    Args:
        session_id: UUID of the research session
    
    Returns:
        List of stored conflict records with IDs
    
    Raises:
        Exception: If database insert fails
    
    Examples:
        >>> conflicts = await detect_conflicts("session-uuid")
        >>> all("id" in c for c in conflicts)
        True
    """
    logger.info(f"Detecting conflicts for session {session_id}")
    
    # Find similar pairs
    pairs = await find_similar_claim_pairs(session_id)
    
    if not pairs:
        logger.info("No similar pairs found, no conflicts to detect")
        return []
    
    logger.info(f"Found {len(pairs)} candidate pairs, judging...")
    
    # Judge each pair concurrently
    tasks = [judge_pair(claim_a, claim_b) for claim_a, claim_b, _ in pairs]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Filter out None and exceptions
    conflicts = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.warning(f"Skipping pair due to error: {result}")
            continue
        if result is not None:
            conflicts.append(result)
    
    if not conflicts:
        logger.info("No conflicts detected (all pairs were agreements or failed)")
        return []
    
    # Batch insert into database
    try:
        from app.db.supabase_client import insert_conflicts
        stored_conflicts = await insert_conflicts(session_id, conflicts)
        
        logger.info(f"Detected {len(stored_conflicts)} conflicts")
        return stored_conflicts
        
    except Exception as e:
        logger.error(f"Failed to insert conflicts: {e}")
        raise


# ============================================================================
# FUNCTION 4 — Classify the information landscape
# ============================================================================

async def classify_information_landscape(session_id: str) -> Dict[str, Any]:
    """
    Classify claims into consensus, contested, and unknown buckets.
    
    This is the CORE output of the entire system: a three-way classification
    of the information landscape based on cross-references and conflicts.
    
    Args:
        session_id: UUID of the research session
    
    Returns:
        Dict with keys:
        - consensus: List of high-credibility claims with cross-references
        - contested: List of claims involved in conflicts
        - unknown: List of low-credibility or single-source claims
        - summary: Counts for each bucket
    
    Examples:
        >>> landscape = await classify_information_landscape("session-uuid")
        >>> set(landscape.keys()) == {"consensus", "contested", "unknown", "summary"}
        True
        >>> landscape["summary"]["total_claims"] >= 0
        True
    """
    logger.info(f"Classifying information landscape for session {session_id}")
    
    # Fetch all data
    try:
        from app.db.supabase_client import (
            get_claims_by_session,
            get_conflicts_by_session,
            get_sources_by_session,
            find_similar_claims,
        )
        
        claims = await get_claims_by_session(session_id)
        conflicts = await get_conflicts_by_session(session_id)
        sources = await get_sources_by_session(session_id)
        
    except Exception as e:
        logger.error(f"Failed to fetch data for landscape: {e}")
        return {
            "consensus": [],
            "contested": [],
            "unknown": [],
            "summary": {
                "total_claims": 0,
                "consensus_count": 0,
                "contested_count": 0,
                "unknown_count": 0,
            }
        }
    
    if not claims:
        logger.info("No claims found, returning empty landscape")
        return {
            "consensus": [],
            "contested": [],
            "unknown": [],
            "summary": {
                "total_claims": 0,
                "consensus_count": 0,
                "contested_count": 0,
                "unknown_count": 0,
            }
        }
    
    # Build source credibility map
    source_credibility = {
        source["id"]: source.get("credibility_score", 50.0)
        for source in sources
    }
    
    source_domain = {
        source["id"]: source.get("domain", "unknown")
        for source in sources
    }
    
    # Build contested claim IDs
    contested_claim_ids = set()
    claim_conflicts = {}  # claim_id -> list of conflicts
    
    for conflict in conflicts:
        claim_a_id = conflict["claim_a_id"]
        claim_b_id = conflict["claim_b_id"]
        
        contested_claim_ids.add(claim_a_id)
        contested_claim_ids.add(claim_b_id)
        
        # Track conflicts for each claim
        if claim_a_id not in claim_conflicts:
            claim_conflicts[claim_a_id] = []
        if claim_b_id not in claim_conflicts:
            claim_conflicts[claim_b_id] = []
        
        claim_conflicts[claim_a_id].append({
            "claim_id": claim_b_id,
            "type": conflict.get("conflict_type", "unknown"),
            "explanation": conflict.get("explanation", ""),
        })
        claim_conflicts[claim_b_id].append({
            "claim_id": claim_a_id,
            "type": conflict.get("conflict_type", "unknown"),
            "explanation": conflict.get("explanation", ""),
        })
    
    # Classify each claim
    consensus = []
    contested = []
    unknown = []
    
    for claim in claims:
        claim_id = claim["id"]
        source_id = claim.get("source_id")
        credibility = source_credibility.get(source_id, 50.0)
        domain = source_domain.get(source_id, "unknown")
        claim_text = claim.get("claim_text", "")
        
        # CONTESTED: claim appears in conflicts
        if claim_id in contested_claim_ids:
            contested.append({
                "claim_id": claim_id,
                "claim_text": claim_text,
                "source_id": source_id,
                "domain": domain,
                "credibility_score": credibility,
                "conflicts_with": claim_conflicts.get(claim_id, []),
            })
            continue
        
        # Check for cross-references (similar claims from different sources)
        cross_reference_count = 0
        if "embedding" in claim:
            try:
                similar = await find_similar_claims(
                    claim["embedding"],
                    threshold=0.85,
                    limit=5
                )
                # Count claims from different sources
                cross_reference_count = sum(
                    1 for s in similar
                    if s["claim"].get("source_id") != source_id
                    and s["claim"]["id"] != claim_id
                )
            except Exception as e:
                logger.warning(f"Failed to find similar claims for {claim_id}: {e}")
        
        # CONSENSUS: high credibility + cross-references
        if credibility >= 60 and cross_reference_count >= 1:
            consensus.append({
                "claim_id": claim_id,
                "claim_text": claim_text,
                "source_id": source_id,
                "domain": domain,
                "credibility_score": credibility,
                "supporting_source_count": cross_reference_count,
            })
        # UNKNOWN: low credibility or no cross-references
        else:
            reason = "low_credibility" if credibility < 60 else "no_cross_reference"
            unknown.append({
                "claim_id": claim_id,
                "claim_text": claim_text,
                "source_id": source_id,
                "domain": domain,
                "credibility_score": credibility,
                "reason": reason,
            })
    
    landscape = {
        "consensus": consensus,
        "contested": contested,
        "unknown": unknown,
        "summary": {
            "total_claims": len(claims),
            "consensus_count": len(consensus),
            "contested_count": len(contested),
            "unknown_count": len(unknown),
        }
    }
    
    logger.info(
        f"Landscape: {len(consensus)} consensus, "
        f"{len(contested)} contested, {len(unknown)} unknown"
    )
    
    return landscape
