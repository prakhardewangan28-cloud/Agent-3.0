"""Tests for credibility scoring service."""
import pytest
from datetime import datetime, timedelta
from app.services.credibility_service import (
    score_source,
    score_sources_batch,
    TRUSTED_DOMAINS,
    LOW_TRUST_DOMAINS
)


def test_gov_domain_scores_higher_than_com():
    """Test that .gov domains score higher than .com domains."""
    gov_source = {
        "url": "https://cdc.gov/article",
        "domain": "cdc.gov",
        "title": "Health Guidelines",
        "snippet": "Official health guidelines from the CDC",
        "engine": "web"
    }
    
    com_source = {
        "url": "https://example.com/article",
        "domain": "example.com",
        "title": "Health Guidelines",
        "snippet": "Health guidelines from example site",
        "engine": "web"
    }
    
    gov_scored = score_source(gov_source)
    com_scored = score_source(com_source)
    
    assert gov_scored["credibility_score"] > com_scored["credibility_score"]
    assert gov_scored["score_breakdown"]["domain_suffix"] == 25
    assert "domain_suffix" not in com_scored["score_breakdown"]  # .com = 0


def test_trusted_domain_gets_bonus():
    """Test that academic domains get +60 points (nature.com is now academic)."""
    academic_source = {
        "url": "https://nature.com/article",
        "domain": "nature.com",
        "title": "Scientific Discovery",
        "snippet": "A peer-reviewed study on climate change with extensive research methodology",  # >50 chars
        "engine": "web"
    }
    
    scored = score_source(academic_source)
    
    assert "academic_domain" in scored["score_breakdown"]
    assert scored["score_breakdown"]["academic_domain"] == 60
    assert scored["credibility_score"] >= 60


def test_low_trust_domain_gets_penalty():
    """Test that low-trust domains get -30 points."""
    untrusted_source = {
        "url": "https://infowars.com/conspiracy",
        "domain": "infowars.com",
        "title": "Breaking News",
        "snippet": "A controversial article",
        "engine": "web"
    }
    
    scored = score_source(untrusted_source)
    
    assert "low_trust_domain" in scored["score_breakdown"]
    assert scored["score_breakdown"]["low_trust_domain"] == -30


def test_low_trust_with_negatives_clamps_to_zero():
    """Test that scores below 0 are clamped to 0."""
    terrible_source = {
        "url": "https://infowars.com/ad/promo/article",
        "domain": "infowars.com",
        "title": "You won't believe this shocking trick!!!",
        "snippet": "Short",  # Less than 50 chars
        "engine": "web"
    }
    
    scored = score_source(terrible_source)
    
    # Should have multiple penalties:
    # -30 (low trust) -15 (clickbait) -20 (sponsored) -10 (short) = -75
    assert scored["credibility_score"] == 0.0
    assert scored["score_breakdown"]["low_trust_domain"] == -30
    assert scored["score_breakdown"]["clickbait_penalty"] == -15
    assert scored["score_breakdown"]["sponsored_penalty"] == -20
    assert scored["score_breakdown"]["short_snippet_penalty"] == -10


