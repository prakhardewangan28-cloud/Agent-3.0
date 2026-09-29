"""Toggle MOCK_MODE in .env file between true and false."""
import os
import sys
from pathlib import Path

# Get backend directory
backend_dir = Path(__file__).parent.parent
env_file = backend_dir / ".env"

def read_env():
    """Read .env file and return lines."""
    if not env_file.exists():
        print(f"❌ .env file not found at: {env_file}")
        print("   Create one from .env.example first")
        sys.exit(1)
    
    with open(env_file, 'r', encoding='utf-8') as f:
        return f.readlines()

def write_env(lines):
    """Write lines to .env file."""
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def toggle_mock_mode():
    """Toggle MOCK_MODE between true and false."""
    lines = read_env()
    found = False
    new_lines = []
    current_value = None
    
    for line in lines:
        # Check if this line is MOCK_MODE
        if line.strip().startswith('MOCK_MODE='):
            found = True
            # Extract current value
            current_value = line.split('=', 1)[1].strip().lower()
            
            # Toggle the value
            if current_value in ['true', '1', 'yes', 'on']:
                new_line = 'MOCK_MODE=false\n'
                new_value = 'false'
            else:
                new_line = 'MOCK_MODE=true\n'
                new_value = 'true'
            
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    
    # If MOCK_MODE not found, add it at the end
    if not found:
        if not new_lines[-1].endswith('\n'):
            new_lines[-1] += '\n'
        new_lines.append('\n# Mock Mode (added by toggle_mode.py)\n')
        new_lines.append('MOCK_MODE=true\n')
        new_value = 'true'
        current_value = 'not set'
    
    # Write back to file
    write_env(new_lines)
    
    print("=" * 60)
    print("🔄 MOCK_MODE TOGGLED")
    print("=" * 60)
    print(f"Previous value: {current_value}")
    print(f"New value:      {new_value}")
    print()
    
    if new_value == 'true':
        print("🧪 Mock mode ENABLED")
        print("   - No real API calls will be made")
        print("   - Using fake data for development")
        print("   - No API keys required")
    else:
        print("🔌 Mock mode DISABLED")
        print("   - Real API calls will be made")
        print("   - Valid API keys required")
        print("   - Supabase, Gemini, and SerpAPI must be configured")
    
    print()
    print(f"✅ .env file updated: {env_file}")
    print()

def main():
    """Main function."""
    print()
    try:
        toggle_mock_mode()
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
