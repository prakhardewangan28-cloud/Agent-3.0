"""Credibility scoring service for evaluating source trustworthiness.

Pure heuristic scorer based on metadata signals. No external APIs or LLMs.
Scores sources from 0-100 using domain reputation, freshness, clickbait detection, etc.
"""
import re
import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS
# ============================================================================

TRUSTED_DOMAINS = {
    "nature.com", "science.org", "reuters.com", "apnews.com", "bbc.com",
    "nytimes.com", "wsj.com", "economist.com", "who.int", "cdc.gov",
    "nih.gov", "nasa.gov", "arxiv.org", "ieee.org", "acm.org",
    "springer.com", "sciencedirect.com", "jstor.org", "pewresearch.org",
    "gallup.com", "theguardian.com", "aljazeera.com", "npr.org",
    "ft.com", "bloomberg.com"
}

LOW_TRUST_DOMAINS = {
    "infowars.com", "naturalnews.com", "beforeitsnews.com",
    "worldnewsdailyreport.com", "empirenews.net", "huzlers.com",
    "theonion.com", "clickhole.com", "dailybuzzlive.com", "newslo.com"
}

CLICKBAIT_PATTERNS = [
    "you won't believe",
    "shocking",
    "!!!",
    "this one trick",
    "doctors hate",
    "gone wrong",
    "must see"
]

SPONSORED_PATTERNS = [
    "sponsored",
    "/ad/",
    "/promo/",
    "/affiliate/"
]

# Byline patterns for author detection
BYLINE_PATTERN = re.compile(r"^By\s+[A-Z][a-z]+|Author:", re.IGNORECASE)


# ============================================================================
# SCORING FUNCTIONS
# ============================================================================

