"""Tests for counter-argument generation service."""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.counter_argument_service import (
    generate_counter_argument,
    _format_sources_for_prompt,
    _parse_counter_argument_json,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_sources():
    """Mock sources from database."""
    return [
        {
            "id": 1,
            "url": "https://example.com/article1",
            "domain": "example.com",
            "title": "Study shows X",
            "credibility_score": 85.0,
        },
        {
            "id": 2,
            "url": "https://research.org/paper2",
            "domain": "research.org",
            "title": "Analysis of Y",
            "credibility_score": 92.0,
        },
        {
            "id": 3,
            "url": "https://blog.net/post3",
            "domain": "blog.net",
            "title": "Opinion on Z",
            "credibility_score": 45.0,
        },
    ]


@pytest.fixture
def mock_report():
    """Mock final report."""
    return """# Research Report: Climate Change

## Summary
Based on multiple sources, climate change is primarily driven by human activities.

## Consensus Findings
- Global temperatures rising
- CO2 levels increasing

## Sources
[1] example.com - Study shows X
[2] research.org - Analysis of Y
"""


@pytest.fixture
def mock_landscape():
    """Mock information landscape."""
    return {
        "consensus": ["Global temperatures rising"],
        "contested": [],
        "unknowns": [],
    }


# ============================================================================
# TEST 1: Mock mode returns valid structure
# ============================================================================

@pytest.mark.asyncio
async def test_generate_counter_argument_mock_mode_returns_valid_structure(
    mock_report, mock_landscape, mock_sources
):
    """Test that generate_counter_argument in MOCK_MODE returns valid structure."""
    with patch("app.services.counter_argument_service.settings") as mock_settings, \
         patch("app.services.counter_argument_service.get_sources_by_session", new_callable=AsyncMock) as mock_get_sources:
        
        mock_settings.mock_mode = True
        mock_get_sources.return_value = mock_sources
        
        result = await generate_counter_argument(
            session_id="test-uuid",
            final_report=mock_report,
            landscape=mock_landscape,
        )
        
        # Verify structure
        assert "counter_argument" in result
        assert "supporting_sources" in result
        assert "strength" in result
        assert "explanation" in result
        
        # Verify types
        assert isinstance(result["counter_argument"], str)
        assert isinstance(result["supporting_sources"], list)
        assert isinstance(result["strength"], str)
        assert isinstance(result["explanation"], str)
        
        # Verify mock content
        assert "Mock counter-argument" in result["counter_argument"]
        assert result["strength"] == "moderate"


# ============================================================================
# TEST 2: Mock mode returns exactly 2 supporting sources
# ============================================================================

@pytest.mark.asyncio
async def test_generate_counter_argument_mock_mode_returns_two_sources(
    mock_report, mock_landscape, mock_sources
):
    """Test that generate_counter_argument in MOCK_MODE returns exactly 2 supporting sources."""
    with patch("app.services.counter_argument_service.settings") as mock_settings, \
         patch("app.services.counter_argument_service.get_sources_by_session", new_callable=AsyncMock) as mock_get_sources:
        
        mock_settings.mock_mode = True
        # Set credibility_score as 0-1 (database format)
        for s in mock_sources:
            s["credibility_score"] = 0.85
        mock_get_sources.return_value = mock_sources
        
        result = await generate_counter_argument(
            session_id="test-uuid",
            final_report=mock_report,
            landscape=mock_landscape,
        )
        
        # Verify exactly 2 sources
        assert len(result["supporting_sources"]) == 2
        
        # Verify source structure
        for source in result["supporting_sources"]:
            assert "source_id" in source
            assert "url" in source
            assert "domain" in source
            assert "credibility_score" in source
            assert "reason" in source
            assert source["reason"] == "Mock supporting source"
            # Verify credibility_score is converted to 0-100 scale
            assert source["credibility_score"] == 85.0  # 0.85 * 100


# ============================================================================
# TEST 3: No sources returns strength="none"
# ============================================================================

@pytest.mark.asyncio
async def test_generate_counter_argument_no_sources_returns_none(
    mock_report, mock_landscape
):
    """Test that generate_counter_argument with no sources returns strength='none'."""
    with patch("app.services.counter_argument_service.settings") as mock_settings, \
         patch("app.services.counter_argument_service.get_sources_by_session", new_callable=AsyncMock) as mock_get_sources:
        
        mock_settings.mock_mode = False
        mock_get_sources.return_value = []  # No sources
        
        result = await generate_counter_argument(
            session_id="test-uuid",
            final_report=mock_report,
            landscape=mock_landscape,
        )
        
        # Verify no-sources result
        assert result["counter_argument"] == ""
        assert result["supporting_sources"] == []
        assert result["strength"] == "none"
        assert "No sources available" in result["explanation"]


# ============================================================================
# TEST 4: Parses valid LLM JSON correctly
# ============================================================================

@pytest.mark.asyncio
async def test_generate_counter_argument_parses_valid_json(
    mock_report, mock_landscape, mock_sources
):
    """Test that generate_counter_argument parses valid LLM JSON correctly."""
    valid_json_response = json.dumps({
        "counter_argument": "However, some studies suggest natural cycles play a larger role than previously thought.",
        "supporting_source_ids": [1, 3],
        "strength": "moderate",
        "explanation": "Sources provide alternative interpretations but don't directly contradict the main conclusion.",
    })
    
    with patch("app.services.counter_argument_service.settings") as mock_settings, \
         patch("app.services.counter_argument_service.get_sources_by_session", new_callable=AsyncMock) as mock_get_sources, \
         patch("app.services.counter_argument_service.generate", new_callable=AsyncMock) as mock_generate:
        
        mock_settings.is_llm_mocked = False  # Mock the property, not mock_mode
        mock_get_sources.return_value = mock_sources
        mock_generate.return_value = valid_json_response
        
        result = await generate_counter_argument(
            session_id="test-uuid",
            final_report=mock_report,
            landscape=mock_landscape,
        )
        
        # Verify parsed result
        assert "natural cycles" in result["counter_argument"]
        assert len(result["supporting_sources"]) == 2
        assert result["strength"] == "moderate"
        assert result["supporting_sources"][0]["source_id"] == 1
        assert result["supporting_sources"][1]["source_id"] == 3


# ============================================================================
# TEST 5: Handles malformed JSON with retry
# ============================================================================

@pytest.mark.asyncio
async def test_generate_counter_argument_handles_malformed_json_with_retry(
    mock_report, mock_landscape, mock_sources
):
    """Test that generate_counter_argument handles malformed JSON with retry."""
    malformed_response = "Here's my response: {invalid json"
    
    valid_retry_response = json.dumps({
        "counter_argument": "Retry response counter-argument.",
        "supporting_source_ids": [2],
        "strength": "weak",
        "explanation": "Limited evidence from retry.",
    })
    
    with patch("app.services.counter_argument_service.settings") as mock_settings, \
         patch("app.services.counter_argument_service.get_sources_by_session", new_callable=AsyncMock) as mock_get_sources, \
         patch("app.services.counter_argument_service.generate", new_callable=AsyncMock) as mock_generate:
        
        mock_settings.is_llm_mocked = False  # Mock the property
        mock_get_sources.return_value = mock_sources
        
        # First call returns malformed, second call returns valid
        mock_generate.side_effect = [malformed_response, valid_retry_response]
        
        result = await generate_counter_argument(
            session_id="test-uuid",
            final_report=mock_report,
            landscape=mock_landscape,
        )
        
        # Verify retry succeeded
        assert "Retry response" in result["counter_argument"]
        assert result["strength"] == "weak"
        assert len(result["supporting_sources"]) == 1
        assert mock_generate.call_count == 2


# ============================================================================
# TEST 6: Returns strength="none" when LLM fails
# ============================================================================

@pytest.mark.asyncio
async def test_generate_counter_argument_returns_none_when_llm_fails(
    mock_report, mock_landscape, mock_sources
):
    """Test that generate_counter_argument returns strength='none' when LLM fails."""
    with patch("app.services.counter_argument_service.settings") as mock_settings, \
         patch("app.services.counter_argument_service.get_sources_by_session", new_callable=AsyncMock) as mock_get_sources, \
         patch("app.services.counter_argument_service.generate", new_callable=AsyncMock) as mock_generate:
        
        mock_settings.is_llm_mocked = False  # Mock the property
        mock_get_sources.return_value = mock_sources
        
        # Both calls fail
        mock_generate.side_effect = Exception("Gemini API error")
        
        result = await generate_counter_argument(
            session_id="test-uuid",
            final_report=mock_report,
            landscape=mock_landscape,
        )
        
        # Verify failure result
        assert result["counter_argument"] == ""
        assert result["supporting_sources"] == []
        assert result["strength"] == "none"
        assert "failed" in result["explanation"].lower()


# ============================================================================
# TEST 7: Only cites sources that exist in session
# ============================================================================

@pytest.mark.asyncio
async def test_generate_counter_argument_only_cites_existing_sources(
    mock_report, mock_landscape, mock_sources
):
    """Test that generate_counter_argument only cites sources that exist in the session."""
    # LLM returns IDs [1, 99], but only 1 exists in mock_sources
    response_with_invalid_id = json.dumps({
        "counter_argument": "Counter with invalid source ID.",
        "supporting_source_ids": [1, 99],  # 99 doesn't exist
        "strength": "moderate",
        "explanation": "Testing invalid ID handling.",
    })
    
    with patch("app.services.counter_argument_service.settings") as mock_settings, \
         patch("app.services.counter_argument_service.get_sources_by_session", new_callable=AsyncMock) as mock_get_sources, \
         patch("app.services.counter_argument_service.generate", new_callable=AsyncMock) as mock_generate:
        
        mock_settings.is_llm_mocked = False  # Mock the property
        mock_get_sources.return_value = mock_sources
        mock_generate.return_value = response_with_invalid_id
        
        result = await generate_counter_argument(
            session_id="test-uuid",
            final_report=mock_report,
            landscape=mock_landscape,
        )
        
        # Verify only valid source ID 1 is included
        assert len(result["supporting_sources"]) == 1
        assert result["supporting_sources"][0]["source_id"] == 1
        # ID 99 should be skipped


# ============================================================================
# TEST 8: Strength value is always valid
# ============================================================================

@pytest.mark.asyncio
async def test_generate_counter_argument_strength_always_valid(
    mock_report, mock_landscape, mock_sources
):
    """Test that generate_counter_argument strength value is always one of the valid options."""
    test_cases = [
        ("strong", "strong"),
        ("moderate", "moderate"),
        ("weak", "weak"),
        ("none", "none"),
        ("invalid_strength", "moderate"),  # Should default to moderate
    ]
    
    for llm_strength, expected_strength in test_cases:
        response = json.dumps({
            "counter_argument": f"Test with {llm_strength} strength.",
            "supporting_source_ids": [1],
            "strength": llm_strength,
            "explanation": "Test explanation.",
        })
        
        with patch("app.services.counter_argument_service.settings") as mock_settings, \
             patch("app.services.counter_argument_service.get_sources_by_session", new_callable=AsyncMock) as mock_get_sources, \
             patch("app.services.counter_argument_service.generate", new_callable=AsyncMock) as mock_generate:
            
            mock_settings.is_llm_mocked = False  # Mock the property
            mock_get_sources.return_value = mock_sources
            mock_generate.return_value = response
            
            result = await generate_counter_argument(
                session_id="test-uuid",
                final_report=mock_report,
                landscape=mock_landscape,
            )
            
            # Verify strength is valid
            assert result["strength"] == expected_strength
            assert result["strength"] in ["strong", "moderate", "weak", "none"]


# ============================================================================
# HELPER FUNCTION TESTS
# ============================================================================

def test_format_sources_for_prompt(mock_sources):
    """Test _format_sources_for_prompt formats sources correctly."""
    formatted = _format_sources_for_prompt(mock_sources)
    
    # Verify format
    assert "[1]" in formatted
    assert "example.com" in formatted
    assert "85.0" in formatted
    assert "Study shows X" in formatted
    
    lines = formatted.split("\n")
    assert len(lines) == 3


def test_parse_counter_argument_json_valid(mock_sources):
    """Test _parse_counter_argument_json with valid JSON."""
    response = json.dumps({
        "counter_argument": "Test counter-argument.",
        "supporting_source_ids": [1, 2],
        "strength": "strong",
        "explanation": "Test explanation.",
    })
    
    result = _parse_counter_argument_json(response, mock_sources)
    
    assert result["counter_argument"] == "Test counter-argument."
    assert len(result["supporting_sources"]) == 2
    assert result["strength"] == "strong"
    assert result["explanation"] == "Test explanation."


def test_parse_counter_argument_json_strips_markdown(mock_sources):
    """Test _parse_counter_argument_json strips markdown code blocks."""
    response = """```json
{
  "counter_argument": "Test.",
  "supporting_source_ids": [1],
  "strength": "weak",
  "explanation": "Test."
}
```"""
    
    result = _parse_counter_argument_json(response, mock_sources)
    
    assert result["counter_argument"] == "Test."
    assert result["strength"] == "weak"


def test_parse_counter_argument_json_missing_keys_raises(mock_sources):
    """Test _parse_counter_argument_json raises on missing keys."""
    response = json.dumps({
        "counter_argument": "Test.",
        # Missing supporting_source_ids, strength, explanation
    })
    
    with pytest.raises(ValueError, match="Missing required keys"):
        _parse_counter_argument_json(response, mock_sources)
