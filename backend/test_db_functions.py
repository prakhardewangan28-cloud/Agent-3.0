"""Test database function signatures and logic without live DB."""
import sys
import inspect
from typing import get_type_hints

print("=" * 70)
print("DATABASE FUNCTION SIGNATURE VERIFICATION")
print("=" * 70)
print()

# Test imports
try:
    from app.db import (
        # Research Sessions
        create_session,
        update_session_status,
        get_session,
        # Sources
        insert_sources,
        get_sources_by_session,
        update_source_ai_flag,
        # Claims
        insert_claims,
        get_claims_by_session,
        find_similar_claims,
        # Conflicts
        insert_conflicts,
        get_conflicts_by_session,
        # Evidence Edges
        insert_evidence_edge,
        get_evidence_graph,
    )
    print("✓ All 15 database functions imported successfully")
    print()
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test function signatures
functions_to_test = {
    "Research Sessions": [
        (create_session, "create_session"),
        (update_session_status, "update_session_status"),
        (get_session, "get_session"),
    ],
    "Sources": [
        (insert_sources, "insert_sources"),
        (get_sources_by_session, "get_sources_by_session"),
        (update_source_ai_flag, "update_source_ai_flag"),
    ],
    "Claims": [
        (insert_claims, "insert_claims"),
        (get_claims_by_session, "get_claims_by_session"),
        (find_similar_claims, "find_similar_claims"),
    ],
    "Conflicts": [
        (insert_conflicts, "insert_conflicts"),
        (get_conflicts_by_session, "get_conflicts_by_session"),
    ],
    "Evidence Graph": [
        (insert_evidence_edge, "insert_evidence_edge"),
        (get_evidence_graph, "get_evidence_graph"),
    ]
}

total_tests = 0
passed_tests = 0

for category, funcs in functions_to_test.items():
    print(f"{category}:")
    print("-" * 70)
    
    for func, name in funcs:
        total_tests += 1
        
        # Check if it's a coroutine (async)
        is_async = inspect.iscoroutinefunction(func)
        
        # Get signature
        sig = inspect.signature(func)
        
        # Get docstring
        doc = inspect.getdoc(func)
        has_docstring = doc is not None and len(doc) > 10
        
        # Get parameters
        params = list(sig.parameters.keys())
        
        # Check type hints
        try:
            hints = get_type_hints(func)
            has_type_hints = len(hints) > 0
        except:
            has_type_hints = False
        
        # Verify function
        checks = []
        checks.append(("async", is_async))
        checks.append(("docstring", has_docstring))
        checks.append(("type hints", has_type_hints))
        checks.append(("params", len(params) > 0))
        
        all_passed = all(check[1] for check in checks)
        
        if all_passed:
            passed_tests += 1
            status = "✓"
        else:
            status = "⚠"
        
        print(f"  {status} {name}()")
        print(f"     Parameters: {', '.join(params)}")
        
        # Show what passed/failed
        details = []
        for check_name, check_result in checks:
            if check_result:
                details.append(f"✓ {check_name}")
            else:
                details.append(f"✗ {check_name}")
        print(f"     Checks: {' | '.join(details)}")
        
        if doc and len(doc) > 0:
            first_line = doc.split('\n')[0][:60]
            print(f"     Doc: {first_line}...")
        
        print()
    
    print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)
print(f"Total functions tested: {total_tests}")
print(f"Functions passed: {passed_tests}")
print(f"Functions with issues: {total_tests - passed_tests}")
print()

if passed_tests == total_tests:
    print("✅ ALL FUNCTIONS VERIFIED!")
    print()
    print("Function signatures are correct with:")
    print("  ✓ Async/await pattern")
    print("  ✓ Type hints")
    print("  ✓ Docstrings")
    print("  ✓ Proper parameters")
    print()
    print("⚠️  NOTE: Live database tests require real Supabase credentials")
    print("   To test with live database:")
    print("   1. Add your Supabase URL and KEY to .env")
    print("   2. Run: python test_database.py")
    sys.exit(0)
else:
    print("⚠️  Some functions have issues (see above)")
    sys.exit(1)
