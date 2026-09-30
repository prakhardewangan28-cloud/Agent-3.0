"""Supabase client initialization and database access functions."""
from supabase import create_client, Client
from functools import lru_cache
from typing import Dict, Any, List, Optional
import logging
import uuid
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# MOCK RESPONSE
# ============================================================================

class MockResponse:
    """Mock response object."""
    def __init__(self, data):
        self.data = data
    
    def execute(self):
        """Execute method for chaining compatibility."""
        return self


# ============================================================================
# MOCK SUPABASE CLIENT
# ============================================================================

class MockSupabase:
    """In-memory mock Supabase client for development without API keys."""
    
    def __init__(self):
        """Initialize in-memory storage."""
        self.sessions = {}
        self.sources = {}
        self.claims = {}
        self.conflicts = {}
        self.evidence_edges = {}
        self._id_counter = 1
        logger.info("🧪 MockSupabase initialized - using in-memory storage")
    
    def _generate_id(self) -> int:
        """Generate a unique ID."""
        result = self._id_counter
        self._id_counter += 1
        return result
    
    def _generate_uuid(self) -> str:
        """Generate a UUID."""
        return str(uuid.uuid4())
    
    class MockTable:
        """Mock table for method chaining."""
        def __init__(self, storage, table_name, mock_instance):
            self.storage = storage
            self.table_name = table_name
            self.mock_instance = mock_instance
            self._filters = []
            self._order_by = None
            self._order_desc = False
        
        def insert(self, data):
            """Insert data into the mock table."""
            if isinstance(data, list):
                results = []
                for item in data:
                    item_copy = item.copy()
                    if 'id' not in item_copy:
                        if self.table_name == 'research_sessions':
                            item_copy['id'] = str(uuid.uuid4())
                        else:
                            item_copy['id'] = self.mock_instance._generate_id()
                    item_copy['created_at'] = datetime.now().isoformat()
                    self.storage[item_copy['id']] = item_copy
                    results.append(item_copy)
                return MockResponse(results)
            else:
                data_copy = data.copy()
                if 'id' not in data_copy:
                    if self.table_name == 'research_sessions':
                        data_copy['id'] = str(uuid.uuid4())
                    else:
                        data_copy['id'] = self.mock_instance._generate_id()
                data_copy['created_at'] = datetime.now().isoformat()
                self.storage[data_copy['id']] = data_copy
                return MockResponse([data_copy])
        
        def update(self, data):
            """Update records."""
            self._update_data = data
            return self
        
        def select(self, columns="*"):
            """Select records."""
            return self
        
        def eq(self, column, value):
            """Filter by equality."""
            self._filters.append(('eq', column, value))
            return self
        
        def order(self, column, desc=False):
            """Order results."""
            self._order_by = column
            self._order_desc = desc
            return self
        
        def limit(self, count):
            """Limit the number of results."""
            self._limit = count
            return self
        
        def execute(self):
            """Execute the query."""
            results = list(self.storage.values())
            
            # Apply filters
            for filter_type, column, value in self._filters:
                if filter_type == 'eq':
                    results = [r for r in results if r.get(column) == value]
            
            # Apply updates if this is an update operation
            if hasattr(self, '_update_data'):
                for record in results:
                    record.update(self._update_data)
                    self.storage[record['id']] = record
            
            # Apply deletes if this is a delete operation
            if hasattr(self, '_is_delete'):
                for record in results:
                    if record['id'] in self.storage:
                        del self.storage[record['id']]
            
            # Apply ordering
            if self._order_by and results:
                reverse = self._order_desc
                results.sort(key=lambda x: x.get(self._order_by, 0), reverse=reverse)
            
            # Apply limit
            if hasattr(self, '_limit') and self._limit:
                results = results[:self._limit]
            
            return MockResponse(results)
        
        def delete(self):
            """Delete records."""
            self._is_delete = True
            return self
    
    class MockResponse:
        """Mock response object."""
        def __init__(self, data):
            self.data = data
        
        def execute(self):
            """Execute method for chaining compatibility."""
            return self
    
    def table(self, table_name: str):
        """Get a mock table."""
        storage_map = {
            'research_sessions': self.sessions,
            'sources': self.sources,
            'claims': self.claims,
            'conflicts': self.conflicts,
            'evidence_edges': self.evidence_edges
        }
        storage = storage_map.get(table_name, {})
        return self.MockTable(storage, table_name, self)
    
    def rpc(self, function_name: str, params: Dict):
        """Mock RPC calls."""
        if function_name == 'match_claims':
            # Return empty list for vector similarity search in mock mode
            return self.MockResponse([])
        return self.MockResponse([])


