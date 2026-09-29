# Database Layer Guide

## Overview

The database layer provides a complete async interface to Supabase with support for:
- Research sessions and workflow tracking
- Source storage with credibility scoring
- Claims with vector embeddings (1536-dimensional)
- Conflict detection between claims
- Evidence graph (source relationships)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│                  (FastAPI Routes, Services)                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 Database Access Layer                        │
│              (app/db/supabase_client.py)                     │
│                                                               │
│  • create_session()      • insert_sources()                  │
│  • update_session()      • insert_claims()                   │
│  • get_session()         • find_similar_claims()             │
│  • insert_conflicts()    • get_evidence_graph()              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     Supabase Client                          │
│                    (supabase-py)                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQL + pgvector                       │
│                      (Supabase)                              │
│                                                               │
│  Tables: research_sessions, sources, claims,                 │
│          conflicts, evidence_edges                           │
│  Extensions: vector                                          │
│  Functions: match_claims (similarity search)                 │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### 1. research_sessions

Tracks research workflows from start to completion.

```sql
CREATE TABLE research_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id),  -- nullable
    original_query TEXT NOT NULL,
    refined_query TEXT,
    status TEXT DEFAULT 'in_progress',       -- in_progress, complete, failed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

### 2. sources

Stores web sources with credibility metadata.

```sql
CREATE TABLE sources (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    title TEXT,
    snippet TEXT,
    domain TEXT,
    engine TEXT,                             -- google, news, scholar
    credibility_score FLOAT,                 -- 0.0 to 1.0
    score_breakdown JSONB,
    published_date TIMESTAMPTZ,
    is_ai_generated BOOLEAN DEFAULT FALSE,
    ai_generation_confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3. claims

Extracted claims with vector embeddings for similarity search.

```sql
CREATE TABLE claims (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,
    source_id BIGINT REFERENCES sources(id) ON DELETE CASCADE,
    claim_text TEXT NOT NULL,
    embedding vector(1536),                  -- Gemini embedding
    confidence FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 4. conflicts

Detected contradictions between claims.

```sql
CREATE TABLE conflicts (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,
    claim_a_id BIGINT REFERENCES claims(id) ON DELETE CASCADE,
    claim_b_id BIGINT REFERENCES claims(id) ON DELETE CASCADE,
    conflict_type TEXT,                      -- contradiction, disagreement, evidence_gap
    confidence FLOAT,
    explanation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 5. evidence_edges

Relationships between sources in the evidence graph.

```sql
CREATE TABLE evidence_edges (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_id UUID REFERENCES research_sessions(id) ON DELETE CASCADE,
    source_a_id BIGINT REFERENCES sources(id) ON DELETE CASCADE,
    source_b_id BIGINT REFERENCES sources(id) ON DELETE CASCADE,
    edge_type TEXT,                          -- supports, refutes, cites, neutral
    confidence FLOAT,
    explanation TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Setup Instructions

### 1. Run the Migration

Copy the contents of `migrations/001_initial.sql` and run it in your Supabase SQL editor:

1. Go to https://supabase.com/dashboard
2. Select your project
3. Navigate to SQL Editor
4. Paste the entire migration
5. Click "Run"

This will:
- Enable the pgvector extension
- Create all 5 tables
- Create 15+ indexes for performance
- Set up RLS policies
- Create the `match_claims()` function

### 2. Verify Installation

Check that tables were created:

```sql
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN ('research_sessions', 'sources', 'claims', 'conflicts', 'evidence_edges');
```

Should return 5 rows.

### 3. Test the Database Functions

```bash
cd backend
.\venv\Scripts\Activate.ps1
python test_database.py
```

## API Reference

### Research Sessions

#### create_session()

Create a new research session.

```python
from app.db import create_session

session = await create_session(
    original_query="What is climate change?",
    user_id="optional-user-uuid"  # None for anonymous
)

# Returns:
{
    "id": "uuid",
    "original_query": "What is climate change?",
    "status": "in_progress",
    "created_at": "2026-09-27T..."
}
```

#### update_session_status()

Update session status and optionally set refined query.

```python
from app.db import update_session_status

updated = await update_session_status(
    session_id="uuid",
    status="complete",  # or "failed"
    refined_query="Optional refined version"
)
```

#### get_session()

Retrieve a session by ID.

```python
from app.db import get_session

session = await get_session(session_id="uuid")
# Returns dict or None if not found
```

### Sources

#### insert_sources()

Bulk insert sources for a session.

```python
from app.db import insert_sources

sources = [
    {
        "url": "https://example.com/article",
        "title": "Article Title",
        "snippet": "Preview text...",
        "domain": "example.com",
        "engine": "google",  # or "news", "scholar"
        "credibility_score": 0.85,
        "score_breakdown": {
            "domain_authority": 0.8,
            "citation_count": 150
        },
        "published_date": "2026-01-15T12:00:00Z",
        "is_ai_generated": False,
        "ai_generation_confidence": 0.1
    }
]

inserted = await insert_sources(session_id="uuid", sources=sources)
```

#### get_sources_by_session()

Get all sources for a session (ordered by credibility).

```python
from app.db import get_sources_by_session

sources = await get_sources_by_session(session_id="uuid")
# Returns list of source dicts
```

#### update_source_ai_flag()

Mark a source as AI-generated.

```python
from app.db import update_source_ai_flag

updated = await update_source_ai_flag(
    source_id=123,
    is_ai=True,
    confidence=0.92
)
```

### Claims

#### insert_claims()

Bulk insert claims with embeddings.

```python
from app.db import insert_claims

claims = [
    {
        "source_id": 123,
        "claim_text": "The sky is blue due to Rayleigh scattering",
        "embedding": [0.1, 0.2, ...],  # 1536 floats from Gemini
        "confidence": 0.95
    }
]

inserted = await insert_claims(session_id="uuid", claims=claims)
```

#### get_claims_by_session()

Get all claims for a session.

```python
from app.db import get_claims_by_session

claims = await get_claims_by_session(session_id="uuid")
```

#### find_similar_claims()

Vector similarity search using pgvector.

```python
from app.db import find_similar_claims

# Get embedding from Gemini first
query_embedding = [0.1, 0.2, ...]  # 1536 dimensions

similar = await find_similar_claims(
    session_id="uuid",
    embedding=query_embedding,
    threshold=0.75,  # cosine similarity threshold
    limit=10
)

# Returns:
[
    {
        "id": 456,
        "claim_text": "...",
        "source_id": 123,
        "similarity": 0.89
    }
]
```

### Conflicts

#### insert_conflicts()

Record conflicts between claims.

```python
from app.db import insert_conflicts

conflicts = [
    {
        "claim_a_id": 100,  # Must be < claim_b_id
        "claim_b_id": 200,
        "conflict_type": "contradiction",  # or "disagreement", "evidence_gap"
        "confidence": 0.85,
        "explanation": "Claims directly contradict each other"
    }
]

inserted = await insert_conflicts(session_id="uuid", conflicts=conflicts)
```

#### get_conflicts_by_session()

Get all conflicts for a session.

```python
from app.db import get_conflicts_by_session

conflicts = await get_conflicts_by_session(session_id="uuid")
```

### Evidence Graph

#### insert_evidence_edge()

Add a relationship between two sources.

```python
from app.db import insert_evidence_edge

edge = {
    "source_a_id": 10,
    "source_b_id": 20,
    "edge_type": "supports",  # or "refutes", "cites", "neutral"
    "confidence": 0.9,
    "explanation": "Source A cites Source B as evidence"
}

inserted = await insert_evidence_edge(session_id="uuid", edge=edge)
```

#### get_evidence_graph()

Get the complete graph (sources + edges).

```python
from app.db import get_evidence_graph

graph = await get_evidence_graph(session_id="uuid")

# Returns:
{
    "nodes": [...sources...],
    "edges": [...evidence_edges...]
}
```

## Vector Embeddings

### Using Gemini for Embeddings

```python
import google.generativeai as genai
from app.config import settings

genai.configure(api_key=settings.gemini_api_key)

def get_embedding(text: str) -> list[float]:
    """Get 1536-dimensional embedding from Gemini."""
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_document",
        output_dimensionality=1536
    )
    return result['embedding']

# Use it
embedding = get_embedding("Climate change is affecting polar bears")
# embedding is now a list of 1536 floats
```

### Similarity Search

The `match_claims()` function uses cosine similarity:

- Similarity score: 0.0 (completely different) to 1.0 (identical)
- Recommended threshold: 0.75 for high similarity
- Uses pgvector's `<=>` operator for efficient search

## Performance

### Indexes

All foreign keys and commonly queried columns are indexed:
- `session_id` on all tables
- `credibility_score` on sources
- `confidence` on claims and conflicts
- Vector index on embeddings (IVFFlat)

### Query Patterns

**Get full research session data:**

```python
# Efficient: one query per type
session = await get_session(session_id)
sources = await get_sources_by_session(session_id)
claims = await get_claims_by_session(session_id)
conflicts = await get_conflicts_by_session(session_id)
graph = await get_evidence_graph(session_id)
```

**Batch inserts:**

```python
# Efficient: insert multiple records at once
await insert_sources(session_id, [source1, source2, source3])
await insert_claims(session_id, [claim1, claim2, claim3])
```

## Row Level Security

All tables have RLS enabled with these policies:

- **Anonymous users (anon role)**: Read-only access
- **Authenticated users**: Full read/write access
- **Service role**: Bypass RLS (use with caution)

To restrict data by user in production:

```sql
-- Example: Users can only see their own sessions
CREATE POLICY "Users see own sessions" ON research_sessions
    FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);
