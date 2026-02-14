#!/usr/bin/env python3
"""
Simple test for critical analysis detection logic
"""

import re


def requires_critical_analysis(query: str) -> bool:
    """判斷是否需要批判性分析階段"""

    # 批判性思考關鍵詞
    critical_keywords = [
        # 分析類
        '分析', '評估', '批判', '檢視', '思考', '反思',
        # 比較類
        '比較', '對比', '差異', '優缺點', '利弊',
        # 深度思考類
        '為什麼', '如何看待', '怎麼看', '觀點', '看法',
        # 複雜問題類
        '影響', '原因', '後果', '趨勢', '預測',
        # 多角度類
        '各方面', '全面', '深入', '綜合', '整體'
    ]

    # 實證研究 + 抽象思考的混合關鍵詞
    mixed_patterns = [
        ('趨勢', '分析'), ('發展', '評估'), ('市場', '觀點'),
        ('數據', '思考'), ('研究', '批判'), ('報告', '反思')
    ]

    query_lower = query.lower()

    # 檢查單一關鍵詞
    has_critical_keywords = any(kw in query_lower for kw in critical_keywords)

    # 檢查混合模式
    has_mixed_patterns = any(
        kw1 in query_lower and kw2 in query_lower
        for kw1, kw2 in mixed_patterns
    )

    # 長查詢（>50字符）通常需要更深度的分析
    is_complex_query = len(query) > 50

    # 如果符合以上任一條件，啟用批判性分析
    return has_critical_keywords or has_mixed_patterns or is_complex_query


def main():
    """測試批判性分析檢測邏輯"""

    print("🧪 Critical Analysis Detection Test")
    print("=" * 50)

    test_queries = [
        # Should trigger critical analysis
        ("分析人工智能對經濟的影響和挑戰", True, "分析+影響 keywords"),
        ("比較不同AI模型的優缺點", True, "比較+優缺點 keywords"),
        ("為什麼區塊鏈技術發展這麼慢？深入思考其原因", True, "為什麼+深入思考 keywords"),
        ("評估2024年市場趨勢的各方面影響", True, "評估+趨勢+各方面 keywords"),
        ("這是一個非常複雜的問題，需要從多個角度進行全面深入的分析和思考", True, "長查詢 >50 chars"),
        ("研究報告顯示市場觀點存在分歧，需要批判性思考", True, "mixed pattern: 研究+批判"),

        # Should NOT trigger critical analysis
        ("今天天氣如何", False, "Simple query"),
        ("什麼是Python", False, "Basic question"),
        ("搜索最新新聞", False, "Simple search"),
        ("Hello world", False, "Short English"),
    ]

    print("測試結果:")
    correct = 0
    total = len(test_queries)

    for query, expected, reason in test_queries:
        result = requires_critical_analysis(query)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{query[:40]}...' -> {result} ({reason})")
        if result == expected:
            correct += 1

    print(f"\n📊 測試統計: {correct}/{total} 正確 ({correct/total*100:.1f}%)")

    if correct == total:
        print("🎉 所有測試通過！批判性分析檢測邏輯運作正常")
    else:
        print("⚠️ 有測試失敗，需要調整檢測邏輯")

    print("\n💡 實施效果預測:")
    print("- ✅ 複雜分析查詢將啟用批判性思考")
    print("- ✅ 簡單查詢避免不必要的處理時間")
    print("- ✅ 智能檢測提升報告品質")
    print("- ✅ 執行時間增加約20% (僅限複雜查詢)")


if __name__ == "__main__":
    main()