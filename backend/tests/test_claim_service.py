"""
Test suite for claim_service.py
Tests claim extraction, embedding, storage, and batch processing.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.claim_service import (
    extract_claims_from_text,
    embed_claim,
    extract_and_store_claims,
    extract_claims_batch
)
from app.db.neon_client import get_mock


@pytest.mark.asyncio
async def test_extract_claims_from_text_basic():
    """Test basic claim extraction from text"""
    # Need longer text (minimum 100 chars)
    source_text = "Paris is the capital of France and one of the most visited cities in the world. The Eiffel Tower was completed in 1889 and has become an iconic symbol of French culture."

    # Run in mock_mode so extraction uses the deterministic mock path instead
    # of making a real Gemini API call (avoids transient 503s in CI/CD).
    with patch("app.config.settings.mock_mode", True):
        claims = await extract_claims_from_text(source_text)
    
    assert isinstance(claims, list)
    assert len(claims) > 0
    for claim in claims:
        assert "claim" in claim
        assert "confidence" in claim
        assert isinstance(claim["claim"], str)
        assert len(claim["claim"]) > 0
        assert 0 <= claim["confidence"] <= 1


@pytest.mark.asyncio
async def test_extract_claims_empty_text():
    """Test claim extraction with empty text"""
    claims = await extract_claims_from_text("")
    
    assert isinstance(claims, list)
    assert len(claims) == 0


@pytest.mark.asyncio
async def test_extract_claims_short_text():
    """Test claim extraction with very short text (under 100 chars)"""
    claims = await extract_claims_from_text("Hello.")
    
    # Short text should return 0 claims
    assert isinstance(claims, list)
    assert len(claims) == 0


@pytest.mark.asyncio
async def test_embed_claim_basic():
    """Test embedding generation for a claim"""
    claim_text = "The Earth orbits the Sun."
    
    embedding = await embed_claim(claim_text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 1536  # Gemini embedding dimension
    assert all(isinstance(x, float) for x in embedding)


@pytest.mark.asyncio
async def test_embed_claim_deterministic_in_mock():
    """Test that embeddings are deterministic in mock mode"""
    claim_text = "Water boils at 100 degrees Celsius."
    
    embedding1 = await embed_claim(claim_text)
    embedding2 = await embed_claim(claim_text)
    
    # In mock mode, same text should produce same embedding
    assert embedding1 == embedding2


@pytest.mark.asyncio
async def test_extract_and_store_claims_basic():
    """Test end-to-end claim extraction and storage"""
    source = {
        "id": "test_source_store_1",
        "title": "Space Facts",
        "snippet": "The Moon orbits Earth in approximately 27 days. Earth is the third planet from the Sun and the only known planet with life in the universe.",
        "credibility_score": 85.0
    }
    session_id = "test-session-uuid"

    # "test-session-uuid" is not a valid UUID — mock insert_claims so the
    # fake ID never reaches Postgres (which enforces UUID syntax on the FK).
    # Also run in mock_mode=True so claim extraction uses the deterministic mock
    # path and does not make real Gemini API calls (avoids transient 503s and
    # keeps the test fast and stable).
    async def _fake_insert_claims(sess_id, claim_records):
        return [
            {
                "id": i + 1,
                "claim_text": cr["claim_text"],
                "source_id": cr["source_id"],
                "session_id": sess_id,
                "embedding": cr.get("embedding", [0.0] * 1536),
                "confidence": cr.get("confidence", 0.9),
            }
            for i, cr in enumerate(claim_records)
        ]

    with patch("app.config.settings.mock_mode", True), \
         patch("app.db.neon_client.insert_claims", side_effect=_fake_insert_claims):
        stored_claims = await extract_and_store_claims(source, session_id)

    assert isinstance(stored_claims, list)
    assert len(stored_claims) > 0

    # Verify stored claim structure
    for claim in stored_claims:
        assert "id" in claim
        assert "claim_text" in claim
        assert "source_id" in claim
        assert "embedding" in claim
        assert claim["source_id"] == source["id"]
        assert isinstance(claim["embedding"], list)
        assert len(claim["embedding"]) == 1536


@pytest.mark.asyncio
async def test_extract_and_store_claims_empty():
    """Test storage with source containing empty/short text"""
    source = {
        "id": "test_source_empty",
        "title": "",
        "snippet": "",  # Too short, will return no claims
        "credibility_score": 50.0
    }
    session_id = "test-session-uuid"
    
    stored_claims = await extract_and_store_claims(source, session_id)
    
    assert isinstance(stored_claims, list)
    assert len(stored_claims) == 0


@pytest.mark.asyncio
async def test_extract_claims_batch_basic():
    """Test batch claim extraction from multiple sources"""
    sources = [
        {
            "id": "batch_source_1",
            "title": "Python History",
            "snippet": "Python was created by Guido van Rossum in 1991. It is a high-level programming language known for its readability and simplicity.",
            "credibility_score": 90.0
        },
        {
            "id": "batch_source_2",
            "title": "JS History",
            "snippet": "JavaScript was created in 1995 by Brendan Eich at Netscape. It has become one of the most widely used programming languages in web development.",
            "credibility_score": 85.0
        }
    ]
    session_id = "test-batch-session"
    
    result = await extract_claims_batch(sources, session_id, top_n=2)
    
    assert isinstance(result, dict)
    assert "total_claims" in result
    assert "per_source" in result
    assert result["total_claims"] >= 0


@pytest.mark.asyncio
async def test_extract_claims_batch_empty_list():
    """Test batch extraction with empty source list"""
    session_id = "test-batch-empty"
    
    result = await extract_claims_batch([], session_id)
    
    assert isinstance(result, dict)
    assert result["total_claims"] == 0


@pytest.mark.asyncio
async def test_extract_claims_batch_with_empty_content():
    """Test batch extraction with some sources having empty content"""
    sources = [
        {
            "id": "batch_source_1",
            "title": "Valid Source",
            "snippet": "This is valid content with factual information about technology and science. It contains enough text to pass the minimum length requirement.",
            "credibility_score": 80.0
        },
        {
            "id": "batch_source_2",
            "title": "Empty Source",
            "snippet": "",  # Empty content
            "credibility_score": 70.0
        },
        {
            "id": "batch_source_3",
            "title": "Another Valid Source",
            "snippet": "More valid content with detailed information about various topics. This text is long enough to be processed by the claim extraction service.",
            "credibility_score": 75.0
        }
    ]
    session_id = "test-batch-mixed"
    
    result = await extract_claims_batch(sources, session_id, top_n=3)
    
    assert isinstance(result, dict)
    assert "total_claims" in result
    assert "per_source" in result
    # Should have claims only from sources with valid content
    if result["total_claims"] > 0:
        assert "batch_source_2" not in result["per_source"] or result["per_source"]["batch_source_2"] == 0
