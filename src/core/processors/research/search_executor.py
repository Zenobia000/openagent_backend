"""
Search Executor - Multi-engine search execution and data management

Contains batch/race search execution, multi-provider fallback,
content enrichment, and research data persistence.
Extracted from DeepResearchProcessor (~500 lines).
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Awaitable

from ...models_v2 import ProcessingContext
from ...prompts import PromptTemplates
from ...logger import structured_logger
from .config import SearchEngineConfig, SearchProviderType
from .events import ResearchEvent


class SearchExecutor:
    """Multi-engine search execution with parallel/race strategies."""

    def __init__(self, call_llm: Callable[..., Awaitable[str]],
                 search_service=None,
                 search_config: SearchEngineConfig = None,
                 emit_event: Callable = None,
                 log_dir: str = None):
        self._call_llm = call_llm
        self.search_service = search_service
        self.search_config = search_config or SearchEngineConfig()
        self._emit_event = emit_event or self._noop_emit
        self.log_dir = log_dir
        self.logger = structured_logger

    @staticmethod
    async def _noop_emit(event):
        """No-op event emitter when streaming is not enabled."""
        pass

    async def execute_search_tasks(self, context: ProcessingContext,
                                   search_tasks: List[Dict]) -> List[Dict]:
        """Execute search tasks in parallel batches."""
        self.logger.progress("task-list", "start")

        self.logger.info(
            f"Task List: Executing {len(search_tasks)} search tasks "
            f"(parallel batch size: {self.search_config.parallel_searches})",
            "deep_research", "tasks",
            phase="task-list",
            total_tasks=len(search_tasks),
            parallel_batch_size=self.search_config.parallel_searches
        )

        results = []
        batch_size = self.search_config.parallel_searches

        for batch_start in range(0, len(search_tasks), batch_size):
            batch_end = min(batch_start + batch_size, len(search_tasks))
            batch_tasks = search_tasks[batch_start:batch_end]

            self.logger.info(
                f"Executing batch {batch_start//batch_size + 1}: "
                f"Tasks {batch_start+1}-{batch_end}",
                "deep_research", "batch_execution",
                batch_index=batch_start//batch_size + 1,
                batch_size=len(batch_tasks)
            )

            async_tasks = []
            for i, task in enumerate(batch_tasks, batch_start + 1):
                query = task.get('query', '')
                goal = task.get('researchGoal', '')
                priority = task.get('priority', 1)

                self.logger.info(
                    f"Search Task {i}/{len(search_tasks)}: {query}",
                    "deep_research", "search_task",
                    task_index=i, query=query, goal=goal,
                    priority=priority,
                    provider=self.search_config.primary.value
                )

                async_tasks.append(
                    self._execute_single_search_task(i, task, query, goal, priority)
                )

            batch_results = await asyncio.gather(*async_tasks, return_exceptions=True)

            for task, result in zip(batch_tasks, batch_results):
                if isinstance(result, Exception):
                    self.logger.error(
                        f"Search task failed: {str(result)}",
                        "deep_research", "search_error",
                        error=str(result)
                    )
                    result = {
                        'query': task.get('query', ''),
                        'goal': task.get('researchGoal', ''),
                        'priority': task.get('priority', 1),
                        'result': {
                            'error': str(result),
                            'sources': [],
                            'summary': f"Search failed: {str(result)}"
                        }
                    }
                results.append(result)

        self.logger.progress("task-list", "end")

        total_sources = sum(len(r.get('result', {}).get('sources', [])) for r in results)
        self.logger.info(
            f"Search Summary: {total_sources} total sources from {len(search_tasks)} tasks",
            "deep_research", "summary",
            phase="search-complete",
            total_sources=total_sources,
            total_tasks=len(search_tasks)
        )

        return results

    async def _execute_single_search_task(self, index: int, task: Dict,
                                          query: str, goal: str, priority: int) -> Dict:
        """Execute a single search task."""
        try:
            self.logger.progress("search-task", "start", {"name": query})
            self.logger.reasoning(f"正在搜索：{query}...", streaming=True)

            search_result = await self._perform_parallel_deep_search(query, goal)
            search_result = await self.enrich_with_full_content(search_result)

            self.logger.info(
                f"Search Result {index}: Found {len(search_result.get('sources', []))} sources",
                "deep_research", "search_result",
                task_index=index,
                sources_count=len(search_result.get('sources', [])),
                relevance_score=search_result.get('relevance', 0)
            )

            self.logger.message(
                f"搜索 {index}: {query}\n結果: {search_result.get('summary', '')[:200]}..."
            )

            self.logger.progress("search-task", "end", {
                "name": query, "data": search_result
            })

            return {
                'query': query,
                'goal': goal,
                'priority': priority,
                'result': search_result
            }
        except Exception as e:
            self.logger.error(
                f"Error in search task: {str(e)}",
                "deep_research", "task_error"
            )
            raise

    async def _perform_parallel_deep_search(self, query: str, goal: str) -> Dict:
        """Execute parallel deep search — race mode or enhanced fallback."""
        if hasattr(self.search_config, 'enable_race_mode') and self.search_config.enable_race_mode:
            return await self._perform_race_search(query, goal)
        return await self._perform_deep_search_enhanced(query, goal)

    async def _perform_race_search(self, query: str, goal: str) -> Dict:
        """Race mode: start all search engines in parallel, return first success."""
        providers = [self.search_config.primary] + (self.search_config.fallback_chain or [])

        self.logger.info(
            f"Race mode: Starting {len(providers)} search engines in parallel",
            "deep_research", "race_mode",
            providers=[p.value for p in providers]
        )

        search_tasks = [
            self._try_search_provider_with_timeout(provider, query, goal)
            for provider in providers
        ]

        for future in asyncio.as_completed(search_tasks):
            try:
                result = await future
                if result and result.get('sources'):
                    provider_name = result.get('provider', 'unknown')
                    self.logger.info(
                        f"Race winner: {provider_name} returned first with "
                        f"{len(result.get('sources', []))} sources",
                        "deep_research", "race_winner",
                        provider=provider_name
                    )
                    return result
            except Exception:
                continue

        return {
            'summary': 'No search results available',
            'sources': [],
            'relevance': 0
        }

    async def _try_search_provider_with_timeout(self, provider: SearchProviderType,
                                                query: str, goal: str) -> Optional[Dict]:
        """Try a search provider with configured timeout."""
        try:
            timeout = getattr(self.search_config, 'timeout', 30.0)
            result = await asyncio.wait_for(
                self._try_search_provider(provider, query, goal),
                timeout=timeout
            )
            if result:
                result['provider'] = provider.value
            return result

        except asyncio.TimeoutError:
            self.logger.warning(
                f"Search timeout for {provider.value} after {timeout}s",
                "deep_research", "timeout"
            )
            return None
        except Exception as e:
            self.logger.error(
                f"Search error with {provider.value}: {str(e)}",
                "deep_research", "provider_error"
            )
            return None

    async def _perform_deep_search(self, query: str, goal: str) -> Dict:
        """Execute deep search — use real search service, fall back to empty."""
        self.logger.info(
            f"Web Query: {query}",
            "web", "query",
            query=query, goal=goal,
            search_engine="web" if self.search_service else "none",
            max_results=10
        )

        search_result = None
        if self.search_service:
            try:
                results = await self.search_service.search(query, max_results=10)
                if results:
                    sources = [
                        {'url': r.url, 'title': r.title, 'relevance': 0.9}
                        for r in results
                    ]
                    summary = "\n".join(
                        f"- {r.title}: {r.snippet}" for r in results[:5]
                    )
                    search_result = {
                        'summary': summary,
                        'sources': sources,
                        'relevance': 0.92,
                        'timestamp': datetime.now().isoformat()
                    }
            except Exception as e:
                self.logger.warning(
                    f"Search service error in deep research: {e}", "web", "fallback"
                )

        if not search_result:
            self.logger.warning(
                f"Web search unavailable for deep research query: {query}",
                "web", "no_results"
            )
            search_result = {
                'summary': f"[Web search unavailable] Unable to retrieve real-time results for '{query}'. "
                           f"The final report will be based on the AI model's training data only.",
                'sources': [],
                'relevance': 0.0,
                'timestamp': datetime.now().isoformat()
            }

        self.logger.info(
            f"Web Results: Retrieved {len(search_result['sources'])} sources",
            "web", "results",
            sources=search_result['sources'][:5],
            avg_relevance=search_result['relevance']
        )

        if self._call_llm:
            result_prompt = PromptTemplates.get_search_result_prompt(
                query=query,
                research_goal=goal,
                context=json.dumps(search_result, ensure_ascii=False)
            )
            processed = await self._call_llm(result_prompt, None)
            search_result['processed'] = processed

        return search_result

    async def _perform_deep_search_enhanced(self, query: str, goal: str) -> Dict:
        """Enhanced deep search — multi-engine with intelligent fallback."""
        await self._emit_event(ResearchEvent(
            type="progress",
            step="search",
            data={
                "status": "start",
                "query": query,
                "goal": goal,
                "provider": self.search_config.primary.value
            }
        ))

        search_result = await self._try_search_provider(
            self.search_config.primary, query, goal
        )

        if not search_result or not search_result.get('sources'):
            for fallback_provider in self.search_config.fallback_chain:
                self.logger.info(
                    f"Switching to fallback: {fallback_provider.value}",
                    "deep_research", "fallback"
                )

                await self._emit_event(ResearchEvent(
                    type="message",
                    step="search",
                    data={
                        "message": f"Switching to {fallback_provider.value}...",
                        "provider": fallback_provider.value
                    }
                ))

                search_result = await self._try_search_provider(
                    fallback_provider, query, goal
                )

                if search_result and search_result.get('sources'):
                    break

        if search_result:
            await self._emit_event(ResearchEvent(
                type="search_result",
                step="search",
                data={
                    "query": query,
                    "sources_count": len(search_result.get('sources', [])),
                    "summary": search_result.get('summary', '')[:200]
                }
            ))

        return search_result or self._empty_search_result(query)

    async def _try_search_provider(self, provider: SearchProviderType,
                                   query: str, goal: str) -> Optional[Dict]:
        """Try a specific search provider."""
        try:
            if provider == SearchProviderType.MODEL:
                return await self._model_based_search(query, goal)
            elif provider == SearchProviderType.EXA:
                return await self._exa_search(query, goal)

            if self.search_service:
                if hasattr(self.search_service, 'set_provider'):
                    self.search_service.set_provider(provider.value.lower())

                results = await self.search_service.search(
                    query=query,
                    max_results=self.search_config.max_results
                )

                if results:
                    return self._format_search_results(results, provider.value)

        except Exception as e:
            self.logger.warning(
                f"Search error with {provider.value}: {e}",
                "deep_research", "search_error"
            )

        return None

    async def _exa_search(self, query: str, goal: str) -> Optional[Dict]:
        """Exa neural search."""
        if not self.search_service:
            return None

        search_type = "general"
        if "code" in goal.lower() or "programming" in goal.lower():
            search_type = "code"
        elif "research" in goal.lower() or "paper" in goal.lower():
            search_type = "research"
        elif "news" in goal.lower() or "latest" in goal.lower():
            search_type = "news"

        try:
            if hasattr(self.search_service, 'provider'):
                old_provider = self.search_service.provider
                self.search_service.provider = "exa"
                results = await self.search_service.search(
                    query=query,
                    max_results=self.search_config.max_results,
                    search_type=search_type
                )
                self.search_service.provider = old_provider

                if results:
                    return self._format_search_results(results, "exa")

        except Exception as e:
            self.logger.error(f"Exa search failed: {e}", "deep_research", "exa_error")

        return None

    async def _model_based_search(self, query: str, goal: str) -> Dict:
        """AI model knowledge-based search fallback."""
        if not self._call_llm:
            return self._empty_search_result(query)

        search_prompt = (
            f"Please search and provide information about:\n"
            f"Query: {query}\n"
            f"Research Goal: {goal}\n\n"
            f"Provide a comprehensive answer based on your knowledge, formatted as:\n"
            f"1. Summary of findings\n"
            f"2. Key facts and details\n"
            f"3. Relevant context\n\n"
            f"Focus on accuracy and relevance."
        )

        try:
            response = await self._call_llm(search_prompt, None)
            return {
                'summary': response,
                'sources': [{
                    'title': 'AI Knowledge Base',
                    'url': 'model://knowledge',
                    'relevance': 0.8
                }],
                'relevance': 0.8,
                'timestamp': datetime.now().isoformat(),
                'provider': 'model'
            }
        except Exception as e:
            self.logger.error(f"Model search failed: {e}", "deep_research", "model_search_error")
            return self._empty_search_result(query)

    def _format_search_results(self, results: List, provider: str) -> Dict:
        """Format search results from various providers into standard format."""
        if not results:
            return None

        sources = []
        summary_parts = []

        for r in results[:self.search_config.max_results]:
            if hasattr(r, 'url'):
                sources.append({
                    'url': r.url,
                    'title': getattr(r, 'title', 'Untitled'),
                    'relevance': getattr(r, 'score', 0.5)
                })
                summary_parts.append(f"- {r.title}: {getattr(r, 'snippet', '')[:100]}")
            elif isinstance(r, dict):
                sources.append({
                    'url': r.get('url', ''),
                    'title': r.get('title', 'Untitled'),
                    'relevance': r.get('score', 0.5)
                })
                summary_parts.append(f"- {r.get('title')}: {r.get('snippet', '')[:100]}")

        return {
            'summary': '\n'.join(summary_parts),
            'sources': sources,
            'relevance': sum(s['relevance'] for s in sources) / max(len(sources), 1),
            'timestamp': datetime.now().isoformat(),
            'provider': provider
        }

    def _empty_search_result(self, query: str) -> Dict:
        """Return empty search result placeholder."""
        return {
            'summary': f"[No search results available for: {query}]",
            'sources': [],
            'relevance': 0.0,
            'timestamp': datetime.now().isoformat(),
            'provider': 'none'
        }

    async def enrich_with_full_content(self, search_result: Dict,
                                       top_n: int = None) -> Dict:
        """Fetch full page content for top search result URLs."""
        if top_n is None:
            top_n = self.search_config.urls_per_query
        if not self.search_service or not hasattr(self.search_service, 'fetch_multiple'):
            return search_result

        sources = search_result.get('sources', [])
        if not sources:
            return search_result

        top_sources = sorted(sources, key=lambda s: s.get('relevance', 0), reverse=True)[:top_n]
        urls = [s['url'] for s in top_sources if s.get('url')]

        if not urls:
            return search_result

        try:
            content_map = await self.search_service.fetch_multiple(urls)
            if content_map:
                full_texts = []
                for url in urls:
                    text = content_map.get(url)
                    if text:
                        full_texts.append(text)
                if full_texts:
                    search_result['full_content'] = "\n\n---\n\n".join(full_texts)
        except Exception as e:
            self.logger.warning(
                f"Full-content extraction failed: {e}",
                "deep_research", "fetch_content_error"
            )

        return search_result

    def save_research_data(self, context: ProcessingContext,
                           search_results: List[Dict]) -> Optional[str]:
        """Save full search results to file (reversible compression)."""
        try:
            log_dir = self.log_dir or getattr(self.logger, 'log_dir', 'logs')
            trace_id = context.request.trace_id
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_dir = Path(log_dir) / "research_data" / f"{trace_id[:8]}_{timestamp}"
            session_dir.mkdir(parents=True, exist_ok=True)

            filepath = session_dir / "search_results.json"

            serializable = []
            for r in search_results:
                inner = r.get('result', {}) if isinstance(r.get('result'), dict) else {}
                serializable.append({
                    "query": r.get("query", ""),
                    "goal": r.get("goal", ""),
                    "priority": r.get("priority", 1),
                    "summary": inner.get("summary", ""),
                    "processed": inner.get("processed", ""),
                    "sources": inner.get("sources", []),
                })

            filepath.write_text(
                json.dumps(serializable, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.logger.info(
                f"Research data saved: {filepath} ({len(search_results)} results)",
                "deep_research", "data_saved",
            )
            return str(filepath)
        except Exception as e:
            self.logger.warning(
                f"Failed to save research data: {e}",
                "deep_research", "data_save_error"
            )
            return None
