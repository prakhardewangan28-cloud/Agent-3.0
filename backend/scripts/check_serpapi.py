"""SerpAPI service verification script."""
import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 70)
print("SERPAPI SERVICE TEST")
print("=" * 70)
print()

try:
    from app.services import (
        search_web,
        search_news,
        search_scholar,
        SerpApiAuthError,
        SerpApiRateLimitError,
    )
    from app.config import settings
    
    print("✅ SerpAPI modules imported successfully")
    print(f"   API Key: {settings.serpapi_key[:15]}...")
    print()
    
except ImportError as e:
    print(f"❌ Failed to import SerpAPI modules: {e}")
    print()
    print("Make sure you have:")
    print("  1. Activated the virtual environment")
    print("  2. Installed all dependencies (run setup.bat)")
    print("  3. Set SERPAPI_KEY in .env")
    sys.exit(1)


async def test_search_engine(search_func, engine_name, query="test query", num_results=2):
    """Test a specific search engine."""
    print(f"Testing {engine_name}...")
    try:
        results = await search_func(query, num_results=num_results)
        
        if results:
            print(f"  ✅ {engine_name} search successful")
            print(f"     Results: {len(results)}")
            if results:
                print(f"     First title: {results[0]['title'][:60]}...")
                print(f"     First URL: {results[0]['url'][:60]}...")
        else:
            print(f"  ⚠️  {engine_name} returned no results")
            print(f"     Query: {query}")
        
        return True, len(results)
        
    except SerpApiAuthError as e:
        print(f"  ❌ Authentication Error: {e}")
        print(f"     Your SERPAPI_KEY is invalid or not set")
        print(f"     Get a key at: https://serpapi.com/")
        return False, 0
        
    except SerpApiRateLimitError as e:
        print(f"  ❌ Rate Limit Error: {e}")
        print(f"     Wait a moment and try again")
        return False, 0
        
    except Exception as e:
        print(f"  ❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False, 0


async def test_serpapi():
    """Test all SerpAPI search engines."""
    all_success = True
    total_results = 0
    
    # Test Google Web Search
    success, count = await test_search_engine(search_web, "Google Web", "artificial intelligence", 2)
    all_success = all_success and success
    total_results += count
    print()
    
    # Wait between requests
    if success:
        await asyncio.sleep(1)
    
    # Test Google News Search
    success, count = await test_search_engine(search_news, "Google News", "technology", 2)
    all_success = all_success and success
    total_results += count
    print()
    
    # Wait between requests
    if success:
        await asyncio.sleep(1)
    
    # Test Google Scholar Search
    success, count = await test_search_engine(search_scholar, "Google Scholar", "machine learning", 2)
    all_success = all_success and success
    total_results += count
    print()
    
    # Summary
    print("=" * 70)
    if all_success:
        print("✅ SERPAPI TEST PASSED")
        print("=" * 70)
        print()
        print(f"All search engines working correctly!")
        print(f"Total results retrieved: {total_results}")
        print()
        print("Available functions:")
        print("  - search_web(query, num_results)")
        print("  - search_news(query, num_results)")
        print("  - search_scholar(query, num_results)")
        print()
    else:
        print("❌ SERPAPI TEST FAILED")
        print("=" * 70)
        print()
        print("Some search engines failed. Check errors above.")
        print()
        print("Common issues:")
        print("  1. Invalid or missing SERPAPI_KEY in .env")
        print("  2. Rate limit exceeded (free tier: 100/month)")
        print("  3. Network connectivity issues")
        print()
        print("Get a free API key at: https://serpapi.com/")
        print()
    
    return all_success


if __name__ == "__main__":
    success = asyncio.run(test_serpapi())
    sys.exit(0 if success else 1)
