"""
Test suite for conflict_service.py
Tests conflict detection, claim comparison, and landscape classification.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.conflict_service import (
    find_similar_claim_pairs,
    judge_pair,
    detect_conflicts,
    classify_information_landscape,
    _parse_judgment_json,
)


@pytest.mark.asyncio
async def test_find_similar_pairs_empty_session():
    """Test that empty session returns empty list"""
    with patch("app.db.supabase_client.get_claims_by_session", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []
        
        pairs = await find_similar_claim_pairs("empty-session")
        
        assert isinstance(pairs, list)
        assert len(pairs) == 0


@pytest.mark.asyncio
async def test_find_similar_pairs_deduplicates():
    """Test that pairs (a,b) and (b,a) are deduplicated"""
    # Create claims with different IDs
    claim_1 = {"id": 1, "claim_text": "Claim A", "embedding": [0.1] * 1536}
    claim_2 = {"id": 2, "claim_text": "Claim B", "embedding": [0.2] * 1536}
    mock_claims = [claim_1, claim_2]
    
    call_count = {"count": 0}
    
    with patch("app.db.supabase_client.get_claims_by_session", new_callable=AsyncMock) as mock_get, \
         patch("app.db.supabase_client.find_similar_claims", new_callable=AsyncMock) as mock_similar:
        
        mock_get.return_value = mock_claims
        
        # Mock find_similar_claims to return the other claim
        async def similar_side_effect(embedding, threshold, limit):
            call_count["count"] += 1
            # First call (for claim 1) returns claim 2
            if call_count["count"] == 1:
                return [{"claim": claim_2, "similarity": 0.85}]
            # Second call (for claim 2) returns claim 1 - this should be deduplicated!
            else:
                return [{"claim": claim_1, "similarity": 0.85}]
        
        mock_similar.side_effect = similar_side_effect
        
        pairs = await find_similar_claim_pairs("test-session")
        
        # Should only have one pair, not two (deduplicated)
        # Both (1,2) and (2,1) should resolve to the same canonical pair (1,2)
        assert len(pairs) == 1, f"Expected 1 pair but got {len(pairs)}: {[(p[0]['id'], p[1]['id']) for p in pairs]}"
        claim_a, claim_b, similarity = pairs[0]
        assert {claim_a["id"], claim_b["id"]} == {1, 2}


@pytest.mark.asyncio
async def test_find_similar_pairs_skips_self_matches():
    """Test that self-matches are skipped"""
    mock_claim = {"id": 1, "claim_text": "Test claim", "embedding": [0.1] * 1536}
    
    with patch("app.db.supabase_client.get_claims_by_session", new_callable=AsyncMock) as mock_get, \
         patch("app.db.supabase_client.find_similar_claims", new_callable=AsyncMock) as mock_similar:
        
        mock_get.return_value = [mock_claim]
        # Return the same claim as similar (self-match)
        mock_similar.return_value = [{"claim": mock_claim, "similarity": 1.0}]
        
        pairs = await find_similar_claim_pairs("test-session")
        
        # Should have no pairs (self-match filtered out)
        assert len(pairs) == 0


@pytest.mark.asyncio
async def test_judge_pair_returns_none_for_agreement():
    """Test that agreement relationship returns None in non-mock mode"""
    claim_a = {"id": 1, "claim_text": "The sky is blue"}
    claim_b = {"id": 2, "claim_text": "The sky appears blue during daytime"}
    
    # Since we're in mock mode by default, test will return mock conflict
    # To properly test, we need to patch at the config level
    with patch("app.config.settings.mock_mode", False), \
         patch("app.services.gemini_client.settings.mock_mode", False), \
         patch("app.services.gemini_client.get_client") as mock_client:
        
        # Mock the Gemini client response
        mock_response = MagicMock()
        mock_response.text = '{"relationship": "agreement", "confidence": 0.9, "explanation": "Both claims agree"}'
        
        mock_client.return_value.models.generate_content.return_value = mock_response
        
        result = await judge_pair(claim_a, claim_b)
        
        assert result is None


@pytest.mark.asyncio
async def test_judge_pair_returns_conflict_for_contradiction():
    """Test that contradiction relationship returns conflict dict in non-mock mode"""
    claim_a = {"id": 1, "claim_text": "Earth is flat"}
    claim_b = {"id": 2, "claim_text": "Earth is round"}
    
    with patch("app.config.settings.mock_mode", False), \
         patch("app.services.gemini_client.settings.mock_mode", False), \
         patch("app.services.gemini_client.get_client") as mock_client:
        
        # Mock the Gemini client response
        mock_response = MagicMock()
        mock_response.text = '{"relationship": "contradiction", "confidence": 0.95, "explanation": "Mutually exclusive claims"}'
        
        mock_client.return_value.models.generate_content.return_value = mock_response
        
        result = await judge_pair(claim_a, claim_b)
        
        assert result is not None
        assert result["claim_a_id"] == 1
        assert result["claim_b_id"] == 2
        assert result["conflict_type"] == "contradiction"
        assert result["confidence"] == 0.95
        assert "explanation" in result


@pytest.mark.asyncio
async def test_judge_pair_handles_malformed_json_with_retry():
    """Test that malformed JSON triggers retry logic in non-mock mode"""
    claim_a = {"id": 1, "claim_text": "Test A"}
    claim_b = {"id": 2, "claim_text": "Test B"}
    
    with patch("app.config.settings.mock_mode", False), \
         patch("app.services.gemini_client.settings.mock_mode", False), \
         patch("app.services.gemini_client.get_client") as mock_client:
        
        # First call returns malformed JSON, second call returns valid JSON
        mock_response_1 = MagicMock()
        mock_response_1.text = "This is not JSON at all"
        
        mock_response_2 = MagicMock()
        mock_response_2.text = '{"relationship": "disagreement", "confidence": 0.7, "explanation": "Minor differences"}'
        
        mock_client.return_value.models.generate_content.side_effect = [
            mock_response_1,
            mock_response_2
        ]
        
        result = await judge_pair(claim_a, claim_b)
        
        # Should succeed after retry
        assert result is not None
        assert result["conflict_type"] == "disagreement"
        assert mock_client.return_value.models.generate_content.call_count == 2  # Called twice due to retry


@pytest.mark.asyncio
async def test_judge_pair_mock_mode_returns_conflict():
    """Test that MOCK_MODE returns a synthetic conflict dict"""
    claim_a = {"id": 1, "claim_text": "Mock claim A"}
    claim_b = {"id": 2, "claim_text": "Mock claim B"}
    
    with patch("app.services.conflict_service.settings.mock_mode", True):
        result = await judge_pair(claim_a, claim_b)
        
        assert result is not None
        assert result["claim_a_id"] == 1
        assert result["claim_b_id"] == 2
        assert result["conflict_type"] == "contradiction"
        assert result["confidence"] == 0.8
        assert "Mock conflict" in result["explanation"]


@pytest.mark.asyncio
async def test_detect_conflicts_empty_when_no_pairs():
    """Test that detect_conflicts returns empty list when no pairs found"""
    with patch("app.services.conflict_service.find_similar_claim_pairs", new_callable=AsyncMock) as mock_pairs:
        mock_pairs.return_value = []
        
        conflicts = await detect_conflicts("test-session")
        
        assert isinstance(conflicts, list)
        assert len(conflicts) == 0


@pytest.mark.asyncio
async def test_detect_conflicts_stores_via_insert():
    """Test that detected conflicts are stored via insert_conflicts"""
    mock_pairs = [
        (
            {"id": 1, "claim_text": "Claim A"},
            {"id": 2, "claim_text": "Claim B"},
            0.85
        )
    ]
    
    mock_conflict = {
        "claim_a_id": 1,
        "claim_b_id": 2,
        "conflict_type": "contradiction",
        "confidence": 0.9,
        "explanation": "Test conflict"
    }
    
    mock_stored = {
        "id": 100,
        **mock_conflict
    }
    
    with patch("app.services.conflict_service.find_similar_claim_pairs", new_callable=AsyncMock) as mock_pairs_fn, \
         patch("app.services.conflict_service.judge_pair", new_callable=AsyncMock) as mock_judge, \
         patch("app.db.supabase_client.insert_conflicts", new_callable=AsyncMock) as mock_insert:
        
        mock_pairs_fn.return_value = mock_pairs
        mock_judge.return_value = mock_conflict
        mock_insert.return_value = [mock_stored]
        
        conflicts = await detect_conflicts("test-session")
        
        assert len(conflicts) == 1
        assert conflicts[0]["id"] == 100
        mock_insert.assert_called_once()


@pytest.mark.asyncio
async def test_classify_landscape_returns_valid_structure():
    """Test that classify_information_landscape returns correct structure"""
    mock_claims = [
        {"id": 1, "claim_text": "Test claim", "source_id": 1, "embedding": [0.1] * 1536}
    ]
    
    mock_sources = [
        {"id": 1, "domain": "test.com", "credibility_score": 70.0}
    ]
    
    with patch("app.db.supabase_client.get_claims_by_session", new_callable=AsyncMock) as mock_claims_fn, \
         patch("app.db.supabase_client.get_conflicts_by_session", new_callable=AsyncMock) as mock_conflicts, \
         patch("app.db.supabase_client.get_sources_by_session", new_callable=AsyncMock) as mock_sources_fn, \
         patch("app.db.supabase_client.find_similar_claims", new_callable=AsyncMock) as mock_similar:
        
        mock_claims_fn.return_value = mock_claims
        mock_conflicts.return_value = []
        mock_sources_fn.return_value = mock_sources
        mock_similar.return_value = []
        
        landscape = await classify_information_landscape("test-session")
        
        # Check structure
        assert "consensus" in landscape
        assert "contested" in landscape
        assert "unknown" in landscape
        assert "summary" in landscape
        
        # Check summary
        assert landscape["summary"]["total_claims"] == 1
        assert landscape["summary"]["consensus_count"] >= 0
        assert landscape["summary"]["contested_count"] >= 0
        assert landscape["summary"]["unknown_count"] >= 0


@pytest.mark.asyncio
async def test_classify_landscape_buckets_contested_claim():
    """Test that claims with conflicts are bucketed as contested"""
    mock_claims = [
        {"id": 1, "claim_text": "Claim A", "source_id": 1, "embedding": [0.1] * 1536},
        {"id": 2, "claim_text": "Claim B", "source_id": 2, "embedding": [0.2] * 1536},
    ]
    
    mock_conflicts = [
        {
            "id": 1,
            "claim_a_id": 1,
            "claim_b_id": 2,
            "conflict_type": "contradiction",
            "explanation": "Test conflict"
        }
    ]
    
    mock_sources = [
        {"id": 1, "domain": "test1.com", "credibility_score": 80.0},
        {"id": 2, "domain": "test2.com", "credibility_score": 75.0},
    ]
    
    with patch("app.db.supabase_client.get_claims_by_session", new_callable=AsyncMock) as mock_claims_fn, \
         patch("app.db.supabase_client.get_conflicts_by_session", new_callable=AsyncMock) as mock_conflicts_fn, \
         patch("app.db.supabase_client.get_sources_by_session", new_callable=AsyncMock) as mock_sources_fn, \
         patch("app.db.supabase_client.find_similar_claims", new_callable=AsyncMock) as mock_similar:
        
        mock_claims_fn.return_value = mock_claims
        mock_conflicts_fn.return_value = mock_conflicts
        mock_sources_fn.return_value = mock_sources
        mock_similar.return_value = []
        
        landscape = await classify_information_landscape("test-session")
        
        # Both claims should be contested
        assert landscape["summary"]["contested_count"] == 2
        assert len(landscape["contested"]) == 2
        
        # Check that contested claims have conflicts_with field
        for contested_claim in landscape["contested"]:
            assert "conflicts_with" in contested_claim
            assert len(contested_claim["conflicts_with"]) > 0


def test_parse_judgment_json_basic():
    """Test parsing basic JSON response"""
    json_str = '{"relationship": "contradiction", "confidence": 0.9, "explanation": "Test"}'
    
    result = _parse_judgment_json(json_str)
    
    assert result["relationship"] == "contradiction"
    assert result["confidence"] == 0.9


def test_parse_judgment_json_with_markdown():
    """Test parsing JSON wrapped in markdown code blocks"""
    json_str = '''```json
{"relationship": "disagreement", "confidence": 0.7, "explanation": "Test"}
```'''
    
    result = _parse_judgment_json(json_str)
    
    assert result["relationship"] == "disagreement"
    assert result["confidence"] == 0.7


def test_parse_judgment_json_missing_key_raises():
    """Test that missing 'relationship' key raises ValueError"""
    json_str = '{"confidence": 0.9, "explanation": "Test"}'
    
    with pytest.raises(ValueError, match="Missing 'relationship' key"):
        _parse_judgment_json(json_str)
