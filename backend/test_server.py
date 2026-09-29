"""Quick test script to verify the server is working."""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Test the health endpoint."""
    response = requests.get(f"{BASE_URL}/health")
    print(f"✓ Health Check: {response.status_code}")
    print(f"  Response: {response.json()}")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_research_endpoint():
    """Test the research endpoint."""
    payload = {
        "query": "What is artificial intelligence?",
        "max_results": 5
    }
    response = requests.post(f"{BASE_URL}/api/v1/research", json=payload)
    print(f"\n✓ Research Endpoint: {response.status_code}")
    print(f"  Response: {json.dumps(response.json(), indent=2)}")
    assert response.status_code == 200

def test_docs():
    """Test that API docs are available."""
    response = requests.get(f"{BASE_URL}/docs")
    print(f"\n✓ API Docs Available: {response.status_code}")
    assert response.status_code == 200

if __name__ == "__main__":
    try:
        print("Testing Backend API...\n")
        print("=" * 50)
        
        test_health()
        test_research_endpoint()
        test_docs()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print(f"\n🌐 Server is running at: {BASE_URL}")
        print(f"📚 API Documentation: {BASE_URL}/docs")
        print(f"📖 Alternative Docs: {BASE_URL}/redoc")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Could not connect to server at {BASE_URL}")
        print("   Make sure the server is running with: python -m uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
