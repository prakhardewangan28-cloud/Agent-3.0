"""
Test Neon database connectivity.

Tests:
- Connection to Neon
- Create a research session
- Read it back
- Delete it
- Report success/failure
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.neon_client import (
    get_pool,
    close_pool,
    create_session,
    get_session
)
from app.config import settings


async def main():
    """Test Neon database connectivity."""
    print("=" * 80)
    print("NEON DATABASE CONNECTIVITY CHECK")
    print("=" * 80)
    print()
    print(f"MOCK_MODE: {settings.mock_mode}")
    
    if not settings.mock_mode:
        db_url = settings.database_url
        # Mask password
        if '@' in db_url:
            parts = db_url.split('@')
            userpass = parts[0].split('://')[-1]
            if ':' in userpass:
                user = userpass.split(':')[0]
                masked = f"postgresql://{user}:****@{parts[1]}"
            else:
                masked = db_url
        else:
            masked = db_url
        print(f"Database URL: {masked}")
    print()
    
    try:
        # Test 1: Basic connection
        print("TEST 1: Basic Connection")
        print("-" * 40)
        
        if settings.mock_mode:
            print("✓ Mock mode - no real connection")
        else:
            pool = await get_pool()
            async with pool.acquire() as conn:
                result = await conn.fetchval("SELECT 1")
                print(f"✓ Connection successful (SELECT 1 = {result})")
        print()
        
        # Test 2: Create session
        print("TEST 2: Create Session")
        print("-" * 40)
        
        session = await create_session(
            original_query="Test query from check_db.py"
        )
        session_id = session["id"]
        print(f"✓ Created session: {session_id}")
        print(f"  Query: {session['original_query']}")
        print(f"  Status: {session['status']}")
        print()
        
        # Test 3: Read session back
        print("TEST 3: Read Session")
        print("-" * 40)
        
        retrieved = await get_session(session_id)
        if retrieved:
            print(f"✓ Retrieved session: {session_id}")
            print(f"  Query: {retrieved['original_query']}")
            print(f"  Status: {retrieved['status']}")
        else:
            print(f"✗ Failed to retrieve session: {session_id}")
            return 1
        print()
        
        # Test 4: Delete session (cleanup)
        print("TEST 4: Cleanup")
        print("-" * 40)
        
        if settings.mock_mode:
            from app.db.neon_client import get_mock
            mock = get_mock()
            if session_id in mock.sessions:
                del mock.sessions[session_id]
            print(f"✓ Deleted session from mock: {session_id}")
        else:
            pool = await get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "DELETE FROM research_sessions WHERE id = $1",
                    session_id
                )
            print(f"✓ Deleted session: {session_id}")
        print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print("✅ All tests PASSED")
        print("✅ Neon database is operational")
        print()
        
        return 0
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        # Close pool
        if not settings.mock_mode:
            await close_pool()
            print("Connection pool closed")


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
