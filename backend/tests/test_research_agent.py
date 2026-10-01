"""
Test suite for research_agent.py
Tests the complete LangGraph workflow orchestration.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.research_agent import (
    run_research,
    run_research_with_refinement,
    refine_node,
    plan_node,
    search_node,
    score_node,
    ResearchState,
)


@pytest.mark.asyncio
async def test_run_research_vague_query_needs_refinement():
    """Test that vague query returns needs_refinement=True and stops"""
    with patch("app.config.settings.mock_mode", True):
        # Use a vague query (< 4 words)
        result = await run_research("apple")
        
        assert result["needs_refinement"] == True
        assert result["status"] == "needs_refinement"
        assert len(result["refinement_options"]) >= 4
        # Should not have proceeded to search
        assert "final_report" not in result or result.get("final_report") is None


@pytest.mark.asyncio
async def test_run_research_specific_query_completes():
    """Test that specific query produces status=complete"""
    with patch("app.config.settings.mock_mode", True):
        # Use a long specific query (>= 6 words in mock mode)
        query = "What are the environmental impacts of renewable energy adoption in Europe?"
        result = await run_research(query)
        
        assert result["status"] == "complete"
        assert result["needs_refinement"] == False


@pytest.mark.asyncio
async def test_run_research_produces_final_report():
    """Test that run_research produces non-empty final_report"""
    with patch("app.config.settings.mock_mode", True):
        query = "What are the health benefits of eating apples daily?"
        result = await run_research(query)
        
        assert "final_report" in result
        assert result["final_report"] is not None
        assert len(result["final_report"]) > 0
        assert isinstance(result["final_report"], str)


@pytest.mark.asyncio
async def test_run_research_produces_landscape():
    """Test that run_research produces landscape with three buckets"""
    with patch("app.config.settings.mock_mode", True):
        query = "What are the main causes of climate change today?"
        result = await run_research(query)
        
        assert "landscape" in result
        landscape = result["landscape"]
        
        # Check three buckets
        assert "consensus" in landscape
        assert "contested" in landscape
        assert "unknown" in landscape
        assert "summary" in landscape
        
        # Check summary structure
        assert "total_claims" in landscape["summary"]
        assert "consensus_count" in landscape["summary"]
        assert "contested_count" in landscape["summary"]
        assert "unknown_count" in landscape["summary"]


@pytest.mark.asyncio
async def test_refine_node_updates_state():
    """Test that refine_node updates state correctly"""
    with patch("app.config.settings.mock_mode", True):
        # Vague query
        state: ResearchState = {
            "original_query": "python",
            "session_id": "test-session",
            "status": "in_progress",
            "node_timings": {}
        }
        
        result = await refine_node(state)
        
        assert "needs_refinement" in result
        if result["needs_refinement"]:
            assert "refinement_options" in result
            assert result["status"] == "needs_refinement"
        else:
            assert "refined_query" in result


@pytest.mark.asyncio
async def test_plan_node_mock_mode_returns_all_engines():
    """Test that plan_node in MOCK_MODE returns all three engines"""
    with patch("app.config.settings.mock_mode", True):
        state: ResearchState = {
            "refined_query": "test query",
            "session_id": "test-session",
            "node_timings": {}
        }
        
        result = await plan_node(state)
        
        assert "planned_engines" in result
        engines = result["planned_engines"]
        assert isinstance(engines, list)
        assert set(engines) == {"google", "news", "scholar"}


@pytest.mark.asyncio
async def test_search_node_combines_results():
    """Test that search_node combines results from all engines"""
    with patch("app.config.settings.mock_mode", True), \
         patch("app.agents.research_agent.search_web", new_callable=AsyncMock) as mock_web, \
         patch("app.agents.research_agent.search_news", new_callable=AsyncMock) as mock_news, \
         patch("app.agents.research_agent.search_scholar", new_callable=AsyncMock) as mock_scholar:
        
        # Mock return values
        mock_web.return_value = [{"title": "Web 1", "domain": "web.com", "url": "http://web.com"}]
        mock_news.return_value = [{"title": "News 1", "domain": "news.com", "url": "http://news.com"}]
        mock_scholar.return_value = [{"title": "Scholar 1", "domain": "scholar.com", "url": "http://scholar.com"}]
        
        state: ResearchState = {
            "refined_query": "test query",
            "planned_engines": ["google", "news", "scholar"],
            "session_id": "test-session",
            "node_timings": {}
        }
        
        result = await search_node(state)
        
        assert "sources" in result
        sources = result["sources"]
        assert len(sources) == 3
        assert any("web.com" in str(s) for s in sources)
        assert any("news.com" in str(s) for s in sources)
        assert any("scholar.com" in str(s) for s in sources)


@pytest.mark.asyncio
async def test_node_timings_recorded():
    """Test that node timings are recorded"""
    with patch("app.config.settings.mock_mode", True):
        query = "What is artificial intelligence and machine learning?"
        result = await run_research(query)
        
        assert "node_timings" in result
        timings = result["node_timings"]
        assert isinstance(timings, dict)
        
        # Should have timing for at least refine node
        assert "refine" in timings
        assert timings["refine"] > 0


@pytest.mark.asyncio
async def test_score_node_sorts_by_credibility():
    """Test that score_node sorts sources by credibility"""
    with patch("app.config.settings.mock_mode", True):
        state: ResearchState = {
            "sources": [
                {"title": "Low", "domain": "example.com", "snippet": "test", "url": "http://example.com"},
                {"title": "High", "domain": "edu", "snippet": "test academic", "url": "http://edu"},
                {"title": "Medium", "domain": "org", "snippet": "test", "url": "http://org"}
            ],
            "session_id": "test-session",
            "node_timings": {}
        }
        
        result = await score_node(state)
        
        assert "scored_sources" in result
        scored = result["scored_sources"]
        assert len(scored) == 3
        
        # Should be sorted by credibility descending
        scores = [s.get("credibility_score", 0) for s in scored]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_run_research_with_refinement():
    """Test run_research_with_refinement continues from refined query"""
    with patch("app.config.settings.mock_mode", True):
        # Mock create_session and insert_sources so no real Supabase UUID is needed.
        # The session_id "test-session-123" is not a valid UUID, so DB operations
        # must be intercepted before they reach Postgres.
        with patch("app.db.neon_client.create_session", new_callable=AsyncMock) as mock_session, \
             patch("app.agents.research_agent.insert_sources", new_callable=AsyncMock) as mock_insert:
            mock_session.return_value = {"id": "test-session-123"}
            # Return minimal stored-source objects that downstream nodes expect
            mock_insert.return_value = [
                {"id": i + 1, "url": f"http://example.com/{i}", "session_id": "test-session-123"}
                for i in range(3)
            ]

            chosen_direction = "Apple Inc. stock performance in 2024 analysis"
            result = await run_research_with_refinement("test-session-123", chosen_direction)

            assert result["status"] == "complete"
            assert result["refined_query"] == chosen_direction
            assert "final_report" in result


# ============================================================================
# COUNTER-ARGUMENT NODE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_counter_argument_node_sets_state():
    """Test that counter_argument_node updates state correctly"""
    from app.agents.research_agent import counter_argument_node
    
    with patch("app.config.settings.mock_mode", True), \
         patch("app.db.neon_client.get_sources_by_session", new_callable=AsyncMock) as mock_get_sources, \
         patch("app.agents.research_agent.update_session_counter_argument", new_callable=AsyncMock):
        
        # Mock sources
        mock_get_sources.return_value = [
            {"id": 1, "url": "https://example.com/1", "domain": "example.com", 
             "title": "Source 1", "credibility_score": 80.0},
            {"id": 2, "url": "https://example.com/2", "domain": "example.com", 
             "title": "Source 2", "credibility_score": 70.0},
        ]
        
        # Create state with final report
        state = ResearchState(
            session_id="test-session-id",
            final_report="# Test Report\n\nThis is a test report with conclusions.",
            landscape={"consensus": [], "contested": [], "unknowns": []},
            node_timings={},
        )
        
        # Call counter_argument_node
        result_state = await counter_argument_node(state)
        
        # Verify counter_argument is set
        assert result_state["counter_argument"] is not None
        assert isinstance(result_state["counter_argument"], dict)
        
        # Verify structure
        counter = result_state["counter_argument"]
        assert "counter_argument" in counter
        assert "supporting_sources" in counter
        assert "strength" in counter
        assert "explanation" in counter
        
        # Verify types
        assert isinstance(counter["counter_argument"], str)
        assert isinstance(counter["supporting_sources"], list)
        assert isinstance(counter["strength"], str)
        assert isinstance(counter["explanation"], str)


@pytest.mark.asyncio
async def test_run_research_includes_counter_argument():
    """Test that full pipeline includes counter-argument"""
    with patch("app.config.settings.mock_mode", True):
        # Use specific query to avoid refinement
        query = "What are the long-term effects of climate change on agriculture?"
        result = await run_research(query)
        
        # Verify counter-argument was generated
        assert "counter_argument" in result
        assert result["counter_argument"] is not None
        
        # Verify structure
        counter = result["counter_argument"]
        assert "counter_argument" in counter
        assert "strength" in counter
        assert counter["strength"] in ["strong", "moderate", "weak", "none"]


@pytest.mark.asyncio
async def test_counter_argument_node_handles_missing_report():
    """Test that counter_argument_node handles missing final_report gracefully"""
    from app.agents.research_agent import counter_argument_node
    
    with patch("app.config.settings.mock_mode", True):
        # Create state WITHOUT final_report
        state = ResearchState(
            session_id="test-session-id",
            final_report="",  # Empty report
            landscape={},
            node_timings={},
        )
        
        # Call counter_argument_node
        result_state = await counter_argument_node(state)
        
        # Verify counter_argument is None
        assert result_state["counter_argument"] is None