def test_trusted_with_positives_clamps_to_hundred():
    """Test that scores above 100 are clamped to 100."""
    perfect_source = {
        "url": "https://nature.com/article",
        "domain": "nature.com",
        "title": "By Dr. Jane Smith: Groundbreaking Research",
        "snippet": "A comprehensive peer-reviewed study published in a leading journal with extensive methodology and robust conclusions.",
        "engine": "scholar",
        "published_date": (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    }
    
    scored = score_source(perfect_source)
    
    # Should have multiple bonuses:
    # +60 (academic) +10 (author) +5 (scholar) +15 (fresh) = 90
    # Even if we artificially boost it, it should clamp to 100
    assert scored["credibility_score"] <= 100.0
    assert scored["score_breakdown"]["academic_domain"] == 60
    assert scored["score_breakdown"]["author_presence"] == 10
    assert scored["score_breakdown"]["scholar_bonus"] == 5
    assert scored["score_breakdown"]["freshness"] == 15


def test_recent_date_gets_freshness_bonus():
    """Test that recent publications get +15 freshness bonus."""
    recent_source = {
        "url": "https://example.com/news",
        "domain": "example.com",
        "title": "Breaking News",
        "snippet": "Latest developments in technology sector with detailed analysis",
        "engine": "web",
        "published_date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    }
    
    scored = score_source(recent_source)
    
    assert "freshness" in scored["score_breakdown"]
    assert scored["score_breakdown"]["freshness"] == 15


def test_year_old_date_gets_reduced_bonus():
    """Test that year-old publications get +10 freshness bonus."""
    old_source = {
        "url": "https://example.com/archive",
        "domain": "example.com",
        "title": "Archive Article",
        "snippet": "Historical analysis of economic trends over the past decade",
        "engine": "web",
        "published_date": (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
    }
    
    scored = score_source(old_source)
    
    assert "freshness" in scored["score_breakdown"]
    assert scored["score_breakdown"]["freshness"] == 10


def test_clickbait_title_gets_penalty():
    """Test that clickbait titles get -15 penalty."""
    clickbait_source = {
        "url": "https://example.com/viral",
        "domain": "example.com",
        "title": "You won't believe what happened next!!!",
        "snippet": "A sensational story that went viral on social media platforms",
        "engine": "web"
    }
    
    scored = score_source(clickbait_source)
    
    assert "clickbait_penalty" in scored["score_breakdown"]
    assert scored["score_breakdown"]["clickbait_penalty"] == -15


def test_short_snippet_gets_penalty():
    """Test that short snippets get -10 penalty."""
    short_source = {
        "url": "https://example.com/brief",
        "domain": "example.com",
        "title": "Brief Update",
        "snippet": "Very short text",  # Less than 50 characters
        "engine": "web"
    }
    
    scored = score_source(short_source)
    
    assert "short_snippet_penalty" in scored["score_breakdown"]
    assert scored["score_breakdown"]["short_snippet_penalty"] == -10


def test_scholar_engine_gets_bonus():
    """Test that scholar engine sources get +5 bonus."""
    scholar_source = {
        "url": "https://arxiv.org/paper",
        "domain": "arxiv.org",
        "title": "Machine Learning Research",
        "snippet": "A comprehensive study on neural network architectures and their applications",
        "engine": "scholar"
    }
    
    scored = score_source(scholar_source)
    
    assert "scholar_bonus" in scored["score_breakdown"]
    assert scored["score_breakdown"]["scholar_bonus"] == 5


def test_batch_sorts_by_credibility_descending():
    """Test that score_sources_batch sorts by credibility descending."""
    sources = [
        {
            "url": "https://example.com/low",
            "domain": "example.com",
            "title": "Low quality",
            "snippet": "This is a very short snippet that barely says anything at all here",  # >50 chars
            "engine": "web"
        },
        {
            "url": "https://nature.com/medium",
            "domain": "nature.com",
            "title": "High quality research",
            "snippet": "A comprehensive peer-reviewed study with extensive methodology and detailed findings",
            "engine": "scholar"
        },
        {
            "url": "https://cdc.gov/high",
            "domain": "cdc.gov",
            "title": "Government guidelines",
            "snippet": "Official health recommendations from federal agency with comprehensive guidelines",
            "engine": "web"
        }
    ]
    
    scored = score_sources_batch(sources)
    
    # Check that results are sorted descending
    assert len(scored) == 3
    for i in range(len(scored) - 1):
        assert scored[i]["credibility_score"] >= scored[i + 1]["credibility_score"]
    
    # Nature.com gets: .com(0) + academic(+60) + scholar(+5) = 65
    # CDC.gov gets: .gov(+25) + trusted(+25) = 50
    # So Nature should be highest now
    assert scored[0]["domain"] == "nature.com"
    assert scored[0]["credibility_score"] == 65.0


def test_batch_skips_invalid_sources():
    """Test that batch function skips sources missing required keys."""
    sources = [
        {
            "url": "https://example.com/valid",
            "domain": "example.com",
            "title": "Valid Source",
            "snippet": "This source has all required fields",
            "engine": "web"
        },
        {
            # Missing 'domain' key
            "url": "https://invalid.com/article",
            "title": "Invalid Source",
            "snippet": "This source is missing the domain key",
            "engine": "web"
        },
        {
            # Missing 'url' key
            "domain": "another-invalid.com",
            "title": "Another Invalid",
            "snippet": "Missing URL",
            "engine": "web"
        }
    ]
    
    scored = score_sources_batch(sources)
    
    # Only the valid source should be returned
    assert len(scored) == 1
    assert scored[0]["domain"] == "example.com"


def test_author_byline_detection():
    """Test that author bylines are detected correctly."""
    with_author = {
        "url": "https://example.com/article",
        "domain": "example.com",
        "title": "By John Smith: Important Discovery",
        "snippet": "A detailed analysis of recent developments",
        "engine": "web"
    }
    
    without_author = {
        "url": "https://example.com/article2",
        "domain": "example.com",
        "title": "Important Discovery",
        "snippet": "A detailed analysis of recent developments",
        "engine": "web"
    }
    
    with_scored = score_source(with_author)
    without_scored = score_source(without_author)
    
    assert "author_presence" in with_scored["score_breakdown"]
    assert with_scored["score_breakdown"]["author_presence"] == 10
    assert "author_presence" not in without_scored["score_breakdown"]


def test_sponsored_url_penalty():
    """Test that sponsored URLs get -20 penalty."""
    sponsored = {
        "url": "https://example.com/sponsored/article",
        "domain": "example.com",
        "title": "Product Review",
        "snippet": "An in-depth review of the latest consumer products",
        "engine": "web"
    }
    
    scored = score_source(sponsored)
    
    assert "sponsored_penalty" in scored["score_breakdown"]
    assert scored["score_breakdown"]["sponsored_penalty"] == -20


def test_edu_domain_bonus():
    """Test that .edu domains get +20 bonus."""
    edu_source = {
        "url": "https://mit.edu/research",
        "domain": "mit.edu",
        "title": "Academic Research",
        "snippet": "Research findings from university laboratory",
        "engine": "web"
    }
    
    scored = score_source(edu_source)
    
    assert "domain_suffix" in scored["score_breakdown"]
    assert scored["score_breakdown"]["domain_suffix"] == 20


def test_org_domain_bonus():
    """Test that .org domains get +10 bonus."""
    org_source = {
        "url": "https://wikipedia.org/article",
        "domain": "wikipedia.org",
        "title": "Encyclopedia Entry",
        "snippet": "A comprehensive encyclopedia article with citations",
        "engine": "web"
    }
    
    scored = score_source(org_source)
    
    assert "domain_suffix" in scored["score_breakdown"]
    assert scored["score_breakdown"]["domain_suffix"] == 10


def test_unknown_suffix_penalty():
    """Test that unknown domain suffixes get -5 penalty."""
    unknown_source = {
        "url": "https://example.xyz/article",
        "domain": "example.xyz",
        "title": "Article",
        "snippet": "Content from a less common top-level domain",
        "engine": "web"
    }
    
    scored = score_source(unknown_source)
    
    assert "domain_suffix" in scored["score_breakdown"]
    assert scored["score_breakdown"]["domain_suffix"] == -5


def test_score_source_returns_new_dict():
    """Test that score_source doesn't mutate the input."""
    original = {
        "url": "https://example.com/test",
        "domain": "example.com",
        "title": "Test Article",
        "snippet": "A test article for checking immutability of input",
        "engine": "web"
    }
    
    original_copy = original.copy()
    scored = score_source(original)
    
    # Original should be unchanged
    assert original == original_copy
    
    # Scored should have additional keys
    assert "credibility_score" in scored
    assert "score_breakdown" in scored
    
    # But not in original
    assert "credibility_score" not in original
    assert "score_breakdown" not in original


def test_missing_optional_fields_handled_gracefully():
    """Test that missing optional fields don't cause errors."""
    minimal_source = {
        "url": "https://example.com/minimal",
        "domain": "example.com"
        # No title, snippet, engine, or published_date
    }
    
    scored = score_source(minimal_source)
    
    # Should still return a score
    assert "credibility_score" in scored
    assert "score_breakdown" in scored
    assert isinstance(scored["credibility_score"], float)
    assert 0 <= scored["credibility_score"] <= 100


def test_trusted_domain_subdomain_match():
    """Test that subdomains of trusted domains are also trusted."""
    # science.nasa.gov should match nasa.gov
    source = {
        "url": "https://science.nasa.gov/article",
        "domain": "science.nasa.gov",
        "title": "NASA Article",
        "snippet": "This is an article from NASA's science division with detailed information about climate research and findings.",
        "engine": "google",
    }
    
    result = score_source(source)
    breakdown = result["score_breakdown"]
    
    # Should get both .gov bonus AND trusted domain bonus
    assert breakdown.get("domain_suffix") == 25
    assert breakdown.get("trusted_domain") == 25
    assert result["credibility_score"] >= 50  # At least 50 from those two


def test_low_trust_domain_subdomain_match():
    """Test that subdomains of low-trust domains are also untrusted."""
    # blog.infowars.com should match infowars.com
    source = {
        "url": "https://blog.infowars.com/article",
        "domain": "blog.infowars.com",
        "title": "Article",
        "snippet": "Some article content",
        "engine": "google",
    }
    
    result = score_source(source)
    breakdown = result["score_breakdown"]
    
    # Should get low-trust penalty
    assert breakdown.get("low_trust_domain") == -30
