"""
Knowledge Base Service - RAG 知識庫服務
整合 Cohere Embedding + 多模態解析（支援圖片）
"""

from typing import List, Dict, Any, Optional
import logging
import os
import uuid
from pathlib import Path

# 使用統一的路徑工具載入環境變數
from core.utils import load_env, get_project_root
load_env()

from core.protocols import MCPServiceProtocol, LongTermMemoryProtocol

# 新的模組
from .multimodal_parser import MultimodalParser, get_multimodal_parser, SUPPORTED_FORMATS
from .indexer import Indexer, get_indexer, reset_indexer
from .retriever import Retriever, get_retriever, reset_retriever

logger = logging.getLogger(__name__)


class KnowledgeBaseService(MCPServiceProtocol, LongTermMemoryProtocol):
    """
    知識庫服務 - Cohere Embedding + DoclingReader
    
    功能:
    - 語意搜尋 (rag_search) - 使用 Cohere embedding
    - 多查詢搜尋 (rag_search_multiple) - 口語化理解
    - 問答生成 (rag_ask) - GPT-4o 回答
    - 文件管理 (upload, delete, list)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._service_id = "knowledge_base"
        self._capabilities = [
            "rag_search",
            "rag_search_multiple",
            "rag_ask",
            "document_upload",
            "document_delete",
            "document_list",
            "get_stats"
        ]
        
        # 新的模組實例
        self.indexer: Optional[Indexer] = None
        self.retriever: Optional[Retriever] = None
        self.parser: Optional[MultimodalParser] = None
        
        # OpenAI client (用於回答生成)
        self.openai_client = None
        
        # 配置
        self.collection_name = self.config.get("collection", "rag_knowledge_base")
        self.chat_model = self.config.get("chat_model", "gpt-4o")
        
        self._initialized = False
    
    @property
    def service_id(self) -> str:
        return self._service_id
    
    @property
    def capabilities(self) -> List[str]:
        return self._capabilities
    
    async def initialize(self) -> None:
        """初始化服務"""
        if self._initialized:
            return
            
        try:
            # 強制重新載入 .env
            load_env()
            
            # 初始化新模組
            logger.info("🚀 [Service] 初始化 KnowledgeBase 服務...")
            
            # Indexer (Cohere/OpenAI embedding)
            try:
                self.indexer = get_indexer()
                logger.info(f"✅ [Service] Indexer 初始化成功 (provider: {self.indexer.embed_provider})")
            except Exception as e:
                logger.warning(f"⚠️ [Service] Indexer 初始化失敗: {e}")
            
            # Retriever (Cohere/OpenAI embedding)
            try:
                self.retriever = get_retriever()
                logger.info(f"✅ [Service] Retriever 初始化成功 (provider: {self.retriever.embed_provider})")
            except Exception as e:
                logger.warning(f"⚠️ [Service] Retriever 初始化失敗: {e}")
            
            # Parser (多模態解析器 - 支援圖片和多種格式)
            try:
                self.parser = get_multimodal_parser()
                logger.info("✅ [Service] MultimodalParser 初始化成功（支援圖片分析）")
                logger.info(f"   支援格式: {', '.join(SUPPORTED_FORMATS.keys())}")
            except Exception as e:
                logger.warning(f"⚠️ [Service] Parser 初始化失敗: {e}")
            
            # OpenAI client (用於回答生成)
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("BASE_URL", "https://api.openai.com")
            if api_key:
                try:
                    from openai import AsyncOpenAI
                    self.openai_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
                    logger.info("✅ [Service] OpenAI client 初始化成功 (用於回答生成)")
                except Exception as e:
                    logger.warning(f"⚠️ [Service] OpenAI client 初始化失敗: {e}")
            else:
                logger.warning("⚠️ [Service] OPENAI_API_KEY 未設定，回答生成功能不可用")
            
            self._initialized = True
            logger.info("🎉 [Service] KnowledgeBase 服務初始化完成")
            
        except Exception as e:
            logger.error(f"❌ [Service] 初始化失敗: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def execute(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行方法
        
        Args:
            method: 方法名稱
            params: 參數
            
        Returns:
            執行結果
        """
        if not self._initialized:
            await self.initialize()
        
        logger.info(f"📌 [Service] 執行方法: {method}")
        logger.info(f"📌 [Service] 參數: {params}")
        
        if method == "rag_search":
            return await self._search(
                query=params.get("query", ""),
                top_k=params.get("top_k", 5),
                filters=params.get("filters")
            )
        
        elif method == "rag_search_multiple":
            return await self._search_multiple(
                queries=params.get("queries", []),
                top_k=params.get("top_k", 3),
                filters=params.get("filters")
            )
        
        elif method == "rag_ask":
            return await self._ask(
                question=params.get("question", ""),
                top_k=params.get("top_k", 5),
                filters=params.get("filters")
            )
        
        elif method == "document_list":
            return await self._list_documents()
        
        elif method == "document_delete":
            return await self._delete_document(params.get("document_name", ""))
        
        elif method == "get_stats":
            return await self._get_stats()
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    async def health_check(self) -> bool:
        """健康檢查"""
        try:
            if self.retriever and self.retriever.qdrant_client:
                self.retriever.qdrant_client.get_collections()
            return True
        except:
            return False
    
    async def shutdown(self) -> None:
        """關閉服務"""
        logger.info(f"🛑 [Service] {self.service_id} shutdown")
        reset_indexer()
        reset_retriever()
    
    # ========== LongTermMemoryProtocol ==========
    
    async def store(
        self, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """儲存內容"""
        if not self.indexer:
            raise RuntimeError("Indexer not initialized")
        
        doc_id = str(uuid.uuid4())
        
        documents = [{
            "text": content,
            "metadata": {
                "doc_id": doc_id,
                "type": "memory",
                **(metadata or {})
            }
        }]
        
        self.indexer.index_documents(documents)
        return doc_id
    
    async def retrieve(
        self, 
        query: str, 
        top_k: int = 5, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """檢索內容"""
        if not self.retriever:
            raise RuntimeError("Retriever not initialized")
        
        results = self.retriever.search(query, top_k=top_k, filters=filters)
        
        return [
            {
                "content": r["text"],
                "metadata": r.get("metadata", {}),
                "score": r["score"]
            }
            for r in results
        ]
    
    async def delete(self, doc_id: str) -> bool:
        """刪除內容"""
        # TODO: 實現按 doc_id 刪除
        return True
    
    # ========== 內部方法 ==========
    
    async def _search(
        self, 
        query: str, 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """語意搜尋"""
        logger.info(f"🔍 [Service] 搜尋: {query[:50]}...")
        
        if not self.retriever:
            return {
                "query": query,
                "results": [],
                "sources": [],
                "error": "Retriever 未初始化"
            }
        
        results = self.retriever.search(query, top_k=top_k, filters=filters)
        
        return {
            "query": query,
            "results": results,
            "sources": [
                {
                    "file_name": r.get("file_name", "unknown"),
                    "page_label": r.get("page_label", "?"),
                    "score": r.get("score", 0),
                    "summary": r.get("text", "")[:100] + "..."
                }
                for r in results
            ]
        }
    
    async def _search_multiple(
        self, 
        queries: List[str], 
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """多查詢搜尋"""
        logger.info(f"🔍 [Service] 多查詢搜尋: {len(queries)} 個查詢")
        
        if not self.retriever:
            return {
                "queries": queries,
                "results": [],
                "sources": [],
                "error": "Retriever 未初始化"
            }
        
        result = self.retriever.search_multiple(queries, top_k=top_k, filters=filters)
        
        return {
            "queries": queries,
            "results": result.get("results", []),
            "sources": [
                {
                    "file_name": r.get("file_name", "unknown"),
                    "page_label": r.get("page_label", "?"),
                    "score": r.get("score", 0)
                }
                for r in result.get("results", [])
            ],
            "total_unique_results": result.get("total", 0)
        }
    
    async def _ask(
        self, 
        question: str, 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """問答生成"""
        logger.info(f"❓ [Service] 問答: {question[:50]}...")
        
        # 先搜尋相關內容
        search_result = await self._search(question, top_k=top_k, filters=filters)
        
        results = search_result.get("results", [])
        sources = search_result.get("sources", [])
        
        if not results:
            return {
                "question": question,
                "answer": "抱歉，在知識庫中沒有找到相關資訊。",
                "sources": [],
                "context_used": 0
            }
        
        # 建構上下文
        context = "\n\n---\n\n".join([
            f"[來源: {r.get('file_name', '未知')}, 第{r.get('page_label', '?')}頁]\n{r.get('text', '')}"
            for r in results
        ])
        
        # 使用 OpenAI 生成回答
        if not self.openai_client:
            return {
                "question": question,
                "answer": "OpenAI client 未初始化，無法生成回答。\n\n相關內容：\n" + context[:500],
                "sources": sources,
                "context_used": len(results)
            }
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": """你是一個專業的知識助手。根據提供的參考資料回答問題。

回答規範：
1. 只根據提供的參考資料回答，不要編造
2. 使用繁體中文
3. 回答要清晰、有結構
4. 如果資料不足以回答，誠實說明"""
                    },
                    {
                        "role": "user",
                        "content": f"""參考資料：
{context}

問題：{question}

請根據以上資料回答問題。"""
                    }
                ],
                temperature=0.3
            )
            
            answer = response.choices[0].message.content
            
            return {
                "question": question,
                "answer": answer,
                "sources": sources,
                "context_used": len(results)
            }
            
        except Exception as e:
            logger.error(f"❌ [Service] 回答生成失敗: {e}")
            return {
                "question": question,
                "answer": f"生成回答時發生錯誤: {str(e)}",
                "sources": sources,
                "context_used": len(results)
            }
    
    async def _list_documents(self) -> Dict[str, Any]:
        """列出所有文件"""
        logger.info("📋 [Service] 列出所有文件")
        
        if not self.retriever or not self.retriever.qdrant_client:
            return {"documents": [], "error": "Qdrant client 未初始化"}
        
        try:
            # 獲取所有文件名
            results, _ = self.retriever.qdrant_client.scroll(
                collection_name=self.collection_name,
                limit=1000,
                with_payload=["file_name", "page_label"],
                with_vectors=False
            )
            
            # 統計每個文件
            file_stats = {}
            for point in results:
                file_name = point.payload.get("file_name", "unknown")
                if file_name not in file_stats:
                    file_stats[file_name] = {"chunks": 0, "pages": set()}
                file_stats[file_name]["chunks"] += 1
                file_stats[file_name]["pages"].add(point.payload.get("page_label", "1"))
            
            documents = [
                {
                    "name": name,
                    "chunks": stats["chunks"],
                    "pages": len(stats["pages"])
                }
                for name, stats in file_stats.items()
            ]
            
            logger.info(f"📋 [Service] 找到 {len(documents)} 個文件")
            
            return {"documents": documents}
            
        except Exception as e:
            logger.error(f"❌ [Service] 列出文件失敗: {e}")
            return {"documents": [], "error": str(e)}
    
    async def _delete_document(self, document_name: str) -> Dict[str, Any]:
        """刪除文件"""
        logger.info(f"🗑️ [Service] 刪除文件: {document_name}")
        
        if not self.indexer:
            return {"success": False, "error": "Indexer 未初始化"}
        
        try:
            deleted = self.indexer.delete_by_filename(document_name)
            
            return {
                "success": True,
                "document_name": document_name,
                "deleted_chunks": deleted
            }
            
        except Exception as e:
            logger.error(f"❌ [Service] 刪除失敗: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_stats(self) -> Dict[str, Any]:
        """取得統計資訊"""
        logger.info("📊 [Service] 取得統計")
        
        if not self.indexer:
            return {"error": "Indexer 未初始化"}
        
        stats = self.indexer.get_stats()
        
        # 加入文件統計
        doc_result = await self._list_documents()
        stats["documents"] = doc_result.get("documents", [])
        stats["document_count"] = len(stats["documents"])
        
        return stats
