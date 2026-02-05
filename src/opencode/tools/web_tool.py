"""
網路搜尋工具 (增強版)

提供網路搜尋和網頁內容抓取功能
"""

import logging
from typing import Dict, List, Any

from .base import BaseTool, ToolDefinition, ToolParameter, ToolCategory

logger = logging.getLogger(__name__)


class WebSearchTool(BaseTool):
    """網路搜尋工具（帶重試和多引擎支援）"""
    
    def __init__(self):
        super().__init__()
        self._service = None
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_search",
            description="""搜尋網路獲取最新資訊。
            
功能：
- 多引擎並行搜尋（Bing + DuckDuckGo）
- 自動重試機制
- 返回標題、摘要、URL

適用情境：
- 查找即時資訊、新聞
- 查詢知識庫中沒有的內容
- 獲取最新技術趨勢""",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="搜尋關鍵詞（建議使用具體關鍵詞，如「神經網路 深度學習 應用」）",
                    required=True
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="最大結果數量（預設 5）",
                    required=False,
                    default=5
                )
            ],
            returns="搜尋結果列表，包含標題、摘要和連結",
            examples=[
                {
                    "query": "Transformer 模型 原理",
                    "max_results": 5
                },
                {
                    "query": "2024 AI 發展趨勢",
                    "max_results": 10
                }
            ]
        )
    
    async def initialize(self) -> bool:
        try:
            from opencode.services.web_search.service import WebSearchService
            self._service = WebSearchService()
            await self._service.initialize()
            self._initialized = True
            logger.info(f"✅ WebSearchTool initialized (provider: {self._service.provider})")
            return True
        except Exception as e:
            logger.error(f"WebSearchTool init error: {e}")
            return False
    
    async def execute(
        self,
        query: str,
        max_results: int = 5,
        **kwargs
    ) -> Dict[str, Any]:
        """執行網路搜尋（帶重試）"""
        if not self._service:
            await self.initialize()
        
        if not self._service:
            return {"error": "WebSearch service not initialized", "success": False, "results": []}
        
        try:
            # 使用帶重試的搜尋
            results = await self._service.search_with_retry(query, max_results)
            
            return {
                "success": len(results) > 0,
                "query": query,
                "results": [r.to_dict() for r in results],
                "count": len(results),
                "message": f"找到 {len(results)} 個結果" if results else "未找到結果，建議嘗試不同關鍵詞"
            }
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return {"error": str(e), "success": False, "results": []}


class WebFetchTool(BaseTool):
    """網頁內容擷取工具"""
    
    def __init__(self):
        super().__init__()
        self._service = None
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_fetch",
            description="""擷取指定網頁的完整內容。

功能：
- 自動提取網頁主要內容
- 移除廣告、導航等雜訊
- 支援中英文網頁

適用情境：
- 讀取搜尋結果的詳細內容
- 深入了解特定網頁
- 整合多個來源的資訊""",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="要擷取的網頁 URL",
                    required=True
                )
            ],
            returns="網頁的主要文字內容",
            examples=[
                {
                    "url": "https://example.com/article"
                }
            ]
        )
    
    async def initialize(self) -> bool:
        try:
            from opencode.services.web_search.service import WebSearchService
            self._service = WebSearchService()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"WebFetchTool init error: {e}")
            return False
    
    async def execute(
        self,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """擷取網頁內容"""
        if not self._service:
            await self.initialize()
        
        if not self._service:
            return {"error": "WebSearch service not initialized", "success": False}
        
        try:
            content = await self._service.fetch_url(url)
            
            if content:
                return {
                    "success": True,
                    "url": url,
                    "content": content,
                    "length": len(content)
                }
            else:
                return {
                    "success": False,
                    "url": url,
                    "content": "",
                    "error": "無法抓取網頁內容"
                }
        except Exception as e:
            logger.error(f"Web fetch error: {e}")
            return {"error": str(e), "success": False}


class WebSearchAndFetchTool(BaseTool):
    """搜尋並抓取網頁內容（深度搜尋）"""
    
    def __init__(self):
        super().__init__()
        self._service = None
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="web_deep_search",
            description="""深度網路搜尋：搜尋 + 自動抓取網頁內容。

功能：
- 搜尋網路
- 自動抓取前 N 個結果的完整內容
- 提供更詳細的資訊

適用情境：
- 需要深入了解某個主題
- 需要整合多個來源的詳細資訊
- 撰寫研究報告""",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="搜尋關鍵詞",
                    required=True
                ),
                ToolParameter(
                    name="max_results",
                    type="integer",
                    description="搜尋結果數量",
                    required=False,
                    default=5
                ),
                ToolParameter(
                    name="fetch_top_n",
                    type="integer",
                    description="抓取前 N 個網頁的內容",
                    required=False,
                    default=3
                )
            ],
            returns="搜尋結果列表，包含完整網頁內容",
            examples=[
                {
                    "query": "CLIP 模型 原理 應用",
                    "max_results": 5,
                    "fetch_top_n": 3
                }
            ]
        )
    
    async def initialize(self) -> bool:
        try:
            from opencode.services.web_search.service import WebSearchService
            self._service = WebSearchService()
            await self._service.initialize()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"WebSearchAndFetchTool init error: {e}")
            return False
    
    async def execute(
        self,
        query: str,
        max_results: int = 5,
        fetch_top_n: int = 3,
        **kwargs
    ) -> Dict[str, Any]:
        """搜尋並抓取網頁內容"""
        if not self._service:
            await self.initialize()
        
        if not self._service:
            return {"error": "WebSearch service not initialized", "success": False}
        
        try:
            results = await self._service.search_and_fetch(query, max_results, fetch_top_n)
            
            fetched_count = sum(1 for r in results if r.fetched)
            
            return {
                "success": len(results) > 0,
                "query": query,
                "results": [r.to_dict() for r in results],
                "count": len(results),
                "fetched_count": fetched_count,
                "message": f"找到 {len(results)} 個結果，成功抓取 {fetched_count} 個網頁內容"
            }
        except Exception as e:
            logger.error(f"Web deep search error: {e}")
            return {"error": str(e), "success": False}
