"""Neon Postgres client using asyncpg."""
import asyncpg
import json
import logging
import uuid
from typing import Optional, Any, Dict, List
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[asyncpg.Pool] = None


# ============================================================================
# MOCK NEON CLIENT
# ============================================================================

class MockNeon:
    """In-memory mock Neon client for development without database connection."""
    
    def __init__(self):
        """Initialize in-memory storage."""
        self.sessions = {}
        self.sources = {}
        self.claims = {}
        self.conflicts = {}
        self.evidence_edges = {}
        self.images = {}  # Add images storage
        self._id_counter = 1
        logger.info("🧪 MockNeon initialized - using in-memory storage")
    
    def _generate_id(self) -> int:
        """Generate a unique ID."""
        result = self._id_counter
        self._id_counter += 1
        return result
    
    def _generate_uuid(self) -> str:
        """Generate a UUID."""
        return str(uuid.uuid4())


# Global mock instance
_mock_neon: Optional[MockNeon] = None


def get_mock() -> MockNeon:
    """Get or create mock instance."""
    global _mock_neon
    if _mock_neon is None:
        _mock_neon = MockNeon()
    return _mock_neon


# ============================================================================
# CONNECTION POOL
# ============================================================================

async def get_pool() -> asyncpg.Pool:
    """
    Get or create the connection pool.
    
    Returns:
        asyncpg.Pool: Connection pool
    """
    global _pool
    if _pool is None:
        # Register pgvector extension
        from pgvector.asyncpg import register_vector
        
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=1,
            max_size=5,
            init=register_vector,
        )
        logger.info("✅ Neon connection pool created")
    return _pool


async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Neon connection pool closed")


# ============================================================================
# RESEARCH SESSIONS
# ============================================================================

async def create_session(
    original_query: str,
    user_id: Optional[str] = None,
    language: str = "en"
) -> Dict[str, Any]:
    """
    Create a new research session.
    
    Args:
        original_query: The original search query
        user_id: Optional user ID for authenticated users
        language: Language code (en, hi, es, fr, de, pt, zh, ja, ar)
        
    Returns:
        Created session record
    """
    if settings.is_db_mocked:
        mock = get_mock()
        session_id = mock._generate_uuid()
        session = {
            "id": session_id,
            "original_query": original_query,
            "user_id": user_id,
            "language": language,
            "refined_query": None,
            "status": "in_progress",
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "final_report": None,
            "summary": None,
            "counter_argument": None
        }
        mock.sessions[session_id] = session
        logger.info(f"MockNeon: Created session {session_id}")
        return session
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO research_sessions (original_query, user_id, language, status)
            VALUES ($1, $2, $3, 'in_progress')
            RETURNING *
            """,
            original_query,
            user_id,
            language
        )
        session = dict(row)
        logger.info(f"Created session: {session['id']}")
        return session


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
    """
    if settings.is_db_mocked:
        mock = get_mock()
        if session_id not in mock.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        mock.sessions[session_id]["status"] = status
        if refined_query:
            mock.sessions[session_id]["refined_query"] = refined_query
        logger.info(f"MockNeon: Updated session {session_id} to status: {status}")
        return mock.sessions[session_id]
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        if refined_query:
            row = await conn.fetchrow(
                """
                UPDATE research_sessions
                SET status = $1, refined_query = $2
                WHERE id = $3
                RETURNING *
                """,
                status,
                refined_query,
                session_id
            )
        else:
            row = await conn.fetchrow(
                """
                UPDATE research_sessions
                SET status = $1
                WHERE id = $2
                RETURNING *
                """,
                status,
                session_id
            )
        
        if not row:
            raise ValueError(f"Session {session_id} not found")
        
        session = dict(row)
        logger.info(f"Updated session {session_id} to status: {status}")
        return session


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
    """
    if settings.is_db_mocked:
        mock = get_mock()
        if session_id not in mock.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        mock.sessions[session_id]["final_report"] = final_report
        logger.info(f"MockNeon: Updated session {session_id} with final report ({len(final_report)} chars)")
        return mock.sessions[session_id]
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE research_sessions
            SET final_report = $1
            WHERE id = $2
            RETURNING *
            """,
            final_report,
            session_id
        )
        
        if not row:
            raise ValueError(f"Session {session_id} not found")
        
        session = dict(row)
        logger.info(f"Updated session {session_id} with final report ({len(final_report)} chars)")
        return session


