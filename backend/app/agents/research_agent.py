"""Research agent using LangGraph for orchestration.

This is the backbone of the entire backend: chains all services into a
state machine that takes a user query and produces a complete, cited
research report with an information landscape.
"""
import json
import logging
import time
import asyncio
import traceback
import statistics
from typing import Dict, Any, List, TypedDict, Optional
from functools import wraps

from langgraph.graph import StateGraph, END

from app.config import settings
from app.services import (
    score_sources_batch,
    extract_claims_batch,
    detect_conflicts,
    classify_information_landscape,
    refine_or_proceed,
    search_web,
    search_news,
    search_scholar,
    generate_counter_argument,
)
from app.services.gemini_client import generate
from app.db.supabase_client import (
    create_session,
    update_session_status,
    update_session_final_report,
    update_session_counter_argument,
    insert_sources,
    get_claims_by_session,
)

logger = logging.getLogger(__name__)


# ============================================================================
# STATE SCHEMA
# ============================================================================

class ResearchState(TypedDict, total=False):
    """Shared state for the research workflow."""
    # Input
    original_query: str
    refined_query: str
    session_id: str
    
    # Refinement
    needs_refinement: bool
    refinement_options: List[Dict[str, Any]]
    
    # Planning
    planned_engines: List[str]  # ["google", "news", "scholar"]
    
    # Sources
    sources: List[Dict[str, Any]]  # raw from SerpApi
    scored_sources: List[Dict[str, Any]]  # after credibility scoring
    stored_sources: List[Dict[str, Any]]  # after DB insert (have IDs)
    
    # Claims
    claims: List[Dict[str, Any]]  # extracted + embedded
    
    # Conflicts
    conflicts: List[Dict[str, Any]]
    
    # Landscape
    landscape: Dict[str, Any]  # consensus/contested/unknown
    
    # Report
    final_report: str
    
    # Counter-argument
    counter_argument: Optional[Dict[str, Any]]  # opposing perspective
    
    # Metadata
    status: str  # "in_progress" | "complete" | "failed" | "needs_refinement"
    error: Optional[str]
    node_timings: Dict[str, float]  # {node_name: duration_ms}


# ============================================================================
# NODE TIMING DECORATOR
# ============================================================================

def timed_node(node_name: str):
    """Decorator to time node execution."""
    def decorator(func):
        @wraps(func)
        async def wrapper(state: ResearchState) -> ResearchState:
            start = time.perf_counter()
            logger.info(f"Node {node_name} starting...")
            
            result = await func(state)
            
            duration_ms = (time.perf_counter() - start) * 1000
            if "node_timings" not in result:
                result["node_timings"] = {}
            result["node_timings"][node_name] = duration_ms
            
            logger.info(f"Node {node_name} completed in {duration_ms:.0f}ms")
            return result
        return wrapper
    return decorator


# ============================================================================
# NODES
# ============================================================================

@timed_node("refine")
async def refine_node(state: ResearchState) -> ResearchState:
    """
    NODE 1: Check if query needs refinement.
    
    If vague, set needs_refinement=True and stop.
    If specific, proceed to planning.
    """
    try:
        result = await refine_or_proceed(state["original_query"])
        
        if result["needs_refinement"]:
            logger.info(f"Query needs refinement: {len(result['options'])} options generated")
            state["needs_refinement"] = True
            state["refinement_options"] = result["options"]
            state["status"] = "needs_refinement"
        else:
            logger.info("Query is specific enough, proceeding")
            state["refined_query"] = result["proceed_with"]
            state["needs_refinement"] = False
            state["status"] = "in_progress"
        
        return state
        
    except Exception as e:
        logger.error(f"Node refine failed: {e}\n{traceback.format_exc()}")
        state["status"] = "failed"
        state["error"] = str(e)
        return state


