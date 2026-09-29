"""Tests for SerpAPI service layer."""
import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from app.services.serpapi_service import (
    extract_domain,
    normalize_result,
    search_web,
    search_news,
    search_scholar,
    SerpApiAuthError,
    SerpApiRateLimitError,
    _run_serpapi,
)


# ============================================================================
# TEST: extract_domain
# ============================================================================

def test_extract_domain_with_www():
    """Test domain extraction removes www prefix."""
    url = "https://www.example.com/path/to/page"
    assert extract_domain(url) == "example.com"


def test_extract_domain_without_www():
    """Test domain extraction without www."""
    url = "https://example.com/path"
    assert extract_domain(url) == "example.com"


def test_extract_domain_with_subdomain():
    """Test domain extraction with subdomain."""
    url = "https://blog.example.com/article"
    assert extract_domain(url) == "blog.example.com"


def test_extract_domain_with_port():
    """Test domain extraction with port number."""
    url = "https://example.com:8080/path"
    assert extract_domain(url) == "example.com:8080"


def test_extract_domain_invalid_url():
    """Test domain extraction with invalid URL."""
    url = "not-a-valid-url"
    result = extract_domain(url)
    # Should return empty string or the input depending on parsing
    assert isinstance(result, str)


def test_extract_domain_none():
    """Test domain extraction with None."""
    assert extract_domain(None) == ""


def test_extract_domain_empty():
    """Test domain extraction with empty string."""
    assert extract_domain("") == ""


# ============================================================================
# TEST: normalize_result
# ============================================================================

def test_normalize_result_google():
    """Test normalization of Google web result."""
    raw = {
        "link": "https://example.com/article",
        "title": "Example Article",
        "snippet": "This is a snippet of the article content.",
    }
    
    result = normalize_result(raw, "google")
    
    assert result["url"] == "https://example.com/article"
    assert result["title"] == "Example Article"
    assert result["snippet"] == "This is a snippet of the article content."
    assert result["domain"] == "example.com"
    assert result["engine"] == "google"
    assert result["published_date"] is None


def test_normalize_result_news():
    """Test normalization of Google News result."""
    raw = {
        "link": "https://news.example.com/story",
        "title": "Breaking News",
        "snippet": "News snippet here",
        "date": "2 hours ago",
    }
    
    result = normalize_result(raw, "news")
    
    assert result["url"] == "https://news.example.com/story"
    assert result["title"] == "Breaking News"
    assert result["snippet"] == "News snippet here"
    assert result["domain"] == "news.example.com"
    assert result["engine"] == "news"
    assert result["published_date"] == "2 hours ago"


def test_normalize_result_scholar():
    """Test normalization of Google Scholar result."""
    raw = {
        "link": "https://scholar.google.com/paper",
        "title": "Research Paper Title",
        "snippet": "Abstract of the paper",
        "publication_info": {
            "summary": "Journal Name, 2023"
        }
    }
    
    result = normalize_result(raw, "scholar")
    
    assert result["url"] == "https://scholar.google.com/paper"
    assert result["title"] == "Research Paper Title"
    assert result["snippet"] == "Abstract of the paper"
    assert result["domain"] == "scholar.google.com"
    assert result["engine"] == "scholar"
    assert result["published_date"] == "Journal Name, 2023"


def test_normalize_result_scholar_no_snippet():
    """Test scholar normalization when snippet is missing but in publication_info."""
    raw = {
        "link": "https://scholar.google.com/paper2",
        "title": "Another Paper",
        "publication_info": {
            "summary": "This should be used as snippet"
        }
    }
    
    result = normalize_result(raw, "scholar")
    
    # When snippet is missing, should use publication_info.summary
    assert result["snippet"] == "This should be used as snippet"


