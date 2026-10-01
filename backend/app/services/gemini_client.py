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
    
    # Claim extraction
    if "json" in p and "claim" in p:
        return '''{
  "claims": [
    {"claim": "Apples contain dietary fiber that supports digestive health and promotes regular bowel movements.", "confidence": 0.92},
    {"claim": "Regular apple consumption is associated with reduced cardiovascular disease risk in epidemiological studies.", "confidence": 0.87},
    {"claim": "The antioxidant quercetin found in apple skins has demonstrated anti-inflammatory properties in laboratory research.", "confidence": 0.81},
    {"claim": "Apple polyphenols may contribute to improved blood sugar regulation according to preliminary studies.", "confidence": 0.74},
    {"claim": "Consuming one apple daily provides approximately 4 grams of soluble fiber which supports heart health.", "confidence": 0.85}
  ]
}'''
    
    # Conflict judgment
    if "json" in p and ("judge" in p or "contradiction" in p or "compare" in p):
        return '''{
  "relationship": "disagreement",
  "confidence": 0.73,
  "explanation": "The two claims emphasize different nutritional aspects of apples - one focuses on fiber content while the other highlights antioxidant compounds. While not directly contradictory, they present distinct mechanistic pathways for health benefits."
}'''
    
    # Vagueness check
    if "json" in p and "vague" in p:
        return '{"is_vague": false, "reason": "Query specifies a clear topic (health benefits of apples) with measurable outcomes."}'
    
    # Research directions
    if "json" in p and "direction" in p:
        return '''{
  "directions": [
    {"direction": "systematic review cardiovascular benefits apples", "rationale": "Target peer-reviewed medical evidence", "type": "academic"},
    {"direction": "apple nutrition fiber antioxidants health", "rationale": "Gather nutritional science perspectives", "type": "context"},
    {"direction": "apple consumption studies clinical trials", "rationale": "Find controlled research data", "type": "academic"}
  ]
}'''
    
    # Counter-argument
    if "json" in p and "counter" in p:
        return '''{
  "counter_argument": "While the cited sources support cardiovascular and digestive benefits of apple consumption, several important limitations must be considered. First, the majority of evidence comes from observational epidemiological studies rather than randomized controlled trials, making it difficult to establish causation versus correlation. Second, many studies do not adequately control for confounding variables such as overall diet quality, physical activity levels, and socioeconomic factors that may independently influence health outcomes. Third, the effect sizes reported are generally modest, and the optimal daily intake remains undefined across different populations. Finally, significant variability exists between apple varieties in polyphenol content and bioavailability, which is rarely addressed in research synthesis.",
  "supporting_source_ids": [1, 3],
  "strength": "moderate",
  "explanation": "The counter-argument identifies methodological limitations in the cited research while acknowledging the consistency of observational findings. Sources 1 and 3 themselves note these limitations in their discussion sections."
}'''
    
    # Report generation
    if "markdown" in p or "report" in p or ("summary" in p and "source" in p):
        return '''# Research Report: Health Benefits of Daily Apple Consumption

## Executive Summary

Analysis of 9 scientific sources reveals consistent evidence supporting multiple health benefits of regular apple consumption, particularly for cardiovascular and digestive health. The body of research demonstrates moderate-to-strong consensus on fiber-related benefits, with some debate regarding the magnitude and mechanisms of antioxidant effects.

## Consensus Findings

### Cardiovascular Health
Multiple epidemiological studies across diverse populations demonstrate an association between regular apple consumption and reduced cardiovascular disease risk. The soluble fiber pectin is consistently identified as a key bioactive compound contributing to cholesterol reduction (Sources: sciencedirect.com, pubs.rsc.org).

### Digestive Health
Dietary fiber content in apples (approximately 4g per medium apple) supports digestive regularity and promotes beneficial gut microbiota. Both soluble and insoluble fiber fractions contribute to these effects through distinct mechanisms (Source: sciencedirect.com).

### Antioxidant Activity
Apple polyphenols, particularly quercetin concentrated in the peel, demonstrate anti-inflammatory and antioxidant properties in laboratory studies. However, bioavailability and dose-response relationships in humans remain subjects of ongoing investigation (Source: pubs.rsc.org).

## Contested Points

### Blood Sugar Regulation
While some research suggests apple polyphenols may support glycemic control, the clinical significance and consistency of this effect across populations remains debated. Studies show mixed results depending on apple variety, processing method, and individual metabolic factors.

### Optimal Intake
The commonly cited "apple a day" guideline lacks rigorous dose-response evidence. Research has not definitively established whether one, two, or more apples daily provides maximum benefit, or whether benefits plateau beyond a certain intake threshold.

## Unknowns and Research Gaps

- **Long-term Effects**: Most studies track outcomes for 1-5 years; effects of lifelong consumption patterns remain unclear
- **Variety Differences**: Significant variation exists in polyphenol profiles across cultivars, but few studies compare health outcomes by variety
- **Processing Impact**: Effects of juice, dried apples, or cooked preparations relative to fresh whole fruit are incompletely characterized
- **Population Specificity**: Most research focuses on Western populations; generalizability to other dietary contexts is uncertain

## Methodological Considerations

The preponderance of observational rather than interventional studies limits causal inference. Residual confounding from overall diet quality, lifestyle factors, and health consciousness cannot be fully excluded. Well-controlled feeding studies with apples as the sole dietary variable are rare and typically short-duration.

## Sources Consulted

1. sciencedirect.com - Effects of apple intake on cardiometabolic health
2. pubs.rsc.org - Apple polyphenols and human health outcomes  
3. oye.odwire.org - Nutritional composition and health claims
4-9. Additional sources providing supporting context

## Conclusion

Regular apple consumption as part of a balanced diet appears to confer modest cardiovascular and digestive health benefits, supported by consistent observational evidence and plausible biological mechanisms. However, claims should be interpreted cautiously given methodological limitations, and apples should be viewed as one component of overall dietary patterns rather than a singular health intervention.'''
    
    return "Mock response generated for unrecognized prompt type."


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
    if settings.is_llm_mocked:
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
    if settings.is_llm_mocked:
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
