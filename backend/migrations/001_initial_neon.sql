-- Initial database schema for Knowledge Intelligence Agent with pgvector
-- Neon Postgres compatible version (no Supabase auth/RLS)

-- Enable pgvector extension for vector embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- TABLE: research_sessions
-- ============================================================================
CREATE TABLE IF NOT EXISTS research_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,  -- Nullable, no foreign key constraint (no auth.users in Neon)
    original_query TEXT NOT NULL,
    refined_query TEXT,
    status TEXT DEFAULT 'in_progress' CHECK (status IN ('in_progress', 'complete', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- ============================================================================
-- TABLE: sources
-- ============================================================================
CREATE TABLE IF NOT EXISTS sources (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    snippet TEXT,
    domain TEXT,
    engine TEXT CHECK (engine IN ('google', 'news', 'scholar')),
    credibility_score FLOAT CHECK (credibility_score >= 0 AND credibility_score <= 1),
    score_breakdown JSONB,
    published_date TIMESTAMPTZ,
    is_ai_generated BOOLEAN DEFAULT FALSE,
    ai_generation_confidence FLOAT CHECK (ai_generation_confidence >= 0 AND ai_generation_confidence <= 1),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- TABLE: claims
-- ============================================================================
CREATE TABLE IF NOT EXISTS claims (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    source_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    embedding vector(1536),
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- TABLE: conflicts
-- ============================================================================
CREATE TABLE IF NOT EXISTS conflicts (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    claim_a_id BIGINT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    claim_b_id BIGINT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
    conflict_type TEXT CHECK (conflict_type IN ('contradiction', 'disagreement', 'evidence_gap')),
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    explanation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT different_claims CHECK (claim_a_id < claim_b_id)
);

-- ============================================================================
-- TABLE: evidence_edges
-- ============================================================================
CREATE TABLE IF NOT EXISTS evidence_edges (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    source_a_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    source_b_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    edge_type TEXT CHECK (edge_type IN ('supports', 'refutes', 'cites', 'neutral')),
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    explanation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- INDEXES for better query performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_research_sessions_created_at ON research_sessions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_sessions_user_id ON research_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_research_sessions_status ON research_sessions(status);

CREATE INDEX IF NOT EXISTS idx_sources_session_id ON sources(session_id);
CREATE INDEX IF NOT EXISTS idx_sources_domain ON sources(domain);
CREATE INDEX IF NOT EXISTS idx_sources_engine ON sources(engine);
CREATE INDEX IF NOT EXISTS idx_sources_credibility_score ON sources(credibility_score DESC);

CREATE INDEX IF NOT EXISTS idx_claims_session_id ON claims(session_id);
CREATE INDEX IF NOT EXISTS idx_claims_source_id ON claims(source_id);

CREATE INDEX IF NOT EXISTS idx_conflicts_session_id ON conflicts(session_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_claim_a_id ON conflicts(claim_a_id);
CREATE INDEX IF NOT EXISTS idx_conflicts_claim_b_id ON conflicts(claim_b_id);

CREATE INDEX IF NOT EXISTS idx_evidence_edges_session_id ON evidence_edges(session_id);
CREATE INDEX IF NOT EXISTS idx_evidence_edges_source_a_id ON evidence_edges(source_a_id);
CREATE INDEX IF NOT EXISTS idx_evidence_edges_source_b_id ON evidence_edges(source_b_id);

-- Create IVFFlat index on embeddings for faster similarity search
-- Note: This requires at least 1000 rows of data to be effective
CREATE INDEX IF NOT EXISTS idx_claims_embedding ON claims 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- ============================================================================
-- FUNCTION: match_claims
-- Finds similar claims using pgvector cosine similarity
-- ============================================================================
CREATE OR REPLACE FUNCTION match_claims(
    query_embedding vector(1536),
    session_id_filter UUID,
    match_threshold FLOAT DEFAULT 0.75,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    id BIGINT,
    claim_text TEXT,
    source_id BIGINT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        c.claim_text,
        c.source_id,
        1 - (c.embedding <=> query_embedding) AS similarity
    FROM claims c
    WHERE 
        c.session_id = session_id_filter
        AND c.embedding IS NOT NULL
        AND 1 - (c.embedding <=> query_embedding) >= match_threshold
    ORDER BY c.embedding <=> query_embedding ASC
    LIMIT match_count;
END;
$$;

-- ============================================================================
-- HELPER FUNCTION: update_completed_at
-- Automatically set completed_at when status changes to 'complete' or 'failed'
-- ============================================================================
CREATE OR REPLACE FUNCTION update_completed_at()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status IN ('complete', 'failed') AND OLD.status = 'in_progress' THEN
        NEW.completed_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_completed_at
    BEFORE UPDATE ON research_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_completed_at();

-- ============================================================================
-- SUMMARY
-- ============================================================================
-- Tables created: 5 (research_sessions, sources, claims, conflicts, evidence_edges)
-- Indexes created: 15+ (including vector index)
-- Functions created: 2 (match_claims, update_completed_at)
-- Vector dimension: 1536 (for gemini-embedding-001)
-- NOTE: RLS and Supabase auth removed for Neon compatibility
-- ============================================================================
