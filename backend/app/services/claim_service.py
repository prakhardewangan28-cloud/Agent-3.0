"""Claim extraction service for extracting verifiable claims from sources.

Extracts factual claims using Gemini (or mock data in mock mode),
embeds them, and stores them in Supabase.
"""
import json
import logging
import asyncio
import hashlib
import struct
from typing import Dict, Any, List
from datetime import datetime

from app.config import settings
from app.services.gemini_client import generate, embed
from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


# ============================================================================
# CLAIM EXTRACTION
# ============================================================================

async def extract_claims_from_text(
    text: str,
    max_claims: int = 5,
    source_credibility: float = 50.0,
) -> List[Dict[str, Any]]:
    """
    Extract verifiable factual claims from text.
    
    Args:
        text: The text to analyze (typically title + snippet)
        max_claims: Maximum number of claims to extract (default: 5)
        source_credibility: Credibility score of the source (0-100)
    
    Returns:
        List of claim dicts with keys:
        - claim (str): The claim text
        - confidence (float): Confidence score 0-1
    
    Examples:
        >>> claims = await extract_claims_from_text("AI systems are advancing rapidly.")
        >>> len(claims) <= 5
        True
        >>> claims[0]["confidence"] <= 1.0
        True
    """
    # Handle empty or very short text
    if not text or len(text.strip()) < 100:
        logger.debug(f"Text too short ({len(text)} chars), returning empty claims")
        return []
    
    # Mock mode: return fake claims
    if settings.mock_mode:
        mock_claims = [
            {
                "claim": f"Mock claim {i+1} from source",
                "confidence": 0.9 - (i * 0.1)
            }
            for i in range(2)
        ]
        logger.debug(f"MOCK MODE: Returning {len(mock_claims)} fake claims")
        return mock_claims
    
    # Real mode: call Gemini
    prompt = f"""You are a fact-extraction engine. From the text below, extract up to {max_claims} verifiable factual claims. Each claim must be a single, self-contained declarative sentence that could be fact-checked against a reference. Do NOT include opinions, predictions, or vague statements.

Return ONLY valid JSON in this exact format, no extra text:
{{"claims": [{{"claim": "...", "confidence": 0.85}}, ...]}}

Text:
---
{text}
---"""
    
    try:
        response = await generate(prompt)
        claims = _parse_claims_json(response)
        
    except (json.JSONDecodeError, ValueError) as e:
        # Retry with stricter prompt
        logger.warning(f"Initial claim extraction failed: {e}. Retrying with strict prompt...")
        
        strict_prompt = f"""Return ONLY JSON, no markdown, no explanation.

Extract up to {max_claims} factual claims from this text:
{text}

Format: {{"claims": [{{"claim": "...", "confidence": 0.85}}]}}"""
        
        try:
            response = await generate(strict_prompt)
            claims = _parse_claims_json(response)
        except Exception as retry_error:
            logger.error(f"Claim extraction failed after retry: {retry_error}")
            return []
    
    # Post-process claims
    processed_claims = []
    for claim_data in claims:
        # Clamp confidence to [0, 1]
        confidence = max(0.0, min(1.0, float(claim_data.get("confidence", 0.5))))
        
        # Downweight by source credibility
        adjusted_confidence = confidence * (source_credibility / 100.0)
        
        processed_claims.append({
            "claim": claim_data["claim"],
            "confidence": adjusted_confidence
        })
    
    logger.info(f"Extracted {len(processed_claims)} claims from {len(text)} chars of text")
    return processed_claims


def _parse_claims_json(response: str) -> List[Dict[str, Any]]:
    """
    Parse JSON response from Gemini.
    
    Handles markdown code blocks and extracts JSON.
    """
    # Remove markdown code blocks if present
    response = response.strip()
    if response.startswith("```"):
        # Extract content between ```json and ```
        lines = response.split("\n")
        json_lines = []
        in_code_block = False
        
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                json_lines.append(line)
        
        response = "\n".join(json_lines)
    
    # Parse JSON
    data = json.loads(response)
    
    # Validate structure
    if "claims" not in data:
        raise ValueError("Response missing 'claims' key")
    
    if not isinstance(data["claims"], list):
        raise ValueError("'claims' must be a list")
    
    # Validate each claim
    for claim in data["claims"]:
        if "claim" not in claim:
            raise ValueError("Each claim must have 'claim' key")
    
    return data["claims"]


