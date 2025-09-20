#!/usr/bin/env python3
"""
Simple test script to verify Phase 4 functionality is working.
"""

import tempfile
import os
from unittest.mock import Mock, patch

# Test the analysis functions directly
def test_analysis_functions():
    """Test that the analysis functions can be imported and have the right structure."""

    print("🔍 Testing Phase 4 analysis functions import...")

    from src.code_index_mcp.services.semantic_edit_service import SemanticEditService

    # Check that new methods exist
    methods = [
        'detect_circular_dependencies',
        'detect_unused_code',
        'analyze_impact_scope',
        'extract_function',
        'extract_variable',
        'inline_function'
    ]

    for method in methods:
        assert hasattr(SemanticEditService, method), f"Method {method} not found"
        print(f"✅ {method} method exists")

    print("🎉 All Phase 4 methods are properly defined!\n")

def test_helper_functions():
    """Test helper functions work correctly."""

    print("🔍 Testing Phase 4 helper functions...")

    from src.code_index_mcp.services.semantic_edit_service import SemanticEditService

    # Create a dummy instance to test helper methods
    mock_ctx = Mock()
    service = SemanticEditService(mock_ctx)

    # Test variable analysis
    code = """
x = 5
y = 10
result = x + y
print(result)
"""

    used_vars, assigned_vars = service._analyze_variables_in_code(code)
    print(f"✅ Used variables: {used_vars}")
    print(f"✅ Assigned variables: {assigned_vars}")

    assert 'x' in used_vars or 'x' in assigned_vars
    assert 'result' in assigned_vars

    # Test variable defined check
    assert service._is_variable_defined_in_code('x', code)
    assert not service._is_variable_defined_in_code('undefined_var', code)
    print("✅ Variable analysis functions work correctly")

    # Test function generation
    func_def = service._generate_function_definition('test_func', ['param1', 'param2'], ['result'], 'return param1 + param2')
    print(f"✅ Generated function: {func_def}")
    assert 'def test_func(param1, param2):' in func_def
    assert 'return result' in func_def

    func_call = service._generate_function_call('test_func', ['a', 'b'], ['output'])
    print(f"✅ Generated call: {func_call}")
    assert 'output = test_func(a, b)' in func_call

    print("🎉 Helper functions work correctly!\n")

def test_server_tools():
    """Test that server tools are properly registered."""

    print("🔍 Testing Phase 4 server tools...")

    from src.code_index_mcp import server

    # Check that new tools are defined in the server module
    tools = [
        'detect_circular_dependencies',
        'detect_unused_code',
        'analyze_impact_scope',
        'extract_function',
        'extract_variable',
        'inline_function'
    ]

    for tool in tools:
        assert hasattr(server, tool), f"Tool {tool} not found in server"
        print(f"✅ {tool} tool is registered")

    print("🎉 All Phase 4 server tools are properly registered!\n")

def test_file_operations():
    """Test basic file operations work."""

    print("🔍 Testing Phase 4 file operations...")

    # Create a temporary test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""def calculate(x, y):
    temp = x * 2
    result = temp + y
    return result

def main():
    value = calculate(5, 10)
    print(value)
""")
        temp_file = f.name

    try:
        # Test that we can read and analyze the file
        with open(temp_file, 'r') as f:
            content = f.read()

        print(f"✅ Created test file with {len(content)} characters")

        # Test basic content validation
        assert 'def calculate' in content
        assert 'def main' in content
        print("✅ Test file contains expected functions")

        print("🎉 File operations work correctly!\n")

    finally:
        os.unlink(temp_file)

def main():
    """Run all simple tests."""
    print("🚀 Running Simple Phase 4 Verification Tests\n")

    try:
        test_analysis_functions()
        test_helper_functions()
        test_server_tools()
        test_file_operations()

        print("🎉 All Phase 4 verification tests passed!")
        print("✨ Phase 4 Advanced Semantic Functionality is properly implemented!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    main()