async def update_session_counter_argument(
    session_id: str,
    counter_argument: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Update the counter-argument for a research session.
    
    Args:
        session_id: UUID of the session
        counter_argument: Counter-argument JSON object or None
    
    Returns:
        Updated session record
    """
    if settings.is_db_mocked:
        mock = get_mock()
        if session_id not in mock.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        mock.sessions[session_id]["counter_argument"] = counter_argument
        strength = counter_argument.get('strength') if counter_argument else None
        logger.info(f"MockNeon: Updated session {session_id} with counter-argument (strength: {strength})")
        return mock.sessions[session_id]
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE research_sessions
            SET counter_argument = $1
            WHERE id = $2
            RETURNING *
            """,
            json.dumps(counter_argument) if counter_argument else None,
            session_id
        )
        
        if not row:
            raise ValueError(f"Session {session_id} not found")
        
        session = dict(row)
        strength = counter_argument.get('strength') if counter_argument else None
        logger.info(f"Updated session {session_id} with counter-argument (strength: {strength})")
        return session


async def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a research session by ID.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        Session record or None if not found
    """
    if settings.is_db_mocked:
        mock = get_mock()
        session = mock.sessions.get(session_id)
        if session:
            logger.info(f"MockNeon: Retrieved session: {session_id}")
        return session
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM research_sessions
            WHERE id = $1
            """,
            session_id
        )
        
        if row:
            session = dict(row)
            logger.info(f"Retrieved session: {session_id}")
            return session
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
        sources: List of source dictionaries
        
    Returns:
        List of inserted source records
    """
    if settings.is_db_mocked:
        mock = get_mock()
        results = []
        for source in sources:
            source_id = mock._generate_id()
            source_record = {
                "id": source_id,
                "session_id": session_id,
                "url": source.get("url"),
                "title": source.get("title"),
                "snippet": source.get("snippet"),
                "domain": source.get("domain"),
                "engine": source.get("engine"),
                "credibility_score": source.get("credibility_score"),
                "score_breakdown": source.get("score_breakdown"),
                "published_date": source.get("published_date"),
                "is_ai_generated": source.get("is_ai_generated", False),
                "ai_generation_confidence": source.get("ai_generation_confidence"),
                "summary": source.get("summary"),  # Add summary field
                "created_at": datetime.now().isoformat()
            }
            mock.sources[source_id] = source_record
            results.append(source_record)
        logger.info(f"MockNeon: Inserted {len(results)} sources for session {session_id}")
        return results
    
    # Sanitize published_date
    def _valid_timestamp(v) -> bool:
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
        pd = source.get("published_date")
        if pd is not None and not _valid_timestamp(pd):
            logger.debug(f"Nullifying unparseable published_date for source {source.get('url', '?')}: {str(pd)[:60]}")
            source["published_date"] = None
    
    pool = await get_pool()
    results = []
    async with pool.acquire() as conn:
        for source in sources:
            row = await conn.fetchrow(
                """
                INSERT INTO sources (
                    session_id, url, title, snippet, domain, engine,
                    credibility_score, score_breakdown, published_date,
                    is_ai_generated, ai_generation_confidence, summary
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING *
                """,
                session_id,
                source.get("url"),
                source.get("title"),
                source.get("snippet"),
                source.get("domain"),
                source.get("engine"),
                source.get("credibility_score"),
                json.dumps(source.get("score_breakdown")) if source.get("score_breakdown") else None,
                source.get("published_date"),
                source.get("is_ai_generated", False),
                source.get("ai_generation_confidence"),
                source.get("summary")  # Add summary field
            )
            results.append(dict(row))
    
    logger.info(f"Inserted {len(results)} sources for session {session_id}")
    return results


async def get_sources_by_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all sources for a research session.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        List of source records
    """
    if settings.is_db_mocked:
        mock = get_mock()
        results = [s for s in mock.sources.values() if s["session_id"] == session_id]
        results.sort(key=lambda x: x.get("credibility_score", 0), reverse=True)
        logger.info(f"MockNeon: Retrieved {len(results)} sources for session {session_id}")
        return results
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM sources
            WHERE session_id = $1
            ORDER BY credibility_score DESC NULLS LAST
            """,
            session_id
        )
        results = [dict(row) for row in rows]
        logger.info(f"Retrieved {len(results)} sources for session {session_id}")
        return results


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
        claims: List of claim dictionaries
        
    Returns:
        List of inserted claim records
    """
    if settings.is_db_mocked:
        mock = get_mock()
        results = []
        for claim in claims:
            claim_id = mock._generate_id()
            claim_record = {
                "id": claim_id,
                "session_id": session_id,
                "source_id": claim.get("source_id"),
                "claim_text": claim.get("claim_text"),
                "embedding": claim.get("embedding"),
                "confidence": claim.get("confidence"),
                "created_at": datetime.now().isoformat()
            }
            mock.claims[claim_id] = claim_record
            results.append(claim_record)
        logger.info(f"MockNeon: Inserted {len(results)} claims for session {session_id}")
        return results
    
    pool = await get_pool()
    results = []
    async with pool.acquire() as conn:
        for claim in claims:
            row = await conn.fetchrow(
                """
                INSERT INTO claims (
                    session_id, source_id, claim_text, embedding, confidence
                )
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                session_id,
                claim.get("source_id"),
                claim.get("claim_text"),
                claim.get("embedding"),  # asyncpg handles list -> vector conversion
                claim.get("confidence")
            )
            results.append(dict(row))
    
    logger.info(f"Inserted {len(results)} claims for session {session_id}")
    return results


async def get_claims_by_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all claims for a research session.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        List of claim records
    """
    if settings.is_db_mocked:
        mock = get_mock()
        results = [c for c in mock.claims.values() if c["session_id"] == session_id]
        results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        logger.info(f"MockNeon: Retrieved {len(results)} claims for session {session_id}")
        return results
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM claims
            WHERE session_id = $1
            ORDER BY confidence DESC NULLS LAST
            """,
            session_id
        )
        results = [dict(row) for row in rows]
        logger.info(f"Retrieved {len(results)} claims for session {session_id}")
        return results


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
    if settings.is_db_mocked:
        # Mock mode returns empty list
        logger.info(f"MockNeon: find_similar_claims returning empty list")
        return []
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM match_claims($1, $2, $3, $4)
            """,
            embedding,  # asyncpg handles list -> vector conversion
            session_id,
            threshold,
            limit
        )
        results = [dict(row) for row in rows]
        logger.info(f"Found {len(results)} similar claims for session {session_id}")
        return results


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
        conflicts: List of conflict dictionaries
        
    Returns:
        List of inserted conflict records
    """
    if settings.is_db_mocked:
        mock = get_mock()
        results = []
        for conflict in conflicts:
            conflict_id = mock._generate_id()
            conflict_record = {
                "id": conflict_id,
                "session_id": session_id,
                "claim_a_id": conflict.get("claim_a_id"),
                "claim_b_id": conflict.get("claim_b_id"),
                "conflict_type": conflict.get("conflict_type"),
                "confidence": conflict.get("confidence"),
                "explanation": conflict.get("explanation"),
                "created_at": datetime.now().isoformat()
            }
            mock.conflicts[conflict_id] = conflict_record
            results.append(conflict_record)
        logger.info(f"MockNeon: Inserted {len(results)} conflicts for session {session_id}")
        return results
    
    pool = await get_pool()
    results = []
    async with pool.acquire() as conn:
        for conflict in conflicts:
            row = await conn.fetchrow(
                """
                INSERT INTO conflicts (
                    session_id, claim_a_id, claim_b_id, conflict_type, confidence, explanation
                )
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                """,
                session_id,
                conflict.get("claim_a_id"),
                conflict.get("claim_b_id"),
                conflict.get("conflict_type"),
                conflict.get("confidence"),
                conflict.get("explanation")
            )
            results.append(dict(row))
    
    logger.info(f"Inserted {len(results)} conflicts for session {session_id}")
    return results


async def get_conflicts_by_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all conflicts for a research session.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        List of conflict records
    """
    if settings.is_db_mocked:
        mock = get_mock()
        results = [c for c in mock.conflicts.values() if c["session_id"] == session_id]
        results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        logger.info(f"MockNeon: Retrieved {len(results)} conflicts for session {session_id}")
        return results
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM conflicts
            WHERE session_id = $1
            ORDER BY confidence DESC NULLS LAST
            """,
            session_id
        )
        results = [dict(row) for row in rows]
        logger.info(f"Retrieved {len(results)} conflicts for session {session_id}")
        return results


# ============================================================================
# EVIDENCE EDGES (Stub implementations for compatibility)
# ============================================================================

async def insert_evidence_edge(
    session_id: str,
    edge: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Insert a single evidence edge.
    
    Args:
        session_id: UUID of the session
        edge: Edge dictionary
        
    Returns:
        Inserted edge record
    """
    if settings.is_db_mocked:
        mock = get_mock()
        edge_id = mock._generate_id()
        edge_record = {
            "id": edge_id,
            "session_id": session_id,
            "source_a_id": edge.get("source_a_id"),
            "source_b_id": edge.get("source_b_id"),
            "edge_type": edge.get("edge_type"),
            "confidence": edge.get("confidence"),
            "explanation": edge.get("explanation"),
            "created_at": datetime.now().isoformat()
        }
        mock.evidence_edges[edge_id] = edge_record
        logger.info(f"MockNeon: Inserted evidence edge for session {session_id}")
        return edge_record
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO evidence_edges (
                session_id, source_a_id, source_b_id, edge_type, confidence, explanation
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            session_id,
            edge.get("source_a_id"),
            edge.get("source_b_id"),
            edge.get("edge_type"),
            edge.get("confidence"),
            edge.get("explanation")
        )
        result = dict(row)
        logger.info(f"Inserted evidence edge for session {session_id}")
        return result


async def get_evidence_graph(session_id: str) -> Dict[str, Any]:
    """
    Get the complete evidence graph (nodes + edges) for a session.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        Dictionary with 'nodes' (sources) and 'edges' (evidence_edges) keys
    """
    if settings.is_db_mocked:
        mock = get_mock()
        nodes = [s for s in mock.sources.values() if s["session_id"] == session_id]
        edges = [e for e in mock.evidence_edges.values() if e["session_id"] == session_id]
        logger.info(f"MockNeon: Retrieved evidence graph for session {session_id}: {len(nodes)} nodes, {len(edges)} edges")
        return {"nodes": nodes, "edges": edges}
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        sources_rows = await conn.fetch(
            """
            SELECT * FROM sources
            WHERE session_id = $1
            """,
            session_id
        )
        
        edges_rows = await conn.fetch(
            """
            SELECT * FROM evidence_edges
            WHERE session_id = $1
            """,
            session_id
        )
        
        graph = {
            "nodes": [dict(row) for row in sources_rows],
            "edges": [dict(row) for row in edges_rows]
        }
        
        logger.info(
            f"Retrieved evidence graph for session {session_id}: "
            f"{len(graph['nodes'])} nodes, {len(graph['edges'])} edges"
        )
        return graph


# ============================================================================
# ADDITIONAL COMPATIBILITY FUNCTION
# ============================================================================

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
    """
    if settings.is_db_mocked:
        mock = get_mock()
        if source_id not in mock.sources:
            raise ValueError(f"Source {source_id} not found")
        
        mock.sources[source_id]["is_ai_generated"] = is_ai
        mock.sources[source_id]["ai_generation_confidence"] = confidence
        logger.info(f"MockNeon: Updated AI flag for source {source_id}: is_ai={is_ai}, confidence={confidence}")
        return mock.sources[source_id]
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE sources
            SET is_ai_generated = $1, ai_generation_confidence = $2
            WHERE id = $3
            RETURNING *
            """,
            is_ai,
            confidence,
            source_id
        )
        
        if not row:
            raise ValueError(f"Source {source_id} not found")
        
        result = dict(row)
        logger.info(f"Updated AI flag for source {source_id}: is_ai={is_ai}, confidence={confidence}")
        return result