# ============================================================================
# EMBEDDING
# ============================================================================

async def embed_claim(claim_text: str) -> List[float]:
    """
    Generate embedding for a claim.
    
    Args:
        claim_text: The claim text to embed
    
    Returns:
        List of 1536 floats representing the embedding
    
    Raises:
        ValueError: If embedding length != 1536
    
    Examples:
        >>> emb = await embed_claim("The sky is blue")
        >>> len(emb)
        1536
    """
    if settings.mock_mode:
        # Deterministic pseudo-random embedding based on claim text
        # This ensures same claim always gets same embedding
        embedding = _generate_deterministic_embedding(claim_text)
        logger.debug(f"MOCK MODE: Generated deterministic embedding for claim")
        return embedding
    
    # Real mode: call Gemini embeddings
    try:
        embedding = await embed(claim_text, dim=1536)
        
        # Validate length
        if len(embedding) != 1536:
            raise ValueError(
                f"Expected embedding length 1536, got {len(embedding)}"
            )
        
        return embedding
        
    except Exception as e:
        logger.error(f"Failed to embed claim: {e}")
        raise


def _generate_deterministic_embedding(text: str, dim: int = 1536) -> List[float]:
    """
    Generate a deterministic pseudo-random embedding from text.
    
    Uses SHA-256 hash to ensure same text always produces same vector.
    """
    # Hash the text
    hash_bytes = hashlib.sha256(text.encode('utf-8')).digest()
    
    # Generate enough random bytes for dim floats
    # Each float needs 4 bytes
    bytes_needed = dim * 4
    extended_bytes = hash_bytes
    
    # Extend hash by re-hashing until we have enough bytes
    while len(extended_bytes) < bytes_needed:
        extended_bytes += hashlib.sha256(extended_bytes).digest()
    
    # Convert bytes to floats in range [0, 1]
    embedding = []
    for i in range(dim):
        # Extract 4 bytes
        offset = i * 4
        four_bytes = extended_bytes[offset:offset+4]
        
        # Convert to unsigned int (0 to 2^32-1)
        uint_val = struct.unpack('>I', four_bytes)[0]
        
        # Normalize to [0, 1]
        float_val = uint_val / (2**32 - 1)
        
        embedding.append(float_val)
    
    # Normalize to unit length (cosine similarity friendly)
    magnitude = sum(x**2 for x in embedding) ** 0.5
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]
    
    return embedding


# ============================================================================
# EXTRACTION + STORAGE
# ============================================================================

