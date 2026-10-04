"""SerpAPI service for web search functionality."""
from serpapi import GoogleSearch
from typing import Dict, Any, List
from urllib.parse import urlparse
import asyncio
import time
import logging

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# CUSTOM EXCEPTIONS
# ============================================================================

class SerpApiAuthError(Exception):
    """Raised when SerpAPI returns an authentication error."""
    pass


class SerpApiRateLimitError(Exception):
    """Raised when SerpAPI rate limit is exceeded after retries."""
    pass


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def extract_domain(url: str) -> str:
    """
    Extract domain from URL without 'www.' prefix.
    
    Args:
        url: Full URL string
        
    Returns:
        Domain string without www. prefix, or empty string if invalid
    """
    if not url:
        return ""
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Remove www. prefix if present
        if domain.startswith("www."):
            domain = domain[4:]
        
        return domain
    except Exception:
        return ""


def normalize_result(raw: Dict[str, Any], engine: str) -> Dict[str, Any]:
    """
    Normalize a raw SerpAPI result into consistent format.
    
    Args:
        raw: Raw result dict from SerpAPI
        engine: Engine type (google, news, scholar)
        
    Returns:
        Normalized dict with keys: url, title, snippet, domain, engine, published_date
    """
    # Extract URL (SerpAPI uses 'link' field)
    url = raw.get("link", "")
    
    # Extract title
    title = raw.get("title", "")
    
    # Extract snippet (varies by engine)
    snippet = raw.get("snippet", "")
    if not snippet and engine == "scholar":
        # Scholar may have snippet in publication_info
        pub_info = raw.get("publication_info", {})
        if isinstance(pub_info, dict):
            snippet = pub_info.get("summary", "")
    
    # Extract domain from URL
    domain = extract_domain(url)
    
    # Extract published date (mainly for news)
    published_date = None
    if engine == "news":
        published_date = raw.get("date")
    elif engine == "scholar":
        # Scholar may have year in publication_info
        pub_info = raw.get("publication_info", {})
        if isinstance(pub_info, dict):
            published_date = pub_info.get("summary")  # Contains year info
    
    return {
        "url": url,
        "title": title,
        "snippet": snippet,
        "domain": domain,
        "engine": engine,
        "published_date": published_date,
    }


