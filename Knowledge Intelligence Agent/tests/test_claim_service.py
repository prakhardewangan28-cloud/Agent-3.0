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
from app.db.supabase_client import get_supabase_client


@pytest.mark.asyncio
async def test_extract_claims_from_text_basic():
    """Test basic claim extraction from text"""
    source_text = "Paris is the capital of France. The Eiffel Tower was completed in 1889."
    source_id = "test_source_1"
    
    claims = await extract_claims_from_text(source_text, source_id)
    
    assert isinstance(claims, list)
    assert len(claims) > 0
    for claim in claims:
        assert "claim_text" in claim
        assert "source_id" in claim
        assert claim["source_id"] == source_id
        assert isinstance(claim["claim_text"], str)
        assert len(claim["claim_text"]) > 0


@pytest.mark.asyncio
async def test_extract_claims_empty_text():
    """Test claim extraction with empty text"""
    claims = await extract_claims_from_text("", "test_source_2")
    
    assert isinstance(claims, list)
    assert len(claims) == 0


@pytest.mark.asyncio
async def test_extract_claims_short_text():
    """Test claim extraction with very short text"""
    claims = await extract_claims_from_text("Hello.", "test_source_3")
    
    # Short text might return 0 or 1 claim depending on implementation
    assert isinstance(claims, list)


@pytest.mark.asyncio
async def test_embed_claim_basic():
    """Test embedding generation for a claim"""
    claim_text = "The Earth orbits the Sun."
    
    embedding = await embed_claim(claim_text)
    
    assert isinstance(embedding, list)
    assert len(embedding) == 768  # Standard embedding dimension
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
    source_text = "The Moon orbits Earth. Earth is the third planet from the Sun."
    source_id = "test_source_store_1"
    
    stored_claims = await extract_and_store_claims(source_text, source_id)
    
    assert isinstance(stored_claims, list)
    assert len(stored_claims) > 0
    
    # Verify stored claim structure
    for claim in stored_claims:
        assert "id" in claim
        assert "claim_text" in claim
        assert "source_id" in claim
        assert "embedding" in claim
        assert claim["source_id"] == source_id
        assert isinstance(claim["embedding"], list)
        assert len(claim["embedding"]) == 768


@pytest.mark.asyncio
async def test_extract_and_store_claims_empty():
    """Test storage with empty text"""
    stored_claims = await extract_and_store_claims("", "test_source_empty")
    
    assert isinstance(stored_claims, list)
    assert len(stored_claims) == 0


@pytest.mark.asyncio
async def test_extract_claims_batch_basic():
    """Test batch claim extraction from multiple sources"""
    sources = [
        {
            "id": "batch_source_1",
            "content": "Python was created by Guido van Rossum.",
            "title": "Python History"
        },
        {
            "id": "batch_source_2",
            "content": "JavaScript was created in 1995.",
            "title": "JS History"
        }
    ]
    
    all_claims = await extract_claims_batch(sources)
    
    assert isinstance(all_claims, list)
    assert len(all_claims) > 0
    
    # Verify claims from multiple sources
    source_ids = set(claim["source_id"] for claim in all_claims)
    assert len(source_ids) > 0


@pytest.mark.asyncio
async def test_extract_claims_batch_empty_list():
    """Test batch extraction with empty source list"""
    all_claims = await extract_claims_batch([])
    
    assert isinstance(all_claims, list)
    assert len(all_claims) == 0


@pytest.mark.asyncio
async def test_extract_claims_batch_with_empty_content():
    """Test batch extraction with some sources having empty content"""
    sources = [
        {
            "id": "batch_source_1",
            "content": "Valid content with facts.",
            "title": "Valid Source"
        },
        {
            "id": "batch_source_2",
            "content": "",
            "title": "Empty Source"
        },
        {
            "id": "batch_source_3",
            "content": "More valid content.",
            "title": "Another Valid Source"
        }
    ]
    
    all_claims = await extract_claims_batch(sources)
    
    assert isinstance(all_claims, list)
    # Should only have claims from sources with content
    source_ids = set(claim["source_id"] for claim in all_claims)
    assert "batch_source_2" not in source_ids or len(all_claims) == 0 or all(
        claim["source_id"] != "batch_source_2" for claim in all_claims
    )
