#!/usr/bin/env python3
"""
Debug T006 - Check content validation
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, '.')

def debug_content_validation():
    """Debug content validation issue"""
    print("🔍 Debugging content validation...")
    
    try:
        from src.code_index_mcp.core.edit_operations import MemoryEditOperations
        
        # Create temporary test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello world\nThis is a test")
            test_file = f.name
        
        try:
            # Read actual content
            with open(test_file, 'r') as f:
                actual_content = f.read()
            
            print(f"Actual file content: {repr(actual_content)}")
            
            # Test different old_content values
            test_values = [
                "Hello world",
                "Hello world\n",
                "Hello world\nThis is a test",
                "Hello world\nThis is a test\n",
                "Hello world\nThis is a test".strip(),
            ]
            
            for i, old_content in enumerate(test_values):
                print(f"\n--- Test {i+1} ---")
                print(f"old_content: {repr(old_content)}")
                print(f"old_content.strip(): {repr(old_content.strip())}")
                print(f"actual_content.strip(): {repr(actual_content.strip())}")
                print(f"Equal: {old_content.strip() == actual_content.strip()}")
                print(f"In: {old_content.strip() in actual_content.strip()}")
            
            # Try actual edit
            edit_ops = MemoryEditOperations()
            old_content = "Hello world"
            new_content = "Hello modified world"
            
            print(f"\n--- Actual Edit Test ---")
            print(f"old_content: {repr(old_content)}")
            print(f"new_content: {repr(new_content)}")
            
            success, error = edit_ops.edit_file_atomic(test_file, old_content, new_content)
            print(f"Success: {success}")
            print(f"Error: {error}")
            
        finally:
            # Cleanup
            if os.path.exists(test_file):
                os.unlink(test_file)
                
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_content_validation()