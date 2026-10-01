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
from app.db.neon_client import (
    get_claims_by_session,
    find_similar_claims,
    get_sources_by_session,
    get_conflicts_by_session,
    insert_conflicts,
)

logger = logging.getLogger(__name__)

# Realistic conflict explanations for mock mode
REALISTIC_CONFLICTS = [
    "One source emphasizes cardiovascular benefits while another highlights digestive effects.",
    "The sources disagree on whether benefits are attributable to fiber or polyphenols.",
    "Some studies report statistically significant effects while others find only trends.",
    "The evidence is stronger for certain apple varieties than for others.",
    "Results vary by population studied, with some groups showing greater effects.",
    "One study uses fresh apples while another examines processed apple products.",
    "The magnitude of blood sugar effects differs between controlled trials and observational studies.",
    "Some research shows dose-dependent effects while other studies find threshold effects.",
]


# ============================================================================
# FUNCTION 1 — Find similar claim pairs
# ============================================================================

async def find_similar_claim_pairs(
    session_id: str,
    similarity_threshold: float = 0.80,  # CHANGE 2: Increased from 0.75 to 0.80
    max_pairs: int = 10,  # CHANGE 2: Reduced from 50 to 10
) -> List[Tuple[Dict[str, Any], Dict[str, Any], float]]:
    """
    Find pairs of claims that are semantically similar.
    
    CHANGE 2: Pre-filters pairs to reduce LLM calls:
    - Only pairs with similarity >= 0.80 (very similar)
    - Max 10 pairs instead of 50
    - Skips pairs from the same domain
    
    Args:
        session_id: UUID of the research session
        similarity_threshold: Minimum cosine similarity (0-1)
        max_pairs: Maximum number of pairs to return
    
    Returns:
        List of tuples: (claim_a, claim_b, similarity_score)
        Deduplicates pairs and skips self-matches.
    
    Examples:
        >>> pairs = await find_similar_claim_pairs("session-uuid")
        >>> len(pairs) <= 10
        True
        >>> all(a["id"] != b["id"] for a, b, _ in pairs)
        True
    """
    logger.info(f"Finding similar claim pairs for session {session_id} (threshold={similarity_threshold}, max={max_pairs})")
    
    # Fetch all claims for the session
    try:
        claims = await get_claims_by_session(session_id)
        sources = await get_sources_by_session(session_id)
        
        # Build source_id -> domain mapping
        source_domain_map = {s["id"]: s.get("domain", "") for s in sources}
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
            
            # CHANGE 2: Skip pairs from same domain
            domain_a = source_domain_map.get(claim_a.get("source_id"), "")
            domain_b = source_domain_map.get(claim_b.get("source_id"), "")
            if domain_a and domain_b and domain_a == domain_b:
                logger.debug(f"Skipping pair from same domain: {domain_a}")
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
    if settings.is_llm_mocked and len(pairs) == 0 and len(claims) >= 2:
        logger.debug("MOCK MODE: Generating synthetic claim pairs")
        # Create pairs from existing claims only if we have NO pairs
        for i in range(min(2, len(claims) - 1)):
            claim_a = claims[i]
            claim_b = claims[i + 1]
            pair_key = tuple(sorted([claim_a["id"], claim_b["id"]]))
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                pairs.append((claim_a, claim_b, 0.85))
    
    logger.info(f"Found {len(pairs)} candidate claim pairs (after filtering)")
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
    
    # Mock mode: return realistic conflict
    if settings.is_llm_mocked:
        logger.debug("MOCK MODE: Returning realistic conflict")
        # Pick a conflict explanation based on claim IDs
        conflict_idx = (claim_a["id"] + claim_b["id"]) % len(REALISTIC_CONFLICTS)
        # Ensure claim_a_id < claim_b_id to satisfy DB constraint
        id_a = min(claim_a["id"], claim_b["id"])
        id_b = max(claim_a["id"], claim_b["id"])
        return {
            "claim_a_id": id_a,
            "claim_b_id": id_b,
            "conflict_type": "disagreement",
            "confidence": 0.68 + (conflict_idx % 4) * 0.06,  # Vary 0.68-0.86
            "explanation": REALISTIC_CONFLICTS[conflict_idx],
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
    Detect all conflicts between claims in a session using BATCHED judgment.
    
    CHANGE 2: Groups pairs into batches of 5 to reduce LLM calls from N to ceil(N/5).
    
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
    
    logger.info(f"Found {len(pairs)} candidate pairs, judging in batches...")
    
    # CHANGE 2: Group pairs into batches of 5
    BATCH_SIZE = 5
    batches = [pairs[i:i + BATCH_SIZE] for i in range(0, len(pairs), BATCH_SIZE)]
    logger.info(f"Created {len(batches)} batches for judgment (batch size: {BATCH_SIZE})")
    
    # Judge batches sequentially
    all_conflicts = []
    for batch_idx, batch in enumerate(batches):
        logger.info(f"Judging batch {batch_idx + 1}/{len(batches)} ({len(batch)} pairs)")
        
        try:
            batch_conflicts = await _judge_pairs_batch(batch)
            all_conflicts.extend(batch_conflicts)
        except Exception as e:
            logger.error(f"Batch {batch_idx + 1} judgment failed: {e}")
            continue
    
    if not all_conflicts:
        logger.info("No conflicts detected (all pairs were agreements or failed)")
        return []
    
    # Batch insert into database
    try:
        stored_conflicts = await insert_conflicts(session_id, all_conflicts)
        
        logger.info(
            f"Detected {len(stored_conflicts)} conflicts using {len(batches)} LLM calls "
            f"(was {len(pairs)} calls before batching)"
        )
        return stored_conflicts
        
    except Exception as e:
        logger.error(f"Failed to insert conflicts: {e}")
        raise


async def _judge_pairs_batch(
    pairs: List[Tuple[Dict[str, Any], Dict[str, Any], float]]
) -> List[Dict[str, Any]]:
    """
    Judge multiple pairs in a SINGLE LLM call.
    
    Args:
        pairs: List of (claim_a, claim_b, similarity) tuples (up to 5)
    
    Returns:
        List of conflict dicts (only conflicts, not agreements)
    """
    if not pairs:
        return []
    
    # Mock mode
    if settings.is_llm_mocked:
        conflicts = []
        for idx, (claim_a, claim_b, _) in enumerate(pairs):
            conflict_idx = (idx + claim_a["id"]) % len(REALISTIC_CONFLICTS)
            # Ensure claim_a_id < claim_b_id to satisfy DB constraint
            id_a = min(claim_a["id"], claim_b["id"])
            id_b = max(claim_a["id"], claim_b["id"])
            conflicts.append({
                "claim_a_id": id_a,
                "claim_b_id": id_b,
                "conflict_type": "disagreement",
                "confidence": 0.68 + (conflict_idx % 4) * 0.06,
                "explanation": REALISTIC_CONFLICTS[conflict_idx],
            })
        return conflicts
    
    # Build prompt with all pairs numbered
    pairs_text = ""
    for idx, (claim_a, claim_b, sim) in enumerate(pairs, 1):
        claim_a_text = claim_a.get("claim_text", "")
        claim_b_text = claim_b.get("claim_text", "")
        pairs_text += f"\nPair {idx}:\n  Claim A (ID {claim_a['id']}): {claim_a_text}\n  Claim B (ID {claim_b['id']}): {claim_b_text}\n"
    
    prompt = f"""You are a fact-comparison engine. For each pair below, determine if the claims contradict, disagree, or agree.

{pairs_text}

For EACH pair, return a judgment. Use these relationships:
- "contradiction": Claims cannot both be true (mutually exclusive)
- "disagreement": Claims present conflicting interpretations or emphasis
- "agreement": Claims support or don't conflict with each other

Return ONLY valid JSON in this format:
{{
  "judgments": [
    {{"pair_id": 1, "claim_a_id": X, "claim_b_id": Y, "relationship": "contradiction", "confidence": 0.9, "explanation": "..."}},
    {{"pair_id": 2, "claim_a_id": X, "claim_b_id": Y, "relationship": "agreement", "confidence": 0.85, "explanation": "..."}}
  ]
}}

Rules:
- Return ALL {len(pairs)} pairs in order
- Only "contradiction" and "disagreement" are conflicts
- "agreement" means no conflict"""
    
    try:
        response = await generate(prompt)
        
        # Parse response
        response_clean = response.strip()
        if response_clean.startswith("```"):
            lines = response_clean.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_clean = "\n".join(lines).strip()
        
        data = json.loads(response_clean)
        judgments = data.get("judgments", [])
        
        # Filter to only conflicts
        conflicts = []
        for judgment in judgments:
            relationship = judgment.get("relationship", "")
            if relationship in ["contradiction", "disagreement"]:
                conflicts.append({
                    "claim_a_id": judgment["claim_a_id"],
                    "claim_b_id": judgment["claim_b_id"],
                    "conflict_type": relationship,
                    "confidence": judgment.get("confidence", 0.5),
                    "explanation": judgment.get("explanation", ""),
                })
        
        return conflicts
    
    except Exception as e:
        logger.error(f"Batched judgment failed: {e}")
        return []


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
        embedding = claim.get("embedding")
        if embedding is not None and len(embedding) > 0:
            try:
                similar = await find_similar_claims(
                    embedding,
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
        else:
            # No embedding available (mock mode or embedding generation failed)
            if settings.is_llm_mocked and credibility >= 60:
                # In partial mock mode, simulate cross-references for high-credibility claims
                # Use claim_id to deterministically assign cross-references
                cross_reference_count = 1 + (claim_id % 3 > 0)  # Most get 1-2 refs
                logger.debug(
                    f"Mock mode: assigned {cross_reference_count} cross-refs to claim {claim_id} "
                    f"(credibility={credibility:.1f})"
                )
        
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
