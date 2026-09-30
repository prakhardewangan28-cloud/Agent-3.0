"""Test to verify actual embedding dimensions from Gemini."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gemini_client import embed
from app.config import settings


async def main():
    print("=" * 80)
    print("EMBEDDING DIMENSION TEST")
    print("=" * 80)
    print(f"MOCK_MODE: {settings.mock_mode}")
    print(f"Config EMBEDDING_DIM: {settings.embedding_dim}")
    print()
    
    # Test with different dimensions
    test_text = "This is a test sentence."
    
    for dim in [768, 1536, 3072]:
        print(f"Testing dimension: {dim}")
        try:
            embedding = await embed(test_text, dim=dim)
            print(f"  ✓ Returned dimension: {len(embedding)}")
            print(f"  First 3 values: {embedding[:3]}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
