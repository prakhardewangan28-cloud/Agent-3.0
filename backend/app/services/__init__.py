"""Service layer for business logic."""
from .serpapi_service import (
    search_web,
    search_news,
    search_scholar,
    SerpApiAuthError,
    SerpApiRateLimitError,
)
from .credibility_service import score_source, score_sources_batch
from .claim_service import (
    extract_claims_from_text,
    embed_claim,
    extract_and_store_claims,
    extract_claims_batch,
)
from .conflict_service import (
    find_similar_claim_pairs,
    judge_pair,
    detect_conflicts,
    classify_information_landscape,
)
from .refinement_service import (
    is_vague,
    generate_refinements,
    refine_or_proceed,
)

__all__ = [
    # SerpAPI functions
    "search_web",
    "search_news",
    "search_scholar",
    "SerpApiAuthError",
    "SerpApiRateLimitError",
    # Credibility functions
    "score_source",
    "score_sources_batch",
    # Claim extraction functions
    "extract_claims_from_text",
    "embed_claim",
    "extract_and_store_claims",
    "extract_claims_batch",
    # Conflict detection functions
    "find_similar_claim_pairs",
    "judge_pair",
    "detect_conflicts",
    "classify_information_landscape",
    # Query refinement functions
    "is_vague",
    "generate_refinements",
    "refine_or_proceed",
]
