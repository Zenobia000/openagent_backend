"""
Deep Research Service - 深度研究服務

實現類似 Manus 的多輪搜尋、網頁瀏覽、內容整合功能

特點：
1. 多關鍵詞並行搜尋
2. 自動抓取網頁內容
3. 失敗重試與關鍵詞擴展
4. SSE 即時進度回報
5. LLM 內容整合
"""

import os
import asyncio
import aiohttp
import logging
import re
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass, asdict
from datetime import datetime
from urllib.parse import quote_plus, urlparse
from bs4 import BeautifulSoup

from opencode.core.utils import load_env
load_env()

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜尋結果"""
    title: str
    url: str
    snippet: str
    source: str = ""
    content: str = ""  # 完整網頁內容（fetch 後填入）
    fetched: bool = False


@dataclass
class ResearchStep:
    """研究步驟（用於 SSE 回報）"""
    step_type: str  # search, fetch, analyze, error
    status: str     # running, completed, failed
    message: str
    data: Dict[str, Any] = None
    
    def to_dict(self):
        return asdict(self)


class DeepResearchService:
    """
    深度研究服務
    
    工作流程：
    1. 擴展搜尋查詢（生成多個相關關鍵詞）
    2. 並行執行多個搜尋
    3. 合併結果，選擇 top URLs
    4. 並行抓取網頁內容
    5. LLM 整合分析
    6. 生成結構化報告
    """
    
    def __init__(self):
        self.search_providers = []
        self.max_search_results = 10
        self.max_fetch_urls = 5
        self.fetch_timeout = 15
        self._session: Optional[aiohttp.ClientSession] = None
        
        # API Keys
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.serper_key = os.getenv("SERPER_API_KEY")  # 另一個搜尋 API
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """獲取 HTTP session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """關閉 session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    # ═══════════════════════════════════════════════════════════════
    # 搜尋方法
    # ═══════════════════════════════════════════════════════════════
    
    async def search_tavily(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Tavily AI 搜尋（推薦，效果最好）"""
        if not self.tavily_key:
            return []
        
        try:
            session = await self._get_session()
            async with session.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_answer": True,
                    "include_raw_content": False,
                    "max_results": max_results
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for r in data.get("results", []):
                        results.append(SearchResult(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            snippet=r.get("content", ""),
                            source="Tavily"
                        ))
                    logger.info(f"✅ Tavily 找到 {len(results)} 個結果")
                    return results
        except Exception as e:
            logger.error(f"❌ Tavily 搜尋失敗: {e}")
        return []
    
    async def search_serper(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Serper.dev Google 搜尋"""
        if not self.serper_key:
            return []
        
        try:
            session = await self._get_session()
            async with session.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": self.serper_key},
                json={"q": query, "num": max_results}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for r in data.get("organic", []):
                        results.append(SearchResult(
                            title=r.get("title", ""),
                            url=r.get("link", ""),
                            snippet=r.get("snippet", ""),
                            source="Serper/Google"
                        ))
                    logger.info(f"✅ Serper 找到 {len(results)} 個結果")
                    return results
        except Exception as e:
            logger.error(f"❌ Serper 搜尋失敗: {e}")
        return []
    
    async def search_duckduckgo_html(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """DuckDuckGo HTML 爬取（免費但較慢）"""
        try:
            session = await self._get_session()
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    results = []
                    
                    for result in soup.select('.result')[:max_results]:
                        title_elem = result.select_one('.result__title a')
                        snippet_elem = result.select_one('.result__snippet')
                        
                        if title_elem:
                            # DuckDuckGo 的 URL 是重定向格式，需要提取真實 URL
                            href = title_elem.get('href', '')
                            # 嘗試從 href 提取真實 URL
                            if 'uddg=' in href:
                                import urllib.parse
                                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                                real_url = parsed.get('uddg', [href])[0]
                            else:
                                real_url = href
                            
                            results.append(SearchResult(
                                title=title_elem.get_text(strip=True),
                                url=real_url,
                                snippet=snippet_elem.get_text(strip=True) if snippet_elem else "",
                                source="DuckDuckGo"
                            ))
                    
                    logger.info(f"✅ DuckDuckGo HTML 找到 {len(results)} 個結果")
                    return results
        except Exception as e:
            logger.error(f"❌ DuckDuckGo HTML 搜尋失敗: {e}")
        return []
    
    async def search_bing(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Bing 搜尋（爬取方式）"""
        try:
            session = await self._get_session()
            url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"
            }
            
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    results = []
                    
                    for item in soup.select('.b_algo')[:max_results]:
                        title_elem = item.select_one('h2 a')
                        snippet_elem = item.select_one('.b_caption p')
                        
                        if title_elem:
                            results.append(SearchResult(
                                title=title_elem.get_text(strip=True),
                                url=title_elem.get('href', ''),
                                snippet=snippet_elem.get_text(strip=True) if snippet_elem else "",
                                source="Bing"
                            ))
                    
                    logger.info(f"✅ Bing 找到 {len(results)} 個結果")
                    return results
        except Exception as e:
            logger.error(f"❌ Bing 搜尋失敗: {e}")
        return []
    
    async def multi_search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """
        多引擎並行搜尋
        
        優先級：Tavily > Serper > Bing > DuckDuckGo
        """
        logger.info(f"🔍 開始多引擎搜尋: {query}")
        
        # 並行執行所有搜尋
        tasks = [
            self.search_tavily(query, max_results),
            self.search_serper(query, max_results),
            self.search_bing(query, max_results),
            self.search_duckduckgo_html(query, max_results),
        ]
        
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合併結果，去重
        seen_urls = set()
        merged = []
        
        for results in all_results:
            if isinstance(results, Exception):
                continue
            for r in results:
                if r.url and r.url not in seen_urls:
                    seen_urls.add(r.url)
                    merged.append(r)
        
        logger.info(f"✅ 多引擎搜尋完成，共 {len(merged)} 個不重複結果")
        return merged[:max_results]
    
    # ═══════════════════════════════════════════════════════════════
    # 網頁抓取
    # ═══════════════════════════════════════════════════════════════
    
    async def fetch_url(self, url: str) -> Optional[str]:
        """抓取網頁內容"""
        try:
            session = await self._get_session()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"
            }
            
            async with session.get(url, headers=headers, timeout=self.fetch_timeout) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    
                    # 提取主要內容
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 移除不需要的元素
                    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
                        tag.decompose()
                    
                    # 嘗試找主要內容區塊
                    main_content = (
                        soup.find('article') or 
                        soup.find('main') or 
                        soup.find(class_=re.compile(r'content|article|post|entry')) or
                        soup.find('body')
                    )
                    
                    if main_content:
                        # 提取文字，限制長度
                        text = main_content.get_text(separator='\n', strip=True)
                        # 清理多餘空行
                        text = re.sub(r'\n{3,}', '\n\n', text)
                        # 限制長度
                        if len(text) > 5000:
                            text = text[:5000] + "...[內容截斷]"
                        return text
                    
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ 抓取超時: {url}")
        except Exception as e:
            logger.error(f"❌ 抓取失敗 {url}: {e}")
        
        return None
    
    async def fetch_multiple(self, urls: List[str]) -> Dict[str, str]:
        """並行抓取多個網頁"""
        logger.info(f"📥 開始抓取 {len(urls)} 個網頁...")
        
        tasks = [self.fetch_url(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        content_map = {}
        success_count = 0
        for url, content in zip(urls, results):
            if content:
                content_map[url] = content
                success_count += 1
        
        logger.info(f"✅ 成功抓取 {success_count}/{len(urls)} 個網頁")
        return content_map
    
    # ═══════════════════════════════════════════════════════════════
    # 深度研究主流程
    # ═══════════════════════════════════════════════════════════════
    
    async def research(
        self,
        query: str,
        expand_queries: bool = True,
        max_urls: int = 5
    ) -> AsyncGenerator[ResearchStep, None]:
        """
        執行深度研究（SSE 串流）
        
        Args:
            query: 原始查詢
            expand_queries: 是否擴展查詢關鍵詞
            max_urls: 最多抓取幾個網頁
            
        Yields:
            ResearchStep 物件（用於前端顯示進度）
        """
        all_results = []
        
        # Step 1: 擴展查詢
        queries = [query]
        if expand_queries:
            # 生成相關查詢變體
            queries.extend([
                f"{query} 最新",
                f"{query} 教學",
                f"{query} 應用",
            ])
        
        yield ResearchStep(
            step_type="search",
            status="running",
            message=f"正在搜尋 {len(queries)} 個查詢...",
            data={"queries": queries}
        )
        
        # Step 2: 並行搜尋
        for i, q in enumerate(queries):
            yield ResearchStep(
                step_type="search",
                status="running",
                message=f"搜尋中 ({i+1}/{len(queries)}): {q}",
                data={"query": q}
            )
            
            results = await self.multi_search(q, max_results=5)
            all_results.extend(results)
            
            yield ResearchStep(
                step_type="search",
                status="completed",
                message=f"找到 {len(results)} 個結果",
                data={"query": q, "count": len(results)}
            )
        
        # 去重
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)
        
        if not unique_results:
            yield ResearchStep(
                step_type="error",
                status="failed",
                message="搜尋未找到任何結果，請嘗試不同的關鍵詞"
            )
            return
        
        yield ResearchStep(
            step_type="search",
            status="completed",
            message=f"搜尋完成，共 {len(unique_results)} 個不重複結果",
            data={"total": len(unique_results)}
        )
        
        # Step 3: 抓取網頁內容
        urls_to_fetch = [r.url for r in unique_results[:max_urls]]
        
        yield ResearchStep(
            step_type="fetch",
            status="running",
            message=f"正在瀏覽 {len(urls_to_fetch)} 個網頁...",
            data={"urls": urls_to_fetch}
        )
        
        for i, url in enumerate(urls_to_fetch):
            domain = urlparse(url).netloc
            yield ResearchStep(
                step_type="fetch",
                status="running",
                message=f"正在瀏覽 ({i+1}/{len(urls_to_fetch)}): {domain}",
                data={"url": url}
            )
            
            content = await self.fetch_url(url)
            
            if content:
                # 更新對應的 SearchResult
                for r in unique_results:
                    if r.url == url:
                        r.content = content
                        r.fetched = True
                        break
                
                yield ResearchStep(
                    step_type="fetch",
                    status="completed",
                    message=f"✅ 成功抓取: {domain}",
                    data={"url": url, "length": len(content)}
                )
            else:
                yield ResearchStep(
                    step_type="fetch",
                    status="failed",
                    message=f"❌ 抓取失敗: {domain}",
                    data={"url": url}
                )
        
        # Step 4: 整理結果
        fetched_results = [r for r in unique_results if r.fetched]
        
        yield ResearchStep(
            step_type="analyze",
            status="running",
            message="正在整理研究結果...",
            data={"fetched_count": len(fetched_results)}
        )
        
        # 返回最終結果
        yield ResearchStep(
            step_type="analyze",
            status="completed",
            message="研究完成",
            data={
                "results": [asdict(r) for r in unique_results],
                "fetched_count": len(fetched_results),
                "total_count": len(unique_results)
            }
        )
    
    async def research_sync(self, query: str, max_urls: int = 5) -> Dict[str, Any]:
        """
        同步版本的深度研究（不用 SSE）
        
        Returns:
            {"results": [...], "fetched_count": int, "summary": str}
        """
        final_data = {}
        
        async for step in self.research(query, max_urls=max_urls):
            if step.step_type == "analyze" and step.status == "completed":
                final_data = step.data or {}
        
        return final_data


# 全域實例
_deep_research_service = None

def get_deep_research_service() -> DeepResearchService:
    """獲取全域 DeepResearchService 實例"""
    global _deep_research_service
    if _deep_research_service is None:
        _deep_research_service = DeepResearchService()
    return _deep_research_service
