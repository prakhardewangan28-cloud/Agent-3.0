"""Test script to verify database functions work correctly."""
import asyncio
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, '.')

from app.db import (
    create_session,
    update_session_status,
    get_session,
    insert_sources,
    get_sources_by_session,
    update_source_ai_flag,
    insert_claims,
    get_claims_by_session,
    find_similar_claims,
    insert_conflicts,
    get_conflicts_by_session,
    insert_evidence_edge,
    get_evidence_graph,
)


async def test_database_functions():
    """Test all database functions."""
    
    print("=" * 70)
    print("DATABASE FUNCTION TESTING")
    print("=" * 70)
    print()
    
    try:
        # ====================================================================
        # TEST 1: Create Research Session
        # ====================================================================
        print("TEST 1: Creating research session...")
        session = await create_session(
            original_query="What is the impact of climate change on polar bears?"
        )
        session_id = session["id"]
        print(f"✓ Session created: {session_id}")
        print(f"  Status: {session['status']}")
        print(f"  Created: {session['created_at']}")
        print()
        
        # ====================================================================
        # TEST 2: Get Session
        # ====================================================================
        print("TEST 2: Retrieving session...")
        retrieved = await get_session(session_id)
        print(f"✓ Session retrieved: {retrieved['original_query']}")
        print()
        
        # ====================================================================
        # TEST 3: Insert Sources
        # ====================================================================
        print("TEST 3: Inserting sources...")
        sources = [
            {
                "url": "https://example.com/article1",
                "title": "Climate Change Effects on Arctic Wildlife",
                "snippet": "Studies show significant impact...",
                "domain": "example.com",
                "engine": "google",
                "credibility_score": 0.85,
                "score_breakdown": {
                    "domain_authority": 0.8,
                    "citation_count": 150,
                    "recency": 0.9
                }
            },
            {
                "url": "https://nature.com/polar-bears",
                "title": "Polar Bear Population Decline",
                "snippet": "Research indicates population decrease...",
                "domain": "nature.com",
                "engine": "scholar",
                "credibility_score": 0.95,
                "is_ai_generated": False,
                "ai_generation_confidence": 0.1
            },
            {
                "url": "https://news.example.com/bears",
                "title": "Latest News on Polar Bears",
                "snippet": "Recent developments suggest...",
                "domain": "news.example.com",
                "engine": "news",
                "credibility_score": 0.65
            }
        ]
        inserted_sources = await insert_sources(session_id, sources)
        print(f"✓ {len(inserted_sources)} sources inserted")
        for src in inserted_sources:
            print(f"  - [{src['id']}] {src['title']} (score: {src['credibility_score']})")
        print()
        
        # ====================================================================
        # TEST 4: Get Sources by Session
        # ====================================================================
        print("TEST 4: Retrieving sources...")
        all_sources = await get_sources_by_session(session_id)
        print(f"✓ Retrieved {len(all_sources)} sources")
        print()
        
        # ====================================================================
        # TEST 5: Update Source AI Flag
        # ====================================================================
        print("TEST 5: Updating AI flag for source...")
        source_id = inserted_sources[0]["id"]
        updated_source = await update_source_ai_flag(source_id, True, 0.85)
        print(f"✓ Source {source_id} updated:")
        print(f"  AI Generated: {updated_source['is_ai_generated']}")
        print(f"  Confidence: {updated_source['ai_generation_confidence']}")
        print()
        
        # ====================================================================
        # TEST 6: Insert Claims
        # ====================================================================
        print("TEST 6: Inserting claims...")
        claims = [
            {
                "source_id": inserted_sources[0]["id"],
                "claim_text": "Polar bear populations are declining due to sea ice loss",
                "confidence": 0.9,
                "embedding": [0.1] * 1536  # Dummy embedding
            },
            {
                "source_id": inserted_sources[1]["id"],
                "claim_text": "Arctic sea ice extent has decreased by 40% since 1979",
                "confidence": 0.95,
                "embedding": [0.2] * 1536
            },
            {
                "source_id": inserted_sources[2]["id"],
                "claim_text": "Conservation efforts are showing positive results",
                "confidence": 0.7,
                "embedding": [0.3] * 1536
            }
        ]
        inserted_claims = await insert_claims(session_id, claims)
        print(f"✓ {len(inserted_claims)} claims inserted")
        for claim in inserted_claims:
            print(f"  - [{claim['id']}] {claim['claim_text'][:50]}...")
        print()
        
        # ====================================================================
        # TEST 7: Get Claims by Session
        # ====================================================================
        print("TEST 7: Retrieving claims...")
        all_claims = await get_claims_by_session(session_id)
        print(f"✓ Retrieved {len(all_claims)} claims")
        print()
        
        # ====================================================================
        # TEST 8: Find Similar Claims
        # ====================================================================
        print("TEST 8: Finding similar claims...")
        query_embedding = [0.15] * 1536  # Dummy query embedding
        similar = await find_similar_claims(
            session_id,
            query_embedding,
            threshold=0.5,
            limit=5
        )
        print(f"✓ Found {len(similar)} similar claims")
        for claim in similar:
            print(f"  - Similarity: {claim['similarity']:.4f}")
            print(f"    Text: {claim['claim_text'][:50]}...")
        print()
        
        # ====================================================================
        # TEST 9: Insert Conflicts
        # ====================================================================
        print("TEST 9: Inserting conflicts...")
        conflicts = [
            {
                "claim_a_id": inserted_claims[0]["id"],
                "claim_b_id": inserted_claims[2]["id"],
                "conflict_type": "contradiction",
                "confidence": 0.8,
                "explanation": "One claim shows decline, other shows positive results"
            }
        ]
        inserted_conflicts = await insert_conflicts(session_id, conflicts)
        print(f"✓ {len(inserted_conflicts)} conflicts inserted")
        for conflict in inserted_conflicts:
            print(f"  - Type: {conflict['conflict_type']}")
            print(f"    Confidence: {conflict['confidence']}")
        print()
        
        # ====================================================================
        # TEST 10: Get Conflicts by Session
        # ====================================================================
        print("TEST 10: Retrieving conflicts...")
        all_conflicts = await get_conflicts_by_session(session_id)
        print(f"✓ Retrieved {len(all_conflicts)} conflicts")
        print()
        
        # ====================================================================
        # TEST 11: Insert Evidence Edge
        # ====================================================================
        print("TEST 11: Inserting evidence edge...")
        edge = {
            "source_a_id": inserted_sources[0]["id"],
            "source_b_id": inserted_sources[1]["id"],
            "edge_type": "supports",
            "confidence": 0.9,
            "explanation": "Both sources corroborate the declining population"
        }
        inserted_edge = await insert_evidence_edge(session_id, edge)
        print(f"✓ Evidence edge inserted")
        print(f"  Type: {inserted_edge['edge_type']}")
        print(f"  Confidence: {inserted_edge['confidence']}")
        print()
        
        # ====================================================================
        # TEST 12: Get Evidence Graph
        # ====================================================================
        print("TEST 12: Retrieving evidence graph...")
        graph = await get_evidence_graph(session_id)
        print(f"✓ Evidence graph retrieved")
        print(f"  Nodes (sources): {len(graph['nodes'])}")
        print(f"  Edges: {len(graph['edges'])}")
        print()
        
        # ====================================================================
        # TEST 13: Update Session Status
        # ====================================================================
        print("TEST 13: Updating session status...")
        updated = await update_session_status(
            session_id,
            "complete",
            refined_query="Impact of climate change on polar bear populations and habitats"
        )
        print(f"✓ Session status updated to: {updated['status']}")
        print(f"  Refined query: {updated['refined_query']}")
        print(f"  Completed at: {updated['completed_at']}")
        print()
        
        # ====================================================================
        # SUMMARY
        # ====================================================================
        print("=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print()
        print("Summary:")
        print(f"  Session ID: {session_id}")
        print(f"  Sources: {len(all_sources)}")
        print(f"  Claims: {len(all_claims)}")
        print(f"  Conflicts: {len(all_conflicts)}")
        print(f"  Evidence Edges: {len(graph['edges'])}")
        print()
        print("Database layer is fully functional!")
        print()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    print("\n🧪 Testing Database Functions\n")
    
    # Check if config is loaded
    try:
        from app.config import settings
        print(f"✓ Configuration loaded")
        print(f"  Supabase URL: {settings.supabase_url[:30]}...")
        print(f"  Embedding Dim: {settings.embedding_dim}")
        print()
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        print("   Make sure .env file exists with SUPABASE_URL and SUPABASE_KEY")
        sys.exit(1)
    
    # Run tests
    success = asyncio.run(test_database_functions())
    
    if success:
        print("🎉 All database functions verified!")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Check the output above.")
        sys.exit(1)
