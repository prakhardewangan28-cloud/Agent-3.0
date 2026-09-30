"""Gemini client using direct HTTP with x-goog-api-key header auth.

The AQ. API keys require x-goog-api-key header authentication,
not Bearer token auth or query parameters.
"""
import asyncio
import logging
import httpx
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_MODEL = "gemini-flash-latest"  # Alias for latest Gemini Flash (currently 2.5)
EMBEDDING_MODEL = "gemini-embedding-2"

# Session-scoped LLM call counter to stay under free-tier quota
_session_call_count = 0
_SESSION_MAX_CALLS = 5


def reset_session_counter() -> None:
    """Reset the session call counter."""
    global _session_call_count
    _session_call_count = 0
    logger.info("Session LLM call counter reset")


def get_session_call_count() -> int:
    """Get current session call count."""
    return _session_call_count


def _mock_response_for_prompt(prompt: str) -> str:
    """Return a realistic mock response based on prompt type."""
    p = prompt.lower()
    
    if "json" in p and "claim" in p:
        return '{"claims": [{"claim": "Mock claim 1", "confidence": 0.9}, {"claim": "Mock claim 2", "confidence": 0.75}]}'
    
    if "json" in p and ("judge" in p or "contradiction" in p or "compare" in p):
        return '{"relationship": "disagreement", "confidence": 0.7, "explanation": "Mock judgment"}'
    
    if "json" in p and "vague" in p:
        return '{"is_vague": false, "reason": "Mock classification"}'
    
    if "json" in p and "direction" in p:
        return '{"directions": [{"direction": "Mock direction 1", "rationale": "r1", "type": "context"}]}'
    
    if "json" in p and "counter" in p:
        return '{"counter_argument": "Mock counter-argument.", "supporting_source_ids": [1], "strength": "moderate", "explanation": "Mock"}'
    
    return "# Mock Report\n\nThis is a mock generated report."


async def generate(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Generate text using Gemini via x-goog-api-key header.
    
    Args:
        prompt: The input prompt
        model: Model to use (default: gemini-flash-latest)
        
    Returns:
        Generated text response
        
    Note:
        Uses x-goog-api-key header authentication for AQ. API keys.
        Falls back to mock after session limit or on errors.
    """
    global _session_call_count
    
    # Mock mode
    if settings.mock_mode:
        await asyncio.sleep(0.05)
        return _mock_response_for_prompt(prompt)
    
    # Check session quota
    if _session_call_count >= _SESSION_MAX_CALLS:
        logger.warning(f"Session LLM call cap ({_SESSION_MAX_CALLS}) reached, using mock")
        return _mock_response_for_prompt(prompt)
    
    # Build URL and headers - AQ. keys use x-goog-api-key header
    url = f"{BASE_URL}/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": settings.gemini_api_key
    }
    
    body = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    # Retry logic with backoff
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                r = await client.post(url, json=body, headers=headers)
            
            # Handle rate limiting
            if r.status_code == 429:
                if attempt < 2:
                    wait = 15 * (attempt + 1)
                    logger.warning(f"429 rate limit, waiting {wait}s (attempt {attempt + 1}/3)")
                    await asyncio.sleep(wait)
                    continue
                logger.warning("Rate limit exhausted after retries, falling back to mock")
                return _mock_response_for_prompt(prompt)
            
            # Handle 404 model not found
            if r.status_code == 404:
                logger.error(f"Model {model} not found")
                return _mock_response_for_prompt(prompt)
            
            # Raise for other HTTP errors
            r.raise_for_status()
            
            # Parse response
            data = r.json()
            _session_call_count += 1
            logger.info(f"LLM call {_session_call_count}/{_SESSION_MAX_CALLS} successful")
            
            return data["candidates"][0]["content"]["parts"][0]["text"]
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Gemini HTTP error (attempt {attempt + 1}/3): "
                f"{e.response.status_code} {e.response.text[:200]}"
            )
            if attempt == 2:
                logger.warning("All HTTP retries failed, falling back to mock")
                return _mock_response_for_prompt(prompt)
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Gemini call failed (attempt {attempt + 1}/3): {e}")
            if attempt == 2:
                logger.warning("All retries failed, falling back to mock")
                return _mock_response_for_prompt(prompt)
            await asyncio.sleep(2)
    
    return _mock_response_for_prompt(prompt)


async def embed(text: str, dim: int = 1536) -> list[float]:
    """Generate embeddings using Gemini via x-goog-api-key header.
    
    Args:
        text: Text to embed
        dim: Output dimensionality (default: 1536)
        
    Returns:
        List of embedding values
        
    Note:
        Uses x-goog-api-key header authentication for AQ. API keys.
        Embedding quota is separate from generation quota.
    """
    if settings.mock_mode:
        # Deterministic mock embeddings based on text hash
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in (h * (dim // 32 + 1))[:dim]]
    
    # Build URL and headers - AQ. keys use x-goog-api-key header
    url = f"{BASE_URL}/models/{EMBEDDING_MODEL}:embedContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": settings.gemini_api_key
    }
    
    body = {
        "model": f"models/{EMBEDDING_MODEL}",
        "content": {
            "parts": [{"text": text}]
        },
        "outputDimensionality": dim
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=body, headers=headers)
            r.raise_for_status()
            data = r.json()
            return data["embedding"]["values"]
            
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        # Fall back to mock
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in (h * (dim // 32 + 1))[:dim]]
