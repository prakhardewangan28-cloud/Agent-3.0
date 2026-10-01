import asyncio
import sys
sys.path.append(".")

from app.db.neon_client import (
    create_session, get_session, 
    insert_sources, get_sources_by_session
)

async def main():
    print("Creating session...")
    session = await create_session("test query from live script")
    print(f"✅ Session created: {session['id']}")
    
    print("Inserting source...")
    sources = await insert_sources(session["id"], [{
        "url": "https://example.com/test",
        "title": "Test Source",
        "snippet": "This is a test snippet for the database round-trip.",
        "domain": "example.com",
        "engine": "google",
        "credibility_score": 75.0,
    }])
    print(f"✅ Inserted {len(sources)} source(s)")
    
    print("Fetching sources back...")
    fetched = await get_sources_by_session(session["id"])
    print(f"✅ Fetched {len(fetched)} source(s)")
    if fetched:
        print(f"   Title: {fetched[0]['title']}")
        print(f"   Domain: {fetched[0]['domain']}")
    print("\n🎉 DATABASE ROUND-TRIP WORKS")

asyncio.run(main())