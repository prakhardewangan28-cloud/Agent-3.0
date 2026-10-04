-- Migration 006: Add frontend support features
-- Adds: summary, language, images, per-source summaries

-- Add summary field to research_sessions
ALTER TABLE research_sessions
ADD COLUMN IF NOT EXISTS summary TEXT NULL;

-- Add language field to research_sessions
ALTER TABLE research_sessions
ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'en';

-- Add summary field to sources
ALTER TABLE sources
ADD COLUMN IF NOT EXISTS summary TEXT NULL;

-- Create session_images table
CREATE TABLE IF NOT EXISTS session_images (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_id UUID NOT NULL REFERENCES research_sessions(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    thumbnail TEXT,
    title TEXT,
    source_url TEXT,
    domain TEXT,
    is_placeholder BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for session_images
CREATE INDEX IF NOT EXISTS idx_session_images_session_id ON session_images(session_id);

-- Add comment
COMMENT ON TABLE session_images IS 'Stores Google Images results for research sessions';
