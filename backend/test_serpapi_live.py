"""Live test of SerpAPI service (requires real API key)."""
import asyncio
import sys
import json

from app.services.serpapi_service import (
    search_web,
    search_news,
    search_scholar,
    SerpApiAuthError,
    SerpApiRateLimitError,
)
from app.config import settings


async def test_web_search():
    """Test Google web search."""
    print("=" * 70)
    print("TEST 1: Google Web Search")
    print("=" * 70)
    
    try:
        query = "artificial intelligence"
        print(f"Query: '{query}'")
        print(f"Requesting: 3 results\n")
        
        results = await search_web(query, num_results=3)
        
        print(f"✓ Found {len(results)} results\n")
        
        for i, result in enumerate(results, 1):
            print(f"Result {i}:")
            print(f"  Title: {result['title']}")
            print(f"  URL: {result['url']}")
            print(f"  Domain: {result['domain']}")
            print(f"  Snippet: {result['snippet'][:100]}...")
            print(f"  Engine: {result['engine']}")
            print()
        
        return True
    except SerpApiAuthError as e:
        print(f"❌ Authentication Error: {e}")
        print("   Please add a valid SERPAPI_KEY to your .env file")
        return False
    except SerpApiRateLimitError as e:
        print(f"❌ Rate Limit Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_news_search():
    """Test Google News search."""
    print("=" * 70)
    print("TEST 2: Google News Search")
    print("=" * 70)
    
    try:
        query = "climate change"
        print(f"Query: '{query}'")
        print(f"Requesting: 3 results (past week)\n")
        
        results = await search_news(query, num_results=3)
        
        print(f"✓ Found {len(results)} news articles\n")
        
        for i, result in enumerate(results, 1):
            print(f"Article {i}:")
            print(f"  Title: {result['title']}")
            print(f"  URL: {result['url']}")
            print(f"  Domain: {result['domain']}")
            print(f"  Published: {result.get('published_date', 'N/A')}")
            print(f"  Snippet: {result['snippet'][:100]}...")
            print()
        
        return True
    except SerpApiAuthError as e:
        print(f"❌ Authentication Error: {e}")
        return False
    except SerpApiRateLimitError as e:
        print(f"❌ Rate Limit Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_scholar_search():
    """Test Google Scholar search."""
    print("=" * 70)
    print("TEST 3: Google Scholar Search")
    print("=" * 70)
    
    try:
        query = "machine learning"
        print(f"Query: '{query}'")
        print(f"Requesting: 3 results\n")
        
        results = await search_scholar(query, num_results=3)
        
        print(f"✓ Found {len(results)} scholarly articles\n")
        
        for i, result in enumerate(results, 1):
            print(f"Paper {i}:")
            print(f"  Title: {result['title']}")
            print(f"  URL: {result['url']}")
            print(f"  Domain: {result['domain']}")
            if result.get('published_date'):
                print(f"  Publication: {result['published_date']}")
            print(f"  Snippet: {result['snippet'][:100]}...")
            print()
        
        return True
    except SerpApiAuthError as e:
        print(f"❌ Authentication Error: {e}")
        return False
    except SerpApiRateLimitError as e:
        print(f"❌ Rate Limit Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_combined_search():
    """Test combining all search types."""
    print("=" * 70)
    print("TEST 4: Combined Search (All Engines)")
    print("=" * 70)
    
    try:
        query = "quantum computing"
        print(f"Query: '{query}'")
        print(f"Requesting: 2 results from each engine\n")
        
        # Run all searches in parallel
        web_results, news_results, scholar_results = await asyncio.gather(
            search_web(query, num_results=2),
            search_news(query, num_results=2),
            search_scholar(query, num_results=2),
        )
        
        all_results = web_results + news_results + scholar_results
        
        print(f"✓ Total results: {len(all_results)}")
        print(f"  - Web: {len(web_results)}")
        print(f"  - News: {len(news_results)}")
        print(f"  - Scholar: {len(scholar_results)}")
        print()
        
        # Group by engine
        by_engine = {}
        for result in all_results:
            engine = result['engine']
            if engine not in by_engine:
                by_engine[engine] = []
            by_engine[engine].append(result)
        
        print("Results by engine:")
        for engine, results in by_engine.items():
            print(f"\n{engine.upper()}:")
            for result in results:
                print(f"  - {result['title'][:60]}...")
                print(f"    {result['domain']}")
        
        print()
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print()
    print("🔍 SERPAPI SERVICE LIVE TESTING")
    print()
    print(f"Configuration:")
    print(f"  SerpAPI Key: {settings.serpapi_key[:20]}...")
    print(f"  Max Results: {settings.max_search_results}")
    print()
    
    results = []
    
    # Test 1: Web Search
    results.append(await test_web_search())
    await asyncio.sleep(1)  # Rate limiting
    
    # Test 2: News Search
    results.append(await test_news_search())
    await asyncio.sleep(1)
    
    # Test 3: Scholar Search
    results.append(await test_scholar_search())
    await asyncio.sleep(1)
    
    # Test 4: Combined Search
    results.append(await test_combined_search())
    
    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    print()
    
    if passed == total:
        print("✅ ALL TESTS PASSED!")
        print()
        print("The SerpAPI service is working correctly.")
        print("You can now use it in your application:")
        print()
        print("  from app.services import search_web, search_news, search_scholar")
        print()
        print("  results = await search_web('your query', num_results=10)")
        print()
    else:
        print("⚠️  Some tests failed.")
        print()
        if settings.serpapi_key == "placeholder-serpapi-key":
            print("📝 NOTE: You need to add a real SerpAPI key to .env")
            print("   Get one at: https://serpapi.com/")
        print()
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
