# Bug Fixes Summary

## Date: 2026-09-27

### ISSUE 1: Demo Script Crashes with 'refined_query' Error

**Problem:**
When running `python scripts/demo_counter_argument.py` or `demo_research.py`, the scripts crashed with:
```
Research failed: 'refined_query'
No final report, skipping counter-argument
```

**Root Cause:**
In `backend/app/agents/research_agent.py`, the `run_research()` function did not initialize the `refined_query` field in the initial state. Downstream nodes (`plan_node`, `search_node`, `report_node`) all expected `state["refined_query"]` to exist, causing KeyError when accessed.

**Fix:**
Updated `run_research()` to initialize `refined_query` with the original query as a default value:
```python
initial_state: ResearchState = {
    "original_query": query,
    "refined_query": query,  # Default to original, refine_node will override if needed
    "session_id": session_id,
    "status": "in_progress",
    "needs_refinement": False,
    "node_timings": {}
}
```

The `refine_node` will override this value if refinement is needed.

**Files Changed:**
- `backend/app/agents/research_agent.py` (lines 660-666)

---

### ISSUE 2: Credibility Scores Too Low for Trusted Domains

**Problem:**
NASA.gov sources were scoring 25/100 instead of the expected 65-90. The diagnostic showed:
- `science.nasa.gov` was not matching `nasa.gov` in `TRUSTED_DOMAINS`
- Sources were missing the +25 trusted domain bonus

**Root Cause:**
The credibility scoring logic used exact string matching (`domain in TRUSTED_DOMAINS`), which failed for subdomains like `science.nasa.gov`, `www.bbc.com`, etc.

**Fix:**
Added subdomain matching support with two new helper functions:

1. `_is_trusted_domain(domain: str) -> bool`
   - Checks exact match first
   - Falls back to subdomain matching (e.g., `science.nasa.gov` matches `nasa.gov`)

2. `_is_low_trust_domain(domain: str) -> bool`
   - Same logic for untrusted domains (e.g., `blog.infowars.com` matches `infowars.com`)

**Example:**
```python
# Before: science.nasa.gov → 25/100 (only .gov bonus)
# After:  science.nasa.gov → 65/100 (.gov + trusted domain + freshness)
```

**Files Changed:**
- `backend/app/services/credibility_service.py`:
  - Added `_is_trusted_domain()` helper (lines 255-278)
  - Added `_is_low_trust_domain()` helper (lines 281-299)
  - Updated RULE 2 to use `_is_trusted_domain()` (line 108)
  - Updated RULE 3 to use `_is_low_trust_domain()` (line 112)

**Tests Added:**
- `backend/tests/test_credibility_service.py`:
  - `test_trusted_domain_subdomain_match()` - Verifies `science.nasa.gov` gets trusted bonus
  - `test_low_trust_domain_subdomain_match()` - Verifies `blog.infowars.com` gets penalty

---

### Diagnostic Script Created

**File:** `backend/scripts/diagnose_credibility.py`

A diagnostic tool to test credibility scoring with a NASA source:
- Creates a test NASA.gov source
- Scores it using `score_source()`
- Displays breakdown of all scoring rules
- Validates expected scores and identifies issues

**Usage:**
```bash
python scripts/diagnose_credibility.py
```

**Output:**
```
Score: 65.0/100
  domain_suffix     +25.0  (.gov bonus)
  trusted_domain    +25.0  (nasa.gov in TRUSTED_DOMAINS)
  freshness         +15.0  (within 30 days)
✓ PASS: Score is realistic for NASA.gov source
```

---

## Test Results

**Before Fixes:** Tests passed, but demo scripts crashed

**After Fixes:**
- ✅ All 127 tests passing (125 original + 2 new subdomain tests)
- ✅ Demo scripts no longer crash with `refined_query` error
- ✅ NASA.gov sources score 65/100 (realistic for .gov + trusted domain + fresh date)
- ✅ Subdomain matching works for both trusted and untrusted domains

---

## Verification Checklist

- [x] `python -m pytest -v` → 127 tests passing
- [x] `python scripts/diagnose_credibility.py` → PASS (65/100 for NASA)
- [x] Demo scripts no longer crash with `refined_query` KeyError
- [x] Subdomain matching works (science.nasa.gov → trusted)
- [x] Low-trust subdomain matching works (blog.infowars.com → untrusted)

---

## Notes

- The demo script still hits API quota limits with real Gemini calls, but this is expected behavior (not a bug)
- To run demos without quota issues, set `MOCK_MODE=true` in `.env`
- Credibility scoring is heuristic-based and doesn't call external APIs
