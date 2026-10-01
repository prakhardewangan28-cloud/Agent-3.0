"""Counter-argument generation service.

Generates the strongest possible counter-argument against a research report's
main conclusion, citing only sources that were retrieved during the session.
"""
import json
import logging
from typing import Dict, Any, List

from app.config import settings
from app.services.gemini_client import generate
from app.db.neon_client import get_sources_by_session

logger = logging.getLogger(__name__)


# ============================================================================
# COUNTER-ARGUMENT GENERATION
# ============================================================================

async def generate_counter_argument(
    session_id: str,
    final_report: str,
    landscape: dict,
) -> dict:
    """
    Generate the strongest possible counter-argument against the report's conclusion.
    
    Given the final report and the information landscape, generates a counter-argument
    that cites only sources that were already retrieved in the session.
    
    Args:
        session_id: UUID of the research session
        final_report: The generated markdown report
        landscape: Classified information landscape (consensus/contested/unknown)
    
    Returns:
        Dict with keys:
        - counter_argument (str): 3-5 sentence counter-argument
        - supporting_sources (List[Dict]): Sources supporting the counter-argument
        - strength (str): "strong" | "moderate" | "weak" | "none"
        - explanation (str): Why this rating was given
    
    Examples:
        >>> result = await generate_counter_argument("uuid", "report...", {})
        >>> result["strength"] in ["strong", "moderate", "weak", "none"]
        True
        >>> isinstance(result["supporting_sources"], list)
        True
    """
    logger.info(f"Generating counter-argument for session {session_id}")
    
    # Fetch sources for the session
    try:
        sources = await get_sources_by_session(session_id)
    except Exception as e:
        logger.error(f"Failed to fetch sources for session {session_id}: {e}")
        return {
            "counter_argument": "",
            "supporting_sources": [],
            "strength": "none",
            "explanation": "Failed to retrieve sources for counter-argument generation.",
        }
    
    # No sources available
    if not sources:
        logger.info(f"No sources available for session {session_id}")
        return {
            "counter_argument": "",
            "supporting_sources": [],
            "strength": "none",
            "explanation": "No sources available to construct a counter-argument.",
        }
    
    # Mock mode: return mock counter-argument
    if settings.is_llm_mocked:
        mock_result = {
            "counter_argument": (
                "Mock counter-argument: some sources suggest alternative "
                "interpretations that challenge the main conclusion."
            ),
            "supporting_sources": [
                {
                    "source_id": s["id"],
                    "url": s["url"],
                    "domain": s["domain"],
                    "credibility_score": s.get("credibility_score", 0.5) * 100,  # Convert 0-1 to 0-100
                    "reason": "Mock supporting source",
                }
                for s in sources[:2]
            ],
            "strength": "moderate",
            "explanation": "Mock mode always returns moderate strength.",
        }
        logger.debug(f"MOCK MODE: Returning mock counter-argument with {len(mock_result['supporting_sources'])} sources")
        return mock_result
    
    # Real mode: call Gemini
    formatted_sources = _format_sources_for_prompt(sources)
    
    prompt = f"""You are a critical reasoning engine. Construct the STRONGEST POSSIBLE counter-argument against the main conclusion of the report below. Be intellectually honest — not a strawman.

REPORT:
---
{final_report}
---

AVAILABLE SOURCES:
{formatted_sources}

Rules:
- Cite specific sources by their ID when they support the counter
- If no sources support a counter-argument, say so explicitly
- Rate strength honestly:
    "strong"  = credible sources directly contradict the conclusion
    "moderate"= sources suggest alternative interpretations
    "weak"    = counter is speculative
    "none"    = no basis for a counter-argument

Return ONLY this JSON, no extra text:
{{
  "counter_argument": "3-5 sentences...",
  "supporting_source_ids": [1, 3],
  "strength": "moderate",
  "explanation": "why this rating"
}}"""
    
    try:
        response = await generate(prompt)
        result = _parse_counter_argument_json(response, sources)
        logger.info(f"Counter-argument strength: {result['strength']}, sources: {len(result['supporting_sources'])}")
        return result
        
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        # Retry with stricter prompt
        logger.warning(f"Initial counter-argument generation failed: {e}. Retrying with strict prompt...")
        
        strict_prompt = f"""Return ONLY JSON. No markdown. No explanation.

Construct a counter-argument against this report using these sources:

REPORT:
{final_report[:500]}...

SOURCES:
{formatted_sources[:500]}...

Format:
{{
  "counter_argument": "...",
  "supporting_source_ids": [1],
  "strength": "moderate",
  "explanation": "..."
}}"""
        
        try:
            response = await generate(strict_prompt)
            result = _parse_counter_argument_json(response, sources)
            logger.info(f"Counter-argument strength: {result['strength']}, sources: {len(result['supporting_sources'])}")
            return result
            
        except Exception as retry_error:
            logger.warning(f"Counter-argument generation failed: {retry_error}")
            return {
                "counter_argument": "",
                "supporting_sources": [],
                "strength": "none",
                "explanation": "Counter-argument generation failed.",
            }
    
    except Exception as e:
        logger.warning(f"Counter-argument generation failed: {e}")
        return {
            "counter_argument": "",
            "supporting_sources": [],
            "strength": "none",
            "explanation": "Counter-argument generation failed.",
        }


