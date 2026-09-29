-- ============================================================================
-- Migration 003: Add all missing columns confirmed absent from live database
-- Run this in your Supabase SQL Editor.
--
-- Safe to run multiple times — all statements use IF NOT EXISTS guards.
-- Does NOT drop tables, does NOT delete data, does NOT reset the database.
--
-- Confirmed missing (probed 2026-09-29):
--   sources.source_type             TEXT  — required by insert_sources / check_db
--   research_sessions.final_report  TEXT  — from 002 (never applied)
--   research_sessions.node_timings  JSONB — from 002 (never applied)
--   research_sessions.error         TEXT  — from 002 (never applied)
--
-- Also re-applies the status CHECK constraint fix from 002 (idempotent).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- sources: add source_type column
-- (was never present in 001_initial.sql; required by application code)
-- ----------------------------------------------------------------------------
ALTER TABLE sources
    ADD COLUMN IF NOT EXISTS source_type TEXT;

-- ----------------------------------------------------------------------------
-- research_sessions: add columns from migration 002 (not previously applied)
-- ----------------------------------------------------------------------------

-- Stores the final markdown research report
ALTER TABLE research_sessions
    ADD COLUMN IF NOT EXISTS final_report TEXT;

-- Stores per-node timing data for the pipeline
ALTER TABLE research_sessions
    ADD COLUMN IF NOT EXISTS node_timings JSONB DEFAULT '{}';

-- Stores error message when status = 'failed'
ALTER TABLE research_sessions
    ADD COLUMN IF NOT EXISTS error TEXT;

-- ----------------------------------------------------------------------------
-- research_sessions: expand status CHECK to include 'needs_refinement'
-- Must DROP and re-ADD — PostgreSQL does not support in-place ALTER CHECK.
-- The DROP uses IF EXISTS so it is safe to re-run.
-- ----------------------------------------------------------------------------
ALTER TABLE research_sessions
    DROP CONSTRAINT IF EXISTS research_sessions_status_check;

ALTER TABLE research_sessions
    ADD CONSTRAINT research_sessions_status_check
    CHECK (status IN ('in_progress', 'complete', 'failed', 'needs_refinement'));

-- ============================================================================
-- SUMMARY
-- Adds to sources:           source_type TEXT
-- Adds to research_sessions: final_report TEXT, node_timings JSONB, error TEXT
-- Fixes research_sessions:   status CHECK now includes 'needs_refinement'
-- Safe:  all ADD COLUMN use IF NOT EXISTS; DROP CONSTRAINT uses IF EXISTS
-- ============================================================================