def score_source(source: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score a single source's credibility from 0-100 based on metadata signals.
    
    Args:
        source: Dictionary with keys: url, title, snippet, domain, engine,
                published_date (optional)
    
    Returns:
        New dictionary with original keys plus:
        - credibility_score (float): Score from 0-100
        - score_breakdown (dict): Points awarded per rule
    
    Example:
        >>> source = {"url": "https://nature.com/article", "domain": "nature.com", ...}
        >>> scored = score_source(source)
        >>> scored["credibility_score"]
        90.0
    """
    # Create a copy to avoid mutating the input
    result = source.copy()
    
    # Initialize score and breakdown
    score = 0
    breakdown = {}
    
    # Extract fields with defaults
    domain = source.get("domain", "")
    url = source.get("url", "")
    title = source.get("title", "")
    snippet = source.get("snippet", "")
    engine = source.get("engine", "")
    published_date = source.get("published_date", None)
    
    # RULE 1: Domain suffix
    domain_suffix_score = _score_domain_suffix(domain)
    if domain_suffix_score != 0:
        score += domain_suffix_score
        breakdown["domain_suffix"] = domain_suffix_score
    
    # RULE 2: Trusted domain allowlist
    if domain in TRUSTED_DOMAINS:
        score += 25
        breakdown["trusted_domain"] = 25
    
    # RULE 3: Low-trust domain denylist
    if domain in LOW_TRUST_DOMAINS:
        score -= 30
        breakdown["low_trust_domain"] = -30
    
    # RULE 4: Author presence
    if _has_author_byline(title, snippet):
        score += 10
        breakdown["author_presence"] = 10
    
    # RULE 5: Date freshness
    freshness_score = _score_freshness(published_date)
    if freshness_score > 0:
        score += freshness_score
        breakdown["freshness"] = freshness_score
    
    # RULE 6: Clickbait signals
    if _has_clickbait(title):
        score -= 15
        breakdown["clickbait_penalty"] = -15
    
    # RULE 7: Sponsored/promotional signals
    if _has_sponsored_signal(url):
        score -= 20
        breakdown["sponsored_penalty"] = -20
    
    # RULE 8: Content length heuristic
    if snippet and len(snippet) < 50:
        score -= 10
        breakdown["short_snippet_penalty"] = -10
    
    # RULE 9: Engine bonus
    if engine == "scholar":
        score += 5
        breakdown["scholar_bonus"] = 5
    
    # Clamp score to 0-100
    clamped_score = max(0.0, min(100.0, float(score)))
    
    # Add total to breakdown
    breakdown["total"] = clamped_score
    
    # Log at DEBUG level
    logger.debug(
        f"Scored source: {domain} -> {clamped_score:.1f} "
        f"(breakdown: {breakdown})"
    )
    
    # Add scores to result
    result["credibility_score"] = clamped_score
    result["score_breakdown"] = breakdown
    
    return result


def score_sources_batch(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Score multiple sources and return them sorted by credibility (highest first).
    
    Args:
        sources: List of source dictionaries
    
    Returns:
        List of scored sources sorted by credibility_score descending
    
    Note:
        Sources missing required keys are skipped with a warning logged.
    """
    scored_sources = []
    
    for i, source in enumerate(sources):
        # Validate required keys
        required_keys = ["url", "domain"]
        missing_keys = [key for key in required_keys if key not in source]
        
        if missing_keys:
            logger.warning(
                f"Source at index {i} missing required keys: {missing_keys}. "
                f"Skipping. Source: {source}"
            )
            continue
        
        # Score the source
        try:
            scored = score_source(source)
            scored_sources.append(scored)
        except Exception as e:
            logger.error(
                f"Error scoring source at index {i}: {e}. "
                f"Source: {source}"
            )
            continue
    
    # Sort by credibility_score descending
    scored_sources.sort(
        key=lambda x: x.get("credibility_score", 0),
        reverse=True
    )
    
    logger.info(
        f"Scored {len(scored_sources)} sources "
        f"(skipped {len(sources) - len(scored_sources)})"
    )
    
    return scored_sources


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _score_domain_suffix(domain: str) -> int:
    """
    Score based on domain suffix.
    
    Returns:
        +25 for .gov
        +20 for .edu
        +10 for .org
        0 for .com or .net
        -5 for other suffixes
    """
    domain_lower = domain.lower()
    
    if domain_lower.endswith(".gov"):
        return 25
    elif domain_lower.endswith(".edu"):
        return 20
    elif domain_lower.endswith(".org"):
        return 10
    elif domain_lower.endswith(".com") or domain_lower.endswith(".net"):
        return 0
    else:
        return -5


def _has_author_byline(title: str, snippet: str) -> bool:
    """
    Check if title or snippet contains an author byline.
    
    Patterns:
        - "By FirstName" (capitalized)
        - "Author:"
    
    Returns:
        True if byline found, False otherwise
    """
    combined_text = f"{title} {snippet}"
    return bool(BYLINE_PATTERN.search(combined_text))


def _score_freshness(published_date: Any) -> int:
    """
    Score based on how recent the published date is.
    
    Args:
        published_date: Date string (ISO format) or None
    
    Returns:
        +15 if within last 30 days
        +10 if within last year
        0 if older or missing
    """
    if not published_date:
        return 0
    
    try:
        # Try parsing as ISO date (YYYY-MM-DD or datetime)
        if isinstance(published_date, str):
            # Handle both date and datetime formats
            if 'T' in published_date or ' ' in published_date:
                pub_date = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
            else:
                pub_date = datetime.strptime(published_date, "%Y-%m-%d")
        elif isinstance(published_date, datetime):
            pub_date = published_date
        else:
            return 0
        
        # Calculate age
        now = datetime.now()
        if pub_date.tzinfo:
            # Make now timezone-aware if pub_date is
            from datetime import timezone
            now = datetime.now(timezone.utc)
        
        age = now - pub_date
        
        if age <= timedelta(days=30):
            return 15
        elif age <= timedelta(days=365):
            return 10
        else:
            return 0
            
    except (ValueError, AttributeError, TypeError) as e:
        logger.debug(f"Could not parse published_date '{published_date}': {e}")
        return 0


def _has_clickbait(title: str) -> bool:
    """
    Check if title contains clickbait patterns (case-insensitive).
    
    Returns:
        True if any clickbait pattern found, False otherwise
    """
    title_lower = title.lower()
    return any(pattern in title_lower for pattern in CLICKBAIT_PATTERNS)


def _has_sponsored_signal(url: str) -> bool:
    """
    Check if URL contains sponsored/promotional signals (case-insensitive).
    
    Returns:
        True if any sponsored pattern found, False otherwise
    """
    url_lower = url.lower()
    return any(pattern in url_lower for pattern in SPONSORED_PATTERNS)