```

## Error Handling

All database functions:
- Log errors using Python logging
- Raise exceptions on write failures
- Return empty lists/None on read failures
- Include try/except blocks

Example:

```python
try:
    session = await create_session("query")
except Exception as e:
    logger.error(f"Failed to create session: {e}")
    # Handle error in your service layer
```

## Testing

Run the comprehensive test suite:

```bash
python test_database.py
```

This tests:
- ✓ Session creation and updates
- ✓ Source insertion and retrieval
- ✓ AI flag updates
- ✓ Claim insertion and similarity search
- ✓ Conflict detection
- ✓ Evidence graph construction

## Troubleshooting

### "Extension vector does not exist"

Run the migration again. The first line enables pgvector:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### "Function match_claims does not exist"

The RPC function wasn't created. Run the migration completely.

### "Embedding dimension mismatch"

Ensure embeddings are exactly 1536 floats. Check:
```python
assert len(embedding) == 1536
assert settings.embedding_dim == 1536
```

### RLS Blocking Queries

For development, you can temporarily disable RLS:
```sql
ALTER TABLE research_sessions DISABLE ROW LEVEL SECURITY;
```

## Next Steps

1. ✅ Run migration in Supabase
2. ✅ Test database functions
3. ⚠️ Implement Gemini embedding service
4. ⚠️ Build service layer that uses these functions
5. ⚠️ Create API endpoints
6. ⚠️ Test end-to-end workflow

## Resources

- [Supabase Documentation](https://supabase.com/docs)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [Gemini Embeddings](https://ai.google.dev/docs/embeddings_guide)
- [supabase-py Client](https://github.com/supabase-community/supabase-py)
