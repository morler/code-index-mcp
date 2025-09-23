#!/usr/bin/env python3
"""
Phase2准确性测试 - 验证90%+准确性和无假阴性
"""

import time
import os
import tempfile
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from core.incremental import FileChangeTracker

def test_change_detection_accuracy():
    """测试变更检测准确性"""
    print("🎯 Phase2变更检测准确性测试")
    print("=" * 50)

    # 创建测试文件
    temp_dir = tempfile.mkdtemp(prefix="accuracy_test_")
    tracker = FileChangeTracker()

    try:
        # 创建不同大小的测试文件
        test_files = []

        # 小文件(< 10KB) - 内容哈希
        for i in range(10):
            file_path = os.path.join(temp_dir, f"small_{i}.py")
            content = f"# Small file {i}\ndef func():\n    pass\n" * 10
            with open(file_path, 'w') as f:
                f.write(content)
            test_files.append(file_path)

        # 大文件(> 10KB) - 元数据哈希
        for i in range(10):
            file_path = os.path.join(temp_dir, f"large_{i}.py")
            content = f"# Large file {i}\ndef func():\n    pass\n" * 1000  # > 10KB
            with open(file_path, 'w') as f:
                f.write(content)
            test_files.append(file_path)

        # 初始跟踪
        for file_path in test_files:
            tracker.update_file_tracking(file_path)

        print(f"📁 创建了 {len(test_files)} 个测试文件 (10小+10大)")

        # 测试1: 无变更检测
        print("\n🔍 测试1: 无变更检测")
        unchanged_detected = 0
        for file_path in test_files:
            if not tracker.is_file_changed(file_path):
                unchanged_detected += 1

        print(f"   • 正确识别未变更: {unchanged_detected}/{len(test_files)} = {unchanged_detected/len(test_files)*100:.1f}%")

        # 测试2: 小文件变更检测
        print("\n📝 测试2: 小文件变更检测")
        time.sleep(0.1)  # 确保mtime不同

        small_changed = 0
        for i in range(5):  # 修改前5个小文件
            file_path = test_files[i]
            with open(file_path, 'w') as f:
                f.write(f"# Modified small file {i}\ndef new_func():\n    return 'changed'\n")
            if tracker.is_file_changed(file_path):
                small_changed += 1

        print(f"   • 正确检测小文件变更: {small_changed}/5 = {small_changed/5*100:.1f}%")

        # 测试3: 大文件变更检测
        print("\n📄 测试3: 大文件变更检测")
        time.sleep(0.1)

        large_changed = 0
        for i in range(10, 15):  # 修改前5个大文件
            file_path = test_files[i]
            with open(file_path, 'w') as f:
                f.write(f"# Modified large file {i}\ndef new_func():\n    return 'changed'\n" * 1000)
            if tracker.is_file_changed(file_path):
                large_changed += 1

        print(f"   • 正确检测大文件变更: {large_changed}/5 = {large_changed/5*100:.1f}%")

        # 测试4: 假阴性检测
        print("\n❌ 测试4: 假阴性检测")
        false_negatives = 0
        modified_files = test_files[:5] + test_files[10:15]  # 实际修改的文件

        for file_path in modified_files:
            if not tracker.is_file_changed(file_path):
                false_negatives += 1
                print(f"      ⚠️ 假阴性: {file_path}")

        print(f"   • 假阴性数量: {false_negatives}/10 = {false_negatives/10*100:.1f}%")

        # 测试5: 假阳性检测
        print("\n✅ 测试5: 假阳性检测")
        false_positives = 0
        unmodified_files = test_files[5:10] + test_files[15:]  # 未修改的文件

        for file_path in unmodified_files:
            if tracker.is_file_changed(file_path):
                false_positives += 1
                print(f"      ⚠️ 假阳性: {file_path}")

        print(f"   • 假阳性数量: {false_positives}/10 = {false_positives/10*100:.1f}%")

        # 总体准确性
        total_correct = (small_changed + large_changed +
                        (len(unmodified_files) - false_positives))
        total_accuracy = total_correct / len(test_files) * 100

        print("\n" + "=" * 50)
        print("📊 准确性测试结果汇总")
        print("=" * 50)
        print(f"✅ 总体准确性: {total_accuracy:.1f}%")
        print(f"❌ 假阴性率: {false_negatives/10*100:.1f}%")
        print(f"⚠️ 假阳性率: {false_positives/10*100:.1f}%")

        # Plans.md成功标准验证
        if total_accuracy >= 90:
            print(f"🎉 目标达成: {total_accuracy:.1f}% >= 90% (plans.md要求)")
        else:
            print(f"❌ 未达目标: {total_accuracy:.1f}% < 90% (plans.md要求)")

        if false_negatives == 0:
            print("🎉 零假阴性: 符合plans.md要求 (No false negatives)")
        else:
            print(f"⚠️ 存在假阴性: {false_negatives}个 (不符合plans.md要求)")

    finally:
        # 清理
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"\n🧹 清理测试文件: {temp_dir}")

if __name__ == "__main__":
    test_change_detection_accuracy()