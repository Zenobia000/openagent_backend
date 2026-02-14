#!/usr/bin/env python
"""
Test script for verifying reference categorization in DeepResearchProcessor
測試 DeepResearchProcessor 的參考文獻分類功能
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.processor import DeepResearchProcessor
from core.models_v2 import ProcessingContext, Request
from core.errors import ErrorClassifier


async def test_reference_categorization():
    """測試參考文獻的引用分類功能"""
    print("=" * 60)
    print("Testing Reference Categorization in Deep Research")
    print("=" * 60)

    # 創建處理器實例（模擬模式）
    processor = DeepResearchProcessor(
        llm_client=None,
        services={}
    )

    # 測試案例：研究 AI 發展趨勢
    test_query = "分析人工智慧在醫療領域的最新應用與未來發展趨勢"

    context = ProcessingContext(
        request=Request(query=test_query)
    )

    try:
        print(f"\n📝 Research Query: {test_query}")
        print("-" * 50)

        # 執行深度研究
        result = await processor.process(context)

        # 驗證結果
        print("\n✅ Research completed successfully!")
        print("-" * 50)

        # 檢查是否包含引用分類
        if "📚 參考文獻 (Cited References)" in result:
            print("✓ Found cited references section")
        else:
            print("✗ Cited references section missing")

        if "📖 相關文獻 (Related Sources - Not Cited)" in result:
            print("✓ Found uncited sources section")
        else:
            print("✗ Uncited sources section missing")

        if "📊 引用統計 (Citation Statistics)" in result:
            print("✓ Found citation statistics")
        else:
            print("✗ Citation statistics missing")

        # 解析引用統計
        import re
        cited_match = re.search(r"實際引用文獻:\s*(\d+)", result)
        uncited_match = re.search(r"相關未引用文獻:\s*(\d+)", result)
        citation_rate = re.search(r"引用率:\s*([\d.]+)%", result)

        if cited_match and uncited_match and citation_rate:
            cited_count = int(cited_match.group(1))
            uncited_count = int(uncited_match.group(1))
            rate = float(citation_rate.group(1))

            print(f"\n📊 Citation Statistics:")
            print(f"  - Cited references: {cited_count}")
            print(f"  - Uncited references: {uncited_count}")
            print(f"  - Citation rate: {rate}%")
            print(f"  - Total sources: {cited_count + uncited_count}")

        # 檢查 workflow state
        if "workflow_state" in context.intermediate_results:
            state = context.intermediate_results["workflow_state"]
            print(f"\n🔄 Workflow Statistics:")
            print(f"  - Status: {state.get('status')}")
            print(f"  - Iterations: {state.get('iterations', 0)}")
            print(f"  - Steps completed: {state.get('steps', [])}")

        # 輸出報告摘要
        print("\n📑 Report Preview (first 500 chars):")
        print("-" * 50)
        print(result[:500] + "...")

        # 輸出參考文獻部分預覽
        ref_section_start = result.find("## 📚 參考文獻")
        if ref_section_start > -1:
            print("\n📚 References Section Preview:")
            print("-" * 50)
            print(result[ref_section_start:ref_section_start+800] + "...")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        error_category = ErrorClassifier.classify(e)
        print(f"Error Category: {error_category}")

        # 打印錯誤詳情
        if hasattr(e, 'error_context'):
            print(f"Error Context: {e.error_context}")

        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("Test Completed Successfully! ✅")
    print("=" * 60)
    return True


async def test_citation_analysis():
    """測試引用分析功能"""
    print("\n" + "=" * 60)
    print("Testing Citation Analysis Function")
    print("=" * 60)

    # 創建測試用的處理器
    processor = DeepResearchProcessor(None)

    # 測試報告文本
    test_report = """
    ## Introduction

    Recent advances in AI have shown remarkable progress [1]. Machine learning
    techniques, particularly deep learning [2], have revolutionized many fields.

    ## Medical Applications

    AI is being used for disease diagnosis [3] and drug discovery [4][5].
    Some promising applications include medical imaging [1] and patient monitoring.

    ## Future Trends

    Experts predict continued growth [6] in AI applications.
    """

    # 測試參考文獻列表
    test_references = [
        {'id': 1, 'title': 'AI Progress Report 2024', 'url': 'http://example1.com'},
        {'id': 2, 'title': 'Deep Learning Review', 'url': 'http://example2.com'},
        {'id': 3, 'title': 'AI in Diagnosis', 'url': 'http://example3.com'},
        {'id': 4, 'title': 'Drug Discovery with ML', 'url': 'http://example4.com'},
        {'id': 5, 'title': 'Pharmaceutical AI', 'url': 'http://example5.com'},
        {'id': 6, 'title': 'Future of AI', 'url': 'http://example6.com'},
        {'id': 7, 'title': 'Uncited Paper 1', 'url': 'http://example7.com'},
        {'id': 8, 'title': 'Uncited Paper 2', 'url': 'http://example8.com'},
    ]

    # 分析引用（增強版）
    cited_refs, uncited_refs, citation_stats = processor._analyze_citations(test_report, test_references)

    print(f"\n📊 Basic Analysis Results:")
    print(f"  - Cited references: {len(cited_refs)}")
    print(f"  - Uncited references: {len(uncited_refs)}")

    print(f"\n📈 Enhanced Statistics:")
    print(f"  - Total citations: {citation_stats['total_citations']}")
    print(f"  - Unique citations: {citation_stats['unique_citations']}")
    print(f"  - Avg citations per source: {citation_stats['avg_citations_per_source']:.1f}")
    print(f"  - Invalid citations: {citation_stats['invalid_citations']}")

    print(f"\n🏆 Most Cited (Top 5):")
    for ref_id, count in citation_stats['most_cited']:
        ref_title = next((r['title'] for r in test_references if r['id'] == ref_id), 'Unknown')
        print(f"  [{ref_id}] {ref_title} - {count} times")

    print(f"\n✅ Cited References (sorted by citation count):")
    for ref in cited_refs:
        citation_count = ref.get('citation_count', 0)
        print(f"  [{ref['id']}] {ref['title']} (×{citation_count})")

    print(f"\n📖 Uncited References:")
    for ref in uncited_refs:
        print(f"  • {ref['title']}")

    # 格式化完整報告（增強版）
    formatted_report = processor._format_report_with_categorized_references(
        test_report, cited_refs, uncited_refs, citation_stats=citation_stats
    )

    print(f"\n📑 Formatted Report Length: {len(formatted_report)} chars")

    # 驗證格式
    assert "📚 參考文獻 (Cited References)" in formatted_report
    assert "📖 相關文獻 (Related Sources - Not Cited)" in formatted_report
    assert "📊 引用統計 (Citation Statistics)" in formatted_report

    print("\n✅ Citation Analysis Test Passed!")
    return True


async def main():
    """主測試函數"""
    print("\n🚀 Starting Reference Categorization Tests")
    print("=" * 80)

    # Test 1: 引用分析功能
    test1_result = await test_citation_analysis()

    # Test 2: 完整的深度研究流程
    print("\n" + "=" * 80)
    print("Note: Full deep research test requires real LLM services")
    print("Skipping full integration test in mock mode...")
    # test2_result = await test_reference_categorization()

    print("\n" + "=" * 80)
    print("🎉 All Tests Completed!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())