@timed_node("plan")
async def plan_node(state: ResearchState) -> ResearchState:
    """
    NODE 2: Plan which search engines to use.
    
    Uses LLM to determine if query needs google/news/scholar.
    """
    try:
        refined_query = state["refined_query"]
        
        # Mock mode: use all three engines
        if settings.mock_mode:
            engines = ["google", "news", "scholar"]
            logger.info(f"MOCK MODE: Planned engines: {engines}")
            state["planned_engines"] = engines
            return state
        
        # Real mode: ask LLM
        prompt = f"""Given this research query: "{refined_query}"

Which search engines should be used? Choose from:
- "google"  (general web search)
- "news"    (recent news, past week)
- "scholar" (academic papers)

Return ONLY this JSON:
{{"engines": ["google", "news", "scholar"]}}

Rules:
- Always include "google"
- Add "news" if query involves recent events, trends, or current state
- Add "scholar" if query is academic, technical, or asks for evidence
- Minimum 1 engine, maximum 3"""
        
        response = await generate(prompt)
        
        # Parse JSON
        response = response.strip()
        if response.startswith("```"):
            lines = response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines).strip()
        
        data = json.loads(response)
        engines = data.get("engines", ["google"])
        
        logger.info(f"Planned engines: {engines}")
        state["planned_engines"] = engines
        return state
        
    except Exception as e:
        logger.error(f"Node plan failed: {e}\n{traceback.format_exc()}")
        # Fallback to google only
        logger.warning("Planning failed, falling back to google search only")
        state["planned_engines"] = ["google"]
        return state


@timed_node("search")
async def search_node(state: ResearchState) -> ResearchState:
    """
    NODE 3: Execute searches across planned engines.
    
    Runs searches concurrently and combines results.
    """
    try:
        engines = state["planned_engines"]
        refined_query = state["refined_query"]
        
        # Map engines to functions
        engine_map = {
            "google": search_web,
            "news": search_news,
            "scholar": search_scholar,
        }
        
        # Build tasks
        tasks = []
        for engine in engines:
            if engine in engine_map:
                tasks.append(engine_map[engine](refined_query))
        
        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        all_sources = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Search {engines[i]} failed: {result}")
                continue
            if isinstance(result, list):
                all_sources.extend(result)
        
        logger.info(f"Search complete: {len(all_sources)} sources from {len(engines)} engines")
        state["sources"] = all_sources
        return state
        
    except Exception as e:
        logger.error(f"Node search failed: {e}\n{traceback.format_exc()}")
        state["status"] = "failed"
        state["error"] = str(e)
        return state


@timed_node("score")
async def score_node(state: ResearchState) -> ResearchState:
    """
    NODE 4: Score sources by credibility.
    
    Applies heuristic credibility scoring to all sources.
    """
    try:
        sources = state["sources"]
        
        if not sources:
            logger.warning("No sources to score")
            state["scored_sources"] = []
            return state
        
        # Score all sources
        scored = score_sources_batch(sources)
        
        # Sort by credibility descending
        scored.sort(key=lambda s: s.get("credibility_score", 0), reverse=True)
        
        scores = [s.get("credibility_score", 0) for s in scored]
        max_score = max(scores) if scores else 0
        median_score = statistics.median(scores) if scores else 0
        
        logger.info(f"Scored {len(scored)} sources. Top score: {max_score:.1f}. Median: {median_score:.1f}.")
        state["scored_sources"] = scored
        return state
        
    except Exception as e:
        logger.error(f"Node score failed: {e}\n{traceback.format_exc()}")
        state["status"] = "failed"
        state["error"] = str(e)
        return state


@timed_node("store")
async def store_node(state: ResearchState) -> ResearchState:
    """
    NODE 5: Store sources in database.
    
    Inserts sources into Supabase and gets IDs.
    """
    try:
        session_id = state["session_id"]
        scored_sources = state["scored_sources"]
        
        if not scored_sources:
            logger.warning("No sources to store")
            state["stored_sources"] = []
            return state
        
        # Insert sources
        stored = await insert_sources(session_id, scored_sources)
        
        logger.info(f"Stored {len(stored)} sources")
        state["stored_sources"] = stored
        return state
        
    except Exception as e:
        logger.error(f"Node store failed: {e}\n{traceback.format_exc()}")
        state["status"] = "failed"
        state["error"] = str(e)
        return state


