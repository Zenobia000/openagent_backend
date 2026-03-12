"""
Web Search Service - 網路搜尋服務 (增強版)
支援多種搜尋引擎: Tavily, SerpAPI, Bing, DuckDuckGo
增加: 多引擎並行、網頁內容抓取、重試機制
"""

import os
import re
import logging
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from urllib.parse import quote_plus, urlparse
from bs4 import BeautifulSoup

from core.utils import load_env
load_env()

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜尋結果"""
    title: str
    url: str
    snippet: str
    source: str = ""
    published_date: Optional[str] = None
    content: str = ""  # 完整網頁內容（fetch 後填入）
    fetched: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WebSearchService:
    """
    網路搜尋服務 (增強版)
    
    新增功能：
    1. 多引擎並行搜尋（提高成功率）
    2. 網頁內容抓取（不只是摘要）
    3. 搜尋失敗時自動重試
    4. 智能關鍵詞擴展
    """
    
    def __init__(self):
        self._initialized = False
        self.provider = None
        self.tavily_key = os.getenv("TAVILY_API_KEY")
        self.serpapi_key = os.getenv("SERPAPI_KEY")
        self.serper_key = os.getenv("SERPER_API_KEY")
        self.brave_key = os.getenv("BRAVE_API_KEY")
        self.exa_key = os.getenv("EXA_API_KEY")
        self._session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self) -> None:
        """初始化服務"""
        if self._initialized:
            return
            
        # 優先順序: Tavily > Serper > SerpAPI > Bing/DDG
        if self.tavily_key:
            self.provider = "tavily"
            logger.info("✅ WebSearch 使用 Tavily API (推薦)")
        elif self.serper_key:
            self.provider = "serper"
            logger.info("✅ WebSearch 使用 Serper (Google)")
        elif self.serpapi_key:
            self.provider = "serpapi"
            logger.info("✅ WebSearch 使用 SerpAPI")
        else:
            self.provider = "multi"  # 多引擎模式
            logger.info("⚠️ WebSearch 使用免費多引擎模式 (Bing + DuckDuckGo)")
            
        self._initialized = True
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """獲取 HTTP session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            # Raise max header size: some sites send Set-Cookie >8KB (aiohttp default 8190)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                max_field_size=16384,
            )
        return self._session
    
    async def close(self):
        """關閉 session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    # ═══════════════════════════════════════════════════════════════
    # 搜尋方法
    # ═══════════════════════════════════════════════════════════════
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_type: str = "general",
        provider: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Execute web search with explicit provider routing.

        Args:
            query: Search keywords
            max_results: Maximum number of results
            search_type: Search type
            provider: Override provider name (tavily/serper/serpapi/brave/duckduckgo).
                      If None, uses the default provider from initialize().
        """
        await self.initialize()

        effective = provider or self.provider

        try:
            if effective == "tavily":
                results = await self._search_tavily(query, max_results, search_type)
            elif effective == "serper":
                results = await self._search_serper(query, max_results)
            elif effective == "serpapi":
                results = await self._search_serpapi(query, max_results)
            elif effective == "brave":
                results = await self._search_brave(query, max_results)
            elif effective == "exa":
                results = await self._search_exa(query, max_results, search_type)
            elif effective == "duckduckgo":
                results = await self._search_duckduckgo_html(query, max_results)
            else:
                results = await self._search_multi_engine(query, max_results)

            if results:
                return results

        except Exception as e:
            logger.error(f"Search failed ({effective}): {e}")

        # Fallback: multi-engine mode
        if effective != "multi":
            logger.info(f"Fallback to multi-engine search (primary {effective} failed)")
            return await self._search_multi_engine(query, max_results)

        return []
    
    async def _search_multi_engine(
        self,
        query: str,
        max_results: int = 5
    ) -> List[SearchResult]:
        """多引擎並行搜尋"""
        logger.info(f"🔍 多引擎搜尋: {query}")
        
        # 並行執行多個搜尋引擎
        tasks = [
            self._search_bing(query, max_results),
            self._search_duckduckgo_html(query, max_results),
        ]
        
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合併結果，去重
        seen_urls = set()
        merged = []
        
        for results in all_results:
            if isinstance(results, Exception):
                logger.warning(f"⚠️ 引擎失敗: {results}")
                continue
            if not results:
                continue
            for r in results:
                if r.url and r.url not in seen_urls:
                    seen_urls.add(r.url)
                    merged.append(r)
        
        logger.info(f"✅ 多引擎搜尋完成，共 {len(merged)} 個不重複結果")
        return merged[:max_results]
    
    async def _search_bing(
        self,
        query: str,
        max_results: int = 5
    ) -> List[SearchResult]:
        """Bing 搜尋（爬取 HTML）"""
        try:
            session = await self._get_session()
            # Truncate query to prevent URL > 8KB (Chinese chars expand ~9x in URL encoding)
            if len(query) > 150:
                query = query[:150]
            url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
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
                        
                        if title_elem and title_elem.get('href'):
                            results.append(SearchResult(
                                title=title_elem.get_text(strip=True),
                                url=title_elem.get('href', ''),
                                snippet=snippet_elem.get_text(strip=True) if snippet_elem else "",
                                source="Bing"
                            ))
                    
                    logger.info(f"✅ Bing 找到 {len(results)} 個結果")
                    return results
                else:
                    logger.warning(f"⚠️ Bing 返回狀態碼: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Bing 搜尋失敗: {e}")
        return []
    
    async def _search_duckduckgo_html(
        self,
        query: str,
        max_results: int = 5
    ) -> List[SearchResult]:
        """DuckDuckGo HTML 搜尋（直接爬取）"""
        try:
            session = await self._get_session()
            # Truncate query to prevent URL > 8KB
            if len(query) > 150:
                query = query[:150]
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
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
                            # 提取真實 URL
                            href = title_elem.get('href', '')
                            if 'uddg=' in href:
                                import urllib.parse
                                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                                real_url = parsed.get('uddg', [href])[0]
                            else:
                                real_url = href
                            
                            if real_url and real_url.startswith('http'):
                                results.append(SearchResult(
                                    title=title_elem.get_text(strip=True),
                                    url=real_url,
                                    snippet=snippet_elem.get_text(strip=True) if snippet_elem else "",
                                    source="DuckDuckGo"
                                ))
                    
                    logger.info(f"✅ DuckDuckGo 找到 {len(results)} 個結果")
                    return results
        except Exception as e:
            logger.error(f"❌ DuckDuckGo 搜尋失敗: {e}")
        return []
    
    async def _search_tavily(
        self,
        query: str,
        max_results: int = 5,
        search_type: str = "general"
    ) -> List[SearchResult]:
        """使用 Tavily API (AI 優化搜尋)"""
        try:
            session = await self._get_session()
            url = "https://api.tavily.com/search"
            payload = {
                "api_key": self.tavily_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "advanced" if search_type == "academic" else "basic",
                "include_answer": True,
                "include_raw_content": False
            }
            
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    
                    for r in data.get("results", []):
                        results.append(SearchResult(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            snippet=r.get("content", ""),
                            source="Tavily",
                            published_date=r.get("published_date")
                        ))
                    
                    logger.info(f"✅ Tavily 找到 {len(results)} 個結果")
                    return results
                else:
                    error = await resp.text()
                    logger.error(f"❌ Tavily API 錯誤: {error}")
        except Exception as e:
            logger.error(f"❌ Tavily 搜尋失敗: {e}")
        return []
    
    async def _search_serper(
        self,
        query: str,
        max_results: int = 5
    ) -> List[SearchResult]:
        """使用 Serper.dev (Google 搜尋)"""
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
                            source="Google"
                        ))
                    logger.info(f"✅ Serper 找到 {len(results)} 個結果")
                    return results
        except Exception as e:
            logger.error(f"❌ Serper 搜尋失敗: {e}")
        return []
    
    async def _search_serpapi(
        self,
        query: str,
        max_results: int = 5
    ) -> List[SearchResult]:
        """使用 SerpAPI (Google 搜尋)"""
        try:
            session = await self._get_session()
            url = "https://serpapi.com/search"
            params = {
                "api_key": self.serpapi_key,
                "q": query,
                "num": max_results,
                "engine": "google"
            }
            
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    
                    for r in data.get("organic_results", []):
                        results.append(SearchResult(
                            title=r.get("title", ""),
                            url=r.get("link", ""),
                            snippet=r.get("snippet", ""),
                            source="Google"
                        ))
                    
                    logger.info(f"✅ SerpAPI 找到 {len(results)} 個結果")
                    return results
        except Exception as e:
            logger.error(f"❌ SerpAPI 搜尋失敗: {e}")
        return []

    async def _search_brave(
        self,
        query: str,
        max_results: int = 5
    ) -> List[SearchResult]:
        """Brave Search API"""
        if not self.brave_key:
            logger.warning("Brave API key not configured")
            return []
        try:
            session = await self._get_session()
            params = {"q": query, "count": max_results}
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.brave_key,
            }
            async with session.get(
                "https://api.search.brave.com/res/v1/web/search",
                params=params, headers=headers,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for r in data.get("web", {}).get("results", []):
                        results.append(SearchResult(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            snippet=r.get("description", ""),
                            source="Brave",
                        ))
                    logger.info(f"Brave found {len(results)} results")
                    return results
                else:
                    error = await resp.text()
                    logger.error(f"Brave API error ({resp.status}): {error}")
        except Exception as e:
            logger.error(f"Brave search failed: {e}")
        return []

    async def _search_exa(
        self,
        query: str,
        max_results: int = 5,
        search_type: str = "general",
    ) -> List[SearchResult]:
        """Exa neural search API (https://api.exa.ai)"""
        if not self.exa_key:
            logger.warning("Exa API key not configured")
            return []
        try:
            session = await self._get_session()
            exa_type = os.getenv("EXA_SEARCH_TYPE", "auto")
            payload = {
                "query": query,
                "numResults": max_results,
                "type": exa_type,
                "contents": {"text": {"maxCharacters": int(os.getenv("EXA_MAX_CHARACTERS", "20000"))}},
            }
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.exa_key,
            }
            async with session.post(
                "https://api.exa.ai/search",
                json=payload, headers=headers,
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = []
                    for r in data.get("results", []):
                        results.append(SearchResult(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            snippet=r.get("text", "")[:500],
                            source="Exa",
                            published_date=r.get("publishedDate"),
                        ))
                    logger.info(f"Exa found {len(results)} results")
                    return results
                else:
                    error = await resp.text()
                    logger.error(f"Exa API error ({resp.status}): {error}")
        except Exception as e:
            logger.error(f"Exa search failed: {e}")
        return []

    # ═══════════════════════════════════════════════════════════════
    # 網頁內容抓取
    # ═══════════════════════════════════════════════════════════════
    
    # Binary extensions that cannot be decoded as text
    # Note: .pdf is NOT here — handled by _fetch_pdf_url()
    _BINARY_EXTENSIONS = frozenset({
        '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt',
        '.zip', '.rar', '.7z', '.gz', '.tar',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp',
        '.mp3', '.mp4', '.avi', '.mov', '.wav',
        '.exe', '.dll', '.so', '.bin',
    })

    async def fetch_url(self, url: str, timeout: int = 15) -> Optional[str]:
        """抓取網頁內容並提取主要文字"""
        # Guard: skip URLs that exceed HTTP header limits
        if len(url.encode('utf-8')) > 4096:
            logger.warning(f"⏭️ URL too long ({len(url.encode('utf-8'))} bytes), skipping: {url[:80]}...")
            return None

        # PDF: download + extract text via PyMuPDF
        parsed_path = urlparse(url).path.lower()
        if parsed_path.endswith('.pdf'):
            return await self._fetch_pdf_url(url, timeout=30)

        # Guard: skip known binary file extensions
        if any(parsed_path.endswith(ext) for ext in self._BINARY_EXTENSIONS):
            logger.warning(f"⏭️ Binary file skipped: {url[:80]}...")
            return None

        try:
            session = await self._get_session()
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8"
            }

            async with session.get(url, headers=headers, timeout=timeout) as resp:
                if resp.status == 200:
                    # Guard: skip binary Content-Type responses
                    content_type = resp.headers.get('Content-Type', '')
                    if 'application/pdf' in content_type:
                        return await self._fetch_pdf_url(url, timeout=30)
                    if not any(t in content_type for t in ('text/', 'application/json', 'application/xml', 'application/xhtml')):
                        logger.warning(f"⏭️ Non-text content ({content_type}), skipping: {url[:80]}...")
                        return None
                    html = await resp.text(errors='replace')
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 移除不需要的元素
                    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript', 'form']):
                        tag.decompose()
                    
                    # 嘗試找主要內容區塊
                    main_content = (
                        soup.find('article') or 
                        soup.find('main') or 
                        soup.find(class_=re.compile(r'content|article|post|entry|text')) or
                        soup.find('body')
                    )
                    
                    if main_content:
                        text = main_content.get_text(separator='\n', strip=True)
                        # 清理多餘空行
                        text = re.sub(r'\n{3,}', '\n\n', text)
                        # 限制長度
                        if len(text) > 5000:
                            text = text[:5000] + "...[內容截斷]"
                        
                        logger.info(f"✅ 抓取成功: {urlparse(url).netloc} ({len(text)} 字)")
                        return text
                    
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ 抓取超時: {url}")
        except Exception as e:
            logger.error(f"❌ 抓取失敗 {url}: {e}")
        
        return None
    
    async def _fetch_pdf_url(self, url: str, timeout: int = 30,
                             max_size_mb: int = 20) -> Optional[str]:
        """Download PDF from URL and extract text with PyMuPDF.

        Returns None gracefully if PyMuPDF is not installed or extraction fails.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.debug("PyMuPDF not installed, skipping PDF: %s", url[:80])
            return None

        import tempfile
        import os as _os

        tmp_path = None
        try:
            session = await self._get_session()
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
            ) as resp:
                if resp.status != 200:
                    return None
                content_length = resp.headers.get('Content-Length')
                if content_length and int(content_length) > max_size_mb * 1024 * 1024:
                    logger.warning(f"⏭️ PDF too large ({content_length} bytes): {url[:80]}")
                    return None
                pdf_bytes = await resp.read()

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = tmp.name

            doc = fitz.open(tmp_path)
            max_pages = min(len(doc), 30)
            text_parts = []
            for i in range(max_pages):
                page_text = doc[i].get_text("text").strip()
                if page_text:
                    text_parts.append(page_text)
            doc.close()

            full_text = "\n\n".join(text_parts)
            if len(full_text) > 15000:
                full_text = full_text[:15000] + "...[PDF content truncated]"

            if full_text:
                logger.info(
                    f"📄 PDF extracted: {urlparse(url).netloc} "
                    f"({len(full_text)} chars, {max_pages} pages)"
                )
            return full_text or None

        except asyncio.TimeoutError:
            logger.warning(f"⏭️ PDF download timeout: {url[:80]}")
            return None
        except Exception as e:
            logger.warning(f"⏭️ PDF extraction failed ({e}): {url[:80]}")
            return None
        finally:
            if tmp_path:
                try:
                    _os.unlink(tmp_path)
                except OSError:
                    pass

    async def fetch_multiple(self, urls: List[str], max_concurrent: int = 3) -> Dict[str, str]:
        """並行抓取多個網頁"""
        logger.info(f"📥 開始抓取 {len(urls)} 個網頁...")
        
        # 使用 semaphore 限制並行數
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_semaphore(url):
            async with semaphore:
                return url, await self.fetch_url(url)
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        content_map = {}
        success_count = 0
        for url, content in results:
            if content:
                content_map[url] = content
                success_count += 1
        
        logger.info(f"✅ 成功抓取 {success_count}/{len(urls)} 個網頁")
        return content_map
    
    # ═══════════════════════════════════════════════════════════════
    # 深度搜尋（搜尋 + 抓取內容）
    # ═══════════════════════════════════════════════════════════════
    
    async def search_and_fetch(
        self,
        query: str,
        max_results: int = 5,
        fetch_top_n: int = 3
    ) -> List[SearchResult]:
        """
        搜尋並抓取網頁內容
        
        Args:
            query: 搜尋關鍵字
            max_results: 搜尋結果數
            fetch_top_n: 抓取前 N 個網頁的完整內容
            
        Returns:
            包含完整內容的搜尋結果
        """
        results = await self.search(query, max_results)
        
        if not results:
            return []
        
        # 抓取前 N 個網頁的內容
        urls_to_fetch = [r.url for r in results[:fetch_top_n]]
        content_map = await self.fetch_multiple(urls_to_fetch)
        
        # 更新結果
        for r in results:
            if r.url in content_map:
                r.content = content_map[r.url]
                r.fetched = True
        
        return results
    
    async def search_with_retry(
        self,
        query: str,
        max_results: int = 5,
        max_retries: int = 2
    ) -> List[SearchResult]:
        """
        帶重試機制的搜尋
        
        如果搜尋失敗，會嘗試：
        1. 簡化關鍵詞
        2. 使用英文關鍵詞
        """
        # 第一次嘗試
        results = await self.search(query, max_results)
        if results:
            return results
        
        # 重試策略
        retry_queries = [
            # 簡化：只取前幾個詞
            ' '.join(query.split()[:3]),
            # 加上 "是什麼"
            f"{query.split()[0]} 是什麼",
        ]
        
        for i, retry_query in enumerate(retry_queries[:max_retries]):
            logger.info(f"🔄 重試搜尋 ({i+1}/{max_retries}): {retry_query}")
            results = await self.search(retry_query, max_results)
            if results:
                return results
        
        return []
    
    # ═══════════════════════════════════════════════════════════════
    # LLM 摘要
    # ═══════════════════════════════════════════════════════════════
    
    async def search_and_summarize(
        self,
        query: str,
        max_results: int = 5,
        fetch_content: bool = True
    ) -> Dict[str, Any]:
        """
        搜尋並用 LLM 摘要結果
        
        Returns:
            {
                "query": str,
                "summary": str,
                "results": List[dict],
                "sources": List[str]
            }
        """
        if fetch_content:
            results = await self.search_and_fetch(query, max_results, fetch_top_n=3)
        else:
            results = await self.search_with_retry(query, max_results)
        
        if not results:
            return {
                "query": query,
                "summary": "未找到相關搜尋結果。建議嘗試不同的關鍵詞。",
                "results": [],
                "sources": []
            }
        
        # 建構搜尋結果文字
        context_parts = []
        for i, r in enumerate(results):
            part = f"[{i+1}] {r.title}\n{r.snippet}"
            if r.content:
                # 如果有完整內容，加入摘要
                part += f"\n\n詳細內容:\n{r.content[:1500]}"
            part += f"\n來源: {r.url}"
            context_parts.append(part)
        
        context = "\n\n---\n\n".join(context_parts)
        
        # 使用 LLM 摘要
        try:
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("BASE_URL", "https://api.openai.com")
            
            if api_key:
                client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                response = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": """你是一個搜尋摘要助手。請根據搜尋結果，用繁體中文詳細回答用戶的問題。

