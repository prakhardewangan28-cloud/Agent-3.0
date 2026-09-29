"""
Test suite for refinement_service.py
Tests query vagueness detection and refinement generation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.refinement_service import (
    is_vague,
    generate_refinements,
    refine_or_proceed,
    _parse_vagueness_json,
    _parse_refinements_json,
)


@pytest.mark.asyncio
async def test_is_vague_returns_true_for_ambiguous_words():
    """Test that single-word ambiguous queries return True"""
    # Test with different ambiguous words
    assert await is_vague("Apple") == True
    assert await is_vague("python") == True
    assert await is_vague("JAVA") == True


@pytest.mark.asyncio
async def test_is_vague_returns_false_for_very_short():
    """Test that very short queries (<3 chars) return False"""
    assert await is_vague("AI") == False
    assert await is_vague("a") == False
    assert await is_vague("") == False


@pytest.mark.asyncio
async def test_is_vague_returns_true_for_short_queries():
    """Test that queries with <4 words return True"""
    assert await is_vague("climate change") == True
    assert await is_vague("AI ethics") == True
    assert await is_vague("quantum computing") == True


@pytest.mark.asyncio
async def test_is_vague_returns_false_for_specific_queries():
    """Test that specific multi-word queries return False in mock mode"""
    # In mock mode, queries with 6+ words are considered specific
    with patch("app.config.settings.mock_mode", True):
        query = "What are the health benefits of eating apples daily?"
        result = await is_vague(query)
        # Query has 10 words, should be False in mock mode
        assert result == False


@pytest.mark.asyncio
async def test_is_vague_mock_mode_word_count():
    """Test that is_vague in MOCK_MODE follows word-count rule"""
    with patch("app.config.settings.mock_mode", True):
        # 5 words: vague (< 6)
        assert await is_vague("this is a short query") == True
        
        # 6 words: not vague (>= 6)
        assert await is_vague("this is a longer specific query now") == False


@pytest.mark.asyncio
async def test_generate_refinements_mock_mode():
    """Test that generate_refinements in MOCK_MODE returns 4 directions"""
    with patch("app.config.settings.mock_mode", True):
        directions = await generate_refinements("apple")
        
        assert isinstance(directions, list)
        assert len(directions) == 4
        
        # Check structure
        for direction in directions:
            assert "direction" in direction
            assert "rationale" in direction
            assert "type" in direction


@pytest.mark.asyncio
async def test_generate_refinements_parses_valid_json():
    """Test that generate_refinements parses valid JSON correctly"""
    mock_response = '''{
        "directions": [
            {"direction": "Question 1", "rationale": "Reason 1", "type": "academic"},
            {"direction": "Question 2", "rationale": "Reason 2", "type": "industry"}
        ]
    }'''
    
    with patch("app.config.settings.mock_mode", False), \
         patch("app.services.gemini_client.get_client") as mock_client:
        
        mock_gen_response = MagicMock()
        mock_gen_response.text = mock_response
        mock_client.return_value.models.generate_content.return_value = mock_gen_response
        
        directions = await generate_refinements("vague query")
        
        assert len(directions) == 2
        assert directions[0]["direction"] == "Question 1"
        assert directions[1]["type"] == "industry"


@pytest.mark.asyncio
async def test_generate_refinements_handles_malformed_json():
    """Test that generate_refinements handles malformed JSON with retry"""
    # First call returns malformed, second returns valid
    mock_response_1 = "This is not JSON"
    mock_response_2 = '''{
        "directions": [
            {"direction": "Fallback question", "rationale": "Reason", "type": "context"}
        ]
    }'''
    
    with patch("app.config.settings.mock_mode", False), \
         patch("app.services.gemini_client.get_client") as mock_client:
        
        mock_gen_1 = MagicMock()
        mock_gen_1.text = mock_response_1
        
        mock_gen_2 = MagicMock()
        mock_gen_2.text = mock_response_2
        
        mock_client.return_value.models.generate_content.side_effect = [
            mock_gen_1,
            mock_gen_2
        ]
        
        directions = await generate_refinements("vague query")
        
        # Should succeed after retry
        assert len(directions) >= 1
        assert mock_client.return_value.models.generate_content.call_count == 2


@pytest.mark.asyncio
async def test_refine_or_proceed_specific_query():
    """Test that refine_or_proceed returns needs_refinement=False for specific query"""
    # Use a long query that won't be considered vague in mock mode
    query = "What are the environmental impacts of renewable energy adoption in Europe?"
    
    with patch("app.config.settings.mock_mode", True):
        result = await refine_or_proceed(query)
        
        assert result["needs_refinement"] == False
        assert result["proceed_with"] == query
        assert result["options"] == []


@pytest.mark.asyncio
async def test_refine_or_proceed_vague_query():
    """Test that refine_or_proceed returns needs_refinement=True with options for vague query"""
    query = "apple"
    
    with patch("app.config.settings.mock_mode", True):
        result = await refine_or_proceed(query)
        
        assert result["needs_refinement"] == True
        assert result["proceed_with"] is None
        assert len(result["options"]) >= 4
        assert result["original_query"] == query


def test_parse_vagueness_json_basic():
    """Test parsing basic vagueness JSON"""
    json_str = '{"is_vague": true, "reason": "Multiple interpretations"}'
    
    result = _parse_vagueness_json(json_str)
    
    assert result["is_vague"] == True
    assert "reason" in result


def test_parse_vagueness_json_with_markdown():
    """Test parsing JSON wrapped in markdown"""
    json_str = '''```json
{"is_vague": false, "reason": "Specific query"}
```'''
    
    result = _parse_vagueness_json(json_str)
    
    assert result["is_vague"] == False


def test_parse_vagueness_json_missing_key_raises():
    """Test that missing 'is_vague' key raises ValueError"""
    json_str = '{"reason": "Test"}'
    
    with pytest.raises(ValueError, match="Missing 'is_vague' key"):
        _parse_vagueness_json(json_str)


def test_parse_refinements_json_basic():
    """Test parsing basic refinements JSON"""
    json_str = '''{"directions": [
        {"direction": "Q1", "rationale": "R1", "type": "academic"}
    ]}'''
    
    result = _parse_refinements_json(json_str)
    
    assert "directions" in result
    assert len(result["directions"]) == 1


def test_parse_refinements_json_missing_key_raises():
    """Test that missing 'directions' key raises ValueError"""
    json_str = '{"other": "data"}'
    
    with pytest.raises(ValueError, match="Missing 'directions' key"):
        _parse_refinements_json(json_str)
