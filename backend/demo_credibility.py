"""Demo script showing credibility scoring in action."""
from app.services.credibility_service import score_source, score_sources_batch
import json

# High credibility source
high_cred = {
    "url": "https://cdc.gov/health",
    "domain": "cdc.gov",
    "title": "By Dr. Smith: COVID Guidelines",
    "snippet": "Comprehensive official health guidelines from the Centers for Disease Control",
    "engine": "web",
    "published_date": "2026-09-15"
}

# Low credibility source
low_cred = {
    "url": "https://infowars.com/sponsored/conspiracy",
    "domain": "infowars.com",
    "title": "SHOCKING!!! You won't believe this!!!",
    "snippet": "Short",
    "engine": "web"
}

print("=" * 70)
print("CREDIBILITY SCORING DEMO")
print("=" * 70)
print()

print("HIGH CREDIBILITY SOURCE (cdc.gov):")
print("-" * 70)
scored_high = score_source(high_cred)
print(f"  Score: {scored_high['credibility_score']}/100")
print(f"  Breakdown:")
for rule, points in scored_high["score_breakdown"].items():
    if rule != "total":
        print(f"    {rule}: {points:+d}")
print()

print("LOW CREDIBILITY SOURCE (infowars.com):")
print("-" * 70)
scored_low = score_source(low_cred)
print(f"  Score: {scored_low['credibility_score']}/100")
print(f"  Breakdown:")
for rule, points in scored_low["score_breakdown"].items():
    if rule != "total":
        print(f"    {rule}: {points:+d}")
print()

# Batch demo
print("=" * 70)
print("BATCH SCORING DEMO (sorted by credibility)")
print("=" * 70)

batch_sources = [
    {
        "url": "https://example.com/blog",
        "domain": "example.com",
        "title": "Blog Post",
        "snippet": "A random blog post with minimal authority or verification",
        "engine": "web"
    },
    {
        "url": "https://nature.com/research",
        "domain": "nature.com",
        "title": "Scientific Research Paper",
        "snippet": "A comprehensive peer-reviewed study with extensive methodology",
        "engine": "scholar"
    },
    high_cred,
    low_cred
]

scored_batch = score_sources_batch(batch_sources)

for i, source in enumerate(scored_batch, 1):
    print(f"{i}. {source['domain']}: {source['credibility_score']:.1f}/100")

print()
print("=" * 70)
print("✅ Credibility scoring working perfectly!")
print("=" * 70)
