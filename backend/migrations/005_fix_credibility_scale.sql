-- Fix credibility_score scale from 0-1 to 0-100

-- Drop old constraint
ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_credibility_score_check;

-- Add new constraint allowing 0-100
ALTER TABLE sources ADD CONSTRAINT sources_credibility_score_check
  CHECK (credibility_score >= 0 AND credibility_score <= 100);

-- Similarly for ai_generation_confidence if it exists
ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_ai_generation_confidence_check;
ALTER TABLE sources ADD CONSTRAINT sources_ai_generation_confidence_check
  CHECK (ai_generation_confidence >= 0 AND ai_generation_confidence <= 1);
