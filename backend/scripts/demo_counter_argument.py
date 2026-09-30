"""Demo script to test the counter-argument feature in the research pipeline.

Run with MOCK_MODE=true to test without API calls.
"""
import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.agents.research_agent import run_research
from app.config import settings


async def main():
    """Run a research query and display the counter-argument."""
    print("=" * 80)
    print("COUNTER-ARGUMENT DEMO")
    print("=" * 80)
    print(f"MOCK_MODE: {settings.mock_mode}")
    print()
    
    # Use a specific query to avoid refinement
    query = "What are the primary causes and effects of climate change?"
    print(f"QUERY: {query}")
    print()
    print("Running research pipeline...")
    print()
    
    # Run the research
    result = await run_research(query)
    
    # Display results
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print()
    
    print(f"Status: {result.get('status')}")
    print(f"Sources: {len(result.get('sources', []))}")
    print(f"Stored Sources: {len(result.get('stored_sources', []))}")
    print(f"Claims: {len(result.get('claims', []))}")
    print(f"Conflicts: {len(result.get('conflicts', []))}")
    print()
    
    # Display landscape
    landscape = result.get("landscape", {})
    print("INFORMATION LANDSCAPE:")
    print(f"  Consensus: {len(landscape.get('consensus', []))} claims")
    print(f"  Contested: {len(landscape.get('contested', []))} claims")
    print(f"  Unknowns: {len(landscape.get('unknowns', []))} gaps")
    print()
    
    # Display final report (truncated)
    final_report = result.get("final_report", "")
    if final_report:
        print("FINAL REPORT (first 500 chars):")
        print("-" * 80)
        print(final_report[:500])
        if len(final_report) > 500:
            print("...")
        print("-" * 80)
        print()
    
    # Display counter-argument
    counter = result.get("counter_argument")
    if counter:
        print("=" * 80)
        print("COUNTER-ARGUMENT")
        print("=" * 80)
        print()
        print(f"Strength: {counter.get('strength', 'N/A')}")
        print()
        print("Argument:")
        print(counter.get("counter_argument", "N/A"))
        print()
        print(f"Supporting Sources: {len(counter.get('supporting_sources', []))}")
        for i, source in enumerate(counter.get("supporting_sources", []), 1):
            print(f"  [{i}] {source.get('domain')} (credibility: {source.get('credibility_score'):.1f})")
            print(f"      {source.get('url')}")
        print()
        print("Explanation:")
        print(counter.get("explanation", "N/A"))
        print()
    else:
        print("No counter-argument generated.")
    
    # Display node timings
    timings = result.get("node_timings", {})
    if timings:
        print("=" * 80)
        print("NODE TIMINGS (ms)")
        print("=" * 80)
        for node, duration in timings.items():
            print(f"  {node:20s}: {duration:7.1f} ms")
        print()


if __name__ == "__main__":
    asyncio.run(main())
