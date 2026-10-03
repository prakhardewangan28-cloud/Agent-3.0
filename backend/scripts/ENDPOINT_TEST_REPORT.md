# Endpoint Test Report

**Generated:** 2026-10-01T19:41:16.367974

**Result:** 9/9 tests passed

**Status:** ✅ All tests passed

**Total Duration:** 29.8s

---

## Test Results

| Test | Status | Duration | Message |
|------|--------|----------|---------|
| TEST 1: GET /api/v1/health | ✅ | 2.33ms | OK - status=ok, mock_mode=True, version=0.1.0 |
| TEST 2: GET /health (legacy) | ✅ | 2.55ms | OK - status=ok |
| TEST 3: POST /api/v1/research/start (specific) | ✅ | 689.84ms | OK - session_id=44745b28..., needs_refinement=false |
| TEST 4: POST /api/v1/research/start (vague) | ✅ | 1116.39ms | OK - needs_refinement=true, 4 options provided |
| TEST 5: POST /api/v1/research/start (empty) | ✅ | 3.04ms | OK - validation error returned |
| TEST 6: GET /api/v1/research/{session_id} | ✅ | 26417.27ms | OK - status=complete, 29 sources (5 polls, 26.4s) |
| TEST 7: GET /api/v1/research/{session_id}/report | ✅ | 446.47ms | OK - 2799 chars |
| TEST 8: GET /api/v1/research/{unknown_uuid} | ✅ | 448.29ms | OK - 404 returned for unknown UUID |
| TEST 9: GET /api/v1/sessions | ✅ | 671.83ms | OK - 18 sessions returned |

---

## Summary

- **Total Tests:** 9
- **Passed:** 9
- **Failed:** 0
- **Success Rate:** 100.0%
