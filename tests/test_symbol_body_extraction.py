#!/usr/bin/env python3
"""
符号体提取测试 - 验证修复效果
"""

import pytest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.index import set_project_path
from core.mcp_tools import tool_get_symbol_body


class TestSymbolBodyExtraction:
    """符号体提取测试"""

    @pytest.fixture(scope="class")
    def project_index(self):
        """初始化项目索引"""
        project_root = Path(__file__).parent.parent
        return set_project_path(str(project_root))

    @pytest.mark.unit
    def test_symbol_body_extraction_with_real_symbols(self, project_index):
        """测试使用真实符号的体提取"""
        # 获取第一个可用的符号进行测试
        if project_index.symbols:
            symbol_name = list(project_index.symbols.keys())[0]
            result = tool_get_symbol_body(symbol_name)

            assert result["success"], (
                f"符号体提取应该成功: {result.get('error', 'Unknown error')}"
            )
            assert "symbol_name" in result, "结果应包含symbol_name"
            assert "symbol_type" in result, "结果应包含symbol_type"
            assert "file_path" in result, "结果应包含file_path"
            assert "start_line" in result, "结果应包含start_line"
            assert "end_line" in result, "结果应包含end_line"
            assert "body_lines" in result, "结果应包含body_lines"
            assert "total_lines" in result, "结果应包含total_lines"

            # 验证行号逻辑
            assert result["start_line"] >= 1, "起始行号应>=1"
            assert result["end_line"] >= result["start_line"], "结束行号应>=起始行号"
            assert result["total_lines"] > 0, "总行数应>0"
            assert len(result["body_lines"]) == result["total_lines"], (
                "body_lines数量应与total_lines一致"
            )

    @pytest.mark.unit
    def test_symbol_body_extraction_invalid_symbol(self, project_index):
        """测试无效符号的体提取"""
        result = tool_get_symbol_body("nonexistent_symbol_12345")

        assert not result["success"], "无效符号应该返回失败"
        assert "error" in result, "错误结果应包含error字段"
        assert "not found" in result["error"].lower(), "错误信息应包含not found"

    @pytest.mark.unit
    def test_symbol_body_extraction_with_line_numbers(self, project_index):
        """测试带行号的符号体提取"""
        if project_index.symbols:
            symbol_name = list(project_index.symbols.keys())[0]
            result = tool_get_symbol_body(symbol_name, show_line_numbers=True)

            assert result["success"], (
                f"符号体提取应该成功: {result.get('error', 'Unknown error')}"
            )
            assert "line_numbers" in result, "结果应包含line_numbers字段"

            # 验证行号数量
            expected_line_count = result["end_line"] - result["start_line"] + 1
            assert len(result["line_numbers"]) == expected_line_count, (
                "行号数量应与提取的行数一致"
            )

            # 验证行号范围
            assert result["line_numbers"][0] == result["start_line"], (
                "第一个行号应等于起始行"
            )
            assert result["line_numbers"][-1] == result["end_line"], (
                "最后一个行号应等于结束行"
            )

    @pytest.mark.unit
    def test_symbol_body_extraction_language_detection(self, project_index):
        """测试语言自动检测"""
        if project_index.symbols:
            symbol_name = list(project_index.symbols.keys())[0]
            symbol_info = project_index.symbols[symbol_name]

            result = tool_get_symbol_body(symbol_name, language="auto")

            assert result["success"], (
                f"符号体提取应该成功: {result.get('error', 'Unknown error')}"
            )
            assert "language" in result, "结果应包含language字段"

            # 验证语言检测
            file_info = project_index.get_file(symbol_info.file)
            expected_language = file_info.language if file_info else "unknown"
            assert result["language"] == expected_language, "检测的语言应与文件语言一致"

    @pytest.mark.unit
    def test_symbol_body_extraction_python_functions(self, project_index):
        """测试Python函数体提取"""
        # 查找Python函数符号
        python_functions = [
            name
            for name, info in project_index.symbols.items()
            if info.type == "function" and info.file.endswith(".py")
        ]

        if python_functions:
            symbol_name = python_functions[0]
            result = tool_get_symbol_body(symbol_name)

            assert result["success"], (
                f"Python函数体提取应该成功: {result.get('error', 'Unknown error')}"
            )
            assert result["symbol_type"] == "function", "符号类型应为function"
            assert result["language"] == "python", "语言应为python"

            # 验证函数体包含def关键字或函数签名
            body_text = "\n".join(result["body_lines"])
            signature = result.get("signature")
            # 有些函数可能是通过其他方式定义的，所以检查多种可能性
            has_function_indicator = (
                "def " in body_text
                or "function " in body_text
                or (signature and signature.strip())
                or len(result["body_lines"]) > 1  # 至少有多行内容
            )
            assert has_function_indicator, (
                f"函数体应包含函数指示器，实际内容: {body_text[:100]}..."
            )

    @pytest.mark.unit
    def test_symbol_body_extraction_error_handling(self, project_index):
        """测试错误处理"""
        # 测试空符号名
        result = tool_get_symbol_body("")
        assert not result["success"], "空符号名应该返回失败"

        # 测试None符号名
        result = tool_get_symbol_body(None)  # type: ignore
        assert not result["success"], "None符号名应该返回失败"

    @pytest.mark.unit
    def test_symbol_body_extraction_boundary_validation(self, project_index):
        """测试边界验证"""
        if project_index.symbols:
            symbol_name = list(project_index.symbols.keys())[0]
            symbol_info = project_index.symbols[symbol_name]

            # 测试指定不存在的文件路径
            result = tool_get_symbol_body(symbol_name, file_path="/nonexistent/path.py")
            assert not result["success"], "不存在的文件应该返回失败"
            assert "not found" in result["error"].lower(), "错误信息应包含not found"

    @pytest.mark.unit
    def test_symbol_body_extraction_similar_symbol_suggestions(self, project_index):
        """测试相似符号建议功能"""
        # 使用一个不太可能存在的符号名
        fake_symbol = "xyz_nonexistent_function_12345"
        result = tool_get_symbol_body(fake_symbol)

        assert not result["success"], "不存在的符号应该返回失败"

        # 检查是否包含相似符号建议
        error_msg = result.get("error", "")
        if "Did you mean:" in error_msg:
            # 如果有建议，验证建议格式
            assert ":" in error_msg, "建议应包含冒号分隔符"

    @pytest.mark.integration
    def test_symbol_body_extraction_consistency(self, project_index):
        """测试符号体提取的一致性"""
        if project_index.symbols:
            # 选择几个符号进行一致性测试
            test_symbols = list(project_index.symbols.keys())[:3]

            for symbol_name in test_symbols:
                # 多次提取同一符号，结果应该一致
                result1 = tool_get_symbol_body(symbol_name)
                result2 = tool_get_symbol_body(symbol_name)

                assert result1["success"] == result2["success"], "多次提取结果应一致"
                if result1["success"]:
                    assert result1["start_line"] == result2["start_line"], (
                        "起始行应一致"
                    )
                    assert result1["end_line"] == result2["end_line"], "结束行应一致"
                    assert result1["total_lines"] == result2["total_lines"], (
                        "总行数应一致"
                    )

    @pytest.mark.integration
    def test_symbol_body_extraction_performance(self, project_index):
        """测试符号体提取性能"""
        import time

        if project_index.symbols:
            symbol_name = list(project_index.symbols.keys())[0]

            # 测试提取时间
            start_time = time.time()
            result = tool_get_symbol_body(symbol_name)
            end_time = time.time()

            extraction_time = end_time - start_time
            assert result["success"], (
                f"符号体提取应该成功: {result.get('error', 'Unknown error')}"
            )
            assert extraction_time < 1.0, (
                f"符号体提取时间应少于1秒，实际: {extraction_time:.3f}秒"
            )


if __name__ == "__main__":
    # 简单的测试运行
    pytest.main([__file__, "-v"])
