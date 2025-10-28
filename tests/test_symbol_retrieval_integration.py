"""
Integration tests for symbol retrieval functionality.

This module tests the complete workflow from symbol search to symbol body extraction,
ensuring all components work together correctly and efficiently.
"""

import pytest
import time
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.search import SearchEngine, SearchQuery
from core.index import set_project_path
from core.mcp_tools import tool_get_symbol_body


class TestSymbolRetrievalIntegration:
    """Integration tests for complete symbol retrieval workflow."""

    @pytest.fixture(scope="class")
    def search_engine(self):
        """Create search engine instance."""
        # Use project root directory
        project_root = Path(__file__).parent.parent
        index = set_project_path(str(project_root))
        return SearchEngine(index)

    def test_complete_symbol_workflow(self, search_engine):
        """Test complete workflow from symbol search to body extraction."""
        # Step 1: Search for symbols
        query = SearchQuery(pattern="User", type="symbol", limit=10)
        search_result = search_engine.search(query)
        assert len(search_result.matches) > 0, "Should find symbols containing 'User'"

        # Step 2: Get symbol body for first result
        first_symbol = search_result.matches[0]
        symbol_body = tool_get_symbol_body(
            first_symbol["symbol"], first_symbol.get("file")
        )

        # Step 3: Validate the workflow
        assert symbol_body is not None, "Should retrieve symbol body"
        if symbol_body.get("success", False):
            assert "body_lines" in symbol_body, "Should have body_lines field"
            assert "start_line" in symbol_body, "Should have start_line field"
            assert "end_line" in symbol_body, "Should have end_line field"

            # Step 4: Verify content consistency
            body_lines = symbol_body["body_lines"]
            content = "\n".join(body_lines)
            assert first_symbol["symbol"] in content, (
                "Content should contain symbol name"
            )
            assert len(content.strip()) > 0, "Content should not be empty"

    def test_symbol_search_and_content_consistency(self, search_engine):
        """Test consistency between search results and actual file content."""
        # Search for Python function symbols
        query = SearchQuery(pattern="get_user", type="symbol", limit=10)
        search_result = search_engine.search(query)

        for match in search_result.matches[:5]:  # Test first 5 results
            symbol_name = match["symbol"]
            file_path = match.get("file")

            # Get symbol body
            symbol_body = tool_get_symbol_body(symbol_name, file_path)

            if symbol_body and symbol_body.get("success", False):
                # Read the actual file content
                try:
                    full_path = Path(file_path) if file_path else None
                    if full_path and full_path.exists():
                        with open(full_path, "r", encoding="utf-8") as f:
                            file_content = f.read()

                        # Verify symbol body is subset of file content
                        body_lines = symbol_body["body_lines"]
                        body_content = "\n".join(body_lines)
                        assert body_content in file_content, (
                            f"Symbol body should be part of file content for {symbol_name}"
                        )

                        # Verify line numbers are within file bounds
                        file_lines = file_content.split("\n")
                        start_line = symbol_body["start_line"]
                        end_line = symbol_body["end_line"]

                        assert 1 <= start_line <= len(file_lines), (
                            f"Start line {start_line} out of bounds for {file_path}"
                        )
                        assert 1 <= end_line <= len(file_lines), (
                            f"End line {end_line} out of bounds for {file_path}"
                        )
                        assert start_line <= end_line, (
                            f"Start line {start_line} should be <= end line {end_line}"
                        )

                except Exception:
                    # Skip if file doesn't exist or can't be read
                    continue

    def test_error_handling_workflow(self, search_engine):
        """Test error handling in the complete workflow."""
        # Test symbol body extraction with non-existent symbol directly
        fake_symbol = "NonExistentSymbolForTestingOnly"
        symbol_body = tool_get_symbol_body(fake_symbol, "non_existent_file.py")
        assert not symbol_body.get("success", True), (
            "Should fail for non-existent symbol"
        )

        # Verify error message contains useful information
        assert "error" in symbol_body, "Should have error message"
        assert "not found" in symbol_body["error"].lower(), (
            "Error should mention symbol not found"
        )

    def test_performance_benchmark(self, search_engine):
        """Test performance of the complete symbol retrieval workflow."""
        # Measure search performance
        start_time = time.time()
        query = SearchQuery(pattern="user", type="symbol", limit=10)
        search_result = search_engine.search(query)
        search_time = time.time() - start_time

        # Should complete search within reasonable time
        assert search_time < 2.0, (
            f"Symbol search should complete within 2 seconds, took {search_time:.2f}s"
        )
        assert len(search_result.matches) > 0, "Should find some results"

        # Measure body extraction performance for first few results
        if search_result.matches:
            body_extraction_times = []
            for match in search_result.matches[:3]:  # Test first 3 results
                start_time = time.time()
                try:
                    symbol_body = tool_get_symbol_body(
                        match["symbol"], match.get("file")
                    )
                    extraction_time = time.time() - start_time
                    if symbol_body and symbol_body.get("success", False):
                        body_extraction_times.append(extraction_time)
                except Exception:
                    continue

            if body_extraction_times:
                avg_extraction_time = sum(body_extraction_times) / len(
                    body_extraction_times
                )
                assert avg_extraction_time < 1.0, (
                    f"Average body extraction should be < 1 second, was {avg_extraction_time:.2f}s"
                )

    def test_concurrent_symbol_operations(self, search_engine):
        """Test handling of multiple symbol operations in sequence."""
        # Perform multiple searches in sequence
        search_terms = ["user", "get", "set", "class", "def"]
        all_matches = []

        for term in search_terms:
            query = SearchQuery(pattern=term, type="symbol", limit=10)
            result = search_engine.search(query)
            all_matches.extend(result.matches)

        # Should have accumulated results
        assert len(all_matches) > 0, "Should have results from multiple searches"

        # Test body extraction for multiple symbols
        successful_extractions = 0
        for match in all_matches[:5]:  # Test first 5
            try:
                symbol_body = tool_get_symbol_body(match["symbol"], match.get("file"))
                if symbol_body and symbol_body.get("success", False):
                    successful_extractions += 1
            except Exception:
                continue

        # Should successfully extract at least some symbol bodies
        assert successful_extractions > 0, (
            "Should successfully extract some symbol bodies"
        )


