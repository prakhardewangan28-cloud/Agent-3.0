"""
Diagnostic script to test credibility scoring logic.

Tests scoring of a NASA.gov source to ensure realistic values.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.credibility_service import score_source


def main():
    """Test credibility scoring with a NASA source."""
    
    # Create a fake NASA source
    nasa_source = {
        "url": "https://science.nasa.gov/climate-change/effects/",
        "title": "The Effects of Climate Change",
        "snippet": "NASA explains the observed effects of climate change on our planet, including rising temperatures, melting ice caps, and changing weather patterns.",
        "domain": "science.nasa.gov",
        "engine": "google",
        "published_date": "2026-09-15"  # Within last 30 days
    }
    
    print("=" * 70)
    print("CREDIBILITY SCORING DIAGNOSTIC")
    print("=" * 70)
    print()
    print("Test Source:")
    print(f"  URL:    {nasa_source['url']}")
    print(f"  Domain: {nasa_source['domain']}")
    print(f"  Title:  {nasa_source['title']}")
    print(f"  Engine: {nasa_source['engine']}")
    print(f"  Date:   {nasa_source['published_date']}")
    print()
    
    # Score the source
    scored = score_source(nasa_source)
    
    # Display results
    score = scored["credibility_score"]
    breakdown = scored["score_breakdown"]
    
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()
    print(f"Final Score: {score}/100")
    print()
    print("Score Breakdown:")
    print("-" * 70)
    
    # Sort breakdown by value (highest first)
    sorted_breakdown = sorted(
        breakdown.items(),
        key=lambda x: x[1] if x[0] != "total" else -999,  # Put total last
        reverse=True
    )
    
    for rule, points in sorted_breakdown:
        if rule == "total":
            print("-" * 70)
        print(f"  {rule:30s} {points:+6.1f}")
    
    print()
    print("=" * 70)
    print("ANALYSIS")
    print("=" * 70)
    print()
    
    # Expected rules for NASA
    expected_rules = {
        "domain_suffix": 25,      # .gov
        "trusted_domain": 25,     # nasa.gov in TRUSTED_DOMAINS
        "freshness": 15,          # within 30 days
    }
    
    expected_score = 65  # Sum of expected rules
    
    # Check which expected rules fired
    all_good = True
    for rule, expected_points in expected_rules.items():
        actual_points = breakdown.get(rule, 0)
        if actual_points == expected_points:
            print(f"✓ {rule}: {actual_points} points (expected {expected_points})")
        else:
            print(f"✗ {rule}: {actual_points} points (expected {expected_points})")
            all_good = False
    
    # Check for unexpected penalties
    penalties = {k: v for k, v in breakdown.items() if v < 0}
    if penalties:
        print()
        print("Unexpected Penalties:")
        for rule, points in penalties.items():
            print(f"  ✗ {rule}: {points} points")
        all_good = False
    
    print()
    if all_good and score >= expected_score:
        print(f"✓ PASS: Score is realistic for NASA.gov source ({score}/100)")
        print(f"  Expected: {expected_score} (domain_suffix + trusted_domain + freshness)")
        print(f"  Note: Additional bonuses (author, scholar) would increase score further")
    print()
    if all_good and score >= expected_score:
        print(f"✓ PASS: Score is realistic for NASA.gov source ({score}/100)")
        print(f"  Expected: {expected_score} (domain_suffix + trusted_domain + freshness)")
        print(f"  Note: Additional bonuses (author, scholar) would increase score further")
    else:
        print("✗ FAIL: Score is too low for NASA.gov source")
        print()
        print("Possible Issues:")
        if "trusted_domain" not in breakdown:
            print("  - 'science.nasa.gov' not matching 'nasa.gov' in TRUSTED_DOMAINS")
            print("  - Try using exact domain 'nasa.gov' or add subdomain support")
        if breakdown.get("freshness", 0) < 15:
            print("  - Freshness scoring may have date parsing issues")
        if penalties:
            print("  - Unexpected penalties are reducing the score")
    
    print()
    print("=" * 70)
    
    return 0 if (all_good and score >= expected_score) else 1


if __name__ == "__main__":
    sys.exit(main())