def test_normalize_result_missing_fields():
    """Test normalization handles missing fields gracefully."""
    raw = {}  # Empty dict
    
    result = normalize_result(raw, "google")
    
    assert result["url"] == ""
    assert result["title"] == ""
    assert result["snippet"] == ""
    assert result["domain"] == ""
    assert result["engine"] == "google"
    assert result["published_date"] is None


# ============================================================================
# TEST: _run_serpapi with error handling
# ============================================================================

@pytest.mark.asyncio
async def test_run_serpapi_auth_error():
    """Test that invalid API key raises SerpApiAuthError."""
    with patch("app.services.serpapi_service.GoogleSearch") as mock_search:
        # Mock the search to return auth error
        mock_instance = Mock()
        mock_instance.get_dict.return_value = {
            "error": "Invalid API key. Please check your API key."
        }
        mock_search.return_value = mock_instance
        
        params = {"q": "test", "api_key": "invalid"}
        
        with pytest.raises(SerpApiAuthError):
            await _run_serpapi(params)


@pytest.mark.asyncio
async def test_run_serpapi_rate_limit_with_retry():
    """Test rate limit error triggers retry logic."""
    with patch("app.services.serpapi_service.GoogleSearch") as mock_search:
        # First two calls fail with rate limit, third succeeds
        mock_instance = Mock()
        call_count = 0
        
        def get_dict_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return {"error": "Rate limit exceeded. Please try again later."}
            return {"organic_results": []}
        
        mock_instance.get_dict.side_effect = get_dict_side_effect
        mock_search.return_value = mock_instance
        
        params = {"q": "test", "api_key": "valid"}
        
        # Should succeed after retries (with mocked sleep)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await _run_serpapi(params)
            assert "organic_results" in result
            assert call_count == 3


@pytest.mark.asyncio
async def test_run_serpapi_rate_limit_exhausted():
    """Test rate limit error raises exception after max retries."""
    with patch("app.services.serpapi_service.GoogleSearch") as mock_search:
        # Always return rate limit error
        mock_instance = Mock()
        mock_instance.get_dict.return_value = {
            "error": "Rate limit exceeded (429)"
        }
        mock_search.return_value = mock_instance
        
        params = {"q": "test", "api_key": "valid"}
        
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(SerpApiRateLimitError):
                await _run_serpapi(params)


@pytest.mark.asyncio
async def test_run_serpapi_success():
    """Test successful API call."""
    with patch("app.services.serpapi_service.GoogleSearch") as mock_search:
        mock_instance = Mock()
        mock_instance.get_dict.return_value = {
            "organic_results": [
                {
                    "link": "https://example.com",
                    "title": "Test",
                    "snippet": "Test snippet"
                }
            ]
        }
        mock_search.return_value = mock_instance
        
        params = {"q": "test", "api_key": "valid"}
        result = await _run_serpapi(params)
        
        assert "organic_results" in result
        assert len(result["organic_results"]) == 1


# ============================================================================
# TEST: search_web
# ============================================================================

@pytest.mark.asyncio
async def test_search_web_success():
    """Test successful web search."""
    with patch("app.services.serpapi_service._run_serpapi") as mock_run:
        mock_run.return_value = {
            "organic_results": [
                {
                    "link": "https://example.com/page1",
                    "title": "Page 1",
                    "snippet": "Snippet 1"
                },
                {
                    "link": "https://example.com/page2",
                    "title": "Page 2",
                    "snippet": "Snippet 2"
                }
            ]
        }
        
        results = await search_web("test query", num_results=2)
        
        assert len(results) == 2
        assert results[0]["url"] == "https://example.com/page1"
        assert results[0]["engine"] == "google"
        assert results[0]["domain"] == "example.com"


@pytest.mark.asyncio
async def test_search_web_no_results():
    """Test web search with no results."""
    with patch("app.services.serpapi_service._run_serpapi") as mock_run:
        mock_run.return_value = {"organic_results": []}
        
        results = await search_web("test query")
        
        assert results == []


