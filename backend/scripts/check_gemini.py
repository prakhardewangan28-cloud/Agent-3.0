"""Gemini API verification script using google-genai SDK (supports AQ. keys)."""
import sys
import os
import traceback
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings

# Check for mock mode
if settings.mock_mode:
    print("=" * 70)
    print("🧪 RUNNING IN MOCK MODE")
    print("=" * 70)
    print("No real API calls will be made. Using fake data for testing.")
    print()

print("=" * 70)
print("GEMINI API TEST (google-genai SDK)")
print("=" * 70)
print()

try:
    from app.services.gemini_client import generate, embed
    
    print("✅ Gemini modules imported successfully")
    if not settings.mock_mode:
        print(f"   API Key prefix: {settings.gemini_api_key[:6]}...")
    else:
        print("   Using MOCK MODE - no API key needed")
    print()
    
except ImportError as e:
    print(f"❌ Failed to import Gemini modules: {e}")
    print()
    traceback.print_exc()
    sys.exit(1)


async def test_gemini_generate():
    """Test Gemini text generation."""
    print("Step 1: Testing Gemini text generation...")
    try:
        response = await generate("Reply with just: OK")
        print(f"  ✅ Generation successful")
        print(f"     Prompt: 'Reply with just: OK'")
        print(f"     Response: {response.strip()[:100]}...")
        print()
        return True
    except Exception as e:
        if settings.mock_mode:
            print(f"  ❌ Generation FAILED (unexpected in mock mode)")
        else:
            print(f"  ❌ Generation FAILED")
        print(f"     Error: {type(e).__name__}: {e}")
        print()
        if not settings.mock_mode:
            print("Full traceback:")
            traceback.print_exc()
            print()
        return False


async def test_gemini_embed():
    """Test Gemini embedding generation."""
    print("Step 2: Testing Gemini embeddings (1536 dimensions)...")
    try:
        vector = await embed("test", dim=1536)
        vector_length = len(vector)
        
        print(f"  ✅ Embedding successful")
        print(f"     Text: 'test'")
        print(f"     Vector length: {vector_length}")
        print(f"     First 5 values: {[round(v, 4) for v in vector[:5]]}")
        print()
        
        if vector_length == 1536:
            print(f"  ✅ Dimension check PASSED (1536)")
        else:
            print(f"  ⚠️ Dimension is {vector_length}, expected 1536")
        
        print()
        return vector_length == 1536
    except Exception as e:
        if settings.mock_mode:
            print(f"  ❌ Embedding FAILED (unexpected in mock mode)")
        else:
            print(f"  ❌ Embedding FAILED")
        print(f"     Error: {type(e).__name__}: {e}")
        print()
        if not settings.mock_mode:
            print("Full traceback:")
            traceback.print_exc()
            print()
        return False


async def main():
    """Run all Gemini tests."""
    generate_success = await test_gemini_generate()
    embed_success = await test_gemini_embed()
    
    print("=" * 70)
    if generate_success and embed_success:
        print("✅ GEMINI WORKS")
        print("=" * 70)
        print()
        if settings.mock_mode:
            print("🧪 Mock mode verification complete!")
            print("Function signatures work correctly.")
        else:
            print("Gemini API is fully functional!")
        print()
        print("Available functions:")
        print("  - await generate(prompt, model='gemini-3.6-flash')")
        print("  - await embed(text, dim=1536)")
        print()
        sys.exit(0)
    else:
        print("❌ GEMINI FAILED")
        print("=" * 70)
        print()
        if not generate_success:
            print("  ❌ Text generation failed")
        if not embed_success:
            print("  ❌ Embedding generation failed")
        print()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