async def extract_and_store_claims(
    source: Dict[str, Any],
    session_id: str,
) -> List[Dict[str, Any]]:
    """
    Extract claims from a source, embed them, and store in database.
    
    Args:
        source: Source dict with id, title, snippet, credibility_score
        session_id: UUID of the research session
    
    Returns:
        List of stored claim records with IDs from database
    
    Raises:
        KeyError: If source missing required 'id' key
        Exception: If database insert fails
    
    Examples:
        >>> source = {"id": 1, "title": "News", "snippet": "...", "credibility_score": 75}
        >>> claims = await extract_and_store_claims(source, "session-uuid")
        >>> all("id" in c for c in claims)
        True
    """
    start_time = datetime.now()
    
    # Validate source has ID
    if "id" not in source:
        raise KeyError("Source must have 'id' key after insert")
    
    source_id = source["id"]
    domain = source.get("domain", "unknown")
    
    logger.info(f"Extracting claims from source {source_id} ({domain})")
    
    # Build text to analyze
    title = source.get("title", "")
    snippet = source.get("snippet", "")
    text = f"{title}. {snippet}".strip()
    
    # Extract claims
    credibility = source.get("credibility_score", 50.0)
    extracted_claims = await extract_claims_from_text(
        text,
        max_claims=5,
        source_credibility=credibility
    )
    
    if not extracted_claims:
        logger.info(f"No claims extracted from source {source_id}")
        return []
    
    # Embed and prepare records
    claim_records = []
    for claim_data in extracted_claims:
        # Embed the claim
        try:
            embedding = await embed_claim(claim_data["claim"])
        except Exception as e:
            logger.error(f"Failed to embed claim from source {source_id}: {e}")
            continue
        
        claim_record = {
            "session_id": session_id,
            "source_id": source_id,
            "claim_text": claim_data["claim"],
            "embedding": embedding,
            "confidence": claim_data["confidence"],
        }
        claim_records.append(claim_record)
    
    # Batch insert into database
    if claim_records:
        try:
            # Import the actual function instead of the module
            from app.db.supabase_client import insert_claims
            stored_claims = await insert_claims(session_id, claim_records)
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(
                f"Extracted {len(stored_claims)} claims from source {source_id} "
                f"in {duration_ms:.0f}ms"
            )
            
            return stored_claims
            
        except Exception as e:
            logger.error(f"Failed to insert claims for source {source_id}: {e}")
            raise
    
    return []


# ============================================================================
# BATCH EXTRACTION
# ============================================================================

async def extract_claims_batch(
    sources: List[Dict[str, Any]],
    session_id: str,
    top_n: int = 10,
) -> Dict[str, Any]:
    """
    Extract claims from top N sources by credibility using BATCHED LLM calls.
    
    CHANGE 1: Groups sources into batches of 5 to reduce LLM calls from N to ceil(N/5).
    
    Args:
        sources: List of source dicts (must have credibility_score and id)
        session_id: UUID of the research session
        top_n: Number of top sources to process (default: 10)
    
    Returns:
        Summary dict with keys:
        - total_claims (int): Total number of claims extracted
        - per_source (dict): Mapping of source_id to claim count
        - successful_sources (int): Number of sources processed successfully
        - failed_sources (int): Number of sources that failed
    
    Examples:
        >>> sources = [{"id": 1, "credibility_score": 90, ...}, ...]
        >>> result = await extract_claims_batch(sources, "session-uuid", top_n=5)
        >>> "total_claims" in result
        True
    """
    logger.info(
        f"Starting BATCHED claim extraction for {len(sources)} sources "
        f"(processing top {top_n})"
    )
    
    # Sort by credibility descending
    sorted_sources = sorted(
        sources,
        key=lambda s: s.get("credibility_score", 0),
        reverse=True
    )
    
    # Take top N
    top_sources = sorted_sources[:top_n]
    
    # Handle empty source list
    if not top_sources:
        logger.info("No sources to process, returning empty result")
        return {
            "total_claims": 0,
            "per_source": {},
            "successful_sources": 0,
            "failed_sources": 0
        }
    
    logger.info(
        f"Processing {len(top_sources)} sources in batches of 5 "
        f"(credibility range: {top_sources[-1].get('credibility_score', 0):.1f} "
        f"to {top_sources[0].get('credibility_score', 0):.1f})"
    )
    
    # CHANGE 1: Group sources into batches of 5
    BATCH_SIZE = 5
    batches = [top_sources[i:i + BATCH_SIZE] for i in range(0, len(top_sources), BATCH_SIZE)]
    
    logger.info(f"Created {len(batches)} batches (batch size: {BATCH_SIZE})")
    
    # Process batches sequentially (to stay under quota)
    total_claims = 0
    per_source = {}
    successful = 0
    failed = 0
    
    for batch_idx, batch in enumerate(batches):
        logger.info(f"Processing batch {batch_idx + 1}/{len(batches)} ({len(batch)} sources)")
        
        try:
            # Extract claims for entire batch in ONE LLM call
            batch_results = await _extract_claims_batch_single_call(batch, session_id)
            
            # Process results
            for source_id, claims in batch_results.items():
                per_source[source_id] = len(claims)
                total_claims += len(claims)
                successful += 1
                logger.info(f"Source {source_id}: extracted {len(claims)} claims")
        
        except Exception as e:
            logger.error(f"Batch {batch_idx + 1} failed: {e}")
            # Mark all sources in batch as failed
            for source in batch:
                source_id = source.get("id", "unknown")
                per_source[source_id] = 0
                failed += 1
    
    summary = {
        "total_claims": total_claims,
        "per_source": per_source,
        "successful_sources": successful,
        "failed_sources": failed,
    }
    
    logger.info(
        f"Batch extraction complete: {total_claims} total claims from "
        f"{successful}/{len(top_sources)} sources using {len(batches)} LLM calls"
    )
    
    return summary


