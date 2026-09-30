"""API routes for the research pipeline.

This is the boundary between the intelligence layer and the user interface.
Exposes REST endpoints and real-time SSE streaming.
"""
import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse

from app.config import settings
from app.models.schemas import (
    HealthResponse,
    ResearchStartRequest,
    ResearchStartResponse,
    RefineRequest,
    RefineResponse,
    SessionListItem,
)
from app.agents import run_research, run_research_with_refinement
from app.services import refine_or_proceed
from app.db.supabase_client import (
    create_session,
    get_session,
    get_sources_by_session,
    get_conflicts_by_session,
    update_session_status,
)
from app.services import classify_information_landscape

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# SSE STREAMING SUPPORT
# ============================================================================

# In-memory storage for SSE streams per session
_session_streams: Dict[str, asyncio.Queue] = {}


def publish_event(session_id: str, event: Dict[str, Any]) -> None:
    """
    Publish an event to the SSE stream for a session.
    
    Args:
        session_id: Session ID
        event: Event dict to publish
    """
    if session_id in _session_streams:
        try:
            _session_streams[session_id].put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(f"Stream queue full for session {session_id}, dropping event")


def get_stream(session_id: str) -> asyncio.Queue:
    """
    Get or create the SSE stream queue for a session.
    
    Args:
        session_id: Session ID
    
    Returns:
        asyncio.Queue for the stream
    """
    if session_id not in _session_streams:
        _session_streams[session_id] = asyncio.Queue(maxsize=100)
    return _session_streams[session_id]


def close_stream(session_id: str) -> None:
    """
    Close and remove the SSE stream for a session.
    
    Args:
        session_id: Session ID
    """
    if session_id in _session_streams:
        del _session_streams[session_id]
        logger.info(f"Stream closed for session {session_id}")


# ============================================================================
# BACKGROUND TASK WRAPPERS
# ============================================================================