async def update_session_summary(
    session_id: str,
    summary: str
) -> Dict[str, Any]:
    """
    Update research session with executive summary.
    
    Args:
        session_id: UUID of the session
        summary: Executive summary (3-6 sentences)
        
    Returns:
        Updated session record
    """
    if settings.is_db_mocked:
        mock = get_mock()
        if session_id not in mock.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        mock.sessions[session_id]["summary"] = summary
        logger.info(f"MockNeon: Updated session {session_id} with summary ({len(summary)} chars)")
        return mock.sessions[session_id]
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE research_sessions
            SET summary = $1
            WHERE id = $2
            RETURNING *
            """,
            summary,
            session_id
        )
        
        if not row:
            raise ValueError(f"Session {session_id} not found")
        
        session = dict(row)
        logger.info(f"Updated session {session_id} with summary ({len(summary)} chars)")
        return session


async def insert_images(
    session_id: str,
    images: List[Dict[str, Any]]
) -> int:
    """
    Insert Google Images results for a session.
    
    Args:
        session_id: UUID of the session
        images: List of image dicts with keys: url, thumbnail, title, source_url, domain, is_placeholder
        
    Returns:
        Number of images inserted
    """
    if not images:
        return 0
    
    if settings.is_db_mocked:
        mock = get_mock()
        if session_id not in mock.sessions:
            raise ValueError(f"Session {session_id} not found")
        
        mock.images[session_id] = images
        logger.info(f"MockNeon: Inserted {len(images)} images for session {session_id}")
        return len(images)
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Insert images
        inserted = 0
        for img in images:
            await conn.execute(
                """
                INSERT INTO session_images (
                    session_id, url, thumbnail, title, source_url, domain, is_placeholder
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                session_id,
                img.get("url"),
                img.get("thumbnail"),
                img.get("title", ""),
                img.get("source_url"),
                img.get("domain"),
                img.get("is_placeholder", False)
            )
            inserted += 1
        
        logger.info(f"Inserted {inserted} images for session {session_id}")
        return inserted


async def get_images_by_session(session_id: str) -> List[Dict[str, Any]]:
    """
    Get all images for a session.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        List of image dicts
    """
    if settings.is_db_mocked:
        mock = get_mock()
        return mock.images.get(session_id, [])
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT url, thumbnail, title, source_url, domain, is_placeholder, created_at
            FROM session_images
            WHERE session_id = $1
            ORDER BY id ASC
            """,
            session_id
        )
        
        return [dict(row) for row in rows]
