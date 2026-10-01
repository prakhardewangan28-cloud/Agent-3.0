"""
Diagnostic script to test credibility scoring for sciencedirect.com and link.springer.com.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.credibility_service import score_source


def main():
    """Test credibility scoring with real demo sources."""
    
    # Create test sources matching what SerpAPI returns
    test_sources = [
        {
            "url": "https://www.sciencedirect.com/science/article/pii/S0963996911004309",
            "title": "A comprehensive review of apples and apple components and their relationship to human health",
            "snippet": "This review examines the health effects of apple consumption including cardiovascular benefits, cancer prevention, and antioxidant properties.",
            "domain": "sciencedirect.com",
            "engine": "google"
        },
        {
            "url": "https://link.springer.com/article/10.1007/s00394-016-1261-7",
            "title": "Intake of whole apples or clear apple juice has contrasting effects on plasma lipids",
            "snippet": "Research comparing whole apple consumption versus apple juice on cardiovascular health markers.",
            "domain": "link.springer.com",
            "engine": "google"
        }
    ]
    
    print("=" * 80)
    print("CREDIBILITY SCORING DIAGNOSTIC - SCIENCE PUBLISHERS")
    print("=" * 80)
    print()
    
    for source in test_sources:
        print("-" * 80)
        print(f"Source: {source['domain']}")
        print(f"URL:    {source['url']}")
        print(f"Title:  {source['title'][:60]}...")
        print()
        
        # Score the source
        scored = score_source(source)
        score = scored["credibility_score"]
        breakdown = scored["score_breakdown"]
        
        print(f"Final Score: {score}/100")
        print()
        print("Breakdown:")
        for rule, points in breakdown.items():
            if rule != "total":
                print(f"  {rule:30s} {points:+6.1f}")
        print()
        
        # Check if score is acceptable
        if score >= 60:
            print(f"✓ PASS: Score {score}/100 is acceptable for {source['domain']}")
        else:
            print(f"✗ FAIL: Score {score}/100 is too low for {source['domain']}")
            print(f"  Expected: >= 60 (trusted academic publisher)")
            if "trusted_domain" not in breakdown:
                print(f"  ERROR: {source['domain']} not recognized as trusted domain")
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("Expected behavior:")
    print("  - sciencedirect.com should score 25 (trusted_domain) + 0 (.com suffix) = 25+")
    print("  - link.springer.com should score 25 (trusted_domain) + 0 (.com suffix) = 25+")
    print("  - Both should score >= 60 with additional signals (author, freshness, etc.)")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
