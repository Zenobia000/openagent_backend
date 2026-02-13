#!/usr/bin/env python3
"""
增強版引用統計測試
測試新增的詳細統計功能，包括：
- 引用次數統計
- 無效引用檢測
- 引用分佈分析
- 最常引用文獻排名
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.processor import DeepResearchProcessor


def test_basic_citation_analysis():
    """測試基本引用分析功能"""
    print("\n" + "=" * 70)
    print("Test 1: Basic Citation Analysis")
    print("=" * 70)

    processor = DeepResearchProcessor(None)

    # 測試報告 - 包含多次引用同一文獻
    test_report = """
    ## Introduction
    Recent AI advances [1] have transformed healthcare [2][3].
    Deep learning [1] is particularly important [4].

    ## Applications
    Medical imaging [1][2] shows great promise.
    Drug discovery [5] is accelerating [1].
    """

    test_references = [
        {'id': 1, 'title': 'AI in Healthcare 2024', 'url': 'http://example1.com'},
        {'id': 2, 'title': 'Medical Imaging AI', 'url': 'http://example2.com'},
        {'id': 3, 'title': 'Healthcare Transformation', 'url': 'http://example3.com'},
        {'id': 4, 'title': 'Deep Learning Primer', 'url': 'http://example4.com'},
        {'id': 5, 'title': 'AI Drug Discovery', 'url': 'http://example5.com'},
        {'id': 6, 'title': 'Uncited Paper', 'url': 'http://example6.com'},
    ]

    cited_refs, uncited_refs, stats = processor._analyze_citations(test_report, test_references)

    print(f"\n✅ Results:")
    print(f"  - Cited: {len(cited_refs)} sources")
    print(f"  - Uncited: {len(uncited_refs)} sources")
    print(f"  - Total citations: {stats['total_citations']}")
    print(f"  - Avg per source: {stats['avg_citations_per_source']:.2f}")

    print(f"\n🏆 Citation Ranking:")
    for ref in cited_refs:
        print(f"  [{ref['id']}] {ref['title']} - ×{ref['citation_count']}")

    # 驗證
    assert len(cited_refs) == 5, "Should have 5 cited references"
    assert len(uncited_refs) == 1, "Should have 1 uncited reference"
    assert stats['total_citations'] == 9, "Should have 9 total citations ([1]×4 + [2]×2 + [3]×1 + [4]×1 + [5]×1)"
    assert cited_refs[0]['citation_count'] == 4, "Ref [1] should be cited 4 times"

    print("\n✅ Test 1 PASSED!")


def test_invalid_citations():
    """測試無效引用檢測"""
    print("\n" + "=" * 70)
    print("Test 2: Invalid Citation Detection")
    print("=" * 70)

    processor = DeepResearchProcessor(None)

    # 測試報告 - 包含無效引用編號
    test_report = """
    Recent research [1][2] shows promising results.
    However, some studies [99] contradict this [100][3].
    Further investigation is needed [999].
    """

    test_references = [
        {'id': 1, 'title': 'Valid Paper 1', 'url': 'http://example1.com'},
        {'id': 2, 'title': 'Valid Paper 2', 'url': 'http://example2.com'},
        {'id': 3, 'title': 'Valid Paper 3', 'url': 'http://example3.com'},
        {'id': 4, 'title': 'Uncited Valid Paper', 'url': 'http://example4.com'},
    ]

    cited_refs, uncited_refs, stats = processor._analyze_citations(test_report, test_references)

    print(f"\n⚠️  Invalid Citations Detected:")
    print(f"  - Count: {len(stats['invalid_citations'])}")
    print(f"  - IDs: {stats['invalid_citations']}")

    print(f"\n✅ Valid Citations:")
    for ref in cited_refs:
        print(f"  [{ref['id']}] {ref['title']}")

    # 驗證
    assert len(stats['invalid_citations']) == 3, "Should detect 3 invalid citations"
    assert 99 in stats['invalid_citations'], "Should detect [99]"
    assert 100 in stats['invalid_citations'], "Should detect [100]"
    assert 999 in stats['invalid_citations'], "Should detect [999]"
    assert len(cited_refs) == 3, "Should have 3 valid cited references"

    print("\n✅ Test 2 PASSED!")


def test_citation_distribution():
    """測試引用分佈統計"""
    print("\n" + "=" * 70)
    print("Test 3: Citation Distribution Analysis")
    print("=" * 70)

    processor = DeepResearchProcessor(None)

    # 測試報告 - 不均勻的引用分佈
    test_report = """
    # Highly Cited Papers
    The seminal work [1][1][1][1][1] is foundational.

    # Moderately Cited
    Related studies [2][2][2] and [3][3] support this.

    # Single Citations
    Additional research [4][5][6][7] provides context.
    """

    test_references = [
        {'id': 1, 'title': 'Seminal Work', 'url': 'http://example1.com'},
        {'id': 2, 'title': 'Supporting Study 1', 'url': 'http://example2.com'},
        {'id': 3, 'title': 'Supporting Study 2', 'url': 'http://example3.com'},
        {'id': 4, 'title': 'Context Paper 1', 'url': 'http://example4.com'},
        {'id': 5, 'title': 'Context Paper 2', 'url': 'http://example5.com'},
        {'id': 6, 'title': 'Context Paper 3', 'url': 'http://example6.com'},
        {'id': 7, 'title': 'Context Paper 4', 'url': 'http://example7.com'},
        {'id': 8, 'title': 'Not Cited', 'url': 'http://example8.com'},
    ]

    cited_refs, uncited_refs, stats = processor._analyze_citations(test_report, test_references)

    print(f"\n📊 Citation Distribution:")
    print(f"  - Total citations: {stats['total_citations']}")
    print(f"  - Unique sources: {stats['unique_citations']}")
    print(f"  - Average: {stats['avg_citations_per_source']:.2f} citations/source")

    print(f"\n🏆 Top 5 Most Cited:")
    for ref_id, count in stats['most_cited']:
        title = next(r['title'] for r in test_references if r['id'] == ref_id)
        print(f"  [{ref_id}] {title}: {count} times")

    print(f"\n📈 Full Distribution:")
    for ref_id, count in sorted(stats['citation_distribution'].items(), key=lambda x: x[1], reverse=True):
        title = next(r['title'] for r in test_references if r['id'] == ref_id)
        bar = "█" * count
        print(f"  [{ref_id:2d}] {bar} ({count})")

    # 驗證
    assert stats['total_citations'] == 14, "Should have 14 total citations"
    assert stats['unique_citations'] == 7, "Should have 7 unique citations"
    assert stats['most_cited'][0] == (1, 5), "Ref [1] should be most cited with 5 citations"
    assert stats['most_cited'][1] == (2, 3), "Ref [2] should be second with 3 citations"

    print("\n✅ Test 3 PASSED!")


def test_formatted_output():
    """測試格式化輸出"""
    print("\n" + "=" * 70)
    print("Test 4: Enhanced Formatted Output")
    print("=" * 70)

    processor = DeepResearchProcessor(None)

    test_report = """
    ## Research Summary
    Multiple studies [1][2][3] demonstrate effectiveness.
    Key findings [1][4] are significant.
    """

    test_references = [
        {'id': 1, 'title': 'Primary Study', 'url': 'http://example1.com', 'query': 'main research'},
        {'id': 2, 'title': 'Supporting Study', 'url': 'http://example2.com'},
        {'id': 3, 'title': 'Related Work', 'url': 'http://example3.com'},
        {'id': 4, 'title': 'Key Findings', 'url': 'http://example4.com'},
        {'id': 5, 'title': 'Background Paper', 'url': 'http://example5.com'},
    ]

    cited_refs, uncited_refs, stats = processor._analyze_citations(test_report, test_references)
    formatted = processor._format_report_with_categorized_references(
        test_report, cited_refs, uncited_refs, citation_stats=stats
    )

    print(f"\n📄 Formatted Report Preview:")
    print("-" * 70)

    # 顯示引用統計部分
    stats_start = formatted.find("## 📊 引用統計")
    if stats_start > -1:
        print(formatted[stats_start:stats_start+1000])

    # 驗證格式化輸出包含所需元素
    assert "📚 參考文獻 (Cited References)" in formatted
    assert "📖 相關文獻 (Related Sources - Not Cited)" in formatted
    assert "📊 引用統計 (Citation Statistics)" in formatted
    assert "基本指標" in formatted
    assert "引用深度分析" in formatted
    assert "總引用次數" in formatted
    assert "平均每篇文獻被引用" in formatted
    assert "最常引用" in formatted
    assert "×2" in formatted  # Citation count indicator for ref [1]

    print("\n✅ Test 4 PASSED!")


def main():
    """執行所有測試"""
    print("\n" + "🚀" * 35)
    print("Enhanced Citation Statistics Test Suite")
    print("增強版引用統計測試套件")
    print("🚀" * 35)

    try:
        test_basic_citation_analysis()
        test_invalid_citations()
        test_citation_distribution()
        test_formatted_output()

        print("\n" + "=" * 70)
        print("🎉 ALL TESTS PASSED! 所有測試通過！")
        print("=" * 70)

        print("\n✅ 增強功能驗證完成：")
        print("  ✓ 引用次數追蹤")
        print("  ✓ 無效引用檢測")
        print("  ✓ 引用分佈分析")
        print("  ✓ 最常引用排名")
        print("  ✓ 詳細統計輸出")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