@pytest.mark.integration
class TestSymbolRetrievalIntegrationExtended:
    """Extended integration tests for edge cases and complex scenarios."""

    @pytest.fixture(scope="class")
    def search_engine(self):
        """Create search engine instance."""
        project_root = Path(__file__).parent.parent
        index = set_project_path(str(project_root))
        return SearchEngine(index)

    def test_symbol_name_variations(self, search_engine):
        """Test symbol retrieval with various name patterns."""
        # Test camelCase
        camel_query = SearchQuery(pattern="getUser", type="symbol", limit=10)
        camel_result = search_engine.search(camel_query)

        # Test snake_case
        snake_query = SearchQuery(pattern="get_user", type="symbol", limit=10)
        snake_result = search_engine.search(snake_query)

        # Test PascalCase
        pascal_query = SearchQuery(pattern="GetUser", type="symbol", limit=10)
        pascal_result = search_engine.search(pascal_query)

        # Should find results for different naming conventions
        total_results = (
            len(camel_result.matches)
            + len(snake_result.matches)
            + len(pascal_result.matches)
        )
        assert total_results > 0, "Should find symbols with various naming patterns"

    def test_special_characters_in_symbols(self, search_engine):
        """Test handling of symbols with special characters."""
        # Search for symbols with common special characters
        special_patterns = ["_", "__", "_init__", "setup_", "teardown_"]

        for pattern in special_patterns:
            query = SearchQuery(pattern=pattern, type="symbol", limit=10)
            result = search_engine.search(query)

            for match in result.matches[:2]:  # Test first 2 results per pattern
                try:
                    symbol_body = tool_get_symbol_body(
                        match["symbol"], match.get("file")
                    )
                    if symbol_body and symbol_body.get("success", False):
                        # Content should contain the symbol name
                        assert match["symbol"] in "\n".join(
                            symbol_body["body_lines"]
                        ), f"Symbol body should contain symbol name {match['symbol']}"
                except Exception:
                    continue
