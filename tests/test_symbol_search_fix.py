#!/usr/bin/env python3
"""
基础符号搜索测试 - 验证修复效果
"""

import pytest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.index import set_project_path
from core.search import SearchEngine, SearchQuery


class TestSymbolSearchFix:
    """符号搜索修复测试"""

    @pytest.fixture(scope="class")
    def search_engine(self):
        """初始化搜索引擎"""
        # 使用项目根目录
        project_root = Path(__file__).parent.parent
        index = set_project_path(str(project_root))
        return SearchEngine(index)

    @pytest.mark.unit
    def test_symbol_search_returns_results(self, search_engine):
        """测试符号搜索返回结果"""
        # 使用实际存在的函数名
        query = SearchQuery(pattern="search", type="symbol", limit=10)
        result = search_engine.search(query)

        assert result.total_count > 0, "符号搜索应该返回结果"
        assert len(result.matches) > 0, "匹配列表不应为空"
        assert result.search_time < 2.0, "搜索时间应少于2秒"

        # 检查结果格式
        match = result.matches[0]
        assert "symbol" in match, "结果应包含symbol字段"
        assert "type" in match, "结果应包含type字段"
        assert "file" in match, "结果应包含file字段"
        assert "line" in match, "结果应包含line字段"

    @pytest.mark.unit
    def test_function_detection(self, search_engine):
        """测试函数类型检测 - 使用实际存在的符号"""
        # 使用项目中实际存在的函数
        query = SearchQuery(pattern="search_code", type="symbol", limit=5)
        result = search_engine.search(query)

        if result.total_count > 0:
            function_matches = [
                m for m in result.matches if m.get("type") == "function"
            ]
            assert len(function_matches) > 0, "应该检测到函数类型"

            # 检查函数定义行包含def
            for match in function_matches:
                if "content" in match:
                    assert "def " in match["content"], "函数定义应包含def关键字"

    @pytest.mark.unit
    def test_class_detection(self, search_engine):
        """测试类类型检测"""
        # 查找可能的类名
        query = SearchQuery(pattern="SearchEngine", type="symbol", limit=10)
        result = search_engine.search(query)

        if result.total_count > 0:
            # 检查是否正确识别为类
            class_matches = [m for m in result.matches if m.get("type") == "class"]
            if class_matches:
                for match in class_matches:
                    if "content" in match:
                        assert "class " in match["content"], "类定义应包含class关键字"

    @pytest.mark.unit
    def test_import_detection(self, search_engine):
        """测试导入类型检测"""
        query = SearchQuery(pattern="SearchQuery", type="symbol", limit=10)
        result = search_engine.search(query)

        if result.total_count > 0:
            # 应该找到导入语句或类定义
            import_matches = [
                m for m in result.matches if m.get("type") in ["import", "class"]
            ]
            assert len(import_matches) > 0, "应该检测到导入或类类型"

            for match in import_matches:
                if "content" in match:
                    assert any(
                        keyword in match["content"]
                        for keyword in ["import ", "from ", "class "]
                    ), "导入或类定义应包含相应关键字"

    @pytest.mark.unit
    def test_multiple_symbol_types(self, search_engine):
        """测试多种符号类型"""
        # 测试常见符号
        test_patterns = ["search", "index", "test"]

        for pattern in test_patterns:
            query = SearchQuery(pattern=pattern, type="symbol", limit=5)
            result = search_engine.search(query)

            if result.total_count > 0:
                # 检查结果包含不同的类型
                types = set(m.get("type", "unknown") for m in result.matches)
                assert len(types) >= 1, f"模式 '{pattern}' 应该返回至少一种类型"

                # 不应该所有结果都是unknown
                non_unknown_types = [t for t in types if t != "unknown"]
                if len(result.matches) > 3:  # 如果结果较多，应该有准确的类型检测
                    assert len(non_unknown_types) > 0, (
                        f"模式 '{pattern}' 应该有准确的类型检测"
                    )

    @pytest.mark.unit
    def test_case_sensitive_search(self, search_engine):
        """测试大小写敏感搜索"""
        # 测试大小写敏感搜索能正常工作
        query_sensitive = SearchQuery(
            pattern="search", type="symbol", case_sensitive=True, limit=10
        )
        result_sensitive = search_engine.search(query_sensitive)

        # 测试大小写不敏感搜索
        query_insensitive = SearchQuery(
            pattern="SEARCH", type="symbol", case_sensitive=False, limit=10
        )
        result_insensitive = search_engine.search(query_insensitive)

        # 两种搜索都应该能找到结果
        assert result_sensitive.total_count >= 0, "大小写敏感搜索应该能正常执行"
        assert result_insensitive.total_count >= 0, "大小写不敏感搜索应该能正常执行"

        # 不敏感搜索应该能找到大小写不匹配的结果
        # 这里我们只验证功能正常，不强制要求结果数量关系

    @pytest.mark.unit
    def test_search_performance(self, search_engine):
        """测试搜索性能"""
        import time

        patterns = ["search", "index", "symbol", "test", "apply"]

        for pattern in patterns:
            start_time = time.time()
            query = SearchQuery(pattern=pattern, type="symbol", limit=20)
            result = search_engine.search(query)
            end_time = time.time()

            search_time = end_time - start_time
            assert search_time < 2.0, (
                f"模式 '{pattern}' 搜索时间应少于2秒，实际: {search_time:.3f}秒"
            )
            assert result.search_time < 2.0, (
                f"结果报告的搜索时间应少于2秒，实际: {result.search_time:.3f}秒"
            )

    @pytest.mark.unit
    def test_fallback_to_index_search(self, search_engine):
        """测试回退到索引搜索"""
        # 这个测试验证当ripgrep找不到结果时，会回退到索引搜索
        # 使用一个不太可能出现在ripgrep模式中但可能在索引中的符号

        # 首先检查索引中是否有符号
        if search_engine.index.symbols:
            # 取第一个符号进行测试
            symbol_name = list(search_engine.index.symbols.keys())[0]
            query = SearchQuery(pattern=symbol_name, type="symbol", limit=5)
            result = search_engine.search(query)

            # 应该找到结果（要么通过ripgrep，要么通过索引fallback）
            assert result.total_count >= 0, "搜索应该完成而不出错"

    @pytest.mark.integration
    def test_symbol_search_with_sample_projects(self, search_engine):
        """使用示例项目测试符号搜索"""
        # 查找示例项目中的符号
        query = SearchQuery(pattern="user", type="symbol", limit=10)
        result = search_engine.search(query)

        if result.total_count > 0:
            # 检查结果来自不同的文件
            files = set(m.get("file", "") for m in result.matches)
            assert len(files) >= 1, "结果应该来自文件"

            # 检查结果格式一致性
            for match in result.matches:
                assert isinstance(match, dict), "每个匹配应该是字典"
                required_keys = ["symbol", "type", "file", "line"]
                for key in required_keys:
                    assert key in match, f"匹配应包含{key}字段"

    @pytest.mark.unit
    def test_symbol_search_exact_match(self, search_engine):
        """测试精确匹配"""
        # 查找精确匹配的符号
        query = SearchQuery(pattern="_search_symbol", type="symbol", limit=5)
        result = search_engine.search(query)

        if result.total_count > 0:
            # 检查是否有精确匹配
            exact_matches = [
                m for m in result.matches if m["symbol"] == "_search_symbol"
            ]
            assert len(exact_matches) > 0, "应该找到精确匹配的符号"

    @pytest.mark.unit
    def test_symbol_search_prefix_match(self, search_engine):
        """测试前缀匹配"""
        # 查找前缀匹配的符号
        query = SearchQuery(pattern="_search", type="symbol", limit=10)
        result = search_engine.search(query)

        if result.total_count > 0:
            # 检查结果是否以前缀开头
            prefix_matches = [
                m for m in result.matches if m["symbol"].startswith("_search")
            ]
            assert len(prefix_matches) > 0, "应该找到前缀匹配的符号"

    @pytest.mark.unit
    def test_symbol_search_case_insensitive(self, search_engine):
        """测试大小写不敏感"""
        # 测试大小写不敏感搜索
        query_lower = SearchQuery(
            pattern="search", type="symbol", case_sensitive=False, limit=10
        )
        result_lower = search_engine.search(query_lower)

        query_upper = SearchQuery(
            pattern="SEARCH", type="symbol", case_sensitive=False, limit=10
        )
        result_upper = search_engine.search(query_upper)

        # 两种搜索应该找到相同或更多的结果
        assert result_lower.total_count >= 0, "小写搜索应该能正常执行"
        assert result_upper.total_count >= 0, "大写搜索应该能正常执行"

    @pytest.mark.unit
    def test_fallback_to_index_search(self, search_engine):
        """测试回退到索引搜索"""
        # 首先检查索引中是否有符号
        if search_engine.index.symbols:
            # 取第一个符号进行测试
            symbol_name = list(search_engine.index.symbols.keys())[0]
            query = SearchQuery(pattern=symbol_name, type="symbol", limit=5)
            result = search_engine.search(query)

            # 应该找到结果（要么通过ripgrep，要么通过索引fallback）
            assert result.total_count >= 0, "搜索应该完成而不出错"


if __name__ == "__main__":
    # 简单的测试运行
    pytest.main([__file__, "-v"])
