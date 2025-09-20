#!/usr/bin/env python3
"""
Simple demo script to test Phase 4 advanced semantic functionality.
"""

import os
import tempfile
import shutil
from unittest.mock import Mock
from src.code_index_mcp.services.semantic_edit_service import SemanticEditService

def create_mock_context():
    """Create a mock context for testing."""
    mock_ctx = Mock()
    mock_settings = Mock()
    mock_settings.project_path = "/mock/project"
    mock_ctx.settings = mock_settings
    return mock_ctx

def test_circular_dependency_detection():
    """Test circular dependency detection functionality."""
    print("🔍 Testing circular dependency detection...")

    mock_ctx = create_mock_context()
    service = SemanticEditService(mock_ctx)

    # Mock the index manager property
    mock_index_manager = Mock()
    mock_index_manager.get_all_symbols.return_value = [
        {'name': 'function_a', 'dependencies': ['function_b']},
        {'name': 'function_b', 'dependencies': ['function_c']},
        {'name': 'function_c', 'dependencies': ['function_a']},  # Creates cycle
        {'name': 'function_d', 'dependencies': ['function_e']},
        {'name': 'function_e', 'dependencies': []},
    ]

    # Mock index manager
    service._index_manager = mock_index_manager

    result = service.detect_circular_dependencies()

    print(f"✅ Success: {result['success']}")
    print(f"📊 Total symbols analyzed: {result['total_symbols_analyzed']}")
    print(f"🔄 Circular dependencies found: {result['circular_dependencies_found']}")
    print(f"⚠️  Affected symbols: {result['affected_symbols_count']}")
    print(f"📈 Impact percentage: {result['impact_percentage']}%")

    if result['cycles']:
        for cycle in result['cycles']:
            print(f"   Cycle {cycle['cycle_id']}: {' -> '.join(cycle['symbols'])} -> {cycle['symbols'][0]}")

    assert result['success'] == True
    assert result['circular_dependencies_found'] > 0
    print("🎉 Circular dependency detection test passed!\n")

def test_unused_code_detection():
    """Test unused code detection functionality."""
    print("🔍 Testing unused code detection...")

    mock_ctx = create_mock_context()
    service = SemanticEditService(mock_ctx)

    # Mock the index manager property
    mock_index_manager = Mock()
    mock_index_manager.get_all_symbols.return_value = [
        {'name': 'used_function', 'type': 'function', 'file': '/test.py', 'called_by': ['main']},
        {'name': 'unused_function', 'type': 'function', 'file': '/test.py', 'called_by': []},
        {'name': 'main', 'type': 'function', 'file': '/test.py', 'called_by': []},
        {'name': 'another_unused', 'type': 'function', 'file': '/utils.py', 'called_by': []},
    ]

    # Mock index manager
    service._index_manager = mock_index_manager

    result = service.detect_unused_code()

    print(f"✅ Success: {result['success']}")
    print(f"📊 Total symbols analyzed: {result['total_symbols_analyzed']}")
    print(f"❌ Unused symbols found: {result['unused_symbols_found']}")
    print(f"📈 Code usage percentage: {result['code_usage_percentage']}%")

    if result['unused_symbols_by_file']:
        for file_path, symbols in result['unused_symbols_by_file'].items():
            print(f"   File {file_path}: {len(symbols)} unused symbols")
            for symbol in symbols:
                print(f"     - {symbol['name']} ({symbol['type']})")

    assert result['success'] == True
    print("🎉 Unused code detection test passed!\n")

def test_impact_analysis():
    """Test impact scope analysis functionality."""
    print("🔍 Testing impact scope analysis...")

    mock_ctx = create_mock_context()
    service = SemanticEditService(mock_ctx)

    # Mock the index manager property
    mock_index_manager = Mock()
    mock_index_manager.search_symbols.return_value = [
        {'name': 'target_function', 'type': 'function', 'file': '/test.py'}
    ]
    mock_index_manager.find_symbol_references.return_value = [
        {'name': 'caller1', 'file': '/test1.py'},
        {'name': 'caller2', 'file': '/test2.py'},
        {'name': 'caller3', 'file': '/test3.py'},
    ]

    # Mock index manager
    service._index_manager = mock_index_manager

    result = service.analyze_impact_scope('target_function')

    print(f"✅ Success: {result['success']}")
    print(f"🎯 Target symbol: {result['target_symbol']}")
    print(f"📊 Direct references: {result['impact_summary']['direct_references']}")
    print(f"🔗 Transitive impact: {result['impact_summary']['transitive_impact']}")
    print(f"📁 Affected files: {result['impact_summary']['affected_files']}")
    print(f"🚨 Severity: {result['impact_summary']['severity']}")

    assert result['success'] == True
    assert result['target_symbol'] == 'target_function'
    print("🎉 Impact scope analysis test passed!\n")

def test_extract_function():
    """Test function extraction functionality."""
    print("🔍 Testing function extraction...")

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""def main():
    x = 5
    y = 10
    result = x + y
    print(f"Result: {result}")
    return result
""")
        temp_file = f.name

    try:
        mock_ctx = create_mock_context()
        mock_ctx.settings.project_path = os.path.dirname(temp_file)
        service = SemanticEditService(mock_ctx)

        result = service.extract_function(
            file_path=temp_file,
            start_line=3,
            end_line=4,
            function_name="calculate_sum"
        )

        print(f"✅ Success: {result['success']}")
        print(f"📝 Modified files: {len(result['modified_files'])}")
        print(f"🔧 Affected symbols: {result['affected_symbols']}")

        # Read the modified file to see the result
        with open(temp_file, 'r') as f:
            content = f.read()
            print(f"📄 Modified content:\n{content}")

        assert result['success'] == True
        assert 'calculate_sum' in result['affected_symbols']
        print("🎉 Function extraction test passed!\n")

    finally:
        os.unlink(temp_file)

def test_extract_variable():
    """Test variable extraction functionality."""
    print("🔍 Testing variable extraction...")

    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("""def calculate():
    result = (x * 2 + y) / (z - 1)
    return result
""")
        temp_file = f.name

    try:
        mock_ctx = create_mock_context()
        mock_ctx.settings.project_path = os.path.dirname(temp_file)
        service = SemanticEditService(mock_ctx)

        result = service.extract_variable(
            file_path=temp_file,
            line_number=2,
            expression="(x * 2 + y)",
            variable_name="intermediate_calc"
        )

        print(f"✅ Success: {result['success']}")
        print(f"📝 Modified files: {len(result['modified_files'])}")
        print(f"🔧 Affected symbols: {result['affected_symbols']}")

        # Read the modified file to see the result
        with open(temp_file, 'r') as f:
            content = f.read()
            print(f"📄 Modified content:\n{content}")

        assert result['success'] == True
        assert 'intermediate_calc' in result['affected_symbols']
        print("🎉 Variable extraction test passed!\n")

    finally:
        os.unlink(temp_file)

def main():
    """Run all Phase 4 demo tests."""
    print("🚀 Starting Phase 4 Advanced Semantic Functionality Demo\n")

    try:
        test_circular_dependency_detection()
        test_unused_code_detection()
        test_impact_analysis()
        test_extract_function()
        test_extract_variable()

        print("🎉 All Phase 4 tests passed successfully!")
        print("✨ Advanced semantic functionality is working correctly!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise

if __name__ == "__main__":
    main()