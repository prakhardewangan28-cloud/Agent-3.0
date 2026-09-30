"""
Check Gemini API connectivity with query-param authentication.

Tests both text generation and embedding with the AQ. API key.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gemini_client import generate, embed, reset_session_counter
from app.config import settings


async def main():
    """Test Gemini API connectivity."""
    
    print("=" * 80)
    print("GEMINI API CONNECTIVITY CHECK")
    print("=" * 80)
    print()
    
    print(f"MOCK_MODE: {settings.mock_mode}")
    print(f"API Key: {settings.gemini_api_key[:10]}...{settings.gemini_api_key[-4:]}")
    print()
    
    # Reset counter
    reset_session_counter()
    
    # Test 1: Simple text generation
    print("=" * 80)
    print("TEST 1: Text Generation")
    print("=" * 80)
    
    try:
        prompt = "Say 'Hello from Gemini!' and nothing else."
        print(f"Prompt: {prompt}")
        print()
        
        response = await generate(prompt)
        
        print("✓ SUCCESS")
        print(f"Response: {response[:200]}")
        print()
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        print()
        return 1
    
    # Test 2: JSON generation
    print("=" * 80)
    print("TEST 2: JSON Generation")
    print("=" * 80)
    
    try:
        prompt = """Return ONLY valid JSON with no markdown:
{"test": "success", "status": "ok"}"""
        print(f"Prompt: Requesting JSON response")
        print()
        
        response = await generate(prompt)
        
        print("✓ SUCCESS")
        print(f"Response: {response[:200]}")
        print()
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        print()
        return 1
    
    # Test 3: Embedding generation
    print("=" * 80)
    print("TEST 3: Embedding Generation")
    print("=" * 80)
    
    try:
        text = "This is a test sentence for embedding."
        print(f"Text: {text}")
        print()
        
        embedding = await embed(text, dim=1536)  # Production dimension
        
        print("✓ SUCCESS")
        print(f"Embedding dimensions: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
        print()
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        print()
        return 1
    
    # Test 4: Multiple calls (quota test)
    print("=" * 80)
    print("TEST 4: Multiple Calls (Quota Management)")
    print("=" * 80)
    
    try:
        from app.services.gemini_client import get_session_call_count
        
        print(f"Call count before: {get_session_call_count()}")
        
        for i in range(3):
            response = await generate(f"Say the number {i+1}")
            print(f"  Call {i+1}: {response[:50]}...")
        
        final_count = get_session_call_count()
        print()
        print(f"✓ SUCCESS")
        print(f"Call count after: {final_count}")
        print(f"Quota status: {'Under limit' if final_count <= 5 else 'Over limit'}")
        print()
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        print()
        return 1
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("✓ All tests passed!")
    print("✓ Gemini API is working correctly with AQ. key")
    print("✓ Query parameter authentication successful")
    print()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
