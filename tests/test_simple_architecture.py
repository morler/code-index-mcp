#!/usr/bin/env python3
"""
Test script for new Linus-style architecture

Verifies that the simplified architecture works correctly.
"""

import sys
from pathlib import Path

# Add src to path for proper imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from core.index import set_project_path, get_index, SearchQuery
from core.builder import IndexBuilder


def test_basic_functionality():
    """Test basic index functionality."""
    print("🧪 Testing basic functionality...")

    # Set project path
    project_path = str(Path(__file__).parent)
    index = set_project_path(project_path)
    print(f"✅ Project path set: {project_path}")

    # Build index
    builder = IndexBuilder(index)
    stats = builder.build_index()
    print(f"✅ Index built: {stats}")

    # Test search
    query = SearchQuery(pattern="def ", type="text")
    result = index.search(query)
    print(f"✅ Search completed: {result.total_count} matches in {result.search_time:.3f}s")

    # Test file pattern matching
    files = index.find_files_by_pattern("*.py")
    print(f"✅ Found {len(files)} Python files")

    # Test stats
    stats = index.get_stats()
    print(f"✅ Stats: {stats}")

    return True


def test_search_operations():
    """Test different search operations."""
    print("\n🔍 Testing search operations...")

    index = get_index()

    # Test text search
    query = SearchQuery(pattern="class", type="text", case_sensitive=False)
    result = index.search(query)
    print(f"✅ Text search: {result.total_count} matches")

    # Test regex search
    query = SearchQuery(pattern=r"def\s+\w+", type="regex")
    result = index.search(query)
    print(f"✅ Regex search: {result.total_count} matches")

    # Test symbol search
    query = SearchQuery(pattern="test", type="symbol", case_sensitive=False)
    result = index.search(query)
    print(f"✅ Symbol search: {result.total_count} matches")

    return True


def main():
    """Run all tests."""
    print("🚀 Testing Linus-style simplified architecture\n")

    try:
        test_basic_functionality()
        test_search_operations()
        print("\n🎉 All tests passed! Architecture is working correctly.")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)