@timed_node("extract")
async def extract_node(state: ResearchState) -> ResearchState:
    """
    NODE 6: Extract claims from top sources.
    
    Uses LLM to extract verifiable claims, embeds them, stores in DB.
    """
    try:
        session_id = state["session_id"]
        stored_sources = state["stored_sources"]
        
        if not stored_sources:
            logger.warning("No sources to extract claims from")
            state["claims"] = []
            return state
        
        # Extract claims from top 10 sources
        result = await extract_claims_batch(stored_sources, session_id, top_n=10)
        
        # Fetch the inserted claims
        claims = await get_claims_by_session(session_id)
        
        logger.info(f"Extracted {result['total_claims']} claims from top {result['successful_sources']} sources")
        state["claims"] = claims
        return state
        
    except Exception as e:
        logger.error(f"Node extract failed: {e}\n{traceback.format_exc()}")
        state["status"] = "failed"
        state["error"] = str(e)
        return state


@timed_node("conflict")
async def conflict_node(state: ResearchState) -> ResearchState:
    """
    NODE 7: Detect conflicts between claims.
    
    Finds contradictions and disagreements using vector similarity + LLM.
    """
    try:
        session_id = state["session_id"]
        
        if not state.get("claims"):
            logger.warning("No claims to check for conflicts")
            state["conflicts"] = []
            return state
        
        # Detect conflicts
        conflicts = await detect_conflicts(session_id)
        
        logger.info(f"Detected {len(conflicts)} conflicts")
        state["conflicts"] = conflicts
        return state
        
    except Exception as e:
        logger.error(f"Node conflict failed: {e}\n{traceback.format_exc()}")
        state["status"] = "failed"
        state["error"] = str(e)
        return state


@timed_node("landscape")
async def landscape_node(state: ResearchState) -> ResearchState:
    """
    NODE 8: Classify information landscape.
    
    Buckets claims into consensus/contested/unknown based on conflicts
    and cross-references.
    """
    try:
        session_id = state["session_id"]
        
        if not state.get("claims"):
            logger.warning("No claims to classify")
            state["landscape"] = {
                "consensus": [],
                "contested": [],
                "unknown": [],
                "summary": {
                    "total_claims": 0,
                    "consensus_count": 0,
                    "contested_count": 0,
                    "unknown_count": 0,
                }
            }
            return state
        
        # Classify landscape
        landscape = await classify_information_landscape(session_id)
        
        summary = landscape["summary"]
        logger.info(
            f"Landscape: {summary['consensus_count']} consensus, "
            f"{summary['contested_count']} contested, {summary['unknown_count']} unknown"
        )
        state["landscape"] = landscape
        return state
        
    except Exception as e:
        logger.error(f"Node landscape failed: {e}\n{traceback.format_exc()}")
        state["status"] = "failed"
        state["error"] = str(e)
        return state