async def _extract_claims_batch_single_call(
    sources: List[Dict[str, Any]],
    session_id: str,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Extract claims from multiple sources in a SINGLE LLM call.
    
    Args:
        sources: List of source dicts (up to 5)
        session_id: UUID of the research session
    
    Returns:
        Dict mapping source_id to list of claims
    """
    from app.db.supabase_client import insert_claims
    
    # Build prompt with all sources labeled by ID
    sources_text = ""
    for idx, source in enumerate(sources):
        source_id = source.get("id")
        title = source.get("title", "")
        snippet = source.get("snippet", "")
        text = f"{title}\n{snippet}".strip()
        
        sources_text += f"\n[SOURCE_{source_id}]\n{text}\n"
    
    # Mock mode
    if settings.mock_mode:
        await asyncio.sleep(0.1)
        results = {}
        for source in sources:
            source_id = source.get("id")
            mock_claims = [
                {
                    "claim": f"Mock claim 1 from source {source_id}",
                    "confidence": 0.9,
                    "source_id": source_id,
                    "session_id": session_id
                },
                {
                    "claim": f"Mock claim 2 from source {source_id}",
                    "confidence": 0.7,
                    "source_id": source_id,
                    "session_id": session_id
                }
            ]
            results[source_id] = mock_claims
            
            # Insert into DB
            await insert_claims(mock_claims, session_id)
        
        return results
    
    # Real mode: single LLM call for all sources
    prompt = f"""You are a fact-extraction engine. Extract up to 3 verifiable factual claims from EACH source below. Return JSON with claims grouped by source ID.

Sources:
{sources_text}

Return ONLY valid JSON in this format:
{{
  "claims_by_source": {{
    "SOURCE_ID_1": [{{"claim": "...", "confidence": 0.9}}],
    "SOURCE_ID_2": [{{"claim": "...", "confidence": 0.85}}]
  }}
}}

Rules:
- Extract ONLY factual, verifiable claims
- Each claim must be self-contained
- Assign confidence 0-1 based on how verifiable the claim is
- Use the exact source IDs from above (e.g., "644", "645")"""
    
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
        claims_by_source = data.get("claims_by_source", {})
        
        # Process and store claims
        results = {}
        for source in sources:
            source_id = source.get("id")
            source_id_str = str(source_id)
            raw_claims = claims_by_source.get(source_id_str, [])
            
            # Process claims
            processed_claims = []
            for claim_data in raw_claims:
                confidence = max(0.0, min(1.0, float(claim_data.get("confidence", 0.5))))
                source_cred = source.get("credibility_score", 50.0)
                adjusted_confidence = confidence * (source_cred / 100.0)
                
                # Embed claim
                embedding = await embed_claim(claim_data["claim"])
                
                claim_record = {
                    "claim": claim_data["claim"],
                    "confidence": adjusted_confidence,
                    "source_id": source_id,
                    "session_id": session_id,
                    "embedding": embedding
                }
                processed_claims.append(claim_record)
            
            # Insert into DB
            if processed_claims:
                await insert_claims(processed_claims, session_id)
            
            results[source_id] = processed_claims
        
        return results
    
    except Exception as e:
        logger.error(f"Batched claim extraction failed: {e}")
        # Return empty results for all sources
        return {source.get("id"): [] for source in sources}
    
    return summary
