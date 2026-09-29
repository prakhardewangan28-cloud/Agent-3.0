# SerpAPI Service Guide

## Overview

The SerpAPI service provides a clean, async interface to search Google (web, news, and scholar) using the SerpAPI SDK. All results are normalized into a consistent format for easy database insertion.

## Features

- ✅ **Three search engines**: Google Web, Google News, Google Scholar
- ✅ **Async/await**: Non-blocking API with asyncio.to_thread wrapper
- ✅ **Error handling**: Automatic retry on rate limits, clear error types
- ✅ **Normalized results**: Consistent dict format across all engines
- ✅ **Logging**: Detailed logging with timing and result counts
- ✅ **Type hints**: Full type annotations
- ✅ **Tested**: 26 passing unit tests

## Installation

The google-search-results package is already included in `requirements.txt`:

```bash
pip install google-search-results
```

## Configuration

Add your SerpAPI key to `.env`:

```env
SERPAPI_KEY=your-serpapi-key-here
MAX_SEARCH_RESULTS=10
```

Get a free API key at: https://serpapi.com/

## API Reference

### search_web()

Search Google web results.

```python
from app.services import search_web

results = await search_web(
    query="artificial intelligence",
    num_results=10  # Optional, defaults to settings.MAX_SEARCH_RESULTS
)
```

**Returns**: List of dicts with keys:
- `url` (str): Full URL
- `title` (str): Page title
- `snippet` (str): Preview text
- `domain` (str): Domain without www.
- `engine` (str): Always "google"
- `published_date` (None): Not available for web results

**Raises**:
- `SerpApiAuthError`: Invalid API key
- `SerpApiRateLimitError`: Rate limit exceeded after retries

---

### search_news()

Search Google News (restricted to past week).

```python
from app.services import search_news

results = await search_news(
    query="climate change",
    num_results=10
)
```

**Returns**: List of dicts with same structure as `search_web`, plus:
- `published_date` (str|None): Human-readable date like "2 hours ago"

**Note**: Results are automatically filtered to the past week using `tbs="qdr:w"`

---

### search_scholar()

Search Google Scholar for academic papers.

```python
from app.services import search_scholar

results = await search_scholar(
    query="machine learning",
    num_results=10
)
```

**Returns**: List of dicts with same structure, plus:
- `published_date` (str|None): Publication info like "Nature, 2023"

**Note**: Snippets may come from `publication_info.summary` if not directly available

---

## Result Format

All three functions return lists of dicts with this structure:

```python
{
    "url": "https://example.com/article",
    "title": "Article Title",
    "snippet": "Preview text from the article...",
    "domain": "example.com",
    "engine": "google",  # or "news" or "scholar"
    "published_date": "2 hours ago"  # or None
}
```

This format is ready to insert into the Supabase `sources` table:

```python
from app.db import insert_sources

# Search
results = await search_web("AI")

# Insert into database
sources = await insert_sources(session_id, results)
```

---

## Error Handling

### SerpApiAuthError

Raised when the API key is invalid.

```python
from app.services import search_web, SerpApiAuthError

try:
    results = await search_web("test")
except SerpApiAuthError as e:
    print(f"Invalid API key: {e}")
    # Update your .env file with a valid key
```

### SerpApiRateLimitError

Raised when rate limit is exceeded after 3 retries.

```python
from app.services import search_web, SerpApiRateLimitError

try:
    results = await search_web("test")
except SerpApiRateLimitError as e:
    print(f"Rate limit hit: {e}")
    # Wait before retrying or upgrade your SerpAPI plan
```

### Automatic Retry

Rate limit errors trigger automatic retry with exponential backoff:
1. First retry: 2 seconds
2. Second retry: 4 seconds
3. Third retry: 8 seconds
4. After 3 failures: Raise SerpApiRateLimitError

---

## Usage Examples

### Example 1: Simple Web Search

```python
import asyncio
from app.services import search_web

async def main():
    results = await search_web("Python programming", num_results=5)
    
    for result in results:
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        print(f"Domain: {result['domain']}")
        print()

asyncio.run(main())
```

### Example 2: Combined Search (All Engines)

```python
import asyncio
from app.services import search_web, search_news, search_scholar

async def comprehensive_search(query: str):
    # Run all searches in parallel
    web, news, scholar = await asyncio.gather(
        search_web(query, num_results=5),
        search_news(query, num_results=5),
        search_scholar(query, num_results=5),
    )
    
    return {
        "web": web,
        "news": news,
        "scholar": scholar,
        "total": len(web) + len(news) + len(scholar)
    }

results = asyncio.run(comprehensive_search("quantum computing"))
print(f"Found {results['total']} total results")
```

### Example 3: With Database Integration

```python
from app.services import search_web, search_news
from app.db import create_session, insert_sources

async def research_workflow(query: str):
    # Create research session
    session = await create_session(query)
    session_id = session["id"]
    
    # Search multiple sources
    web_results = await search_web(query, num_results=10)
    news_results = await search_news(query, num_results=5)
    
    # Combine results
    all_sources = web_results + news_results
    
    # Insert into database
    saved_sources = await insert_sources(session_id, all_sources)
    
    print(f"Saved {len(saved_sources)} sources to database")
    return session_id
```

### Example 4: Error Handling