@timed_node("report")
async def report_node(state: ResearchState) -> ResearchState:
    """
    NODE 9: Generate final research report.
    
    Synthesizes landscape and sources into a cited markdown report.
    """
    try:
        refined_query = state["refined_query"]
        landscape = state["landscape"]
        stored_sources = state["stored_sources"]
        
        # Format sources
        formatted_sources = []
        for i, source in enumerate(stored_sources[:20], 1):  # Top 20 sources
            formatted_sources.append(
                f"{i}. {source.get('title', 'Untitled')} "
                f"({source.get('domain', 'unknown')}) "
                f"[Score: {source.get('credibility_score', 0):.0f}/100]\n"
                f"   {source.get('link', 'No URL')}"
            )
        
        sources_text = "\n".join(formatted_sources)
        
        # Build prompt
        prompt = f"""You are a research report writer. Synthesize a cited research report based on the analyzed information below.

Original query: {refined_query}

INFORMATION LANDSCAPE:

Consensus (well-supported across sources):
{json.dumps(landscape["consensus"][:10], indent=2)}

Contested (sources disagree):
{json.dumps(landscape["contested"][:10], indent=2)}

Unknown (single-source or low-credibility):
{json.dumps(landscape["unknown"][:10], indent=2)}

SOURCES (with credibility scores):
{sources_text}

Write a report with these sections:

1. Summary — 2-3 sentences answering the query
2. Consensus Findings — bullet points, each with [Source N] citations
3. Contested Points — bullet points showing disagreements
4. Unknowns — what could not be verified
5. Sources — numbered list with URL, domain, credibility score

Rules:
- Every factual claim must have a [Source N] citation
- Do not invent sources or claims not present in the input
- Be explicit about uncertainty
- Use markdown formatting"""
        
        # Generate report
        if settings.mock_mode:
            report = f"""# Research Report: {refined_query}

## Summary
Based on analysis of {len(stored_sources)} sources, this report synthesizes the findings on: {refined_query}.

## Consensus Findings
- Mock consensus finding 1 [Source 1]
- Mock consensus finding 2 [Source 2]

## Contested Points
- Mock contested point 1 [Source 1 vs Source 3]

## Unknowns
- Mock unknown aspect 1

## Sources
{sources_text}

---
*Generated in MOCK MODE*
"""
        else:
            report = await generate(prompt)
        
        logger.info(f"Report generated ({len(report)} chars)")
        state["final_report"] = report
        state["status"] = "complete"
        
        # Update session status and final_report in DB
        try:
            await update_session_status(state["session_id"], "complete")
            await update_session_final_report(state["session_id"], report)
        except Exception as e:
            logger.warning(f"Failed to update session in database: {e}")
        
        return state
        
    except Exception as e:
        logger.error(f"Node report failed: {e}\n{traceback.format_exc()}")
        state["status"] = "failed"
        state["error"] = str(e)
        return state


