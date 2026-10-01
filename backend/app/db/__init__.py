"""Database layer for Neon Postgres integration."""
from .neon_client import (
    get_pool,
    close_pool,
    get_mock,
    # Research Sessions
    create_session,
    update_session_status,
    update_session_final_report,
    update_session_counter_argument,
    get_session,
    # Sources
    insert_sources,
    get_sources_by_session,
    update_source_ai_flag,
    # Claims
    insert_claims,
    get_claims_by_session,
    find_similar_claims,
    # Conflicts
    insert_conflicts,
    get_conflicts_by_session,
    # Evidence Edges
    insert_evidence_edge,
    get_evidence_graph,
)

__all__ = [
    "get_pool",
    "close_pool",
    "get_mock",
    # Research Sessions
    "create_session",
    "update_session_status",
    "update_session_final_report",
    "update_session_counter_argument",
    "get_session",
    # Sources
    "insert_sources",
    "get_sources_by_session",
    "update_source_ai_flag",
    # Claims
    "insert_claims",
    "get_claims_by_session",
    "find_similar_claims",
    # Conflicts
    "insert_conflicts",
    "get_conflicts_by_session",
    # Evidence Edges
    "insert_evidence_edge",
    "get_evidence_graph",
]
