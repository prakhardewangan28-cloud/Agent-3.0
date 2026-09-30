"""Query refinement service for clarifying vague or ambiguous queries.

This is the third differentiator: prevent wasted API calls by detecting
vague queries and offering precise research directions BEFORE running
the full pipeline.
"""
import json
import logging
from typing import Dict, Any, List

from app.config import settings
from app.services.gemini_client import generate

logger = logging.getLogger(__name__)


# Ambiguous single-word patterns (whole query matches only)
AMBIGUOUS_WORDS = {
    "apple", "python", "java", "mercury", "jaguar",
    "amazon", "tesla", "meta", "spring", "rust"
}


# ============================================================================
# FUNCTION 1 — Detect if a query is vague
# ============================================================================

async def is_vague(query: str) -> bool:
    """
    Determine if a query is vague and needs refinement.
    
    Uses rule-based heuristics and LLM classification to detect:
    - Single-word ambiguous terms
    - Very short queries
    - Queries with multiple plausible interpretations
    
    Args:
        query: User's search query
    
    Returns:
        True if query needs refinement, False if specific enough
    
    Examples:
        >>> await is_vague("apple")
        True
        >>> await is_vague("What are the health benefits of eating apples daily?")
        False
    """
    query = query.strip()
    
    logger.info(f"Checking if query is vague: {query[:50]}...")
    
    # Too short to judge reliably
    if len(query) < 3:
        return False
    
    # CHANGE 3: Rule-based pre-check to avoid LLM calls
    word_count = len(query.split())
    query_lower = query.lower()
    
    # Rule 1: Single word or two words → definitely vague
    if word_count <= 2:
        logger.info(f"Query classified as vague: True (only {word_count} words, no LLM call)")
        return True
    
    # Rule 2: Contains question word + enough words → probably specific
    question_words = ["compare", "what", "how", "why", "when", "which", "explain", "who", "where"]
    has_question_word = any(qw in query_lower for qw in question_words)
    
    # Check for ambiguous single-word terms that might be the whole query
    ambiguous_terms = ["apple", "jaguar", "python", "mercury", "spring", "bank", "mouse"]
    is_ambiguous_term = any(term == query_lower for term in ambiguous_terms)
    
    if word_count >= 6 and has_question_word and not is_ambiguous_term:
        logger.info(
            f"Query classified as specific: True "
            f"(>= 6 words, has question word, no LLM call)"
        )
        return False
    
    # Mock mode: simple word count rule
    if settings.mock_mode:
        result = word_count < 6
        logger.info(f"Query classified as vague: {result} (MOCK MODE, word count: {word_count})")
        return result
    
    # Edge case: Need LLM to decide
    logger.info(f"Edge case detected, calling LLM to decide (word_count={word_count})")
    
    # Real mode: use LLM
    prompt = f"""You are a query clarity classifier. Determine if the user's query is specific enough to research directly, or if it needs clarification.

User query: "{query}"

A query is VAGUE if:
- It has multiple plausible interpretations
- It lacks a specific angle, timeframe, or scope
- It could refer to entirely different topics

A query is SPECIFIC if:
- It has one clear research direction
- It names specific entities, comparisons, or questions

Return ONLY this JSON:
{{"is_vague": true, "reason": "one-sentence explanation"}}"""
    
    try:
        response = await generate(prompt)
        result = _parse_vagueness_json(response)
        is_vague_result = result.get("is_vague", False)
        
        logger.info(f"Query classified as vague: {is_vague_result}")
        return is_vague_result
        
    except (json.JSONDecodeError, ValueError) as e:
        # Retry once
        logger.warning(f"Initial vagueness check failed: {e}. Retrying...")
        
        strict_prompt = f"""Return ONLY JSON, no markdown.

Is this query vague or specific: "{query}"

Format: {{"is_vague": true, "reason": "explanation"}}"""
        
        try:
            response = await generate(strict_prompt)
            result = _parse_vagueness_json(response)
            is_vague_result = result.get("is_vague", False)
            
            logger.info(f"Query classified as vague: {is_vague_result} (after retry)")
            return is_vague_result
            
        except Exception as retry_error:
            # Fall back to word count rule
            logger.error(f"Vagueness check failed after retry: {retry_error}. Using fallback.")
            result = word_count < 6
            logger.info(f"Query classified as vague: {result} (fallback)")
            return result


def _parse_vagueness_json(response: str) -> Dict[str, Any]:
    """Parse JSON from vagueness check response."""
    response = response.strip()
    
    # Remove markdown code blocks
    if response.startswith("```"):
        lines = response.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response = "\n".join(lines).strip()
    
    # Parse JSON
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        # Try to extract JSON
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            response = response[start:end]
            data = json.loads(response)
        else:
            raise e
    
    # Validate required key
    if "is_vague" not in data:
        raise ValueError("Missing 'is_vague' key in response")
    
    return data