# ============================================================================
# CLIENT INITIALIZATION
# ============================================================================

@lru_cache()
def get_supabase_client() -> Client:
    """
    Get or create a Supabase client instance.
    
    Returns:
        Client: Initialized Supabase client (or MockSupabase in mock mode)
    """
    if settings.mock_mode:
        logger.info("🧪 Using MockSupabase - no real database connection")
        return MockSupabase()
    
    client = create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_key
    )
    
    # Startup check
    masked_key = settings.supabase_key[:12] + "..." if len(settings.supabase_key) > 12 else "***"
    logger.info(f"✅ Supabase client initialized successfully")
    logger.info(f"   URL: {settings.supabase_url}")
    logger.info(f"   Key: {masked_key}")
    logger.info(f"   Key type: {'JWT' if settings.supabase_key.startswith('eyJ') else 'Publishable'}")
    
    return client


# Create singleton instance
supabase: Client = get_supabase_client()


# ============================================================================
# RESEARCH SESSIONS
# ============================================================================

async def create_session(
    original_query: str,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new research session.
    
    Args:
        original_query: The original search query
        user_id: Optional user ID for authenticated users
        
    Returns:
        Created session record
        
    Raises:
        Exception: If database operation fails
    """
    try:
        data = {
            "original_query": original_query,
            "status": "in_progress"
        }
        if user_id:
            data["user_id"] = user_id
            
        response = supabase.table("research_sessions").insert(data).execute()
        logger.info(f"Created session: {response.data[0]['id']}")
        return response.data[0]
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise


async def update_session_status(
    session_id: str,
    status: str,
    refined_query: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update research session status and optionally the refined query.
    
    Args:
        session_id: UUID of the session
        status: New status (in_progress, complete, failed)
        refined_query: Optional refined query text
        
    Returns:
        Updated session record
        
    Raises:
        Exception: If database operation fails
    """
    try:
        data = {"status": status}
        if refined_query:
            data["refined_query"] = refined_query
            
        response = supabase.table("research_sessions")\
            .update(data)\
            .eq("id", session_id)\
            .execute()
        logger.info(f"Updated session {session_id} to status: {status}")
        return response.data[0]
    except Exception as e:
        logger.error(f"Failed to update session {session_id}: {e}")
        raise


async def update_session_final_report(
    session_id: str,
    final_report: str
) -> Dict[str, Any]:
    """
    Update research session with final report.
    
    Args:
        session_id: UUID of the session
        final_report: Markdown research report
        
    Returns:
        Updated session record
        
    Raises:
        Exception: If database operation fails
    """
    try:
        response = supabase.table("research_sessions")\
            .update({"final_report": final_report})\
            .eq("id", session_id)\
            .execute()
        logger.info(f"Updated session {session_id} with final report ({len(final_report)} chars)")
        return response.data[0]
    except Exception as e:
        logger.error(f"Failed to update final report for session {session_id}: {e}")
        raise


async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a research session by ID.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        Session record or None if not found
    """
    try:
        response = supabase.table("research_sessions")\
            .select("*")\
            .eq("id", session_id)\
            .execute()
        
        if response.data:
            logger.info(f"Retrieved session: {session_id}")
            return response.data[0]
        return None
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {e}")
        return None


# ============================================================================
# SOURCES
# ============================================================================

async def insert_sources(
    session_id: str,
    sources: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Insert multiple sources for a research session.
    
    Args:
        session_id: UUID of the session
        sources: List of source dictionaries with keys:
                - url (required)
                - title, snippet, domain, engine
                - credibility_score, score_breakdown
                - published_date, is_ai_generated, ai_generation_confidence
        
    Returns:
        List of inserted source records
        
    Raises:
        Exception: If database operation fails
    """
    try:
        # Add session_id to each source and sanitise published_date.
        # SerpAPI Scholar results sometimes return citation strings
        # (e.g. "L Chang, ... 2022 - Elsevier") in the published_date field
        # instead of a valid ISO timestamp. Postgres rejects the entire batch
        # when any value is unparseable, so we null-out anything that isn't a
        # valid ISO 8601 / RFC 3339 string before inserting.
        from datetime import datetime, timezone

        def _valid_timestamp(v) -> bool:
            """Return True if v is a non-empty string parseable as a timestamp."""
            if not isinstance(v, str) or not v.strip():
                return False
            for fmt in (
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%d",
            ):
                try:
                    datetime.strptime(v.strip(), fmt)
                    return True
                except ValueError:
                    continue
            return False

        for source in sources:
            source["session_id"] = session_id
            pd = source.get("published_date")
            if pd is not None and not _valid_timestamp(pd):
                logger.debug(
                    "Nullifying unparseable published_date for source %s: %r",
                    source.get("url", "?"),
                    str(pd)[:60],
                )
                source["published_date"] = None

            # Normalise credibility_score to [0, 1] range required by the
            # DB CHECK constraint. The credibility service outputs 0-100.
            cs = source.get("credibility_score")
            if cs is not None:
                cs = float(cs)
                if cs > 1.0:
                    # Scale from 0-100 down to 0-1
                    cs = round(cs / 100.0, 6)
                source["credibility_score"] = cs

            # Normalise ai_generation_confidence to [0, 1] (same constraint)
            ac = source.get("ai_generation_confidence")
            if ac is not None:
                ac = float(ac)
                if ac > 1.0:
                    ac = round(ac / 100.0, 6)
                source["ai_generation_confidence"] = ac

        response = supabase.table("sources").insert(sources).execute()
        logger.info(f"Inserted {len(response.data)} sources for session {session_id}")
        return response.data
    except Exception as e:
        logger.error(f"Failed to insert sources for session {session_id}: {e}")
        raise


async def get_sources_by_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all sources for a research session.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        List of source records
    """
    try:
        response = supabase.table("sources")\
            .select("*")\
            .eq("session_id", session_id)\
            .order("credibility_score", desc=True)\
            .execute()
        logger.info(f"Retrieved {len(response.data)} sources for session {session_id}")
        return response.data
    except Exception as e:
        logger.error(f"Failed to get sources for session {session_id}: {e}")
        return []


async def update_source_ai_flag(
    source_id: int,
    is_ai: bool,
    confidence: float
) -> Dict[str, Any]:
    """
    Update AI generation flag and confidence for a source.
    
    Args:
        source_id: ID of the source
        is_ai: Whether the source is AI-generated
        confidence: Confidence score (0.0 to 1.0)
        
    Returns:
        Updated source record
        
    Raises:
        Exception: If database operation fails
    """
    try:
        response = supabase.table("sources")\
            .update({
                "is_ai_generated": is_ai,
                "ai_generation_confidence": confidence
            })\
            .eq("id", source_id)\
            .execute()
        logger.info(f"Updated AI flag for source {source_id}: is_ai={is_ai}, confidence={confidence}")
        return response.data[0]
    except Exception as e:
        logger.error(f"Failed to update AI flag for source {source_id}: {e}")
        raise


# ============================================================================
# CLAIMS
# ============================================================================

async def insert_claims(
    session_id: str,
    claims: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Insert multiple claims for a research session.
    
    Args:
        session_id: UUID of the session
        claims: List of claim dictionaries with keys:
                - source_id (required)
                - claim_text (required)
                - embedding (optional, list of 1536 floats)
                - confidence (optional)
        
    Returns:
        List of inserted claim records
        
    Raises:
        Exception: If database operation fails
    """
    try:
        # Add session_id to each claim
        for claim in claims:
            claim["session_id"] = session_id
            
        response = supabase.table("claims").insert(claims).execute()
        logger.info(f"Inserted {len(response.data)} claims for session {session_id}")
        return response.data
    except Exception as e:
        logger.error(f"Failed to insert claims for session {session_id}: {e}")
        raise


async def get_claims_by_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all claims for a research session.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        List of claim records
    """
    try:
        response = supabase.table("claims")\
            .select("*")\
            .eq("session_id", session_id)\
            .order("confidence", desc=True)\
            .execute()
        logger.info(f"Retrieved {len(response.data)} claims for session {session_id}")
        return response.data
    except Exception as e:
        logger.error(f"Failed to get claims for session {session_id}: {e}")
        return []


async def find_similar_claims(
    session_id: str,
    embedding: List[float],
    threshold: float = 0.75,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Find similar claims using vector similarity search.
    
    Args:
        session_id: UUID of the session
        embedding: Query embedding vector (1536 dimensions)
        threshold: Minimum similarity threshold (0.0 to 1.0)
        limit: Maximum number of results
        
    Returns:
        List of similar claims with similarity scores
    """
    try:
        response = supabase.rpc(
            "match_claims",
            {
                "query_embedding": embedding,
                "session_id_filter": session_id,
                "match_threshold": threshold,
                "match_count": limit
            }
        ).execute()
        logger.info(f"Found {len(response.data)} similar claims for session {session_id}")
        return response.data
    except Exception as e:
        logger.error(f"Failed to find similar claims for session {session_id}: {e}")
        return []


# ============================================================================
# CONFLICTS
# ============================================================================

async def insert_conflicts(
    session_id: str,
    conflicts: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Insert multiple conflicts for a research session.
    
    Args:
        session_id: UUID of the session
        conflicts: List of conflict dictionaries with keys:
                   - claim_a_id (required, must be < claim_b_id)
                   - claim_b_id (required)
                   - conflict_type (contradiction, disagreement, evidence_gap)
                   - confidence (optional)
                   - explanation (optional)
        
    Returns:
        List of inserted conflict records
        
    Raises:
        Exception: If database operation fails
    """
    try:
        # Add session_id to each conflict
        for conflict in conflicts:
            conflict["session_id"] = session_id
            
        response = supabase.table("conflicts").insert(conflicts).execute()
        logger.info(f"Inserted {len(response.data)} conflicts for session {session_id}")
        return response.data
    except Exception as e:
        logger.error(f"Failed to insert conflicts for session {session_id}: {e}")
        raise


async def get_conflicts_by_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all conflicts for a research session.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        List of conflict records
    """
    try:
        response = supabase.table("conflicts")\
            .select("*")\
            .eq("session_id", session_id)\
            .order("confidence", desc=True)\
            .execute()
        logger.info(f"Retrieved {len(response.data)} conflicts for session {session_id}")
        return response.data
    except Exception as e:
        logger.error(f"Failed to get conflicts for session {session_id}: {e}")
        return []


# ============================================================================
# EVIDENCE EDGES
# ============================================================================

async def insert_evidence_edge(
    session_id: str,
    edge: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Insert a single evidence edge.
    
    Args:
        session_id: UUID of the session
        edge: Edge dictionary with keys:
              - source_a_id (required)
              - source_b_id (required)
              - edge_type (supports, refutes, cites, neutral)
              - confidence (optional)
              - explanation (optional)
        
    Returns:
        Inserted edge record
        
    Raises:
        Exception: If database operation fails
    """
    try:
        edge["session_id"] = session_id
        response = supabase.table("evidence_edges").insert(edge).execute()
        logger.info(f"Inserted evidence edge for session {session_id}")
        return response.data[0]
    except Exception as e:
        logger.error(f"Failed to insert evidence edge for session {session_id}: {e}")
        raise


async def get_evidence_graph(session_id: str) -> Dict[str, Any]:
    """
    Get the complete evidence graph (nodes + edges) for a session.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        Dictionary with 'nodes' (sources) and 'edges' (evidence_edges) keys
    """
    try:
        # Get all sources (nodes)
        sources_response = supabase.table("sources")\
            .select("*")\
            .eq("session_id", session_id)\
            .execute()
        
        # Get all evidence edges
        edges_response = supabase.table("evidence_edges")\
            .select("*")\
            .eq("session_id", session_id)\
            .execute()
        
        graph = {
            "nodes": sources_response.data,
            "edges": edges_response.data
        }
        
        logger.info(
            f"Retrieved evidence graph for session {session_id}: "
            f"{len(graph['nodes'])} nodes, {len(graph['edges'])} edges"
        )
        return graph
    except Exception as e:
        logger.error(f"Failed to get evidence graph for session {session_id}: {e}")
        return {"nodes": [], "edges": []}
