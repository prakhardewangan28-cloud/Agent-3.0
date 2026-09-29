"""Database layer for Supabase integration."""
from .supabase_client import (
    get_supabase_client,
    supabase,
    # Research Sessions
    create_session,
    update_session_status,
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
    "get_supabase_client",
    "supabase",
    # Research Sessions
    "create_session",
    "update_session_status",
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