```python
from app.services import search_web, SerpApiAuthError, SerpApiRateLimitError
import asyncio

async def safe_search(query: str):
    try:
        results = await search_web(query)
        return results
    
    except SerpApiAuthError:
        print("ERROR: Invalid SerpAPI key")
        print("Get a key at: https://serpapi.com/")
        return []
    
    except SerpApiRateLimitError:
        print("ERROR: Rate limit exceeded")
        print("Waiting 60 seconds before retry...")
        await asyncio.sleep(60)
        return await search_web(query)  # Retry once
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []
```

---

## Helper Functions

### extract_domain()

Extract clean domain from URL.

```python
from app.services.serpapi_service import extract_domain

domain = extract_domain("https://www.example.com/path")
# Returns: "example.com"
```

### normalize_result()

Convert raw SerpAPI result to normalized format.

```python
from app.services.serpapi_service import normalize_result

raw = {
    "link": "https://example.com",
    "title": "Example",
    "snippet": "Description"
}

normalized = normalize_result(raw, engine="google")
# Returns: {url, title, snippet, domain, engine, published_date}
```

---

## Performance

### Timing

All search functions log execution time:

```
INFO: Google web search complete: query='AI', results=10, duration=342.15ms
```

### Parallel Searches

Use `asyncio.gather()` for parallel searches:

```python
# Sequential (slow)
web = await search_web("AI")
news = await search_news("AI")
scholar = await search_scholar("AI")
# Total time: ~1200ms

# Parallel (fast)
web, news, scholar = await asyncio.gather(
    search_web("AI"),
    search_news("AI"),
    search_scholar("AI"),
)
# Total time: ~400ms
```

---

## Testing

### Run Unit Tests

```bash
pytest tests/test_serpapi_service.py -v
```

**Output**:
```
26 passed in 0.14s
```

### Run Live Tests

Requires real SerpAPI key:

```bash
python test_serpapi_live.py
```

Tests:
1. ✓ Google web search
2. ✓ Google news search
3. ✓ Google scholar search
4. ✓ Combined parallel search

---

## Logging

The service logs every search with details:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

results = await search_web("test")
```

**Log output**:
```
INFO: Starting Google web search: query='test', num=10
INFO: Google web search complete: query='test', results=10, duration=342ms
```

**On errors**:
```
ERROR: SerpAPI authentication error: Invalid API key
WARNING: SerpAPI rate limit hit, retrying in 2s (attempt 1/3)
```

---

## Troubleshooting

### Issue: "Invalid API key"

**Solution**: Check your `.env` file:
```env
SERPAPI_KEY=your-actual-key-here
```

Get a key at: https://serpapi.com/

### Issue: "Rate limit exceeded"

**Solutions**:
1. Wait 60 seconds between requests
2. Use parallel searches (doesn't count as multiple requests)
3. Upgrade your SerpAPI plan

### Issue: Empty results

Check logs for warnings:
```
WARNING: No results found for query: 'obscure search term'
```

Try:
- More common search terms
- Different engines (web, news, scholar)
- Increase `num_results`

### Issue: Import errors

Make sure the service is imported correctly:

```python
# Correct
from app.services import search_web, search_news, search_scholar

# Incorrect (old way)
from app.services import SerpAPIService  # This no longer exists
```

---

## Migration from Old Code

If you have code using the old `SerpAPIService` class:

**Old code**:
```python
from app.services import SerpAPIService

service = SerpAPIService()
results = await service.search("query")
```

**New code**:
```python
from app.services import search_web

results = await search_web("query")
```

The new API is simpler and more direct!

---

## Rate Limits

SerpAPI free tier:
- 100 searches/month
- Rate limit: ~1 request/second

Pro tier:
- 5,000+ searches/month
- Higher rate limits

Check your usage at: https://serpapi.com/dashboard

---

## Database Integration

Results are designed to insert directly into Supabase:

```python
from app.services import search_web
from app.db import insert_sources

# 1. Search
results = await search_web("query", num_results=10)

# 2. Insert (results already in correct format!)
sources = await insert_sources(session_id, results)

# sources table will have:
# - url, title, snippet, domain, engine
# - credibility_score (add separately)
# - published_date (from news results)
```

---

## Best Practices

1. **Always handle errors**:
   ```python
   try:
       results = await search_web(query)
   except SerpApiAuthError:
       # Handle invalid key
   except SerpApiRateLimitError:
       # Handle rate limit
   ```

2. **Use parallel searches** when searching multiple engines:
   ```python
   results = await asyncio.gather(
       search_web(query),
       search_news(query),
   )
   ```

3. **Limit results** to what you need:
   ```python
   results = await search_web(query, num_results=5)
   # Don't request 100 if you only need 5
   ```

4. **Check for empty results**:
   ```python
   results = await search_web(query)
   if not results:
       logger.warning(f"No results for: {query}")
   ```

5. **Log searches** for debugging:
   ```python
   logger.info(f"Searching: {query}")
   results = await search_web(query)
   logger.info(f"Found: {len(results)} results")
   ```

---

## Next Steps

1. ✅ SerpAPI service is complete
2. ⚠️ Implement credibility scoring for sources
3. ⚠️ Implement claim extraction from sources
4. ⚠️ Build LangGraph workflow that uses search

See the database guide for inserting search results into Supabase.

---

## Resources

- [SerpAPI Documentation](https://serpapi.com/docs)
- [SerpAPI Python SDK](https://github.com/serpapi/google-search-results-python)
- [Get API Key](https://serpapi.com/)
- [Pricing Plans](https://serpapi.com/pricing)
