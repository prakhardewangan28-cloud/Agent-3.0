"""Centralized Gemini client using google-genai SDK (supports AQ. keys)."""
import logging
import asyncio
import random
from google import genai
from app.config import settings

logger = logging.getLogger(__name__)

_client = None


def get_client() -> genai.Client:
    """Get or create the Gemini client singleton."""
    global _client
    if _client is None:
        if settings.mock_mode:
            logger.info("🧪 Gemini client in MOCK MODE - no real API calls")
            return None
        _client = genai.Client(api_key=settings.gemini_api_key)
        logger.info("Gemini client initialized with key prefix: %s...",
                    settings.gemini_api_key[:6])
    return _client


async def generate(prompt: str, model: str = "gemini-3.6-flash") -> str:
    """Generate text using Gemini.
    
    Args:
        prompt: The input prompt
        model: Model to use (default: gemini-3.6-flash)
        
    Returns:
        Generated text response
    """
    if settings.mock_mode:
        await asyncio.sleep(0.1)  # simulate latency
        return '{"claims": [{"claim": "Mock claim 1", "confidence": 0.9}, {"claim": "Mock claim 2", "confidence": 0.7}]}'
    
    # Real implementation
    client = get_client()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
    )
    return response.text


async def embed(text: str, dim: int = 1536) -> list[float]:
    """Generate embeddings using Gemini.
    
    Args:
        text: Text to embed
        dim: Output dimensionality (default: 1536)
        
    Returns:
        List of embedding values
    """
    if settings.mock_mode:
        await asyncio.sleep(0.05)
        return [random.random() for _ in range(dim)]
    
    # Real implementation
    client = get_client()
    result = client.models.embed_content(
        model="text-embedding-004",
        contents=text,
        config={"output_dimensionality": dim},
    )
    return result.embeddings[0].values