要求：
1. 綜合所有來源的資訊
2. 使用 [1], [2] 等標記引用來源
3. 結構化呈現資訊
4. 最後列出參考來源"""
                        },
                        {
                            "role": "user",
                            "content": f"問題: {query}\n\n搜尋結果:\n{context}\n\n請根據以上搜尋結果詳細回答問題，並標註來源。"
                        }
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                summary = response.choices[0].message.content
            else:
                summary = f"找到 {len(results)} 個相關結果。"
                
        except Exception as e:
            logger.error(f"❌ LLM 摘要失敗: {e}")
            summary = f"找到 {len(results)} 個相關結果。"
        
        return {
            "query": query,
            "summary": summary,
            "results": [r.to_dict() for r in results],
            "sources": [{"title": r.title, "url": r.url} for r in results]
        }
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """MCP 統一執行介面"""
        await self.initialize()
        
        if action == "search":
            query = parameters.get("query", "")
            max_results = parameters.get("max_results", 5)
            results = await self.search_with_retry(query, max_results)
            return {
                "success": len(results) > 0,
                "results": [r.to_dict() for r in results],
                "count": len(results)
            }
        
        elif action == "search_and_fetch":
            query = parameters.get("query", "")
            max_results = parameters.get("max_results", 5)
            fetch_top_n = parameters.get("fetch_top_n", 3)
            results = await self.search_and_fetch(query, max_results, fetch_top_n)
            return {
                "success": len(results) > 0,
                "results": [r.to_dict() for r in results],
                "count": len(results),
                "fetched_count": sum(1 for r in results if r.fetched)
            }
            
        elif action == "fetch":
            url = parameters.get("url", "")
            content = await self.fetch_url(url)
            return {
                "success": content is not None,
                "url": url,
                "content": content or "",
                "length": len(content) if content else 0
            }
            
        elif action == "search_summarize":
            query = parameters.get("query", "")
            max_results = parameters.get("max_results", 5)
            fetch_content = parameters.get("fetch_content", True)
            return await self.search_and_summarize(query, max_results, fetch_content)
            
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


# 全域實例
_web_search_service = None

def get_web_search_service() -> WebSearchService:
    global _web_search_service
    if _web_search_service is None:
        _web_search_service = WebSearchService()
    return _web_search_service
