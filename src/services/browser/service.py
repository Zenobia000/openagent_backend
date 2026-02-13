"""
Deep Research Service

實現功能：
1. Playwright 自動化瀏覽器（支援 JavaScript 渲染）
2. 多輪搜尋 + 內容分析
3. 截圖功能
4. SSE 即時進度回報
5. LLM 智能分析和報告生成
"""

import os
import re
import base64
import asyncio
import logging
import json
from typing import Dict, Any, Optional, List, AsyncGenerator
from dataclasses import dataclass, asdict, field
from datetime import datetime
from urllib.parse import urlparse, quote_plus
import aiohttp
from bs4 import BeautifulSoup

from core.utils import load_env
from core.prompts import PromptTemplates
load_env()

logger = logging.getLogger(__name__)

# Playwright 是可選依賴
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, Browser, Page, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Playwright 未安裝")


# ═══════════════════════════════════════════════════════════════════════════════
# 資料結構
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class SearchResult:
    """搜尋結果"""
    title: str
    url: str
    snippet: str
    source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BrowseResult:
    """瀏覽結果"""
    url: str
    title: str
    content: str
    screenshot: str = ""  # base64 encoded JPEG
    success: bool = True
    error: str = ""
    load_time: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        # 不包含完整 screenshot（太大）
        d = asdict(self)
        if d.get('screenshot'):
            d['screenshot'] = f"data:image/jpeg;base64,{d['screenshot'][:100]}..." if len(d['screenshot']) > 100 else d['screenshot']
            d['has_screenshot'] = True
        else:
            d['has_screenshot'] = False
        return d


@dataclass
class ResearchStep:
    """研究步驟（用於 SSE）"""
    step_type: str  # thinking, searching, browsing, reading, analyzing, complete, error
    status: str     # running, completed, failed
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# 瀏覽器服務
# ═══════════════════════════════════════════════════════════════════════════════