async def run_research_background(session_id: str, query: str) -> None:
    """
    Run research in background and publish events.
    
    Args:
        session_id: Session ID
        query: Research query
    """
    try:
        publish_event(session_id, {
            "status": "started",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        result = await run_research_with_refinement(session_id, query)
        
        publish_event(session_id, {
            "status": "complete" if result.get("status") == "complete" else "failed",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Close stream after completion
        close_stream(session_id)
        
    except Exception as e:
        logger.error(f"Background research failed for {session_id}: {e}\n{traceback.format_exc()}")
        publish_event(session_id, {
            "status": "failed",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
        close_stream(session_id)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Health status with mock mode and version info
    """
    return HealthResponse(
        status="ok",
        mock_mode=settings.mock_mode,
        version="0.1.0"
    )


@router.post("/research/start", response_model=ResearchStartResponse)
async def start_research(request: ResearchStartRequest):
    """
    Start a new research session.
    
    If query is vague, returns refinement options and waits for user choice.
    If query is specific, starts research in background and returns immediately.
    
    Args:
        request: Research start request with query
    
    Returns:
        Session ID and either refinement options or in-progress status
    """
    query = request.query
    logger.info(f"POST /api/v1/research/start  query={query[:50]}...")
    
    try:
        # Create session
        session = await create_session(query)
        session_id = session["id"]
        logger.info(f"Session created: {session_id}")
        
        # Check if refinement needed
        refinement_result = await refine_or_proceed(query)
        
        if refinement_result["needs_refinement"]:
            # Update session status
            await update_session_status(session_id, "needs_refinement")
            
            return ResearchStartResponse(
                session_id=session_id,
                needs_refinement=True,
                options=refinement_result["options"],
                status="needs_refinement"
            )
        
        # Query is specific, start research in background
        asyncio.create_task(run_research_background(session_id, query))
        
        return ResearchStartResponse(
            session_id=session_id,
            needs_refinement=False,
            options=[],
            status="in_progress"
        )
        
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Error {error_id} in start_research: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error (error_id: {error_id})"
        )


@router.post("/research/refine", response_model=RefineResponse)
async def refine_research(request: RefineRequest):
    """
    Continue research with a refined query direction.
    
    Args:
        request: Refine request with session_id and chosen direction
    
    Returns:
        Session ID and in-progress status
    """
    session_id = request.session_id
    chosen_direction = request.chosen_direction
    
    logger.info(f"POST /api/v1/research/refine  session={session_id}, direction={chosen_direction[:50]}...")
    
    try:
        # Verify session exists
        session = await get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Start research in background
        asyncio.create_task(run_research_background(session_id, chosen_direction))
        
        return RefineResponse(
            session_id=session_id,
            status="in_progress"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Error {error_id} in refine_research: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error (error_id: {error_id})"
        )


@router.get("/research/{session_id}")
async def get_research_results(session_id: str):
    """
    Get complete research results for a session.
    
    Args:
        session_id: Session ID
    
    Returns:
        Full session data with sources, conflicts, landscape, and report
    """
    logger.info(f"GET /api/v1/research/{session_id}")
    
    try:
        # Fetch session
        session = await get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Fetch related data
        sources = await get_sources_by_session(session_id)
        conflicts = await get_conflicts_by_session(session_id)
        
        # Rebuild landscape
        try:
            landscape = await classify_information_landscape(session_id)
        except Exception as e:
            logger.warning(f"Failed to classify landscape: {e}")
            landscape = {
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
        
        # Build response
        response_data = {
            "session_id": session_id,
            "status": session.get("status", "unknown"),
            "original_query": session.get("original_query", ""),
            "refined_query": session.get("refined_query"),
            "sources": sources,
            "conflicts": conflicts,
            "landscape": landscape,
            "final_report": session.get("final_report"),
            "counter_argument": session.get("counter_argument"),
            "node_timings": session.get("node_timings", {}),
            "error": session.get("error"),
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Error {error_id} in get_research_results: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error (error_id: {error_id})"
        )


@router.get("/research/{session_id}/stream")
async def stream_research_progress(session_id: str):
    """
    Stream research progress via Server-Sent Events (SSE).
    
    Args:
        session_id: Session ID
    
    Returns:
        StreamingResponse with text/event-stream content type
    """
    logger.info(f"Stream connected for session {session_id}")
    
    # Get or create stream queue
    queue = get_stream(session_id)
    
    async def event_generator():
        """Generate SSE events from the queue."""
        try:
            while True:
                # Wait for next event with timeout
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                    continue
                
                # Send event
                yield f"data: {json.dumps(event)}\n\n"
                
                # If complete or failed, close stream
                if event.get("status") in ["complete", "failed"]:
                    break
                    
        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Stream error for {session_id}: {e}")
        finally:
            logger.info(f"Stream closed for session {session_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/research/{session_id}/report")
async def get_research_report(session_id: str):
    """
    Get the final research report as markdown.
    
    Args:
        session_id: Session ID
    
    Returns:
        Markdown report text with optional counter-argument section
    """
    logger.info(f"GET /api/v1/research/{session_id}/report")
    
    try:
        session = await get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        report = session.get("final_report")
        if not report:
            raise HTTPException(status_code=404, detail="Report not yet available")
        
        # Append counter-argument section if available
        counter = session.get("counter_argument")
        if counter and isinstance(counter, dict):
            report += "\n\n---\n\n"
            report += "## Counter-Argument\n\n"
            report += f"**Strength:** {counter.get('strength', 'unknown')}\n\n"
            report += f"{counter.get('counter_argument', '')}\n\n"
            report += f"**Explanation:** {counter.get('explanation', '')}\n\n"
            
            supporting_sources = counter.get("supporting_sources", [])
            if supporting_sources and counter.get('strength') != 'none':
                source_links = [
                    f"[{s.get('domain', 'Source')}]({s.get('url', '#')})"
                    for s in supporting_sources
                ]
                report += f"**Supporting sources:** {', '.join(source_links)}\n"
            elif counter.get('strength') == 'none':
                report += "*No supporting sources were found for a counter-argument.*\n"
        
        return Response(
            content=report,
            media_type="text/markdown"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Error {error_id} in get_research_report: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error (error_id: {error_id})"
        )


@router.get("/sessions", response_model=List[SessionListItem])
async def list_sessions():
    """
    List the 20 most recent research sessions.
    
    Returns:
        List of session summaries
    """
    logger.info("GET /api/v1/sessions")
    
    try:
        # Query supabase for recent sessions
        from app.db.supabase_client import supabase
        
        response = supabase.table("research_sessions")\
            .select("id, original_query, status, created_at")\
            .order("created_at", desc=True)\
            .limit(20)\
            .execute()
        
        sessions = response.data if response.data else []
        
        return [
            SessionListItem(
                id=s["id"],
                original_query=s.get("original_query", ""),
                status=s.get("status", "unknown"),
                created_at=s.get("created_at", "")
            )
            for s in sessions
        ]
        
    except Exception as e:
        error_id = str(uuid4())[:8]
        logger.error(f"Error {error_id} in list_sessions: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error (error_id: {error_id})"
        )
