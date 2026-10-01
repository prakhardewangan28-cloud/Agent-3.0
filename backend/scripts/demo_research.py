"""
Demo script to run a full research query and display structured results.
Tests the complete pipeline: search → score → extract → conflict → landscape → report.
"""
import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.agents.research_agent import run_research
from app.db.neon_client import (
    get_sources_by_session,
    get_claims_by_session,
    get_conflicts_by_session,
)


def mask_url(url: str) -> str:
    """Mask password in database URL for safe display."""
    if not url or "://" not in url:
        return url
    
    # postgresql://user:password@host/db
    parts = url.split("://")
    if len(parts) != 2:
        return url
    
    protocol = parts[0]
    rest = parts[1]
    
    # Split by @ to separate credentials from host
    if "@" in rest:
        credentials, host_db = rest.split("@", 1)
        # Split credentials by :
        if ":" in credentials:
            user, _ = credentials.split(":", 1)
            return f"{protocol}://{user}:****@{host_db}"
    
    return url


async def main():
    """Run demo research query and display results."""
    print("=" * 80)
    print("KNOWLEDGE INTELLIGENCE AGENT - DEMO RESEARCH")
    print("=" * 80)
    print()
    
    # Print configuration
    print("CONFIGURATION:")
    print(f"  MOCK_MODE: {settings.mock_mode}")
    print(f"  DATABASE_URL: {mask_url(settings.database_url)}")
    print()
    
    # Research query
    query = "What are the documented health benefits of eating apples daily?"
    print(f"RESEARCH QUERY:")
    print(f"  {query}")
    print()
    
    # Track mock fallbacks
    mock_fallbacks = []
    
    # Run research
    print("EXECUTING RESEARCH...")
    print("-" * 80)
    start_time = time.time()
    
    try:
        result = await run_research(query)
        elapsed_time = time.time() - start_time
        
        print()
        print("=" * 80)
        print("RESEARCH RESULTS")
        print("=" * 80)
        print()
        
        # Status
        status = result.get("status", "unknown")
        print(f"STATUS: {status.upper()}")
        print(f"TOTAL TIME: {elapsed_time:.2f} seconds")
        print()
        
        if status == "failed":
            print("❌ Research failed")
            print(f"Error: {result.get('error', 'Unknown error')}")
            return 1
        
        session_id = result.get("session_id")
        if not session_id:
            print("❌ No session ID returned")
            return 1
        
        print(f"SESSION ID: {session_id}")
        print()
        
        # Fetch detailed data
        sources = await get_sources_by_session(session_id)
        claims = await get_claims_by_session(session_id)
        conflicts = await get_conflicts_by_session(session_id)
        
        # Sources
        print("SOURCES:")
        print(f"  Total: {len(sources)}")
        if sources:
            print("  Top 3 by credibility:")
            sorted_sources = sorted(sources, key=lambda s: s.get("credibility_score", 0), reverse=True)
            for i, source in enumerate(sorted_sources[:3], 1):
                domain = source.get("domain", "unknown")
                score = source.get("credibility_score", 0)
                title = source.get("title", "No title")[:60]
                print(f"    {i}. [{domain}] {score:.1f}/100 - {title}...")
        print()
        
        # Claims
        print("CLAIMS:")
        print(f"  Total: {len(claims)}")
        if claims:
            print("  First 3 claim texts:")
            for i, claim in enumerate(claims[:3], 1):
                text = claim.get("claim_text", "")[:80]
                print(f"    {i}. {text}...")
        print()
        
        # Conflicts
        print("CONFLICTS:")
        print(f"  Total: {len(conflicts)}")
        if conflicts:
            print("  First 2 conflict explanations:")
            for i, conflict in enumerate(conflicts[:2], 1):
                conflict_type = conflict.get("conflict_type", "unknown")
                explanation = conflict.get("explanation", "")[:100]
                print(f"    {i}. [{conflict_type}] {explanation}...")
        print()
        
        # Landscape
        landscape = result.get("landscape", {})
        if landscape:
            summary = landscape.get("summary", {})
            print("INFORMATION LANDSCAPE:")
            print(f"  Consensus claims: {summary.get('consensus_count', 0)}")
            print(f"  Contested claims: {summary.get('contested_count', 0)}")
            print(f"  Unknown claims: {summary.get('unknown_count', 0)}")
            print()
        
        # Counter-argument
        counter = result.get("counter_argument")
        if counter:
            strength = counter.get("strength", "unknown")
            argument = counter.get("argument", "")[:200]
            print("COUNTER-ARGUMENT:")
            print(f"  Strength: {strength}")
            print(f"  Preview: {argument}...")
            print()
        
        # Final report
        final_report = result.get("final_report")
        if final_report:
            print("FINAL REPORT:")
            print(f"  Length: {len(final_report)} characters")
            print(f"  Preview: {final_report[:150]}...")
            print()
            
            # Save report to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = Path(__file__).parent / f"demo_report_{timestamp}.md"
            report_file.write_text(final_report, encoding="utf-8")
            print(f"✅ Report saved to: {report_file}")
            print()
        
        # Check for mock fallbacks
        print("MOCK FALLBACKS:")
        if not sources and not claims:
            print("  ⚠ No sources or claims found (possible mock fallback)")
            mock_fallbacks.append("No data retrieved")
        elif settings.mock_mode:
            print("  ⚠ MOCK_MODE is enabled - using mock data")
            mock_fallbacks.append("Mock mode enabled")
        else:
            print("  ✅ No mock fallbacks detected")
        print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ Status: {status}")
        print(f"✅ Time: {elapsed_time:.2f}s")
        print(f"✅ Sources: {len(sources)}")
        print(f"✅ Claims: {len(claims)}")
        print(f"✅ Conflicts: {len(conflicts)}")
        print(f"✅ Report: {'Generated' if final_report else 'None'}")
        
        if mock_fallbacks:
            print()
            print("⚠ WARNINGS:")
            for fallback in mock_fallbacks:
                print(f"  - {fallback}")
        
        print()
        print("=" * 80)
        print("✅ DEMO COMPLETE")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        elapsed_time = time.time() - start_time
        print()
        print("=" * 80)
        print("❌ RESEARCH FAILED")
        print("=" * 80)
        print(f"Time elapsed: {elapsed_time:.2f}s")
        print(f"Error: {str(e)}")
        print()
        
        import traceback
        print("Traceback:")
        traceback.print_exc()
        print()
        
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
