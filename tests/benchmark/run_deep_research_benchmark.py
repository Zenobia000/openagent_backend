#!/usr/bin/env python3
"""
V.1 End-to-End Quality Benchmark — Deep Research Enhancement

Runs the benchmark query through the real deep research pipeline,
measures quality metrics, and compares against Google Deep Research targets.
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


BENCHMARK_QUERY = "2026年藍領垂直領域平台服務轉型報告"

# Google Deep Research targets (from gap_analysis)
TARGETS = {
    "word_count": 3000,       # Google: ~6000, our target: >=3000
    "citation_count": 15,     # Google: 30+, our target: >=15
    "table_count": 3,         # Google: 5, our target: >=3
    "domain_count": 3,        # Google: 4+, our target: >=3
    "section_count": 5,       # Minimum meaningful sections
}


def analyze_report(report: str, metadata: dict) -> dict:
    """Extract quality metrics from the generated report."""

    # Word count (mixed CJK + English)
    cjk_chars = len(re.findall(r'[\u4e00-\u9fff]', report))
    english_words = len(re.findall(r'[a-zA-Z]+', report))
    # Rough estimate: 1 CJK char ≈ 0.66 English words for length comparison
    effective_word_count = int(cjk_chars * 0.66 + english_words)
    raw_char_count = len(report)

    # Citations [N]
    citations = re.findall(r'\[(\d+)\]', report)
    unique_citations = set(citations)

    # Tables (markdown tables: lines with |)
    table_lines = [l for l in report.split('\n') if '|' in l and '--' not in l]
    # Count distinct table blocks (groups of consecutive | lines)
    table_count = 0
    in_table = False
    for line in report.split('\n'):
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                table_count += 1
                in_table = True
        else:
            in_table = False

    # Sections (## headings)
    sections = re.findall(r'^#{1,3}\s+(.+)$', report, re.MULTILINE)

    # Domain coverage — check for cross-domain keywords
    domain_keywords = {
        "technology": ["AI", "技術", "平台", "SaaS", "SaaP", "數位", "數據", "演算法", "自動化"],
        "business": ["營收", "商業模式", "市場", "市佔率", "獲利", "客戶", "競爭", "市值"],
        "labor/workforce": ["藍領", "勞動", "人力", "招聘", "技能", "薪資", "就業", "工人"],
        "regulation": ["法規", "政策", "合規", "監管", "勞基法", "隱私", "ESG"],
        "economics": ["經濟", "成長率", "GDP", "通膨", "投資", "融資", "估值"],
    }

    domains_covered = []
    for domain, keywords in domain_keywords.items():
        if any(kw in report for kw in keywords):
            domains_covered.append(domain)

    # Research domains from metadata
    research_domains = metadata.get("research_domains", [])
    iterations = metadata.get("workflow_state", {}).get("iterations", 0)
    synthesis_history = metadata.get("synthesis_history", [])

    return {
        "raw_char_count": raw_char_count,
        "effective_word_count": effective_word_count,
        "total_citations": len(citations),
        "unique_citations": len(unique_citations),
        "table_count": table_count,
        "section_count": len(sections),
        "sections": sections[:15],
        "domains_covered": domains_covered,
        "domain_count": len(domains_covered),
        "research_domains": research_domains,
        "iterations": iterations,
        "synthesis_rounds": len(synthesis_history),
    }


def print_scorecard(metrics: dict, duration_s: float):
    """Print quality scorecard with pass/fail against targets."""

    print("\n" + "=" * 70)
    print("  V.1 DEEP RESEARCH BENCHMARK — QUALITY SCORECARD")
    print("=" * 70)

    checks = [
        ("Word Count", metrics["effective_word_count"], TARGETS["word_count"], ">="),
        ("Unique Citations", metrics["unique_citations"], TARGETS["citation_count"], ">="),
        ("Tables", metrics["table_count"], TARGETS["table_count"], ">="),
        ("Domains Covered", metrics["domain_count"], TARGETS["domain_count"], ">="),
        ("Sections", metrics["section_count"], TARGETS["section_count"], ">="),
    ]

    passed = 0
    total = len(checks)

    print(f"\n{'Metric':<22} {'Actual':>8} {'Target':>8} {'Status':>8}")
    print("-" * 50)

    for name, actual, target, op in checks:
        ok = actual >= target if op == ">=" else actual == target
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"  {name:<20} {actual:>8} {target:>8}    {status}")

    print("-" * 50)
    print(f"  {'Score':<20} {passed}/{total}")
    print(f"  {'Duration':<20} {duration_s:.1f}s")
    print(f"  {'Raw Chars':<20} {metrics['raw_char_count']:,}")
    print(f"  {'Iterations':<20} {metrics['iterations']}")
    print(f"  {'Synthesis Rounds':<20} {metrics['synthesis_rounds']}")

    print(f"\n  Research Domains: {', '.join(metrics.get('research_domains', []) or ['(none)'])}")
    print(f"  Content Domains:  {', '.join(metrics['domains_covered'])}")

    print(f"\n  Sections:")
    for s in metrics["sections"]:
        print(f"    - {s}")

    print("\n" + "=" * 70)
    return passed, total


async def run_benchmark():
    """Execute the full deep research benchmark."""

    print(f"[Benchmark] Query: {BENCHMARK_QUERY}")
    print(f"[Benchmark] Initializing services...")

    # Import after path setup
    from core.service_initializer import ServiceInitializer
    from core.processors.research.processor import DeepResearchProcessor
    from core.processors.research.config import SearchEngineConfig
    from core.models_v2 import ProcessingContext, Modes, Request, Response
    from services.llm import create_llm_client

    # Create LLM client
    llm_client = create_llm_client()
    print(f"[Benchmark] LLM: {llm_client.provider_name} ({getattr(llm_client, 'model', 'unknown')})")

    # Initialize services
    initializer = ServiceInitializer()
    services = await initializer.initialize_all()
    print(f"[Benchmark] Services: {list(services.keys())}")

    # Create processor with search config
    search_config = SearchEngineConfig()
    processor = DeepResearchProcessor(
        llm_client=llm_client,
        services=services,
        search_config=search_config,
    )

    # Create context
    req = Request(query=BENCHMARK_QUERY, mode=Modes.DEEP_RESEARCH)
    resp = Response(result="", mode=Modes.DEEP_RESEARCH, trace_id=req.trace_id)
    context = ProcessingContext(request=req, response=resp)

    # Execute
    print(f"[Benchmark] Starting deep research pipeline...")
    start = time.time()
    result = await processor.process(context)
    duration = time.time() - start
    print(f"[Benchmark] Pipeline complete in {duration:.1f}s")

    # Analyze
    metrics = analyze_report(result, context.response.metadata)

    # Save report
    output_dir = PROJECT_ROOT / "tests" / "benchmark" / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "benchmark_report.md"
    report_path.write_text(result, encoding="utf-8")
    print(f"[Benchmark] Report saved: {report_path}")

    metrics_path = output_dir / "benchmark_metrics.json"
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[Benchmark] Metrics saved: {metrics_path}")

    # Scorecard
    passed, total = print_scorecard(metrics, duration)

    return passed, total


if __name__ == "__main__":
    passed, total = asyncio.run(run_benchmark())
    sys.exit(0 if passed >= 3 else 1)  # Pass if at least 3/5 targets met