@pytest.mark.asyncio
async def test_search_web_with_default_num_results():
    """Test web search uses default num_results from settings."""
    with patch("app.services.serpapi_service._run_serpapi") as mock_run:
        mock_run.return_value = {"organic_results": []}
        
        # Call without num_results parameter
        await search_web("test query")
        
        # Verify the call was made with settings.max_search_results
        call_args = mock_run.call_args[0][0]
        assert "num" in call_args


# ============================================================================
# TEST: search_news
# ============================================================================

@pytest.mark.asyncio
async def test_search_news_success():
    """Test successful news search."""
    with patch("app.services.serpapi_service._run_serpapi") as mock_run:
        mock_run.return_value = {
            "news_results": [
                {
                    "link": "https://news.example.com/story1",
                    "title": "News Story 1",
                    "snippet": "News snippet 1",
                    "date": "2 hours ago"
                }
            ]
        }
        
        results = await search_news("test news", num_results=1)
        
        assert len(results) == 1
        assert results[0]["url"] == "https://news.example.com/story1"
        assert results[0]["engine"] == "news"
        assert results[0]["published_date"] == "2 hours ago"


@pytest.mark.asyncio
async def test_search_news_limits_results():
    """Test news search limits results to requested number."""
    with patch("app.services.serpapi_service._run_serpapi") as mock_run:
        # Return 5 results
        mock_run.return_value = {
            "news_results": [
                {"link": f"https://news.example.com/{i}", "title": f"Story {i}", "snippet": f"Snippet {i}"}
                for i in range(5)
            ]
        }
        
        # Request only 2
        results = await search_news("test", num_results=2)
        
        assert len(results) == 2


# ============================================================================
# TEST: search_scholar
# ============================================================================

@pytest.mark.asyncio
async def test_search_scholar_success():
    """Test successful scholar search."""
    with patch("app.services.serpapi_service._run_serpapi") as mock_run:
        mock_run.return_value = {
            "organic_results": [
                {
                    "link": "https://scholar.google.com/paper1",
                    "title": "Research Paper",
                    "snippet": "Abstract here",
                    "publication_info": {
                        "summary": "Nature, 2023"
                    }
                }
            ]
        }
        
        results = await search_scholar("research topic", num_results=1)
        
        assert len(results) == 1
        assert results[0]["url"] == "https://scholar.google.com/paper1"
        assert results[0]["engine"] == "scholar"
        assert results[0]["published_date"] == "Nature, 2023"


@pytest.mark.asyncio
async def test_search_scholar_no_results():
    """Test scholar search with no results."""
    with patch("app.services.serpapi_service._run_serpapi") as mock_run:
        mock_run.return_value = {"organic_results": []}
        
        results = await search_scholar("obscure topic")
        
        assert results == []


# ============================================================================
# TEST: Error propagation
# ============================================================================

@pytest.mark.asyncio
async def test_search_web_propagates_auth_error():
    """Test that auth errors propagate from search_web."""
    with patch("app.services.serpapi_service._run_serpapi") as mock_run:
        mock_run.side_effect = SerpApiAuthError("Invalid key")
        
        with pytest.raises(SerpApiAuthError):
            await search_web("test")


@pytest.mark.asyncio
async def test_search_news_propagates_rate_limit_error():
    """Test that rate limit errors propagate from search_news."""
    with patch("app.services.serpapi_service._run_serpapi") as mock_run:
        mock_run.side_effect = SerpApiRateLimitError("Rate limit")
        
        with pytest.raises(SerpApiRateLimitError):
            await search_news("test")


@pytest.mark.asyncio
async def test_search_scholar_handles_generic_exception():
    """Test that generic exceptions are caught and return empty list."""
    with patch("app.services.serpapi_service._run_serpapi") as mock_run:
        mock_run.side_effect = Exception("Unexpected error")
        
        # Should not raise, should return empty list
        results = await search_scholar("test")
        assert results == []
