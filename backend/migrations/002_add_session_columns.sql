-- ============================================================================
-- Migration 002: Add missing columns and fix status constraint
-- Run this in your Supabase SQL Editor AFTER 001_initial.sql
--
-- Safe to run multiple times (uses IF NOT EXISTS and DROP/ADD CONSTRAINT).
--
-- Changes:
--   • Add final_report TEXT column to research_sessions
--   • Add node_timings JSONB column to research_sessions
--   • Add error TEXT column to research_sessions
--   • Expand status CHECK to include 'needs_refinement'
--     (required by research agent state machine)
-- ============================================================================

-- Add final_report column (stores the markdown research report)
ALTER TABLE research_sessions
    ADD COLUMN IF NOT EXISTS final_report TEXT;

-- Add node_timings column (stores timing data per pipeline node)
ALTER TABLE research_sessions
    ADD COLUMN IF NOT EXISTS node_timings JSONB DEFAULT '{}';

-- Add error column (stores error message if status = 'failed')
ALTER TABLE research_sessions
    ADD COLUMN IF NOT EXISTS error TEXT;

-- Expand status CHECK constraint to include 'needs_refinement'
-- Must DROP and re-ADD because PostgreSQL does not support ALTER CHECK in-place
ALTER TABLE research_sessions
    DROP CONSTRAINT IF EXISTS research_sessions_status_check;

ALTER TABLE research_sessions
    ADD CONSTRAINT research_sessions_status_check
    CHECK (status IN ('in_progress', 'complete', 'failed', 'needs_refinement'));

-- ============================================================================
-- SUMMARY
-- Adds: final_report TEXT, node_timings JSONB, error TEXT
-- Fixes: status CHECK now includes 'needs_refinement'
-- Safe: all operations use IF NOT EXISTS / IF EXISTS guards
-- ============================================================================
