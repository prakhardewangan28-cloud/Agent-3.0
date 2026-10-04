"""
Run all database migrations on Neon Postgres
"""
import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


async def run_migrations():
    """Apply all migration files to the Neon database"""
    print("=" * 80)
    print("NEON DATABASE MIGRATION RUNNER")
    print("=" * 80)
    print(f"Database: {settings.database_url.split('@')[1].split('/')[0]}")
    print()
    
    # Get migration files in order
    migrations_dir = Path(__file__).parent.parent / "migrations"
    
    # Use Neon-specific migrations (without Supabase auth/RLS)
    migration_files = [
        migrations_dir / "001_initial_neon.sql",
        migrations_dir / "002_add_session_columns.sql",
        migrations_dir / "003_add_missing_columns.sql",
        migrations_dir / "004_add_counter_argument.sql",
        migrations_dir / "005_fix_credibility_scale.sql",
        migrations_dir / "006_add_frontend_support.sql",
    ]
    
    # Filter to only existing files
    migration_files = [f for f in migration_files if f.exists()]
    
    if not migration_files:
        print("❌ No migration files found in migrations/")
        return False
    
    print(f"Found {len(migration_files)} migration file(s):")
    for mf in migration_files:
        print(f"  - {mf.name}")
    print()
    
    # Connect to database
    try:
        conn = await asyncpg.connect(settings.database_url)
        print("✓ Connected to database")
        print()
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return False
    
    try:
        # Run each migration
        for migration_file in migration_files:
            print(f"Running: {migration_file.name}")
            print("-" * 40)
            
            # Read migration SQL
            sql = migration_file.read_text(encoding='utf-8')
            
            # Execute the migration
            try:
                await conn.execute(sql)
                print(f"✓ {migration_file.name} applied successfully")
            except Exception as e:
                error_str = str(e)
                # Check if error is because object already exists
                if "already exists" in error_str or "duplicate" in error_str.lower():
                    print(f"⚠ {migration_file.name} - objects already exist (skipping)")
                else:
                    print(f"❌ Failed to apply {migration_file.name}")
                    print(f"Error: {e}")
                    return False
            
            print()
        
        # Verify tables exist
        print("Verifying tables...")
        print("-" * 40)
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        if tables:
            print(f"✓ Found {len(tables)} table(s):")
            for table in tables:
                print(f"  - {table['table_name']}")
        else:
            print("⚠ No tables found")
        
        print()
        print("=" * 80)
        print("✅ MIGRATIONS COMPLETED SUCCESSFULLY")
        print("=" * 80)
        return True
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ MIGRATION FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await conn.close()
        print("Connection closed")


if __name__ == "__main__":
    success = asyncio.run(run_migrations())
    sys.exit(0 if success else 1)
