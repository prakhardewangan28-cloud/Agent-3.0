"""Database connectivity verification script."""
import sys
import os
import asyncio
import traceback
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

# Check for mock mode
if settings.mock_mode:
    print("=" * 70)
    print("🧪 RUNNING IN MOCK MODE")
    print("=" * 70)
    print("Using in-memory mock database. No real Supabase connection.")
    print()

print("=" * 70)
print("DATABASE CONNECTIVITY TEST")
print("=" * 70)
print()

try:
    from app.db.supabase_client import (
        supabase,
        create_session,
        insert_sources,
        get_session
    )
    
    print("✅ Database modules imported successfully")
    if not settings.mock_mode:
        masked_key = settings.supabase_key[:12] + "..." if len(settings.supabase_key) > 12 else "***"
        print(f"   Supabase URL: {settings.supabase_url[:30]}...")
        print(f"   Supabase Key: {masked_key}")
    else:
        print("   Using MockSupabase - in-memory storage")
    print()
    
except ImportError as e:
    print(f"❌ Failed to import database modules: {e}")
    print()
    traceback.print_exc()
    print()
    sys.exit(1)


async def test_database():
    """Test database CRUD operations."""
    session_id = None
    source_id = None
    
    try:
        # Step 1: Create a test research session
        print("Step 1: Creating test research session...")
        session = await create_session(
            original_query="test query for verification",
            user_id="test_user"
        )
        session_id = session['id']
        print(f"  ✅ Session created successfully")
        print(f"     Session ID: {session_id}")
        print()
        
        # Step 2: Insert a test source
        print("Step 2: Inserting test source...")
        sources = await insert_sources(
            session_id=session_id,
            sources=[{
                "url": "https://example.com/test",
                "title": "Test Source",
                "snippet": "Test snippet for verification",
                "domain": "example.com",
                "source_type": "web",
                "credibility_score": 0.8
            }]
        )
        source_id = sources[0]['id']
        print(f"  ✅ Source inserted successfully")
        print(f"     Source ID: {source_id}")
        print(f"     URL: {sources[0]['url']}")
        print()
        
        # Step 3: Read back the session
        print("Step 3: Reading session back...")
        retrieved_session = await get_session(session_id)
        print(f"  ✅ Session retrieved successfully")
        print(f"     Original query: {retrieved_session['original_query']}")
        print(f"     Status: {retrieved_session['status']}")
        print()
        
        # Step 4: Delete the test session (skip in mock mode - no persistence anyway)
        if not settings.mock_mode:
            print("Step 4: Deleting test session...")
            supabase.table("research_sessions").delete().eq("id", session_id).execute()
            print(f"  ✅ Session deleted successfully")
            print()
        else:
            print("Step 4: Skipping cleanup (mock mode - data not persisted)")
            print()
        
        return True
        
    except Exception as e:
        print(f"  ❌ Operation failed: {e}")
        print()
        print("=" * 70)
        print("❌ DATABASE TEST FAILED")
        print("=" * 70)
        print(f"Error: {type(e).__name__}: {e}")
        print()
        if not settings.mock_mode:
            print("Full traceback:")
            traceback.print_exc()
            print()
            print("Common issues:")
            print("  1. Database migration not run in Supabase")
            print("  2. Invalid Supabase credentials in .env")
            print("  3. Network connectivity issues")
            print("  4. Row Level Security policies blocking operations")
            print()
        return False


def main():
    """Run database tests."""
    try:
        success = asyncio.run(test_database())
        
        if success:
            print("=" * 70)
            print("✅ DATABASE TEST PASSED")
            print("=" * 70)
            print()
            if settings.mock_mode:
                print("🧪 Mock mode verification complete!")
                print("Function signatures work correctly.")
            else:
                print("Database is working correctly!")
            print()
            print("Verified operations:")
            print("  - Create session")
            print("  - Insert source")
            print("  - Read session")
            if not settings.mock_mode:
                print("  - Delete session")
            print()
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        if not settings.mock_mode:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