# ============================================================================
# FUNCTION 2 — Generate refinement directions
# ============================================================================

async def generate_refinements(query: str) -> List[Dict[str, Any]]:
    """
    Generate precise research directions for a vague query.
    
    Creates 4-5 specific, researchable questions that clarify different
    angles the user might be interested in.
    
    Args:
        query: The vague query to refine
    
    Returns:
        List of direction dicts with keys: direction, rationale, type
    
    Examples:
        >>> directions = await generate_refinements("apple")
        >>> len(directions) >= 4
        True
        >>> all("direction" in d for d in directions)
        True
    """
    logger.info(f"Generating refinements for query: {query[:50]}...")
    
    # Mock mode: return fake directions
    if settings.mock_mode:
        directions = [
            {
                "direction": f"{query} — academic perspective",
                "rationale": "Mock direction 1",
                "type": "academic"
            },
            {
                "direction": f"{query} — industry perspective",
                "rationale": "Mock direction 2",
                "type": "industry"
            },
            {
                "direction": f"{query} — policy perspective",
                "rationale": "Mock direction 3",
                "type": "policy"
            },
            {
                "direction": f"{query} — historical context",
                "rationale": "Mock direction 4",
                "type": "context"
            }
        ]
        logger.info(f"Generated {len(directions)} refinement directions (MOCK MODE)")
        return directions
    
    # Real mode: use LLM
    prompt = f"""The user asked a vague query: "{query}"

Generate 4-5 precise research directions that clarify what they might mean. Each direction should be a specific, researchable question that could be answered with sources.

Return ONLY this JSON:
{{"directions": [
    {{"direction": "specific researchable question",
     "rationale": "why this angle matters",
     "type": "academic" | "industry" | "policy" | "context" | "comparison"}},
    ...
]}}"""
    
    try:
        response = await generate(prompt)
        result = _parse_refinements_json(response)
        directions = result.get("directions", [])
        
    except (json.JSONDecodeError, ValueError) as e:
        # Retry once
        logger.warning(f"Initial refinement generation failed: {e}. Retrying...")
        
        strict_prompt = f"""Return ONLY JSON, no markdown.

Generate 4 research directions for: "{query}"

Format: {{"directions": [{{"direction": "question", "rationale": "why", "type": "academic"}}]}}"""
        
        try:
            response = await generate(strict_prompt)
            result = _parse_refinements_json(response)
            directions = result.get("directions", [])
            
        except Exception as retry_error:
            # Fall back to generic option
            logger.error(f"Refinement generation failed after retry: {retry_error}. Using fallback.")
            directions = [{
                "direction": query,
                "rationale": "Retry with your original query",
                "type": "context"
            }]
    
    # Cap at 5 directions
    directions = directions[:5]
    
    logger.info(f"Generated {len(directions)} refinement directions")
    return directions


def _parse_refinements_json(response: str) -> Dict[str, Any]:
    """Parse JSON from refinements response."""
    response = response.strip()
    
    # Remove markdown code blocks
    if response.startswith("```"):
        lines = response.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response = "\n".join(lines).strip()
    
    # Parse JSON
    try:
        data = json.loads(response)
    except json.JSONDecodeError as e:
        # Try to extract JSON
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            response = response[start:end]
            data = json.loads(response)
        else:
            raise e
    
    # Validate required key
    if "directions" not in data:
        raise ValueError("Missing 'directions' key in response")
    
    return data


# ============================================================================
# FUNCTION 3 — Orchestrate
# ============================================================================

async def refine_or_proceed(query: str) -> Dict[str, Any]:
    """
    Determine if a query needs refinement and provide options if so.
    
    This is the main entry point for the refinement service. It checks
    if a query is vague and either:
    - Returns the query as-is if specific enough
    - Returns refinement options if vague
    
    Args:
        query: User's search query
    
    Returns:
        Dict with keys:
        - needs_refinement (bool): Whether query needs clarification
        - proceed_with (str|None): Query to use if specific
        - options (list): Refinement directions if vague
        - original_query (str): Original query (only if vague)
    
    Examples:
        >>> result = await refine_or_proceed("What is climate change?")
        >>> result["needs_refinement"]
        False
        >>> result = await refine_or_proceed("apple")
        >>> result["needs_refinement"]
        True
        >>> len(result["options"]) >= 4
        True
    """
    vague = await is_vague(query)
    
    if not vague:
        return {
            "needs_refinement": False,
            "proceed_with": query,
            "options": []
        }
    
    # Query is vague, generate refinements
    options = await generate_refinements(query)
    
    return {
        "needs_refinement": True,
        "proceed_with": None,
        "options": options,
        "original_query": query
    }
