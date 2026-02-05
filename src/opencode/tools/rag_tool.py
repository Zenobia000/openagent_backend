"""
RAG 搜尋工具

提供知識庫搜尋功能
"""

import logging
from typing import Dict, List, Any, Optional

from .base import BaseTool, ToolDefinition, ToolParameter, ToolCategory

logger = logging.getLogger(__name__)


class RAGSearchTool(BaseTool):
    """RAG 知識庫搜尋工具"""
    
    def __init__(self):
        super().__init__()
        self._retriever = None
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="rag_search",
            description="在知識庫中搜尋相關文檔內容。適用於需要查找已上傳文件中的信息。",
            category=ToolCategory.KNOWLEDGE,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="搜尋查詢語句",
                    required=True
                ),
                ToolParameter(
                    name="top_k",
                    type="integer",
                    description="返回結果數量",
                    required=False,
                    default=5
                ),
                ToolParameter(
                    name="collection",
                    type="string",
                    description="指定搜尋的知識庫（可選）",
                    required=False,
                    default=None
                ),
                ToolParameter(
                    name="file_filter",
                    type="string",
                    description="限定搜尋的文件名，多個文件用逗號分隔（可選）",
                    required=False,
                    default=None
                )
            ],
            returns="搜尋結果列表，包含文本內容、來源文件、頁碼和相關度分數",
            examples=[
                {
                    "query": "機器學習的應用場景",
                    "top_k": 5
                },
                {
                    "query": "深度學習模型架構",
                    "file_filter": "paper.pdf"
                }
            ]
        )
    
    async def initialize(self) -> bool:
        """初始化 Retriever"""
        try:
            from opencode.services.knowledge_base.retriever import Retriever
            self._retriever = Retriever()
            self._initialized = True
            logger.info("✅ RAGSearchTool initialized")
            return True
        except Exception as e:
            logger.error(f"RAGSearchTool init error: {e}")
            return False
    
    async def execute(
        self,
        query: str,
        top_k: int = 5,
        collection: str = None,
        file_filter: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """執行 RAG 搜尋"""
        if not self._retriever:
            return {"error": "Retriever not initialized"}
        
        try:
            # 構建過濾條件
            filters = {}
            if file_filter:
                # 支援逗號分隔的多文件
                files = [f.strip() for f in file_filter.split(",")]
                filters["file_name"] = files
            
            # 執行搜尋
            results = self._retriever.search(
                query=query,
                top_k=top_k,
                filters=filters if filters else None
            )
            
            return {
                "success": True,
                "query": query,
                "results": [
                    {
                        "text": r.get("text", ""),
                        "file_name": r.get("file_name", "unknown"),
                        "page": r.get("page_label") or r.get("page_number"),
                        "score": r.get("score", 0)
                    }
                    for r in results
                ],
                "count": len(results)
            }
        except Exception as e:
            logger.error(f"RAG search error: {e}")
            return {"error": str(e)}


class RAGMultiSearchTool(BaseTool):
    """RAG 多查詢搜尋工具"""
    
    def __init__(self):
        super().__init__()
        self._retriever = None
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="rag_multi_search",
            description="使用多個查詢語句搜尋知識庫，適合複雜問題需要從多個角度搜尋。",
            category=ToolCategory.KNOWLEDGE,
            parameters=[
                ToolParameter(
                    name="queries",
                    type="string",
                    description="多個搜尋查詢語句，用 | 分隔，例如: 方法論|實驗結果|結論",
                    required=True
                ),
                ToolParameter(
                    name="top_k",
                    type="integer",
                    description="每個查詢返回的結果數量",
                    required=False,
                    default=3
                ),
                ToolParameter(
                    name="file_filter",
                    type="string",
                    description="限定搜尋的文件名，多個文件用逗號分隔",
                    required=False,
                    default=None
                )
            ],
            returns="合併去重後的搜尋結果",
            examples=[
                {
                    "queries": "方法論|實驗結果|結論",
                    "top_k": 3
                }
            ]
        )
    
    async def initialize(self) -> bool:
        try:
            from opencode.services.knowledge_base.retriever import Retriever
            self._retriever = Retriever()
            self._initialized = True
            logger.info("✅ RAGMultiSearchTool initialized")
            return True
        except Exception as e:
            logger.error(f"RAGMultiSearchTool init error: {e}")
            return False
    
    async def execute(
        self,
        queries: str,
        top_k: int = 3,
        file_filter: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """執行多查詢搜尋"""
        if not self._retriever:
            return {"error": "Retriever not initialized"}
        
        try:
            # 解析查詢（用 | 分隔）
            query_list = [q.strip() for q in queries.split("|")]
            
            # 解析文件過濾
            filters = None
            if file_filter:
                files = [f.strip() for f in file_filter.split(",")]
                filters = {"file_name": files}
            
            results = self._retriever.search_multiple(
                queries=query_list,
                top_k=top_k,
                filters=filters
            )
            
            return {
                "success": True,
                "queries": query_list,
                "results": [
                    {
                        "text": r.get("text", ""),
                        "file_name": r.get("file_name", "unknown"),
                        "page": r.get("page_label") or r.get("page_number"),
                        "score": r.get("score", 0)
                    }
                    for r in results.get("results", [])
                ],
                "count": results.get("total", 0)
            }
        except Exception as e:
            logger.error(f"RAG multi-search error: {e}")
            return {"error": str(e)}
