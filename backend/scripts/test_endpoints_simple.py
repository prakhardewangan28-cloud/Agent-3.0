"""
Simplified endpoint testing script - assumes server is already running on port 8000.

Usage:
    1. Start server: python -m uvicorn app.main:app --port 8000
    2. Run tests: python scripts/test_endpoints_simple.py
"""
import asyncio
import httpx
import sys
import uuid
from datetime import datetime
from pathlib import Path

BASE_URL = "http://127.0.0.1:8001"
RESULTS = []


def record(name: str, passed: bool, message: str, duration_ms: float = 0):
    """Record a test result."""
    RESULTS.append({
        "name": name,
        "passed": passed,
        "message": message,
        "duration_ms": round(duration_ms, 2),
    })
    icon = "✅" if passed else "❌"
    print(f"{icon} {name} ({duration_ms:.0f}ms): {message}")


async def test_health_v1(client):
    """TEST 1 — GET /api/v1/health"""
    import time
    start = time.time()
    try:
        r = await client.get(f"{BASE_URL}/api/v1/health")
        duration = (time.time() - start) * 1000
        
        if r.status_code != 200:
            record("TEST 1: GET /api/v1/health", False, f"Expected 200, got {r.status_code}", duration)
            return
        
        data = r.json()
        required_fields = ["status", "mock_mode", "version"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            record("TEST 1: GET /api/v1/health", False, f"Missing fields: {missing_fields}", duration)
            return
        
        if data["status"] != "ok":
            record("TEST 1: GET /api/v1/health", False, f"Status is '{data['status']}', expected 'ok'", duration)
            return
        
        record("TEST 1: GET /api/v1/health", True, f"OK - status=ok, mock_mode={data['mock_mode']}, version={data['version']}", duration)
    except Exception as e:
        duration = (time.time() - start) * 1000
        record("TEST 1: GET /api/v1/health", False, f"Exception: {e}", duration)


async def test_health_legacy(client):
    """TEST 2 — GET /health (legacy)"""
    import time
    start = time.time()
    try:
        r = await client.get(f"{BASE_URL}/health")
        duration = (time.time() - start) * 1000
        
        if r.status_code != 200:
            record("TEST 2: GET /health (legacy)", False, f"Expected 200, got {r.status_code}", duration)
            return
        
        data = r.json()
        if "status" not in data:
            record("TEST 2: GET /health (legacy)", False, "Missing 'status' field", duration)
            return
        
        record("TEST 2: GET /health (legacy)", True, f"OK - status={data['status']}", duration)
    except Exception as e:
        duration = (time.time() - start) * 1000
        record("TEST 2: GET /health (legacy)", False, f"Exception: {e}", duration)


async def test_research_start_specific(client):
    """TEST 3 — POST /api/v1/research/start (specific query)"""
    import time
    start = time.time()
    try:
        r = await client.post(
            f"{BASE_URL}/api/v1/research/start",
            json={"query": "What are the health benefits of apples?"}
        )
        duration = (time.time() - start) * 1000
        
        if r.status_code != 200:
            record("TEST 3: POST /api/v1/research/start (specific)", False, f"Expected 200, got {r.status_code}", duration)
            return None
        
        data = r.json()
        required_fields = ["session_id", "status", "needs_refinement"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            record("TEST 3: POST /api/v1/research/start (specific)", False, f"Missing fields: {missing_fields}", duration)
            return None
        
        if data["needs_refinement"] != False:
            record("TEST 3: POST /api/v1/research/start (specific)", False, f"Expected needs_refinement=false, got {data['needs_refinement']}", duration)
            return None
        
        # Validate UUID format
        try:
            uuid.UUID(data["session_id"])
        except ValueError:
            record("TEST 3: POST /api/v1/research/start (specific)", False, f"Invalid UUID: {data['session_id']}", duration)
            return None
        
        session_id = data["session_id"]
        record("TEST 3: POST /api/v1/research/start (specific)", True, f"OK - session_id={session_id[:8]}..., needs_refinement=false", duration)
        return session_id
    except Exception as e:
        duration = (time.time() - start) * 1000
        record("TEST 3: POST /api/v1/research/start (specific)", False, f"Exception: {e}", duration)
        return None


async def test_research_start_vague(client):
    """TEST 4 — POST /api/v1/research/start (vague query)"""
    import time
    start = time.time()
    try:
        r = await client.post(
            f"{BASE_URL}/api/v1/research/start",
            json={"query": "apple"}
        )
        duration = (time.time() - start) * 1000
        
        if r.status_code != 200:
            record("TEST 4: POST /api/v1/research/start (vague)", False, f"Expected 200, got {r.status_code}", duration)
            return None
        
        data = r.json()
        
        if "needs_refinement" not in data:
            record("TEST 4: POST /api/v1/research/start (vague)", False, "Missing 'needs_refinement' field", duration)
            return None
        
        if data["needs_refinement"] != True:
            record("TEST 4: POST /api/v1/research/start (vague)", False, f"Expected needs_refinement=true, got {data['needs_refinement']}", duration)
            return None
        
        if "options" not in data:
            record("TEST 4: POST /api/v1/research/start (vague)", False, "Missing 'options' field", duration)
            return None
        
        if not isinstance(data["options"], list) or len(data["options"]) < 4:
            record("TEST 4: POST /api/v1/research/start (vague)", False, f"Expected options list with 4+ items, got {len(data.get('options', []))}", duration)
            return None
        
        session_id = data.get("session_id")
        record("TEST 4: POST /api/v1/research/start (vague)", True, f"OK - needs_refinement=true, {len(data['options'])} options provided", duration)
        return session_id
    except Exception as e:
        duration = (time.time() - start) * 1000
        record("TEST 4: POST /api/v1/research/start (vague)", False, f"Exception: {e}", duration)
        return None


async def test_research_start_empty(client):
    """TEST 5 — POST /api/v1/research/start (empty query)"""
    import time
    start = time.time()
    try:
        r = await client.post(
            f"{BASE_URL}/api/v1/research/start",
            json={"query": ""}
        )
        duration = (time.time() - start) * 1000
        
        if r.status_code != 422:
            record("TEST 5: POST /api/v1/research/start (empty)", False, f"Expected 422, got {r.status_code}", duration)
            return
        
        record("TEST 5: POST /api/v1/research/start (empty)", True, "OK - validation error returned", duration)
    except Exception as e:
        duration = (time.time() - start) * 1000
        record("TEST 5: POST /api/v1/research/start (empty)", False, f"Exception: {e}", duration)


async def test_research_get(client, session_id):
    """TEST 6 — GET /api/v1/research/{session_id} - poll until complete"""
    import time
    if not session_id:
        record("TEST 6: GET /api/v1/research/{session_id}", False, "No session_id from TEST 3", 0)
        return
    
    start = time.time()
    try:
        max_wait = 45
        poll_interval = 3
        attempts = 0
        
        while time.time() - start < max_wait:
            attempts += 1
            r = await client.get(f"{BASE_URL}/api/v1/research/{session_id}")
            
            if r.status_code != 200:
                duration = (time.time() - start) * 1000
                record("TEST 6: GET /api/v1/research/{session_id}", False, f"Expected 200, got {r.status_code}", duration)
                return
            
            data = r.json()
            status = data.get("status", "unknown")
            
            if status != "in_progress":
                duration = (time.time() - start) * 1000
                
                required_fields = ["session_id", "status", "sources", "landscape", "final_report"]
                missing_fields = [f for f in required_fields if f not in data]
                
                if missing_fields:
                    record("TEST 6: GET /api/v1/research/{session_id}", False, f"Missing fields: {missing_fields}", duration)
                    return
                
                if not isinstance(data["sources"], list):
                    record("TEST 6: GET /api/v1/research/{session_id}", False, "sources is not a list", duration)
                    return
                
                if not isinstance(data["landscape"], dict):
                    record("TEST 6: GET /api/v1/research/{session_id}", False, "landscape is not a dict", duration)
                    return
                
                if not isinstance(data["final_report"], str):
                    record("TEST 6: GET /api/v1/research/{session_id}", False, "final_report is not a string", duration)
                    return
                
                record("TEST 6: GET /api/v1/research/{session_id}", True, 
                       f"OK - status={status}, {len(data['sources'])} sources ({attempts} polls, {duration/1000:.1f}s)", 
                       duration)
                return
            
            print(f"  ⏳ Poll {attempts}: status=in_progress, waiting {poll_interval}s...")
            await asyncio.sleep(poll_interval)
        
        duration = (time.time() - start) * 1000
        record("TEST 6: GET /api/v1/research/{session_id}", False, f"Timeout after {max_wait}s, status still 'in_progress'", duration)
    except Exception as e:
        duration = (time.time() - start) * 1000
        record("TEST 6: GET /api/v1/research/{session_id}", False, f"Exception: {e}", duration)


async def test_research_get_report(client, session_id):
    """TEST 7 — GET /api/v1/research/{session_id}/report"""
    import time
    if not session_id:
        record("TEST 7: GET /api/v1/research/{session_id}/report", False, "No session_id from TEST 3", 0)
        return
    
    start = time.time()
    try:
        r = await client.get(f"{BASE_URL}/api/v1/research/{session_id}/report")
        duration = (time.time() - start) * 1000
        
        if r.status_code == 404:
            record("TEST 7: GET /api/v1/research/{session_id}/report", True, "OK - 404 (report not ready)", duration)
            return
        
        if r.status_code != 200:
            record("TEST 7: GET /api/v1/research/{session_id}/report", False, f"Expected 200 or 404, got {r.status_code}", duration)
            return
        
        content_type = r.headers.get("content-type", "")
        body = r.text
        
        if len(body) < 500:
            record("TEST 7: GET /api/v1/research/{session_id}/report", False, f"Report too short: {len(body)} chars (expected > 500)", duration)
            return
        
        record("TEST 7: GET /api/v1/research/{session_id}/report", True, f"OK - {len(body)} chars", duration)
    except Exception as e:
        duration = (time.time() - start) * 1000
        record("TEST 7: GET /api/v1/research/{session_id}/report", False, f"Exception: {e}", duration)


async def test_research_get_unknown(client):
    """TEST 8 — GET /api/v1/research/{unknown_uuid}"""
    import time
    start = time.time()
    try:
        unknown_uuid = "00000000-0000-0000-0000-000000000000"
        r = await client.get(f"{BASE_URL}/api/v1/research/{unknown_uuid}")
        duration = (time.time() - start) * 1000
        
        if r.status_code != 404:
            record("TEST 8: GET /api/v1/research/{unknown_uuid}", False, f"Expected 404, got {r.status_code}", duration)
            return
        
        record("TEST 8: GET /api/v1/research/{unknown_uuid}", True, "OK - 404 returned for unknown UUID", duration)
    except Exception as e:
        duration = (time.time() - start) * 1000
        record("TEST 8: GET /api/v1/research/{unknown_uuid}", False, f"Exception: {e}", duration)


async def test_sessions_list(client):
    """TEST 9 — GET /api/v1/sessions"""
    import time
    start = time.time()
    try:
        r = await client.get(f"{BASE_URL}/api/v1/sessions")
        duration = (time.time() - start) * 1000
        
        if r.status_code != 200:
            record("TEST 9: GET /api/v1/sessions", False, f"Expected 200, got {r.status_code}", duration)
            return
        
        data = r.json()
        if not isinstance(data, list):
            record("TEST 9: GET /api/v1/sessions", False, "Response is not a list", duration)
            return
        
        if len(data) < 1:
            record("TEST 9: GET /api/v1/sessions", False, "Expected at least 1 session", duration)
            return
        
        record("TEST 9: GET /api/v1/sessions", True, f"OK - {len(data)} sessions returned", duration)
    except Exception as e:
        duration = (time.time() - start) * 1000
        record("TEST 9: GET /api/v1/sessions", False, f"Exception: {e}", duration)


async def main():
    """Main test execution."""
    print("=" * 70)
    print("KNOWLEDGE INTELLIGENCE AGENT - ENDPOINT TESTS")
    print("=" * 70)
    print()
    print(f"Testing server at: {BASE_URL}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            # Check if server is responsive
            print("Checking server connectivity...")
            try:
                r = await client.get(f"{BASE_URL}/api/v1/health", timeout=5.0)
                if r.status_code == 200:
                    print("✓ Server is responsive\n")
                else:
                    print(f"❌ Server returned status {r.status_code}\n")
                    return 1
            except Exception as e:
                print(f"❌ Cannot connect to server: {e}\n")
                print("Please start the server first:")
                print("  python -m uvicorn app.main:app --port 8000\n")
                return 1
            
            print("Running endpoint tests...\n")
            
            await test_health_v1(client)
            await test_health_legacy(client)
            
            specific_session_id = await test_research_start_specific(client)
            vague_session_id = await test_research_start_vague(client)
            
            await test_research_start_empty(client)
            await test_research_get(client, specific_session_id)
            await test_research_get_report(client, specific_session_id)
            await test_research_get_unknown(client)
            await test_sessions_list(client)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user\n")
        return 1
    
    # Print summary
    print("\n" + "=" * 70)
    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r["passed"])
    failed = total - passed
    
    if failed == 0:
        print(f"✅ ALL TESTS PASSED: {passed}/{total}")
    else:
        print(f"❌ SOME TESTS FAILED: {passed}/{total} passed, {failed} failed")
    
    total_duration = sum(r["duration_ms"] for r in RESULTS)
    print(f"⏱️  Total duration: {total_duration/1000:.1f}s")
    print("=" * 70)
    print()
    
    # Save report
    backend_dir = Path(__file__).parent.parent
    report_path = backend_dir / "scripts" / "ENDPOINT_TEST_REPORT.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Endpoint Test Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write(f"**Result:** {passed}/{total} tests passed\n\n")
        
        if failed > 0:
            f.write(f"**Status:** ❌ {failed} test(s) failed\n\n")
        else:
            f.write(f"**Status:** ✅ All tests passed\n\n")
        
        f.write(f"**Total Duration:** {total_duration/1000:.1f}s\n\n")
        f.write("---\n\n")
        f.write("## Test Results\n\n")
        f.write("| Test | Status | Duration | Message |\n")
        f.write("|------|--------|----------|---------|\n")
        
        for r in RESULTS:
            icon = "✅" if r["passed"] else "❌"
            name = r["name"].replace("|", "\\|")
            message = r["message"].replace("|", "\\|")
            f.write(f"| {name} | {icon} | {r['duration_ms']}ms | {message} |\n")
        
        f.write("\n---\n\n")
        f.write("## Summary\n\n")
        f.write(f"- **Total Tests:** {total}\n")
        f.write(f"- **Passed:** {passed}\n")
        f.write(f"- **Failed:** {failed}\n")
        f.write(f"- **Success Rate:** {(passed/total*100):.1f}%\n")
    
    print(f"📄 Report saved to: {report_path}\n")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
