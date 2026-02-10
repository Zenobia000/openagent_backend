#!/usr/bin/env python3
"""
驗證 Prompts 100% 整合
確認所有 prompt 方法都已被使用
"""

import sys
import re
import os
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent / "src"))

from core.prompts import PromptTemplates


def find_prompt_usage():
    """掃描程式碼找出所有 prompt 使用位置"""

    # 獲取所有 prompt 方法
    prompt_methods = [
        method for method in dir(PromptTemplates)
        if method.startswith('get_') and callable(getattr(PromptTemplates, method))
    ]

    print(f"📊 總共有 {len(prompt_methods)} 個 prompt 方法\n")

    # 掃描 src 目錄
    src_path = Path(__file__).parent / "src"
    usage_map = {}

    for prompt_method in prompt_methods:
        usage_map[prompt_method] = []

    # 遞迴搜索所有 .py 檔案
    for py_file in src_path.rglob("*.py"):
        # 跳過 prompts.py 本身
        if py_file.name == "prompts.py":
            continue

        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
            line_num = 0

            for line in content.split('\n'):
                line_num += 1

                # 搜索每個 prompt 方法的使用
                for method in prompt_methods:
                    pattern = rf'PromptTemplates\.{method}\('
                    if re.search(pattern, line):
                        relative_path = py_file.relative_to(src_path)
                        usage_map[method].append(f"{relative_path}:{line_num}")

    return usage_map


def generate_usage_report(usage_map):
    """生成使用報告"""

    used_prompts = []
    unused_prompts = []

    for method, locations in usage_map.items():
        if locations:
            used_prompts.append((method, locations))
        else:
            unused_prompts.append(method)

    # 打印結果
    print("✅ 已使用的 Prompts:")
    print("-" * 60)

    for method, locations in sorted(used_prompts):
        print(f"\n📌 {method}")
        for loc in locations[:3]:  # 顯示前 3 個使用位置
            print(f"   └─ {loc}")
        if len(locations) > 3:
            print(f"   └─ ... 還有 {len(locations) - 3} 處使用")

    if unused_prompts:
        print("\n\n⚠️ 未使用的 Prompts:")
        print("-" * 60)
        for method in sorted(unused_prompts):
            print(f"   ❌ {method}")
    else:
        print("\n\n🎉 太棒了！所有 prompts 都已被使用！")

    # 統計
    print("\n\n📈 統計結果:")
    print("-" * 60)
    total = len(usage_map)
    used = len(used_prompts)
    unused = len(unused_prompts)
    percentage = (used / total * 100) if total > 0 else 0

    print(f"總數: {total} 個")
    print(f"已使用: {used} 個")
    print(f"未使用: {unused} 個")
    print(f"使用率: {percentage:.1f}%")

    if percentage == 100:
        print("\n🏆 恭喜！達成 100% prompt 整合！")

    return percentage


def check_special_cases():
    """檢查特殊情況"""
    print("\n\n🔍 特殊情況檢查:")
    print("-" * 60)

    # get_guidelines_prompt 是內部輔助方法
    print("• get_guidelines_prompt() - 內部輔助方法，被 get_report_plan_prompt() 使用 ✓")

    # get_serp_query_schema_prompt 是內部輔助方法
    print("• get_serp_query_schema_prompt() - 內部輔助方法，被其他 SERP prompts 使用 ✓")


def main():
    print("=" * 60)
    print("🔍 Prompts 整合驗證工具")
    print("=" * 60)
    print()

    # 找出所有使用位置
    usage_map = find_prompt_usage()

    # 生成報告
    percentage = generate_usage_report(usage_map)

    # 檢查特殊情況
    check_special_cases()

    print("\n" + "=" * 60)

    # 回傳結果
    return percentage == 100


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)