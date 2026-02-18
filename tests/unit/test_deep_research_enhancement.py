"""
TDD Tests for Deep Research Enhancement — Phase 1 + Phase 2 + Phase 3

Phase 1: Info retention, prompt constraints, query dedup, dead code cleanup
Phase 2: Intermediate synthesis, structured completeness review, critical analysis always-on
Phase 3: Full-content extraction, domain-aware search strategy
"""

import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.processors.research.processor import DeepResearchProcessor
from core.models_v2 import ProcessingContext, Modes, Request, Response
from core.prompts import PromptTemplates
from core.logger import structured_logger


# ========== Fixtures ==========

@pytest.fixture
def mock_llm():
    client = AsyncMock()
    client.generate = AsyncMock(return_value="test response")
    client.model_name = "test-model"
    return client


@pytest.fixture
def processor(mock_llm):
    return DeepResearchProcessor(mock_llm)


@pytest.fixture
def deep_context():
    req = Request(query="2026年藍領垂直領域平台服務轉型報告", mode=Modes.DEEP_RESEARCH)
    resp = Response(result="", mode=Modes.DEEP_RESEARCH, trace_id=req.trace_id)
    return ProcessingContext(request=req, response=resp)


@pytest.fixture
def sample_search_results():
    """12 search results — tests that ALL are used, not just first 5."""
    return [
        {
            'query': f'query_{i}',
            'goal': f'goal_{i}',
            'priority': 1,
            'result': {
                'summary': f'Summary for query {i} ' * 20,
                'sources': [{'url': f'https://example.com/{i}', 'title': f'Source {i}', 'relevance': 0.9}],
                'processed': f'Processed findings for query {i} ' * 20,
            },
            'results': f'Raw content for query {i} that must be preserved in full without truncation ' * 10,
        }
        for i in range(12)
    ]


@pytest.fixture
def sample_references():
    """35 references — tests that ALL are used, not capped at 20."""
    return [
        {'id': i, 'title': f'Reference Title {i}', 'url': f'https://ref.com/{i}',
         'query': f'q{i}', 'relevance': 0.8}
        for i in range(1, 36)
    ]


@pytest.fixture
def mock_logger_ctx():
    """Patches structured_logger methods to prevent side effects."""
    with patch.object(structured_logger, 'info'), \
         patch.object(structured_logger, 'debug'), \
         patch.object(structured_logger, 'error'), \
         patch.object(structured_logger, 'warning'), \
         patch.object(structured_logger, 'progress'), \
         patch.object(structured_logger, 'message'), \
         patch.object(structured_logger, 'reasoning'), \
         patch.object(structured_logger, 'log_llm_call'), \
         patch.object(structured_logger, 'log_tool_decision'), \
         patch.object(structured_logger, 'save_response_as_markdown', return_value="/tmp/test.md"):
        yield


# ========== Phase 1.1: Information Retention ==========

class TestInformationRetention:
    """_summarize_search_results must use ALL results without truncation."""

    def test_summarize_uses_all_results(self, processor, sample_search_results):
        result = processor._summarize_search_results(sample_search_results)
        # All 12 results should appear
        for i in range(12):
            assert f'query_{i}' in result, f"query_{i} missing from summary"

    def test_summarize_no_truncation(self, processor):
        long_content = "A" * 500
        results = [{'query': 'test', 'results': long_content}]
        summary = processor._summarize_search_results(results)
        # Full content preserved
        assert long_content in summary

    def test_summarize_no_ellipsis_for_full_content(self, processor):
        content = "Complete content here"
        results = [{'query': 'test', 'results': content}]
        summary = processor._summarize_search_results(results)
        assert content in summary

    def test_report_prompt_uses_all_references(self, processor, sample_references):
        prompt = processor._build_academic_report_prompt(
            plan="test plan", context="test context",
            references=sample_references, requirement="test"
        )
        # Reference 35 (beyond old cap of 20) must be present
        assert "[35]" in prompt
        assert "Reference Title 35" in prompt

    def test_report_prompt_reference_30_present(self, processor, sample_references):
        prompt = processor._build_academic_report_prompt(
            plan="plan", context="ctx",
            references=sample_references, requirement="req"
        )
        assert "[30]" in prompt