class BrowserService:
    """
    Playwright 瀏覽器服務
    
    如果 Playwright 不可用，自動降級到 aiohttp
    """
    
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._initialized = False
        self.use_playwright = PLAYWRIGHT_AVAILABLE
        
        # HTTP session for fallback
        self._http_session: Optional[aiohttp.ClientSession] = None
        
        # 設定
        self.timeout = 30000  # 30 秒
        self.viewport = {"width": 1280, "height": 720}
    
    async def initialize(self) -> bool:
        """初始化"""
        if self._initialized:
            return True
        
        if self.use_playwright:
            try:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
                )
                logger.info("✅ Playwright 瀏覽器啟動成功")
            except Exception as e:
                logger.warning(f"⚠️ Playwright 啟動失敗: {e}，降級到 HTTP 模式")
                self.use_playwright = False
        
        # 初始化 HTTP session
        timeout = aiohttp.ClientTimeout(total=30)
        self._http_session = aiohttp.ClientSession(timeout=timeout)
        
        self._initialized = True
        return True
    
    async def close(self):
        """關閉"""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
        self._initialized = False
    
    async def browse(
        self,
        url: str,
        take_screenshot: bool = True
    ) -> BrowseResult:
        """瀏覽網頁"""
        await self.initialize()
        
        if self.use_playwright and self._browser:
            return await self._browse_playwright(url, take_screenshot)
        else:
            return await self._browse_http(url)
    
    async def _browse_playwright(self, url: str, take_screenshot: bool) -> BrowseResult:
        """使用 Playwright 瀏覽"""
        page = None
        try:
            import time
            start = time.time()
            
            page = await self._browser.new_page(viewport=self.viewport)
            page.set_default_timeout(self.timeout)
            
            logger.info(f"🌐 [Playwright] 正在瀏覽: {url}")
            response = await page.goto(url, wait_until="domcontentloaded")
            
            if not response or response.status >= 400:
                return BrowseResult(
                    url=url, title="", content="",
                    success=False,
                    error=f"HTTP {response.status if response else 'error'}"
                )
            
            # 等待內容載入
            await asyncio.sleep(1)
            
            title = await page.title()
            
            # 截圖
            screenshot_b64 = ""
            if take_screenshot:
                try:
                    screenshot_bytes = await page.screenshot(type="jpeg", quality=60)
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
                except:
                    pass
            
            # 提取內容
            content = await page.evaluate("""
                () => {
                    // 移除干擾元素
                    ['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', '.ad', '.advertisement'].forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => el.remove());
                    });
                    
                    const main = document.querySelector('article') || document.querySelector('main') || document.body;
                    return main ? main.innerText : '';
                }
            """)
            
            # 清理內容
            content = re.sub(r'\n{3,}', '\n\n', content).strip()
            if len(content) > 6000:
                content = content[:6000] + "\n...[截斷]"
            
            return BrowseResult(
                url=url,
                title=title,
                content=content,
                screenshot=screenshot_b64,
                success=True,
                load_time=time.time() - start
            )
            
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Playwright 超時: {url}")
            return BrowseResult(url=url, title="", content="", success=False, error="超時")
        except Exception as e:
            logger.error(f"❌ Playwright 瀏覽失敗: {e}")
            return BrowseResult(url=url, title="", content="", success=False, error=str(e))
        finally:
            if page:
                await page.close()
    
    async def _browse_http(self, url: str) -> BrowseResult:
        """使用 HTTP 瀏覽（降級模式）- 優化版"""
        try:
            import time
            import ssl
            start = time.time()
            
            # 檢查是否是已知難以訪問的網站
            skip_domains = [
                'zhihu.com', 'zhuanlan.zhihu.com',  # 知乎需要登錄
                'weixin.qq.com', 'mp.weixin.qq.com',  # 微信公眾號
                'jianshu.com',  # 簡書
                'bilibili.com',  # B站
            ]
            
            domain = urlparse(url).netloc.lower()
            for skip in skip_domains:
                if skip in domain:
                    logger.warning(f"⚠️ 跳過受限網站: {domain}")
                    return BrowseResult(
                        url=url, title="", content="",
                        success=False, error=f"受限網站: {domain}"
                    )
            
            # 更完整的 headers，模擬真實瀏覽器
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
            }
            
            # 創建較短超時的 session
            timeout = aiohttp.ClientTimeout(total=15, connect=8)
            
            # 創建 SSL context 以忽略證書錯誤
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            logger.info(f"🌐 [HTTP] 正在瀏覽: {url}")
            
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url, headers=headers, allow_redirects=True) as resp:
                    if resp.status >= 400:
                        return BrowseResult(
                            url=url, title="", content="",
                            success=False, error=f"HTTP {resp.status}"
                        )
                    
                    # 檢查內容類型
                    content_type = resp.headers.get('Content-Type', '')
                    if 'text/html' not in content_type and 'text/plain' not in content_type:
                        return BrowseResult(
                            url=url, title="", content="",
                            success=False, error=f"非 HTML 內容: {content_type}"
                        )
                    
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 移除干擾元素
                    for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
                        tag.decompose()
                    
                    title = soup.title.string if soup.title else ""
                    
                    # 提取內容
                    main = soup.find('article') or soup.find('main') or soup.find(class_='content') or soup.body
                    content = main.get_text(separator='\n', strip=True) if main else ""
                    
                    content = re.sub(r'\n{3,}', '\n\n', content)
                    if len(content) > 6000:
                        content = content[:6000] + "\n...[截斷]"
                    
                    return BrowseResult(
                        url=url,
                        title=title,
                        content=content,
                        screenshot="",  # HTTP 模式無截圖
                        success=True,
                        load_time=time.time() - start
                    )
        
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ HTTP 超時: {url}")
            return BrowseResult(url=url, title="", content="", success=False, error="連線超時")
        except aiohttp.ClientError as e:
            logger.warning(f"⚠️ HTTP 連線錯誤: {url} - {e}")
            return BrowseResult(url=url, title="", content="", success=False, error="連線錯誤")
        except Exception as e:
            logger.error(f"❌ HTTP 瀏覽失敗: {e}")
            return BrowseResult(url=url, title="", content="", success=False, error=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# 搜尋服務
# ═══════════════════════════════════════════════════════════════════════════════

class SearchService:
    """多引擎搜尋服務"""
    
    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self.tavily_key = os.getenv("TAVILY_API_KEY")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """執行搜尋"""
        # 優先使用 Tavily
        if self.tavily_key:
            results = await self._search_tavily(query, max_results)
            if results:
                return results
        
        # Fallback: Bing + DuckDuckGo
        results = await self._search_multi(query, max_results)
        return results
    
    async def _search_tavily(self, query: str, max_results: int) -> List[SearchResult]:
        """Tavily AI 搜尋"""
        try:
            session = await self._get_session()
            async with session.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [
                        SearchResult(
                            title=r.get("title", ""),
                            url=r.get("url", ""),
                            snippet=r.get("content", ""),
                            source="Tavily"
                        )
                        for r in data.get("results", [])
                    ]
        except Exception as e:
            logger.error(f"Tavily 搜尋失敗: {e}")
        return []
    
    async def _search_multi(self, query: str, max_results: int) -> List[SearchResult]:
        """多引擎搜尋"""
        tasks = [
            self._search_bing(query, max_results),
            self._search_duckduckgo(query, max_results)
        ]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合併去重
        seen = set()
        merged = []
        for results in all_results:
            if isinstance(results, Exception):
                continue
            for r in results:
                if r.url not in seen:
                    seen.add(r.url)
                    merged.append(r)
        
        return merged[:max_results]
    
    async def _search_bing(self, query: str, max_results: int) -> List[SearchResult]:
        """Bing 搜尋"""
        try:
            session = await self._get_session()
            url = f"https://www.bing.com/search?q={quote_plus(query)}&count={max_results}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    results = []
                    
                    for item in soup.select('.b_algo')[:max_results]:
                        title_el = item.select_one('h2 a')
                        snippet_el = item.select_one('.b_caption p')
                        if title_el and title_el.get('href'):
                            results.append(SearchResult(
                                title=title_el.get_text(strip=True),
                                url=title_el.get('href'),
                                snippet=snippet_el.get_text(strip=True) if snippet_el else "",
                                source="Bing"
                            ))
                    return results
        except Exception as e:
            logger.error(f"Bing 搜尋失敗: {e}")
        return []
    
    async def _search_duckduckgo(self, query: str, max_results: int) -> List[SearchResult]:
        """DuckDuckGo 搜尋"""
        try:
            session = await self._get_session()
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    results = []
                    
                    for item in soup.select('.result')[:max_results]:
                        title_el = item.select_one('.result__title a')
                        snippet_el = item.select_one('.result__snippet')
                        if title_el:
                            href = title_el.get('href', '')
                            # 解析 DuckDuckGo 重定向 URL
                            if 'uddg=' in href:
                                import urllib.parse
                                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                                href = parsed.get('uddg', [href])[0]
                            
                            if href.startswith('http'):
                                results.append(SearchResult(
                                    title=title_el.get_text(strip=True),
                                    url=href,
                                    snippet=snippet_el.get_text(strip=True) if snippet_el else "",
                                    source="DuckDuckGo"
                                ))
                    return results
        except Exception as e:
            logger.error(f"DuckDuckGo 搜尋失敗: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════════════════
# 深度研究 Agent
# ═══════════════════════════════════════════════════════════════════════════════

class DeepResearchAgent:
    """
    Manus 風格深度研究 Agent
    
    工作流程：
    1. 分析問題 → 生成搜尋策略
    2. 多輪搜尋 + 瀏覽
    3. 智能分析 → 決定是否需要更多資料
    4. 生成結構化報告
    """
    
    def __init__(self):
        self.browser = BrowserService()
        self.search = SearchService()
        self._llm_client = None
        
        # 配置
        self.max_rounds = 3  # 最多搜尋輪數
        self.browse_per_round = 3  # 每輪瀏覽網頁數
    
    async def initialize(self):
        """初始化"""
        await self.browser.initialize()
        
        # 初始化 LLM
        try:
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._llm_client = AsyncOpenAI(api_key=api_key)
        except Exception as e:
            logger.warning(f"LLM 初始化失敗: {e}")
    
    async def close(self):
        """關閉"""
        await self.browser.close()
        await self.search.close()
    
    async def research(
        self,
        query: str,
        depth: str = "standard",  # quick, standard, deep
        selected_docs: Optional[List[str]] = None  # 用戶選擇的文件
    ) -> AsyncGenerator[ResearchStep, None]:
        """
        執行深度研究（SSE 串流）
        
        Args:
            query: 研究主題
            depth: 研究深度
            selected_docs: 用戶選擇的文件列表（可選）
            
        Yields:
            ResearchStep 用於前端顯示
        """
        await self.initialize()
        
        # 配置
        config = {
            "quick": {"rounds": 1, "browse": 2, "queries": 2},
            "standard": {"rounds": 2, "browse": 3, "queries": 4},
            "deep": {"rounds": 3, "browse": 4, "queries": 6}
        }.get(depth, {"rounds": 2, "browse": 3, "queries": 4})
        
        all_content = []  # 收集所有內容
        all_sources = []  # 收集所有來源
        browsed_urls = set()
        doc_sources = []  # 用戶文件來源
        
        # ═══════════════════════════════════════════════════════════════
        # Step 0: 如果有選擇文件，先檢查相關性並搜尋文件
        # ═══════════════════════════════════════════════════════════════
        if selected_docs and len(selected_docs) > 0:
            yield ResearchStep(
                step_type="thinking",
                status="running",
                message=f"正在分析 {len(selected_docs)} 個用戶文件的相關性...",
                data={"documents": selected_docs}
            )
            
            # 檢查文件與主題的相關性
            relevance_check = await self._check_document_relevance(query, selected_docs)
            
            if not relevance_check["is_relevant"]:
                yield ResearchStep(
                    step_type="thinking",
                    status="completed",
                    message=f"⚠️ {relevance_check['message']}",
                    data={
                        "warning": True,
                        "suggestion": relevance_check.get("suggestion", ""),
                        "documents": selected_docs
                    }
                )
                # 如果完全不相關，詢問是否繼續（這裡我們會繼續但標記警告）
            else:
                yield ResearchStep(
                    step_type="thinking",
                    status="completed",
                    message=f"✅ 文件與主題相關，將整合分析",
                    data={"documents": selected_docs}
                )
            
            # 搜尋用戶文件
            yield ResearchStep(
                step_type="searching",
                status="running",
                message="正在搜尋用戶文件...",
                data={"type": "rag", "documents": selected_docs}
            )
            
            doc_results = await self._search_user_documents(query, selected_docs)
            
            if doc_results:
                for doc in doc_results:
                    all_content.append({
                        "title": f"[用戶文件] {doc['source']}",
                        "url": f"file://{doc['source']}",
                        "content": doc['content'],
                        "type": "document"
                    })
                    doc_sources.append({
                        "title": doc['source'],
                        "url": f"file://{doc['source']}",
                        "page": doc.get('page', ''),
                        "type": "document"
                    })
                
                yield ResearchStep(
                    step_type="reading",
                    status="completed",
                    message=f"從用戶文件中找到 {len(doc_results)} 個相關片段",
                    data={"count": len(doc_results), "sources": [d['source'] for d in doc_results]}
                )
            else:
                yield ResearchStep(
                    step_type="searching",
                    status="completed",
                    message="用戶文件中未找到直接相關內容，將以網路搜尋為主",
                    data={}
                )
        
        # ═══════════════════════════════════════════════════════════════
        # Step 1: 思考 - 分析問題
        # ═══════════════════════════════════════════════════════════════
        yield ResearchStep(
            step_type="thinking",
            status="running",
            message="正在分析研究主題...",
            data={"query": query}
        )
        
        search_queries = await self._generate_search_queries(query, config["queries"])
        
        yield ResearchStep(
            step_type="thinking",
            status="completed",
            message=f"已規劃 {len(search_queries)} 個搜尋方向",
            data={"queries": search_queries}
        )
        
        # ═══════════════════════════════════════════════════════════════
        # Step 2: 多輪搜尋 + 瀏覽
        # ═══════════════════════════════════════════════════════════════
        for round_num in range(config["rounds"]):
            if round_num >= len(search_queries):
                break
            
            current_query = search_queries[round_num]
            
            # 搜尋
            yield ResearchStep(
                step_type="searching",
                status="running",
                message=f"網路搜尋: {current_query}",
                data={"query": current_query, "round": round_num + 1}
            )
            
            results = await self.search.search(current_query, max_results=8)
            
            if not results:
                yield ResearchStep(
                    step_type="searching",
                    status="failed",
                    message="搜尋無結果",
                    data={"query": current_query}
                )
                continue
            
            yield ResearchStep(
                step_type="searching",
                status="completed",
                message=f"找到 {len(results)} 個結果",
                data={
                    "query": current_query,
                    "count": len(results),
                    "results": [{"title": r.title, "url": r.url} for r in results[:5]]
                }
            )
            
            # 選擇要瀏覽的 URL
            urls_to_browse = []
            for r in results:
                if r.url not in browsed_urls and len(urls_to_browse) < config["browse"]:
                    urls_to_browse.append(r)
                    browsed_urls.add(r.url)
            
            # 瀏覽網頁
            for i, result in enumerate(urls_to_browse):
                domain = urlparse(result.url).netloc
                
                yield ResearchStep(
                    step_type="browsing",
                    status="running",
                    message=f"正在瀏覽: {domain}",
                    data={"url": result.url, "title": result.title, "index": i + 1, "total": len(urls_to_browse)}
                )
                
                browse_result = await self.browser.browse(result.url, take_screenshot=True)
                
                if browse_result.success and browse_result.content:
                    all_content.append({
                        "title": browse_result.title or result.title,
                        "url": result.url,
                        "content": browse_result.content
                    })
                    all_sources.append({
                        "title": browse_result.title or result.title,
                        "url": result.url
                    })
                    
                    yield ResearchStep(
                        step_type="reading",
                        status="completed",
                        message=f"✅ 已讀取: {browse_result.title[:50] if browse_result.title else domain}",
                        data={
                            "url": result.url,
                            "title": browse_result.title,
                            "content_length": len(browse_result.content),
                            "screenshot": browse_result.screenshot,  # base64 截圖
                            "load_time": browse_result.load_time
                        }
                    )
                else:
                    yield ResearchStep(
                        step_type="browsing",
                        status="failed",
                        message=f"❌ 無法讀取: {domain}",
                        data={"url": result.url, "error": browse_result.error}
                    )
        
        # ═══════════════════════════════════════════════════════════════
        # Step 3: 分析並生成報告
        # ═══════════════════════════════════════════════════════════════
        # 合併文件來源到所有來源
        if doc_sources:
            # 為文件來源添加索引
            for i, ds in enumerate(doc_sources):
                ds["index"] = len(all_sources) + i + 1
            all_sources.extend(doc_sources)
        
        # 為所有來源添加索引（如果還沒有）
        for i, src in enumerate(all_sources):
            if "index" not in src:
                src["index"] = i + 1
        
        if not all_content:
            yield ResearchStep(
                step_type="error",
                status="failed",
                message="未能收集到足夠的研究資料",
                data={}
            )
            return
        
        yield ResearchStep(
            step_type="analyzing",
            status="running",
            message=f"正在分析 {len(all_content)} 個來源，生成報告...",
            data={"source_count": len(all_content), "doc_count": len(doc_sources)}
        )
        
        report = await self._generate_report(query, all_content)
        
        yield ResearchStep(
            step_type="complete",
            status="completed",
            message="研究完成！",
            data={
                "report": report,
                "sources": all_sources,
                "stats": {
                    "total_sources": len(all_sources),
                    "pages_browsed": len(browsed_urls),
                    "documents_used": len(doc_sources) if doc_sources else 0
                }
            }
        )
    
    async def _generate_search_queries(self, query: str, num_queries: int) -> List[str]:
        """使用 LLM 生成搜尋查詢"""
        if not self._llm_client:
            return [
                query,
                f"{query} 介紹",
                f"{query} 教學",
                f"{query} 應用",
                f"{query} 最新發展",
                f"{query} 優缺點"
            ][:num_queries]
        
        try:
            response = await self._llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": f"""你是研究助手。根據用戶的研究主題，生成 {num_queries} 個不同角度的搜尋關鍵詞。

每行一個關鍵詞，不要編號，不要解釋。
關鍵詞應該：
- 涵蓋不同面向（定義、原理、應用、比較等）
- 使用適合搜尋引擎的用詞
- 中英文混合使用效果更好"""
                    },
                    {"role": "user", "content": f"研究主題：{query}"}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            queries = response.choices[0].message.content.strip().split('\n')
            queries = [q.strip() for q in queries if q.strip() and len(q.strip()) > 2]
            return queries[:num_queries]
            
        except Exception as e:
            logger.error(f"生成搜尋查詢失敗: {e}")
            return [query]
    
    async def _generate_report(self, query: str, contents: List[Dict]) -> str:
        """使用 LLM 生成報告 - 使用專業 prompts"""
        if not self._llm_client:
            report = f"# {query} 研究報告\n\n"
            for i, c in enumerate(contents, 1):
                source_type = "📄 用戶文件" if c.get('type') == 'document' else "🌐 網路來源"
                report += f"## [{i}] {source_type}: {c['title']}\n\n"
                report += c['content'][:800] + "\n\n"
            return report

        try:
            # 先生成研究計劃
            plan_prompt = PromptTemplates.get_report_plan_prompt(query)
            plan_response = await self._llm_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": plan_prompt}],
                temperature=0.3,
                max_tokens=500
            )
            report_plan = plan_response.choices[0].message.content

            # 整理研究發現 (learnings)
            learnings = []
            for i, c in enumerate(contents, 1):
                source_type = "用戶文件" if c.get('type') == 'document' else "網路來源"
                learnings.append(f"- [{i}] ({source_type}) {c['title']}: {c['content'][:400]}...")
            learnings_text = "\n".join(learnings)

            # 整理來源 (sources)
            sources_list = []
            for i, c in enumerate(contents, 1):
                source_type = "用戶文件" if c.get('type') == 'document' else "網路來源"
                sources_list.append(f"- [{i}] [{source_type}] {c['title']} - {c['url']}")
            sources_text = "\n".join(sources_list)

            # 統計來源類型
            doc_count = sum(1 for c in contents if c.get('type') == 'document')
            web_count = len(contents) - doc_count

            # 使用專業的最終報告 prompt
            requirement = f"""生成詳細、專業的繁體中文研究報告。
資料來源包含：{web_count} 個網路來源" + (f"和 {doc_count} 個用戶文件" if doc_count > 0 else "") + "。
請綜合分析所有資料，提供全面的見解。"""

            final_prompt = PromptTemplates.get_final_report_prompt(
                plan=report_plan,
                learnings=learnings_text,
                sources=sources_text,
                images="",  # 暫時不包含截圖
                requirement=requirement
            )

            # 加上引用規則、圖片規則和輸出指南
            references_prompt = PromptTemplates.get_final_report_references_prompt()
            image_prompt = PromptTemplates.get_final_report_citation_image_prompt()
            output_guidelines = PromptTemplates.get_output_guidelines()
            full_prompt = f"{final_prompt}\n\n{references_prompt}\n\n{image_prompt}\n\n{output_guidelines}"

            response = await self._llm_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": full_prompt}

## 格式要求
1. 使用繁體中文
2. 使用 Markdown 格式
3. 結構：摘要 → 主要內容（分小節）→ 結論

## 來源說明
- 資料來源分為「網路來源」和「用戶文件」兩類
- 兩者都同等重要，請綜合分析
- 如果用戶文件與主題高度相關，應給予適當權重

## 引用標記（非常重要！）
- 每個事實、數據、觀點後面都必須標註來源編號，格式為 [1]、[2] 等
- 引用標記要緊跟在相關句子後面，像 Wikipedia 那樣
- 例如：「根據研究報告[1]，該技術已被廣泛應用[2][3]。」
- 同一句話如果引用多個來源，可以寫成 [1][2] 或 [1,2]

## 寫作風格
- 客觀、專業、學術性
- 重點突出
- 邏輯清晰
- 不要在報告末尾重複列出參考來源（前端會自動顯示）"""
                    },
                    {
                        "role": "user",
                        "content": f"研究主題：{query}\n\n收集到的資料{source_info}：\n\n{context}\n\n請撰寫完整的研究報告（記得在每個事實後標註來源編號 [1], [2] 等）："
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"生成報告失敗: {e}")
            return f"# {query}\n\n收集到 {len(contents)} 個來源，但報告生成失敗：{e}"
    
    async def _check_document_relevance(
        self, 
        query: str, 
        documents: List[str]
    ) -> Dict[str, Any]:
        """
        檢查用戶文件與研究主題的相關性
        
        Returns:
            {
                "is_relevant": bool,
                "message": str,
                "suggestion": str (如果不相關)
            }
        """
        if not self._llm_client:
            # 沒有 LLM，假設相關
            return {"is_relevant": True, "message": "文件已添加"}
        
        try:
            doc_names = ", ".join(documents[:5])  # 最多顯示 5 個
            
            response = await self._llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """你是一個研究助手。請判斷用戶選擇的文件是否與研究主題相關。

回覆格式（JSON）：
{
  "is_relevant": true/false,
  "relevance_score": 0-100,
  "reason": "簡短說明",
  "suggestion": "如果不相關，建議如何調整"
}

判斷標準：
- 文件名稱包含相關關鍵詞 → 相關
- 主題與文件內容領域相近 → 相關
- 完全不同領域 → 不相關（但仍可作為背景參考）"""
                    },
                    {
                        "role": "user",
                        "content": f"研究主題：{query}\n\n選擇的文件：{doc_names}\n\n請判斷相關性："
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            import json
            try:
                result = json.loads(response.choices[0].message.content.strip())
                return {
                    "is_relevant": result.get("is_relevant", True),
                    "message": result.get("reason", ""),
                    "suggestion": result.get("suggestion", ""),
                    "score": result.get("relevance_score", 50)
                }
            except:
                return {"is_relevant": True, "message": "文件已添加"}
                
        except Exception as e:
            logger.error(f"檢查相關性失敗: {e}")
            return {"is_relevant": True, "message": "文件已添加"}
    
    async def _search_user_documents(
        self,
        query: str,
        documents: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        使用 RAG 搜尋用戶文件
        
        Args:
            query: 搜尋查詢
            documents: 文件名稱列表
            top_k: 返回結果數量
            
        Returns:
            [{
                "content": str,
                "source": str (文件名),
                "page": str,
                "score": float
            }]
        """
        try:
            import cohere
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchAny
            
            # 確保環境變數
            from core.utils import load_env
            load_env()
            
            cohere_key = os.getenv("COHERE_API_KEY")
            if not cohere_key:
                logger.error("COHERE_API_KEY 未設置")
                return []
            
            # 初始化客戶端
            cohere_client = cohere.Client(cohere_key)
            qdrant_client = QdrantClient(host="localhost", port=6333)
            
            # 生成查詢向量
            embed_response = cohere_client.embed(
                texts=[query],
                model="embed-multilingual-v3.0",
                input_type="search_query"
            )
            query_vector = embed_response.embeddings[0]
            
            # 建立文件過濾條件
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="file_name",
                        match=MatchAny(any=documents)
                    )
                ]
            )
            
            # 執行搜尋
            results = qdrant_client.query_points(
                collection_name="rag_knowledge_base",
                query=query_vector,
                query_filter=search_filter,
                limit=top_k,
                with_payload=True
            )
            
            return [
                {
                    "content": point.payload.get("text", ""),
                    "source": point.payload.get("file_name", ""),
                    "page": point.payload.get("page_label", "1"),
                    "score": point.score
                }
                for point in results.points
                if point.payload.get("text")
            ]
            
        except Exception as e:
            logger.error(f"搜尋用戶文件失敗: {e}")
            return []


# ═══════════════════════════════════════════════════════════════════════════════
# 全域實例
# ═══════════════════════════════════════════════════════════════════════════════

_research_agent = None

def get_research_agent() -> DeepResearchAgent:
    """獲取全域 DeepResearchAgent 實例"""
    global _research_agent
    if _research_agent is None:
        _research_agent = DeepResearchAgent()
    return _research_agent


# 導出
__all__ = [
    "BrowserService",
    "SearchService", 
    "DeepResearchAgent",
    "SearchResult",
    "BrowseResult",
    "ResearchStep",
    "get_research_agent",
    "PLAYWRIGHT_AVAILABLE"
]
