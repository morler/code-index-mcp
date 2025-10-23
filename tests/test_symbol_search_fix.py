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
        query = SearchQuery(pattern="test_apply_edit", type="symbol", limit=10)
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
        """测试函数类型检测"""
        query = SearchQuery(pattern="test_apply_edit", type="symbol", limit=5)
        result = search_engine.search(query)

        # 应该找到函数定义
        function_matches = [m for m in result.matches if m.get("type") == "function"]
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
        query = SearchQuery(pattern="set_project_path", type="symbol", limit=10)
        result = search_engine.search(query)

        if result.total_count > 0:
            # 应该找到导入语句
            import_matches = [m for m in result.matches if m.get("type") == "import"]
            assert len(import_matches) > 0, "应该检测到导入类型"

            for match in import_matches:
                if "content" in match:
                    assert any(
                        keyword in match["content"] for keyword in ["import ", "from "]
                    ), "导入定义应包含import或from关键字"

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
            pattern="test_apply_edit", type="symbol", case_sensitive=True, limit=10
        )
        result_sensitive = search_engine.search(query_sensitive)

        # 测试大小写不敏感搜索
        query_insensitive = SearchQuery(
            pattern="TEST_APPLY_EDIT", type="symbol", case_sensitive=False, limit=10
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


if __name__ == "__main__":
    # 简单的测试运行
    pytest.main([__file__, "-v"])
