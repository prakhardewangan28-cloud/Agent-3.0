-- ============================================================================
-- Migration 004: Add counter_argument column
-- Run this in your Supabase SQL Editor.
--
-- Safe to run multiple times — uses IF NOT EXISTS guards.
--
-- Purpose:
--   Adds counter_argument JSONB column to store the opposing perspective
--   generated after the research report is complete.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- research_sessions: add counter_argument column
-- ----------------------------------------------------------------------------

-- Stores the counter-argument JSON with structure:
-- {
--   "counter_argument": "3-5 sentence argument...",
--   "supporting_sources": [{source_id, url, domain, credibility_score, reason}, ...],
--   "strength": "strong" | "moderate" | "weak" | "none",
--   "explanation": "Why this rating was given"
-- }
ALTER TABLE research_sessions
    ADD COLUMN IF NOT EXISTS counter_argument JSONB;

-- Create GIN index for efficient JSON queries
CREATE INDEX IF NOT EXISTS idx_sessions_counter_argument
    ON research_sessions USING gin (counter_argument);

-- ============================================================================
-- SUMMARY
-- Adds to research_sessions: counter_argument JSONB
-- Index: GIN index on counter_argument for efficient JSON queries
-- Safe: uses IF NOT EXISTS guards
-- ============================================================================