async def _run_serpapi(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute SerpAPI search with async wrapper and error handling.
    
    Args:
        params: SerpAPI parameters dict
        
    Returns:
        Response dict from SerpAPI
        
    Raises:
        SerpApiAuthError: If API key is invalid
        SerpApiRateLimitError: If rate limit exceeded after retries
    """
    max_retries = 3
    backoff_delays = [2, 4, 8]  # Exponential backoff in seconds
    
    for attempt in range(max_retries):
        try:
            # Run synchronous GoogleSearch in thread pool
            def _search():
                search = GoogleSearch(params)
                return search.get_dict()
            
            response = await asyncio.to_thread(_search)
            
            # Check for errors in response
            if "error" in response:
                error_msg = response.get("error", "")
                
                # Check for authentication error
                if "Invalid API key" in error_msg or "API key" in error_msg:
                    logger.error(f"SerpAPI authentication error: {error_msg}")
                    raise SerpApiAuthError(f"Invalid SerpAPI key: {error_msg}")
                
                # Check for rate limit error
                if "rate limit" in error_msg.lower() or "429" in error_msg:
                    if attempt < max_retries - 1:
                        delay = backoff_delays[attempt]
                        logger.warning(
                            f"SerpAPI rate limit hit, retrying in {delay}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"SerpAPI rate limit exceeded after {max_retries} attempts")
                        raise SerpApiRateLimitError(
                            f"Rate limit exceeded after {max_retries} retries"
                        )
                
                # Other errors
                logger.error(f"SerpAPI error: {error_msg}")
                return {}
            
            # Success
            return response
            
        except (SerpApiAuthError, SerpApiRateLimitError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in SerpAPI call: {e}", exc_info=True)
            if attempt < max_retries - 1:
                delay = backoff_delays[attempt]
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)
                continue
            return {}
    
    return {}


# ============================================================================
# PUBLIC API
# ============================================================================

async def search_web(query: str, num_results: int | None = None) -> List[Dict[str, Any]]:
    """
    Search Google web results via SerpAPI.
    
    Args:
        query: Search query string
        num_results: Number of results to return (default from settings)
        
    Returns:
        List of normalized result dicts
        
    Raises:
        SerpApiAuthError: If API key is invalid
        SerpApiRateLimitError: If rate limit exceeded
    """
    start_time = time.perf_counter()
    
    if num_results is None:
        num_results = settings.max_search_results
    
    logger.info(f"Starting Google web search: query='{query}', num={num_results}")
    
    params = {
        "q": query,
        "num": num_results,
        "engine": "google",
        "api_key": settings.serpapi_key,
    }
    
    try:
        response = await _run_serpapi(params)
        
        # Extract organic results
        raw_results = response.get("organic_results", [])
        
        # Normalize results
        normalized = [
            normalize_result(raw, engine="google")
            for raw in raw_results
        ]
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Google web search complete: query='{query}', "
            f"results={len(normalized)}, duration={duration_ms:.2f}ms"
        )
        
        if not normalized:
            logger.warning(f"No results found for query: '{query}'")
        
        return normalized
        
    except (SerpApiAuthError, SerpApiRateLimitError):
        raise
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            f"Google web search failed: query='{query}', "
            f"duration={duration_ms:.2f}ms, error={e}",
            exc_info=True
        )
        return []


async def search_news(query: str, num_results: int | None = None) -> List[Dict[str, Any]]:
    """
    Search Google News via SerpAPI (restricted to past week).
    
    Args:
        query: Search query string
        num_results: Number of results to return (default from settings)
        
    Returns:
        List of normalized result dicts
        
    Raises:
        SerpApiAuthError: If API key is invalid
        SerpApiRateLimitError: If rate limit exceeded
    """
    start_time = time.perf_counter()
    
    if num_results is None:
        num_results = settings.max_search_results
    
    logger.info(f"Starting Google News search: query='{query}', num={num_results}")
    
    params = {
        "q": query,
        "engine": "google_news",
        "tbs": "qdr:w",  # Restrict to past week
        "api_key": settings.serpapi_key,
    }
    
    try:
        response = await _run_serpapi(params)
        
        # Extract news results
        raw_results = response.get("news_results", [])
        
        # Limit to requested number
        if raw_results:
            raw_results = raw_results[:num_results]
        
        # Normalize results
        normalized = [
            normalize_result(raw, engine="news")
            for raw in raw_results
        ]
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Google News search complete: query='{query}', "
            f"results={len(normalized)}, duration={duration_ms:.2f}ms"
        )
        
        if not normalized:
            logger.warning(f"No news results found for query: '{query}'")
        
        return normalized
        
    except (SerpApiAuthError, SerpApiRateLimitError):
        raise
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            f"Google News search failed: query='{query}', "
            f"duration={duration_ms:.2f}ms, error={e}",
            exc_info=True
        )
        return []


async def search_scholar(query: str, num_results: int | None = None) -> List[Dict[str, Any]]:
    """
    Search Google Scholar via SerpAPI.
    
    Args:
        query: Search query string
        num_results: Number of results to return (default from settings)
        
    Returns:
        List of normalized result dicts
        
    Raises:
        SerpApiAuthError: If API key is invalid
        SerpApiRateLimitError: If rate limit exceeded
    """
    start_time = time.perf_counter()
    
    if num_results is None:
        num_results = settings.max_search_results
    
    logger.info(f"Starting Google Scholar search: query='{query}', num={num_results}")
    
    params = {
        "q": query,
        "num": num_results,
        "engine": "google_scholar",
        "api_key": settings.serpapi_key,
    }
    
    try:
        response = await _run_serpapi(params)
        
        # Extract organic results
        raw_results = response.get("organic_results", [])
        
        # Normalize results
        normalized = [
            normalize_result(raw, engine="scholar")
            for raw in raw_results
        ]
        
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Google Scholar search complete: query='{query}', "
            f"results={len(normalized)}, duration={duration_ms:.2f}ms"
        )
        
        if not normalized:
            logger.warning(f"No scholar results found for query: '{query}'")
        
        return normalized
        
    except (SerpApiAuthError, SerpApiRateLimitError):
        raise
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            f"Google Scholar search failed: query='{query}', "
            f"duration={duration_ms:.2f}ms, error={e}",
            exc_info=True
        )
        return []


async def search_images(query: str, num: int = 6, language: str = "en") -> List[Dict[str, Any]]:
    """
    Search Google Images via SerpAPI.
    
    Args:
        query: Search query
        num: Number of images to return (default: 6)
        language: Language code (en, hi, es, etc.)
    
    Returns:
        List of image dicts with keys: url, thumbnail, title, source_url, domain
    
    Example:
        >>> images = await search_images("healthy apples", num=6)
        >>> len(images) <= 6
        True
    """
    from app.config import settings
    
    # Mock mode: return placeholder images
    if settings.is_search_mocked:
        logger.info(f"MOCK MODE: Returning {num} placeholder images for query: {query}")
        return [
            {
                "url": f"https://picsum.photos/seed/{i}/800/600",
                "thumbnail": f"https://picsum.photos/seed/{i}/200/150",
                "title": f"Sample image {i+1} for {query[:30]}",
                "source_url": "https://example.com",
                "domain": "example.com",
                "is_placeholder": True
            }
            for i in range(min(num, 6))
        ]
    
    # Real mode: call SerpAPI
    try:
        # Map language to country code
        country_map = {
            "en": "us", "hi": "in", "es": "es", "fr": "fr",
            "de": "de", "pt": "br", "zh": "cn", "ja": "jp", "ar": "eg"
        }
        country = country_map.get(language, "us")
        
        params = {
            "engine": "google_images",
            "q": query,
            "num": num,
            "hl": language,
            "gl": country,
            "api_key": settings.serpapi_key
        }
        
        start_time = time.time()
        logger.info(f"Starting Google Images search: query='{query}', num={num}, lang={language}")
        
        search = GoogleSearch(params)
        results = search.get_dict()
        
        duration = (time.time() - start_time) * 1000
        
        # Extract images
        images = []
        raw_results = results.get("images_results", [])
        logger.info(f"SerpAPI returned {len(raw_results)} raw image results")
        
        for img in raw_results[:num]:
            images.append({
                "url": img.get("original"),
                "thumbnail": img.get("thumbnail"),
                "title": img.get("title", ""),
                "source_url": img.get("link", ""),
                "domain": img.get("source", ""),
                "is_placeholder": False
            })
        
        logger.info(f"Google Images search complete: query='{query}', results={len(images)}, duration={duration:.2f}ms")
        
        if not images and raw_results:
            logger.warning(f"SerpAPI returned results but parsing failed. Keys in first result: {list(raw_results[0].keys()) if raw_results else 'none'}")
        
        return images
        
    except Exception as e:
        logger.error(f"Google Images search failed: {e}")
        # Fallback to placeholder images
        return [
            {
                "url": f"https://picsum.photos/seed/{i}/800/600",
                "thumbnail": f"https://picsum.photos/seed/{i}/200/150",
                "title": f"Fallback image {i+1}",
                "source_url": "https://example.com",
                "domain": "example.com",
                "is_placeholder": True
            }
            for i in range(min(num, 3))
        ]