def _format_sources_for_prompt(sources: List[Dict[str, Any]]) -> str:
    """
    Format sources for inclusion in the LLM prompt.
    
    Args:
        sources: List of source dicts from database
    
    Returns:
        Formatted string with source information
    """
    formatted = []
    for s in sources:
        source_id = s.get("id", "?")
        domain = s.get("domain", "unknown")
        credibility = s.get("credibility_score", 0.0)
        title = s.get("title", "No title")
        formatted.append(f"[{source_id}] {domain} (credibility: {credibility:.1f}): {title}")
    
    return "\n".join(formatted)


def _parse_counter_argument_json(
    response: str,
    sources: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Parse the LLM response JSON and map source IDs to full source objects.
    
    Args:
        response: Raw LLM response (may contain markdown or extra text)
        sources: List of available sources for the session
    
    Returns:
        Dict with counter_argument, supporting_sources, strength, explanation
    
    Raises:
        ValueError: If JSON is invalid or missing required keys
        json.JSONDecodeError: If response is not valid JSON
    """
    # Strip markdown code blocks if present
    cleaned = response.strip()
    if cleaned.startswith("```"):
        # Remove opening ```json or ```
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    
    cleaned = cleaned.strip()
    
    # Parse JSON
    data = json.loads(cleaned)
    
    # Validate required keys
    required_keys = ["counter_argument", "supporting_source_ids", "strength", "explanation"]
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"Missing required keys: {missing}")
    
    # Validate strength value
    valid_strengths = ["strong", "moderate", "weak", "none"]
    if data["strength"] not in valid_strengths:
        logger.warning(f"Invalid strength '{data['strength']}', defaulting to 'moderate'")
        data["strength"] = "moderate"
    
    # Map source IDs to full source objects
    source_id_map = {s["id"]: s for s in sources}
    supporting_sources = []
    
    for source_id in data["supporting_source_ids"]:
        if source_id in source_id_map:
            s = source_id_map[source_id]
            # Convert credibility_score from 0-1 (database) to 0-100 (display)
            cred_score = s.get("credibility_score", 0.0)
            if isinstance(cred_score, (int, float)) and cred_score <= 1.0:
                cred_score = cred_score * 100
            
            supporting_sources.append({
                "source_id": s["id"],
                "url": s["url"],
                "domain": s.get("domain", "unknown"),
                "credibility_score": cred_score,
                "reason": f"Cited in counter-argument",
            })
        else:
            logger.warning(f"Source ID {source_id} not found in session sources, skipping")
    
    return {
        "counter_argument": data["counter_argument"],
        "supporting_sources": supporting_sources,
        "strength": data["strength"],
        "explanation": data["explanation"],
    }
