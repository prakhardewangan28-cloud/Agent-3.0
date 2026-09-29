"""Check Gemini embedding dimensions using google-genai library."""
import sys
sys.path.append(".")

from app.config import settings
from google import genai

client = genai.Client(api_key=settings.gemini_api_key)

# Test 1: default call
r1 = client.models.embed_content(
    model="text-embedding-004",
    contents="test"
)
print(f"Default dim: {len(r1.embeddings[0].values)}")

# Test 2: explicit 1536
r2 = client.models.embed_content(
    model="text-embedding-004",
    contents="test",
    config={"output_dimensionality": 1536}
)
print(f"Explicit 1536 dim: {len(r2.embeddings[0].values)}")