# ========== Phase 1.2: Report Prompt Structure Constraints ==========

class TestReportPromptConstraints:
    """Report prompt must enforce tables, word count, forward-looking, cross-domain."""

    def _get_prompt(self, processor, refs=None):
        refs = refs or [{'id': 1, 'title': 'T', 'url': 'u', 'query': 'q', 'relevance': 0.8}]
        return processor._build_academic_report_prompt(
            plan="plan", context="ctx", references=refs, requirement="req"
        )

    def test_requires_comparison_tables(self, processor):
        prompt = self._get_prompt(processor)
        assert "comparison table" in prompt.lower() or "structured comparison" in prompt.lower()

    def test_requires_3000_words(self, processor):
        prompt = self._get_prompt(processor)
        assert "3000" in prompt

    def test_requires_forward_looking(self, processor):
        prompt = self._get_prompt(processor)
        assert "forward-looking" in prompt.lower() or "trend prediction" in prompt.lower()

    def test_requires_cross_domain(self, processor):
        prompt = self._get_prompt(processor)
        assert "cross-domain" in prompt.lower()

    def test_requires_specific_examples(self, processor):
        prompt = self._get_prompt(processor)
        p = prompt.lower()
        assert "specific" in p and ("company" in p or "example" in p or "product" in p)

    def test_requires_actionable_recommendations(self, processor):
        prompt = self._get_prompt(processor)
        p = prompt.lower()
        assert "actionable" in p or "recommendation" in p


# ========== Phase 1.3: Query Deduplication ==========

