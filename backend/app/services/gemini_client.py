"""Centralized Gemini client using google-genai SDK (supports AQ. keys)."""
import logging
import asyncio
import random
from google import genai
from google.genai.errors import ClientError
from app.config import settings

logger = logging.getLogger(__name__)

_client = None
_session_call_count = 0
_SESSION_MAX_CALLS = 5


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


def reset_session_counter():
    """Reset the session call counter. Call at the start of run_research()."""
    global _session_call_count
    _session_call_count = 0
    logger.info("Session call counter reset")


def _mock_generate_response(prompt: str) -> str:
    """Generate a mock response for when quota is exceeded."""
    # Try to infer what kind of response is expected from the prompt
    prompt_lower = prompt.lower()
    
    if "claims" in prompt_lower or "extract" in prompt_lower:
        return '{"claims": [{"claim": "Mock claim 1", "confidence": 0.9}, {"claim": "Mock claim 2", "confidence": 0.7}]}'
    elif "conflict" in prompt_lower or "relationship" in prompt_lower:
        # Check if it's batched judgment
        if "judgments" in prompt_lower or "pair_id" in prompt_lower:
            return '{"judgments": [{"pair_id": 1, "claim_a_id": 1, "claim_b_id": 2, "relationship": "contradiction", "confidence": 0.8, "explanation": "Mock conflict"}]}'
        else:
            return '{"relationship": "contradiction", "explanation": "Mock agreement", "confidence": 0.8}'
    elif "vague" in prompt_lower or "specific" in prompt_lower:
        return '{"is_vague": false, "reasoning": "Query is specific enough"}'
    elif "counter" in prompt_lower or "opposing" in prompt_lower:
        return '{"strength": "weak", "explanation": "Mock counter-argument", "supporting_sources": []}'
    elif "landscape" in prompt_lower or "classify" in prompt_lower:
        return '{"consensus": [], "contested": [], "unknowns": []}'
    elif "report" in prompt_lower:
        return "# Mock Research Report\n\nThis is a mock report generated after quota limit."
    else:
        return '{"result": "Mock response due to quota limit"}'


async def generate(prompt: str, model: str = "gemini-1.5-flash-002") -> str:
    """Generate text using Gemini with session quota management.
    
    Args:
        prompt: The input prompt
        model: Model to use (default: gemini-1.5-flash-002 for better stability)
        
    Returns:
        Generated text response
        
    Note:
        - Uses session call counter to stay under free-tier limits
        - Falls back to mock after _SESSION_MAX_CALLS per session
        - Retries on 429 with exponential backoff
    """
    global _session_call_count
    
    if settings.mock_mode:
        await asyncio.sleep(0.1)  # simulate latency
        return _mock_generate_response(prompt)
    
    # Check session quota
    if _session_call_count >= _SESSION_MAX_CALLS:
        logger.warning(
            f"Session call cap reached ({_session_call_count}/{_SESSION_MAX_CALLS}), "
            f"using mock response"
        )
        return _mock_generate_response(prompt)
    
    # Increment counter
    _session_call_count += 1
    logger.info(f"LLM call {_session_call_count}/{_SESSION_MAX_CALLS}")
    
    # Real implementation with retry logic
    client = get_client()
    
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
            )
            return response.text
            
        except ClientError as e:
            error_str = str(e)
            
            # Handle 429 rate limit
            if "429" in error_str and attempt < 2:
                wait_time = 15 * (attempt + 1)  # 15s, 30s
                logger.warning(
                    f"429 rate limit hit (attempt {attempt + 1}/3), "
                    f"waiting {wait_time}s before retry"
                )
                await asyncio.sleep(wait_time)
                continue
            
            # Handle model not available (try fallback)
            elif "404" in error_str or "not found" in error_str.lower():
                # Try different model variants in order
                fallback_models = ["gemini-1.5-flash-002", "gemini-1.5-flash", "gemini-1.5-pro"]
                if model not in fallback_models and attempt < 2:
                    next_model = fallback_models[min(attempt, len(fallback_models) - 1)]
                    logger.warning(f"{model} not available, falling back to {next_model}")
                    model = next_model
                    continue
                else:
                    logger.error(f"All model fallbacks failed, using mock")
                    return _mock_generate_response(prompt)
            
            # Other errors or final attempt
            else:
                logger.error(f"Gemini API error after {attempt + 1} attempts: {e}")
                # Fall back to mock on final failure
                if attempt == 2:
                    logger.warning("All retries failed, using mock response")
                    return _mock_generate_response(prompt)
                raise
        
        except Exception as e:
            logger.error(f"Unexpected error in generate(): {e}")
            if attempt == 2:
                logger.warning("Unexpected error, using mock response")
                return _mock_generate_response(prompt)
            raise
    
    # Should never reach here, but just in case
    return _mock_generate_response(prompt)


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
    # Use models/gemini-embedding-001 — the stable embedding model available
    # via the google-genai SDK for AQ. keys. text-embedding-004 is not
    # supported on the v1beta endpoint used by this SDK version.
    client = get_client()
    result = client.models.embed_content(
        model="models/gemini-embedding-001",
        contents=text,
        config={"output_dimensionality": dim},
    )
    return result.embeddings[0].values

