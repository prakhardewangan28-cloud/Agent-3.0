"""Environment verification script."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 70)
print("ENVIRONMENT VERIFICATION")
print("=" * 70)
print()

# Step 1: Check Python version
print("Step 1: Checking Python version...")
print(f"  Python version: {sys.version}")
print(f"  Version info: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
if sys.version_info < (3, 11):
    print("  ⚠️  WARNING: Python 3.11+ recommended")
else:
    print("  ✅ Python version OK")
print()

# Step 2: Check if venv is active
print("Step 2: Checking virtual environment...")
in_venv = hasattr(sys, 'real_prefix') or (
    hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
)
if in_venv:
    print(f"  ✅ Virtual environment active: {sys.prefix}")
else:
    print("  ⚠️  WARNING: Virtual environment not active")
    print("     Run: venv\\Scripts\\activate")
print()

# Step 3: Test imports
print("Step 3: Testing module imports...")
errors = []

modules_to_test = [
    ("app.config", "Configuration"),
    ("app.main", "FastAPI application"),
    ("app.db.supabase_client", "Database client"),
    ("app.services.serpapi_service", "SerpAPI service"),
    ("app.services.credibility_service", "Credibility service"),
    ("app.services.claim_service", "Claim service"),
    ("app.services.conflict_service", "Conflict service"),
    ("app.services.refinement_service", "Refinement service"),
    ("app.agents.research_agent", "Research agent"),
    ("app.api.routes", "API routes"),
    ("app.models.schemas", "Data models"),
]

for module_name, description in modules_to_test:
    try:
        __import__(module_name)
        print(f"  ✅ {description:30s} ({module_name})")
    except ImportError as e:
        print(f"  ❌ {description:30s} ({module_name})")
        print(f"     Error: {e}")
        errors.append((module_name, str(e)))
    except Exception as e:
        print(f"  ⚠️  {description:30s} ({module_name})")
        print(f"     Warning: {e}")

print()

# Step 4: Check .env file
print("Step 4: Checking environment variables...")
# Get the backend directory (parent of scripts directory)
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_file = os.path.join(backend_dir, ".env")
print(f"  Looking for: {env_file}")

if not os.path.exists(env_file):
    print("  ❌ .env file not found")
    print("     Copy .env.example to .env and fill in your API keys")
    errors.append((".env", "File not found"))
else:
    print("  ✅ .env file found")
    
    # Read .env and check required keys
    required_keys = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "SERPAPI_KEY",
        "GEMINI_API_KEY",
    ]
    
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    print()
    print("  Required environment variables:")
    for key in required_keys:
        if key in env_vars and env_vars[key] and env_vars[key] != f"your-{key.lower().replace('_', '-')}":
            # Mask the value
            value = env_vars[key]
            if len(value) > 20:
                masked = value[:10] + "..." + value[-5:]
            else:
                masked = value[:5] + "..." if len(value) > 5 else "***"
            print(f"    ✅ {key:20s} = {masked}")
        else:
            print(f"    ❌ {key:20s} = <not set or placeholder>")
            errors.append((key, "Not set or using placeholder value"))

print()

# Summary
print("=" * 70)
if errors:
    print(f"VERIFICATION FAILED - {len(errors)} issues found:")
    print()
    for item, error in errors:
        print(f"  ❌ {item}: {error}")
    print()
    print("Please fix the issues above before running the application.")
    sys.exit(1)
else:
    print("✅ ALL CHECKS PASSED")
    print()
    print("Your environment is properly configured!")
    print()
    print("Next steps:")
    print("  1. Run database migration in Supabase (migrations/001_initial.sql)")
    print("  2. Test database: python scripts\\check_db.py")
    print("  3. Test SerpAPI: python scripts\\check_serpapi.py")
    print("  4. Test Gemini: python scripts\\check_gemini.py")
    print("  5. Run all tests: run_tests.bat")
    sys.exit(0)