@timed_node("counter_argument")
async def counter_argument_node(state: ResearchState) -> ResearchState:
    """
    NODE 10: Generate the strongest counter-argument to the report.
    Prevents AI overconfidence by surfacing opposing perspectives.
    This is a nice-to-have feature — it never fails the pipeline.
    """
    try:
        session_id = state["session_id"]
        final_report = state.get("final_report", "")
        landscape = state.get("landscape", {})
        
        if not final_report:
            logger.warning("No final report, skipping counter-argument")
            state["counter_argument"] = None
            return state
        
        result = await generate_counter_argument(
            session_id=session_id,
            final_report=final_report,
            landscape=landscape,
        )
        
        logger.info(
            f"Counter-argument generated: strength={result.get('strength')}, "
            f"supporting_sources={len(result.get('supporting_sources', []))}"
        )
        
        state["counter_argument"] = result
        
        # Persist to database
        if result:
            try:
                await update_session_counter_argument(session_id, result)
            except Exception as e:
                logger.warning(f"Failed to persist counter-argument: {e}")
        
        return state
        
    except Exception as e:
        logger.error(f"Node counter_argument failed: {e}\n{traceback.format_exc()}")
        state["counter_argument"] = None
        return state


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def build_research_graph() -> StateGraph:
    """Build the LangGraph state machine for research workflow."""
    workflow = StateGraph(ResearchState)
    
    # Add nodes
    workflow.add_node("refine", refine_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("search", search_node)
    workflow.add_node("score", score_node)
    workflow.add_node("store", store_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("conflict", conflict_node)
    workflow.add_node("landscape", landscape_node)
    workflow.add_node("report", report_node)
    workflow.add_node("counter_argument", counter_argument_node)
    
    # Set entry point
    workflow.set_entry_point("refine")
    
    # Conditional edge from refine
    def should_continue_after_refine(state: ResearchState) -> str:
        """Decide if workflow should continue or stop for user refinement."""
        if state.get("needs_refinement"):
            return "end"
        return "continue"
    
    workflow.add_conditional_edges(
        "refine",
        should_continue_after_refine,
        {"end": END, "continue": "plan"}
    )
    
    # Linear chain from plan to counter_argument
    workflow.add_edge("plan", "search")
    workflow.add_edge("search", "score")
    workflow.add_edge("score", "store")
    workflow.add_edge("store", "extract")
    workflow.add_edge("extract", "conflict")
    workflow.add_edge("conflict", "landscape")
    workflow.add_edge("landscape", "report")
    workflow.add_edge("report", "counter_argument")
    workflow.add_edge("counter_argument", END)
    
    return workflow.compile()


# Create the compiled graph
research_graph = build_research_graph()


# ============================================================================
# PUBLIC ENTRY POINTS
# ============================================================================

async def run_research(query: str) -> Dict[str, Any]:
    """
    Run the full research pipeline for a query.
    
    Creates a session, runs the graph, returns the final state.
    
    Args:
        query: User's research query
    
    Returns:
        Final state dict with all results
    
    Examples:
        >>> result = await run_research("What is climate change?")
        >>> result["status"]
        'complete'
        >>> "final_report" in result
        True
    """
    # Reset session call counter for quota management
    from app.services.gemini_client import reset_session_counter
    reset_session_counter()
    
    # Create session
    session = await create_session(query)
    session_id = session["id"]
    
    logger.info(f"Starting research for session {session_id}: {query}")
    
    # Initialize state
    initial_state: ResearchState = {
        "original_query": query,
        "refined_query": query,  # Default to original, refine_node will override if needed
        "session_id": session_id,
        "status": "in_progress",
        "needs_refinement": False,
        "node_timings": {}
    }
    
    # Run graph
    final_state = await research_graph.ainvoke(initial_state)
    
    # Log summary
    if final_state.get("status") == "complete":
        logger.info(
            f"Research complete: {len(final_state.get('sources', []))} sources, "
            f"{len(final_state.get('claims', []))} claims, "
            f"{len(final_state.get('conflicts', []))} conflicts"
        )
    elif final_state.get("status") == "needs_refinement":
        logger.info(
            f"Research paused: query needs refinement "
            f"({len(final_state.get('refinement_options', []))} options)"
        )
    else:
        logger.error(f"Research failed: {final_state.get('error', 'Unknown error')}")
    
    return final_state


async def run_research_with_refinement(
    session_id: str,
    chosen_direction: str,
) -> Dict[str, Any]:
    """
    Continue a refined research flow after user chose a direction.
    
    Args:
        session_id: Existing session ID
        chosen_direction: The refined query direction user selected
    
    Returns:
        Final state dict with all results
    
    Examples:
        >>> result = await run_research_with_refinement(
        ...     "session-uuid",
        ...     "Apple Inc. stock performance in 2024"
        ... )
        >>> result["status"]
        'complete'
    """
    logger.info(f"Continuing research for session {session_id} with: {chosen_direction}")
    
    # Initialize state (skip refinement node)
    initial_state: ResearchState = {
        "original_query": chosen_direction,
        "refined_query": chosen_direction,
        "session_id": session_id,
        "needs_refinement": False,
        "status": "in_progress",
        "node_timings": {}
    }
    
    # Build a graph that starts at plan (skip refine)
    workflow = StateGraph(ResearchState)
    workflow.add_node("plan", plan_node)
    workflow.add_node("search", search_node)
    workflow.add_node("score", score_node)
    workflow.add_node("store", store_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("conflict", conflict_node)
    workflow.add_node("landscape", landscape_node)
    workflow.add_node("report", report_node)
    
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "search")
    workflow.add_edge("search", "score")
    workflow.add_edge("score", "store")
    workflow.add_edge("store", "extract")
    workflow.add_edge("extract", "conflict")
    workflow.add_edge("conflict", "landscape")
    workflow.add_edge("landscape", "report")
    workflow.add_edge("report", END)
    
    refined_graph = workflow.compile()
    
    # Run graph
    final_state = await refined_graph.ainvoke(initial_state)
    
    # Log summary
    if final_state.get("status") == "complete":
        logger.info(
            f"Refined research complete: {len(final_state.get('sources', []))} sources, "
            f"{len(final_state.get('claims', []))} claims"
        )
    
    return final_state


# ============================================================================
# LEGACY CLASS (for backward compatibility)
# ============================================================================

class ResearchAgent:
    """Legacy class wrapper for backward compatibility."""
    
    def __init__(self):
        """Initialize the research agent."""
        logger.info("Research agent initialized successfully")
    
    async def research(self, query: str) -> Dict[str, Any]:
        """
        Execute research workflow for a given query.
        
        Args:
            query: Research query
            
        Returns:
            Research results
        """
        return await run_research(query)
