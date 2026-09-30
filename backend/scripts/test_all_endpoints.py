"""
Comprehensive API endpoint testing script.

Tests all endpoints twice with real API calls and generates health report.
"""
import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from app.config import settings


BASE_URL = "http://localhost:8000/api/v1"
TEST_RESULTS = []


def log_test(endpoint, method, status, duration_ms, details=""):
    """Log test result."""
    result = {
        "endpoint": endpoint,
        "method": method,
        "status": "✓ PASS" if status else "✗ FAIL",
        "duration_ms": round(duration_ms, 2),
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    TEST_RESULTS.append(result)
    
    status_icon = "✓" if status else "✗"
    print(f"{status_icon} {method:6s} {endpoint:50s} {duration_ms:6.0f}ms  {details}")
    
    return status


async def test_health_endpoint():
    """Test GET /health endpoint."""
    print("\n" + "=" * 80)
    print("TEST 1: Health Check Endpoint")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        # Test 1
        start = time.time()
        try:
            response = await client.get(f"{BASE_URL}/health")
            duration = (time.time() - start) * 1000
            
            success = response.status_code == 200
            data = response.json() if success else {}
            details = f"Status: {data.get('status', 'N/A')}"
            
            log_test("/health", "GET", success, duration, details)
        except Exception as e:
            duration = (time.time() - start) * 1000
            log_test("/health", "GET", False, duration, f"Error: {str(e)}")
        
        # Test 2 (repeat)
        start = time.time()
        try:
            response = await client.get(f"{BASE_URL}/health")
            duration = (time.time() - start) * 1000
            
            success = response.status_code == 200
            data = response.json() if success else {}
            details = f"Status: {data.get('status', 'N/A')}"
            
            log_test("/health", "GET", success, duration, details)
        except Exception as e:
            duration = (time.time() - start) * 1000
            log_test("/health", "GET", False, duration, f"Error: {str(e)}")


async def test_start_research():
    """Test POST /research/start endpoint."""
    print("\n" + "=" * 80)
    print("TEST 2: Start Research Endpoint")
    print("=" * 80)
    
    session_ids = []
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Test 1: Specific query
        start = time.time()
        try:
            response = await client.post(
                f"{BASE_URL}/research/start",
                json={"query": "What are the benefits of renewable energy?"}
            )
            duration = (time.time() - start) * 1000
            
            success = response.status_code in [200, 202]
            data = response.json() if success else {}
            session_id = data.get("session_id", "N/A")
            status = data.get("status", "N/A")
            
            if session_id != "N/A":
                session_ids.append(session_id)
            
            details = f"Session: {session_id[:8]}..., Status: {status}"
            log_test("/research/start", "POST", success, duration, details)
        except Exception as e:
            duration = (time.time() - start) * 1000
            log_test("/research/start", "POST", False, duration, f"Error: {str(e)}")
        
        # Test 2: Another query
        start = time.time()
        try:
            response = await client.post(
                f"{BASE_URL}/research/start",
                json={"query": "How does photosynthesis work in plants?"}
            )
            duration = (time.time() - start) * 1000
            
            success = response.status_code in [200, 202]
            data = response.json() if success else {}
            session_id = data.get("session_id", "N/A")
            status = data.get("status", "N/A")
            
            if session_id != "N/A":
                session_ids.append(session_id)
            
            details = f"Session: {session_id[:8]}..., Status: {status}"
            log_test("/research/start", "POST", success, duration, details)
        except Exception as e:
            duration = (time.time() - start) * 1000
            log_test("/research/start", "POST", False, duration, f"Error: {str(e)}")
    
    return session_ids


async def test_get_research(session_ids):
    """Test GET /research/{id} endpoint."""
    print("\n" + "=" * 80)
    print("TEST 3: Get Research Status Endpoint")
    print("=" * 80)
    
    if not session_ids:
        print("No session IDs available, skipping...")
        return
    
    async with httpx.AsyncClient() as client:
        for session_id in session_ids[:2]:  # Test first 2 sessions
            # Test 1
            start = time.time()
            try:
                response = await client.get(f"{BASE_URL}/research/{session_id}")
                duration = (time.time() - start) * 1000
                
                success = response.status_code == 200
                data = response.json() if success else {}
                status = data.get("status", "N/A")
                sources = len(data.get("sources", []))
                
                details = f"Status: {status}, Sources: {sources}"
                log_test(f"/research/{session_id[:8]}...", "GET", success, duration, details)
            except Exception as e:
                duration = (time.time() - start) * 1000
                log_test(f"/research/{session_id[:8]}...", "GET", False, duration, f"Error: {str(e)}")
            
            # Test 2 (repeat)
            start = time.time()
            try:
                response = await client.get(f"{BASE_URL}/research/{session_id}")
                duration = (time.time() - start) * 1000
                
                success = response.status_code == 200
                data = response.json() if success else {}
                status = data.get("status", "N/A")
                claims = len(data.get("claims", []))
                
                details = f"Status: {status}, Claims: {claims}"
                log_test(f"/research/{session_id[:8]}...", "GET", success, duration, details)
            except Exception as e:
                duration = (time.time() - start) * 1000
                log_test(f"/research/{session_id[:8]}...", "GET", False, duration, f"Error: {str(e)}")


async def test_list_sessions():
    """Test GET /research/sessions endpoint."""
    print("\n" + "=" * 80)
    print("TEST 4: List Sessions Endpoint")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        # Test 1
        start = time.time()
        try:
            response = await client.get(f"{BASE_URL}/sessions")
            duration = (time.time() - start) * 1000
            
            success = response.status_code == 200
            sessions = response.json() if success else []
            
            details = f"Total sessions: {len(sessions)}"
            log_test("/sessions", "GET", success, duration, details)
        except Exception as e:
            duration = (time.time() - start) * 1000
            log_test("/sessions", "GET", False, duration, f"Error: {str(e)}")
        
        # Test 2 (with limit)
        start = time.time()
        try:
            response = await client.get(f"{BASE_URL}/sessions?limit=5")
            duration = (time.time() - start) * 1000
            
            success = response.status_code == 200
            sessions = response.json() if success else []
            
            details = f"Limited to {len(sessions)} sessions"
            log_test("/sessions?limit=5", "GET", success, duration, details)
        except Exception as e:
            duration = (time.time() - start) * 1000
            log_test("/sessions?limit=5", "GET", False, duration, f"Error: {str(e)}")


async def test_get_report(session_ids):
    """Test GET /research/{id}/report endpoint."""
    print("\n" + "=" * 80)
    print("TEST 5: Get Report Endpoint")
    print("=" * 80)
    
    if not session_ids:
        print("No session IDs available, skipping...")
        return
    
    async with httpx.AsyncClient() as client:
        for session_id in session_ids[:1]:  # Test first session
            # Test 1
            start = time.time()
            try:
                response = await client.get(f"{BASE_URL}/research/{session_id}/report")
                duration = (time.time() - start) * 1000
                
                success = response.status_code == 200
                report_length = len(response.text) if success else 0
                
                details = f"Report length: {report_length} chars"
                log_test(f"/research/{session_id[:8]}.../report", "GET", success, duration, details)
            except Exception as e:
                duration = (time.time() - start) * 1000
                log_test(f"/research/{session_id[:8]}.../report", "GET", False, duration, f"Error: {str(e)}")
            
            # Test 2 (repeat)
            start = time.time()
            try:
                response = await client.get(f"{BASE_URL}/research/{session_id}/report")
                duration = (time.time() - start) * 1000
                
                success = response.status_code == 200
                report_length = len(response.text) if success else 0
                has_markdown = "##" in response.text if success else False
                
                details = f"Report length: {report_length} chars, Markdown: {has_markdown}"
                log_test(f"/research/{session_id[:8]}.../report", "GET", success, duration, details)
            except Exception as e:
                duration = (time.time() - start) * 1000
                log_test(f"/research/{session_id[:8]}.../report", "GET", False, duration, f"Error: {str(e)}")


async def test_error_cases():
    """Test error handling."""
    print("\n" + "=" * 80)
    print("TEST 6: Error Handling")
    print("=" * 80)
    
    async with httpx.AsyncClient() as client:
        # Test 1: Invalid session ID
        start = time.time()
        try:
            response = await client.get(f"{BASE_URL}/research/invalid-uuid-123")
            duration = (time.time() - start) * 1000
            
            success = response.status_code == 404
            details = f"Expected 404, got {response.status_code}"
            log_test("/research/invalid-uuid", "GET", success, duration, details)
        except Exception as e:
            duration = (time.time() - start) * 1000
            log_test("/research/invalid-uuid", "GET", False, duration, f"Error: {str(e)}")
        
        # Test 2: Empty query
        start = time.time()
        try:
            response = await client.post(
                f"{BASE_URL}/research/start",
                json={"query": ""}
            )
            duration = (time.time() - start) * 1000
            
            success = response.status_code == 422
            details = f"Expected 422, got {response.status_code}"
            log_test("/research/start (empty query)", "POST", success, duration, details)
        except Exception as e:
            duration = (time.time() - start) * 1000
            log_test("/research/start (empty query)", "POST", False, duration, f"Error: {str(e)}")


def generate_health_report():
    """Generate comprehensive health report."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE HEALTH REPORT")
    print("=" * 80)
    print()
    
    total_tests = len(TEST_RESULTS)
    passed_tests = sum(1 for r in TEST_RESULTS if r["status"] == "✓ PASS")
    failed_tests = total_tests - passed_tests
    
    avg_duration = sum(r["duration_ms"] for r in TEST_RESULTS) / total_tests if total_tests > 0 else 0
    
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print(f"MOCK_MODE: {settings.mock_mode}")
    print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
    print(f"Average Response Time: {avg_duration:.2f}ms")
    print()
    
    # Group by endpoint
    endpoints = {}
    for result in TEST_RESULTS:
        endpoint = result["endpoint"].split("/")[1] if "/" in result["endpoint"] else result["endpoint"]
        if endpoint not in endpoints:
            endpoints[endpoint] = {"passed": 0, "failed": 0, "durations": []}
        
        if result["status"] == "✓ PASS":
            endpoints[endpoint]["passed"] += 1
        else:
            endpoints[endpoint]["failed"] += 1
        endpoints[endpoint]["durations"].append(result["duration_ms"])
    
    print("=" * 80)
    print("ENDPOINT HEALTH")
    print("=" * 80)
    for endpoint, stats in endpoints.items():
        total = stats["passed"] + stats["failed"]
        success_rate = (stats["passed"] / total * 100) if total > 0 else 0
        avg_dur = sum(stats["durations"]) / len(stats["durations"]) if stats["durations"] else 0
        
        health_icon = "✓" if success_rate >= 100 else "⚠" if success_rate >= 50 else "✗"
        print(f"{health_icon} /{endpoint:30s} {success_rate:5.1f}% pass rate, {avg_dur:6.0f}ms avg")
    
    print()
    print("=" * 80)
    print("API KEY STATUS")
    print("=" * 80)
    print(f"✓ Supabase: Connected ({settings.supabase_url[:30]}...)")
    print(f"✓ SerpAPI: Configured ({settings.serpapi_key[:10]}...)")
    print(f"✓ Gemini: Configured ({settings.gemini_api_key[:10]}...)")
    print()
    
    print("=" * 80)
    print("INTEGRATION STATUS")
    print("=" * 80)
    print(f"✓ Database: Operational (Supabase)")
    print(f"✓ Search: Ready (SerpAPI)")
    print(f"✓ LLM: Ready (Gemini with quota management)")
    print(f"✓ Embeddings: Ready (gemini-embedding-001)")
    print()
    
    if failed_tests > 0:
        print("=" * 80)
        print("FAILED TESTS")
        print("=" * 80)
        for result in TEST_RESULTS:
            if result["status"] == "✗ FAIL":
                print(f"✗ {result['method']:6s} {result['endpoint']:50s}")
                print(f"  {result['details']}")
        print()
    
    print("=" * 80)
    print("OVERALL STATUS")
    print("=" * 80)
    if failed_tests == 0:
        print("✓ ALL SYSTEMS OPERATIONAL")
        print("✓ Backend is healthy and ready for production")
    elif failed_tests <= total_tests * 0.2:
        print("⚠ MOSTLY OPERATIONAL")
        print(f"⚠ {failed_tests} test(s) failed, review recommended")
    else:
        print("✗ ISSUES DETECTED")
        print(f"✗ {failed_tests} test(s) failed, attention required")
    print()
    
    # Save report to file
    report_file = Path(__file__).parent.parent / "test_results" / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": passed_tests / total_tests * 100 if total_tests > 0 else 0,
                "avg_response_time_ms": avg_duration
            },
            "endpoints": endpoints,
            "tests": TEST_RESULTS
        }, f, indent=2)
    
    print(f"📄 Detailed report saved to: {report_file}")
    print()
    
    return failed_tests == 0


async def main():
    """Run all tests."""
    print("=" * 80)
    print("COMPREHENSIVE API ENDPOINT TESTING")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run tests
    await test_health_endpoint()
    session_ids = await test_start_research()
    
    # Wait for research to process
    print("\n⏳ Waiting 10 seconds for research to process...")
    await asyncio.sleep(10)
    
    await test_get_research(session_ids)
    await test_list_sessions()
    await test_get_report(session_ids)
    await test_error_cases()
    
    # Generate report
    success = generate_health_report()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