class TestQueryDeduplication:
    """Follow-up queries must receive and use executed_queries for dedup."""

    @pytest.mark.asyncio
    async def test_followup_accepts_executed_queries_param(self, processor, deep_context, mock_logger_ctx):
        """Should not raise TypeError for executed_queries parameter."""
        processor.llm_client.generate = AsyncMock(return_value='```json\n[]\n```')
        result = await processor._generate_followup_queries(
            context=deep_context,
            report_plan="test plan",
            existing_results=[],
            executed_queries=["q1", "q2"]
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_dedup_notice_appears_in_prompt(self, processor, deep_context, mock_logger_ctx):
        """Executed queries must appear in the LLM prompt as dedup notice."""
        captured = []

        async def capture(prompt, **kw):
            captured.append(prompt)
            return '```json\n[]\n```'

        processor.llm_client.generate = capture

        await processor._generate_followup_queries(
            context=deep_context,
            report_plan="test plan",
            existing_results=[],
            executed_queries=["already searched alpha", "already searched beta"]
        )

        assert len(captured) > 0
        assert "already searched alpha" in captured[0]
        assert "already searched beta" in captured[0]

    @pytest.mark.asyncio
    async def test_no_dedup_when_no_executed_queries(self, processor, deep_context, mock_logger_ctx):
        """When executed_queries is empty, no dedup notice should appear."""
        captured = []

        async def capture(prompt, **kw):
            captured.append(prompt)
            return '```json\n[]\n```'

        processor.llm_client.generate = capture

        await processor._generate_followup_queries(
            context=deep_context,
            report_plan="test plan",
            existing_results=[],
            executed_queries=[]
        )

        assert len(captured) > 0
        # No dedup keywords
        assert "already been executed" not in captured[0].lower() or "executed_queries" not in captured[0]


# ========== Phase 1.4: Dead Code Cleanup ==========

class TestDeadCodeCleanup:
    """Workflow must NOT call _should_clarify or _ask_clarifying_questions."""

    @pytest.mark.asyncio
    async def test_workflow_skips_clarification(self, mock_llm, deep_context, mock_logger_ctx):
        processor = DeepResearchProcessor(mock_llm)

        # Pipeline: plan → domains → SERP → search → synthesis → review → critical → final
        mock_llm.generate = AsyncMock(side_effect=[
            "Plan",
            '{"domains": []}',
            '```json\n[{"query": "test", "researchGoal": "g", "priority": 1}]\n```',
            "Search result from model",
            '{"synthesis": "s", "section_coverage": {}, "knowledge_gaps": [], "cross_domain_links": []}',
            '{"is_sufficient": true, "overall_coverage": 90, "sections": [], "priority_gaps": []}',
            "Critical analysis result",
            "Final report",
        ])

        with patch.object(processor, '_should_clarify') as mock_sc, \
             patch.object(processor, '_ask_clarifying_questions') as mock_aq:
            await processor.process(deep_context)
            mock_sc.assert_not_called()
            mock_aq.assert_not_called()


# ========== Phase 2.1: Intermediate Synthesis ==========

class TestIntermediateSynthesis:
    """Progressive synthesis must exist and be called in the search loop."""

    def test_prompt_template_exists(self):
        assert hasattr(PromptTemplates, 'get_intermediate_synthesis_prompt')

    def test_prompt_includes_query(self):
        prompt = PromptTemplates.get_intermediate_synthesis_prompt(
            query="quantum computing",
            report_plan="plan sections",
            wave_results="search findings",
            previous_synthesis=None,
        )
        assert "quantum computing" in prompt

    def test_prompt_includes_previous_synthesis(self):
        prompt = PromptTemplates.get_intermediate_synthesis_prompt(
            query="q", report_plan="p", wave_results="w",
            previous_synthesis="Previously we learned that X is true",
        )
        assert "Previously we learned that X is true" in prompt

    def test_prompt_without_previous_synthesis(self):
        prompt = PromptTemplates.get_intermediate_synthesis_prompt(
            query="q", report_plan="p", wave_results="w",
            previous_synthesis=None,
        )
        assert isinstance(prompt, str) and len(prompt) > 50

    def test_processor_has_method(self, processor):
        assert hasattr(processor, '_intermediate_synthesis')
        assert callable(getattr(processor, '_intermediate_synthesis'))

    @pytest.mark.asyncio
    async def test_synthesis_returns_dict(self, processor, deep_context, mock_logger_ctx):
        processor.llm_client.generate = AsyncMock(
            return_value='{"synthesis": "understood", "section_coverage": {}, "knowledge_gaps": [], "cross_domain_links": []}'
        )
        result = await processor._intermediate_synthesis(
            context=deep_context,
            report_plan="plan",
            wave_results=[{'query': 'q', 'result': {'summary': 's'}}],
            previous_synthesis=None,
        )
        assert isinstance(result, dict)
        assert "synthesis" in result

    @pytest.mark.asyncio
    async def test_synthesis_fallback_on_bad_json(self, processor, deep_context, mock_logger_ctx):
        processor.llm_client.generate = AsyncMock(return_value="Not valid JSON at all")
        result = await processor._intermediate_synthesis(
            context=deep_context,
            report_plan="plan",
            wave_results=[],
            previous_synthesis=None,
        )
        # Should not crash; return a dict with at least 'synthesis' key
        assert isinstance(result, dict)
        assert "synthesis" in result


# ========== Phase 2.2: Structured Completeness Review ==========

class TestStructuredCompletenessReview:
    """Completeness review must return (bool, dict) with structured gap report."""

    def test_prompt_template_exists(self):
        assert hasattr(PromptTemplates, 'get_completeness_review_prompt')

    def test_prompt_includes_plan(self):
        prompt = PromptTemplates.get_completeness_review_prompt(
            report_plan="Section 1: Intro\nSection 2: Analysis",
            section_coverage={"Intro": {"status": "covered"}},
            iteration=1,
            max_iterations=3,
        )
        assert "Section 1" in prompt

    @pytest.mark.asyncio
    async def test_review_returns_tuple(self, processor, deep_context, mock_logger_ctx):
        processor.llm_client.generate = AsyncMock(
            return_value='{"is_sufficient": true, "overall_coverage": 85, "sections": [], "priority_gaps": []}'
        )
        result = await processor._review_research_completeness(
            context=deep_context,
            report_plan="plan",
            search_results=[],
            iteration=1,
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        is_sufficient, gap_report = result
        assert isinstance(is_sufficient, bool)
        assert isinstance(gap_report, dict)

    @pytest.mark.asyncio
    async def test_review_detects_insufficient(self, processor, deep_context, mock_logger_ctx):
        processor.llm_client.generate = AsyncMock(
            return_value='{"is_sufficient": false, "overall_coverage": 40, "sections": [], "priority_gaps": ["need more data"]}'
        )
        is_sufficient, gap_report = await processor._review_research_completeness(
            context=deep_context,
            report_plan="plan",
            search_results=[],
            iteration=1,
        )
        assert is_sufficient is False
        assert "need more data" in gap_report.get("priority_gaps", [])

    @pytest.mark.asyncio
    async def test_review_fallback_on_bad_json(self, processor, deep_context, mock_logger_ctx):
        processor.llm_client.generate = AsyncMock(return_value="YES this is sufficient")
        is_sufficient, gap_report = await processor._review_research_completeness(
            context=deep_context,
            report_plan="plan",
            search_results=[],
            iteration=1,
        )
        # Fallback to YES/NO parsing
        assert is_sufficient is True
        assert isinstance(gap_report, dict)


# ========== Phase 2.3: Critical Analysis Always-On ==========

class TestCriticalAnalysisAlwaysOn:
    """Critical analysis must run unconditionally — no keyword gate."""

    @pytest.mark.asyncio
    async def test_critical_analysis_called_for_simple_query(self, mock_llm, mock_logger_ctx):
        """Even short/simple queries should trigger critical analysis."""
        req = Request(query="hello", mode=Modes.DEEP_RESEARCH)
        resp = Response(result="", mode=Modes.DEEP_RESEARCH, trace_id=req.trace_id)
        ctx = ProcessingContext(request=req, response=resp)

        processor = DeepResearchProcessor(mock_llm)

        mock_llm.generate = AsyncMock(side_effect=[
            "Plan",
            '{"domains": []}',
            '```json\n[{"query": "test", "researchGoal": "g", "priority": 1}]\n```',
            "Search result",
            '{"synthesis": "s", "section_coverage": {}, "knowledge_gaps": [], "cross_domain_links": []}',
            '{"is_sufficient": true}',
            "Critical analysis result",
            "Final report",
        ])

        with patch.object(processor, '_critical_analysis_stage',
                          wraps=processor._critical_analysis_stage) as mock_ca:
            await processor.process(ctx)
            mock_ca.assert_called_once()


# ========== Integration: Full Pipeline ==========

class TestFullPipelineIntegration:
    """End-to-end pipeline with all Phase 1+2 changes."""

    @pytest.mark.asyncio
    async def test_pipeline_with_all_enhancements(self, mock_llm, deep_context, mock_logger_ctx):
        processor = DeepResearchProcessor(mock_llm)

        mock_llm.generate = AsyncMock(side_effect=[
            "Comprehensive research plan with sections",          # 1. plan
            '{"domains": [{"name": "tech", "weight": 0.5, "search_angles": ["AI"]}, {"name": "labor", "weight": 0.5, "search_angles": ["workforce"]}]}',  # 2. domain identification
            '```json\n[{"query": "blue collar AI 2026", "researchGoal": "market trends", "priority": 1}]\n```',  # 3. SERP
            "Detailed search findings about blue collar AI transformation",  # 4. model search
            '{"synthesis": "Blue collar AI is transforming via SaaP model", "section_coverage": {"market": {"status": "covered"}}, "knowledge_gaps": [], "cross_domain_links": ["tech-business"]}',  # 5. synthesis
            '{"is_sufficient": true, "overall_coverage": 85, "sections": [], "priority_gaps": []}',  # 6. review
            "Multi-perspective critical analysis of blue collar transformation",  # 7. critical analysis
            "Final comprehensive report on blue collar AI transformation with tables and analysis",  # 8. final report
        ])

        result = await processor.process(deep_context)

        assert isinstance(result, str)
        assert len(result) > 0
        # Verify workflow completed
        assert deep_context.response.metadata["workflow_state"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_pipeline_multi_iteration(self, mock_llm, deep_context, mock_logger_ctx):
        """Test that insufficient review triggers follow-up iteration."""
        processor = DeepResearchProcessor(mock_llm)

        mock_llm.generate = AsyncMock(side_effect=[
            "Plan",                                                          # 1. plan
            '{"domains": []}',                                               # 2. domain identification
            '```json\n[{"query": "q1", "researchGoal": "g1", "priority": 1}]\n```',  # 3. SERP iter 1
            "Search result iter 1",                                          # 4. model search
            '{"synthesis": "partial understanding", "section_coverage": {}, "knowledge_gaps": ["gap1"], "cross_domain_links": []}',  # 5. synthesis
            '{"is_sufficient": false, "overall_coverage": 40, "sections": [], "priority_gaps": ["need gap1 data"]}',  # 6. review → NOT sufficient
            '```json\n[{"query": "q2 followup", "researchGoal": "fill gap1", "priority": 1}]\n```',  # 7. followup queries
            "Search result iter 2",                                          # 8. model search iter 2
            '{"synthesis": "complete understanding", "section_coverage": {}, "knowledge_gaps": [], "cross_domain_links": []}',  # 9. synthesis
            '{"is_sufficient": true, "overall_coverage": 90, "sections": [], "priority_gaps": []}',  # 10. review → sufficient
            "Critical analysis across iterations",                           # 11. critical analysis
            "Final report synthesizing both iterations",                     # 12. final report
        ])

        result = await processor.process(deep_context)
        assert isinstance(result, str)
        assert deep_context.response.metadata["workflow_state"]["iterations"] == 2


# ========== Phase 3.1: Full-content Extraction ==========

class TestFullContentExtraction:
    """Processor should enrich search results with full page content via search service."""

    def test_processor_has_enrich_method(self, processor):
        """_enrich_with_full_content method must exist."""
        assert hasattr(processor, '_enrich_with_full_content')
        assert callable(getattr(processor, '_enrich_with_full_content'))

    @pytest.mark.asyncio
    async def test_enrich_calls_fetch_multiple(self, mock_llm):
        """Should call search_service.fetch_multiple() with top URLs."""
        mock_search = AsyncMock()
        mock_search.fetch_multiple = AsyncMock(return_value={
            "https://example.com/1": "Full content of page 1",
            "https://example.com/2": "Full content of page 2",
        })

        processor = DeepResearchProcessor(mock_llm, services={"search": mock_search})

        search_result = {
            'summary': 'test summary',
            'sources': [
                {'url': 'https://example.com/1', 'title': 'Page 1', 'relevance': 0.9},
                {'url': 'https://example.com/2', 'title': 'Page 2', 'relevance': 0.8},
                {'url': 'https://example.com/3', 'title': 'Page 3', 'relevance': 0.7},
            ],
            'relevance': 0.85,
        }

        enriched = await processor._enrich_with_full_content(search_result)
        mock_search.fetch_multiple.assert_called_once()
        # Check URLs were passed
        call_args = mock_search.fetch_multiple.call_args
        urls_passed = call_args[0][0] if call_args[0] else call_args[1].get('urls', [])
        assert 'https://example.com/1' in urls_passed
        assert 'https://example.com/2' in urls_passed

    @pytest.mark.asyncio
    async def test_enrich_stores_full_content(self, mock_llm):
        """Enriched result must contain full_content field with fetched text."""
        mock_search = AsyncMock()
        mock_search.fetch_multiple = AsyncMock(return_value={
            "https://a.com": "Article about AI trends in 2026 with detailed statistics...",
        })

        processor = DeepResearchProcessor(mock_llm, services={"search": mock_search})

        search_result = {
            'summary': 'snippet',
            'sources': [{'url': 'https://a.com', 'title': 'AI', 'relevance': 0.9}],
            'relevance': 0.9,
        }

        enriched = await processor._enrich_with_full_content(search_result)
        assert 'full_content' in enriched
        assert 'AI trends' in enriched['full_content']

    @pytest.mark.asyncio
    async def test_enrich_graceful_without_search_service(self, mock_llm):
        """Without search service, enrichment should return result unchanged."""
        processor = DeepResearchProcessor(mock_llm, services={})

        search_result = {
            'summary': 'snippet',
            'sources': [{'url': 'https://a.com', 'title': 'AI', 'relevance': 0.9}],
        }

        enriched = await processor._enrich_with_full_content(search_result)
        assert enriched == search_result  # unchanged
        assert 'full_content' not in enriched

    @pytest.mark.asyncio
    async def test_enrich_graceful_on_fetch_error(self, mock_llm):
        """If fetch_multiple fails, result should still be returned intact."""
        mock_search = AsyncMock()
        mock_search.fetch_multiple = AsyncMock(side_effect=Exception("Network timeout"))

        processor = DeepResearchProcessor(mock_llm, services={"search": mock_search})

        search_result = {
            'summary': 'snippet',
            'sources': [{'url': 'https://a.com', 'title': 'AI', 'relevance': 0.9}],
        }

        enriched = await processor._enrich_with_full_content(search_result)
        # Should return original on failure, no crash
        assert enriched['summary'] == 'snippet'

    @pytest.mark.asyncio
    async def test_enrich_limits_urls(self, mock_llm):
        """Should only fetch top N URLs by relevance, not all."""
        mock_search = AsyncMock()
        mock_search.fetch_multiple = AsyncMock(return_value={})

        processor = DeepResearchProcessor(mock_llm, services={"search": mock_search})

        # 15 sources — should NOT fetch all 15
        search_result = {
            'summary': 'test',
            'sources': [
                {'url': f'https://example.com/{i}', 'title': f'P{i}', 'relevance': 0.9 - i*0.01}
                for i in range(15)
            ],
        }

        await processor._enrich_with_full_content(search_result)
        call_args = mock_search.fetch_multiple.call_args
        urls_passed = call_args[0][0] if call_args[0] else call_args[1].get('urls', [])
        assert len(urls_passed) <= 5  # should cap at top 5

    @pytest.mark.asyncio
    async def test_enrich_integrates_in_search_task(self, mock_llm, mock_logger_ctx):
        """_execute_single_search_task should call _enrich_with_full_content."""
        mock_search = AsyncMock()
        mock_search.fetch_multiple = AsyncMock(return_value={
            "https://a.com": "Full article text...",
        })

        processor = DeepResearchProcessor(mock_llm, services={"search": mock_search})

        # Mock the deep search to return a basic result
        processor._perform_parallel_deep_search = AsyncMock(return_value={
            'summary': 'snippet',
            'sources': [{'url': 'https://a.com', 'title': 'Test', 'relevance': 0.9}],
            'relevance': 0.9,
        })

        result = await processor._execute_single_search_task(
            1, {'query': 'test', 'researchGoal': 'goal', 'priority': 1},
            'test', 'goal', 1
        )

        # The result should have gone through enrichment
        assert result['result'].get('full_content') is not None or \
               mock_search.fetch_multiple.called


# ========== Phase 3.2: Domain-aware Search Strategy ==========

class TestDomainAwareSearch:
    """Research should identify domains and distribute queries across them."""

    def test_domain_prompt_template_exists(self):
        """PromptTemplates must have get_domain_identification_prompt."""
        assert hasattr(PromptTemplates, 'get_domain_identification_prompt')
        prompt = PromptTemplates.get_domain_identification_prompt(
            query="AI agent market analysis",
            report_plan="1. Market overview\n2. Technology stack\n3. Business models"
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_domain_prompt_includes_query(self):
        """Domain prompt must include the research query."""
        prompt = PromptTemplates.get_domain_identification_prompt(
            query="blockchain in supply chain",
            report_plan="test plan"
        )
        assert "blockchain" in prompt.lower() or "supply chain" in prompt.lower()

    def test_domain_prompt_requests_json(self):
        """Domain prompt must request JSON output with domains array."""
        prompt = PromptTemplates.get_domain_identification_prompt(
            query="test query",
            report_plan="test plan"
        )
        assert "json" in prompt.lower() or "JSON" in prompt

    def test_processor_has_identify_domains_method(self, processor):
        """_identify_research_domains method must exist."""
        assert hasattr(processor, '_identify_research_domains')
        assert callable(getattr(processor, '_identify_research_domains'))

    @pytest.mark.asyncio
    async def test_identify_domains_returns_list(self, mock_llm, mock_logger_ctx):
        """_identify_research_domains should return a list of domain dicts."""
        mock_llm.generate = AsyncMock(return_value=json.dumps({
            "domains": [
                {"name": "technology", "weight": 0.4, "search_angles": ["AI frameworks", "LLM benchmarks"]},
                {"name": "business", "weight": 0.3, "search_angles": ["market size", "revenue models"]},
                {"name": "regulation", "weight": 0.3, "search_angles": ["AI policy", "data privacy"]},
            ]
        }))

        processor = DeepResearchProcessor(mock_llm)
        deep_context = ProcessingContext(
            request=Request(query="AI governance report", mode=Modes.DEEP_RESEARCH),
            response=Response(result="", mode=Modes.DEEP_RESEARCH, trace_id="test")
        )

        domains = await processor._identify_research_domains(deep_context, "plan")
        assert isinstance(domains, list)
        assert len(domains) >= 2
        assert all('name' in d for d in domains)
        assert all('search_angles' in d for d in domains)

    @pytest.mark.asyncio
    async def test_identify_domains_fallback_on_bad_json(self, mock_llm, mock_logger_ctx):
        """Bad JSON should return a sensible fallback, not crash."""
        mock_llm.generate = AsyncMock(return_value="I think the domains are technology and business")

        processor = DeepResearchProcessor(mock_llm)
        deep_context = ProcessingContext(
            request=Request(query="test", mode=Modes.DEEP_RESEARCH),
            response=Response(result="", mode=Modes.DEEP_RESEARCH, trace_id="test")
        )

        domains = await processor._identify_research_domains(deep_context, "plan")
        assert isinstance(domains, list)
        # Fallback should still return something usable (possibly empty or general)

    @pytest.mark.asyncio
    async def test_domains_passed_to_serp_generation(self, mock_llm, mock_logger_ctx):
        """_generate_serp_queries should accept and use domain info."""
        mock_llm.generate = AsyncMock(return_value='```json\n[{"query": "q1", "researchGoal": "g1", "priority": 1}]\n```')

        processor = DeepResearchProcessor(mock_llm)
        deep_context = ProcessingContext(
            request=Request(query="test", mode=Modes.DEEP_RESEARCH),
            response=Response(result="", mode=Modes.DEEP_RESEARCH, trace_id="test")
        )

        domains = [
            {"name": "tech", "weight": 0.5, "search_angles": ["AI", "ML"]},
            {"name": "biz", "weight": 0.5, "search_angles": ["revenue", "market"]},
        ]

        # Should accept domains parameter without error
        queries = await processor._generate_serp_queries(deep_context, "plan", domains=domains)
        assert isinstance(queries, list)

    @pytest.mark.asyncio
    async def test_workflow_calls_identify_domains(self, mock_llm, mock_logger_ctx):
        """Full pipeline should call _identify_research_domains after plan."""
        processor = DeepResearchProcessor(mock_llm)

        mock_llm.generate = AsyncMock(side_effect=[
            "Plan",                                                                # 1. plan
            '{"domains": [{"name": "tech", "weight": 1.0, "search_angles": ["AI"]}]}',  # 2. domain identification
            '```json\n[{"query": "test", "researchGoal": "test", "priority": 1}]\n```',  # 3. SERP
            "Search result from model",                                            # 4. model search
            '{"synthesis": "s", "section_coverage": {}, "knowledge_gaps": [], "cross_domain_links": []}',  # 5. synthesis
            '{"is_sufficient": true}',                                             # 6. review
            "Critical analysis result",                                            # 7. critical analysis
            "Final research report",                                               # 8. final report
        ])

        deep_context = ProcessingContext(
            request=Request(query="AI report", mode=Modes.DEEP_RESEARCH),
            response=Response(result="", mode=Modes.DEEP_RESEARCH, trace_id="test")
        )

        result = await processor.process(deep_context)
        assert isinstance(result, str)
        # Verify domain identification was called (2nd LLM call)
        assert mock_llm.generate.call_count == 8
