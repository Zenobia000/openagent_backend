"""
Knowledge Base Service - RAG 知識庫服務
從 rag-project 遷移並增強
"""

from typing import List, Dict, Any, Optional
import logging
import os
import uuid
from pathlib import Path

# 使用統一的路徑工具載入環境變數
from opencode.core.utils import load_env, get_project_root
load_env()

from opencode.core.protocols import MCPServiceProtocol, LongTermMemoryProtocol

logger = logging.getLogger(__name__)


class KnowledgeBaseService(MCPServiceProtocol, LongTermMemoryProtocol):
    """
    知識庫服務
    
    功能:
    - 語意搜尋 (rag_search)
    - 多查詢搜尋 (rag_search_multiple)
    - 問答生成 (rag_ask)
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
        
        # 客戶端
        self.qdrant_client = None
        self.openai_client = None
        
        # 配置
        self.collection_name = self.config.get("collection", "rag_knowledge_base")
        self.qdrant_host = self.config.get("qdrant_host", "localhost")
        self.qdrant_port = self.config.get("qdrant_port", 6333)
        self.embedding_model = self.config.get("embedding_model", "text-embedding-3-small")
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
        try:
            from qdrant_client import QdrantClient
            
            # 強制重新載入 .env（確保環境變數可用）
            load_dotenv(_env_path, override=True)
            
            # Qdrant 客戶端 (必需)
            self.qdrant_client = QdrantClient(
                host=self.qdrant_host,
                port=self.qdrant_port
            )
            
            # OpenAI 客戶端 (可選，用於 embedding)
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                from openai import AsyncOpenAI
                self.openai_client = AsyncOpenAI(api_key=api_key)
            else:
                logger.warning("OPENAI_API_KEY not set - search/ask features will be limited")
                self.openai_client = None
            
            # 確保 collection 存在
            await self._ensure_collection()
            
            self._initialized = True
            logger.info(f"✅ {self.service_id} initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize {self.service_id}: {e}")
            raise
    
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
            if self.qdrant_client:
                self.qdrant_client.get_collections()
            return True
        except:
            return False
    
    async def shutdown(self) -> None:
        """關閉服務"""
        logger.info(f"{self.service_id} shutdown")
    
    # ========== LongTermMemoryProtocol ==========
    
    async def store(
        self, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """儲存內容"""
        from qdrant_client.models import PointStruct
        
        doc_id = str(uuid.uuid4())
        embedding = await self._get_embedding(content)
        
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=doc_id,
                    vector=embedding,
                    payload={
                        "text": content,
                        **(metadata or {})
                    }
                )
            ]
        )
        
        return doc_id
    
    async def retrieve(
        self, 
        query: str, 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """檢索內容"""
        result = await self._search(query, top_k, filters)
        return result.get("results", [])
    
    async def delete(self, doc_id: str) -> bool:
        """刪除內容"""
        try:
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=[doc_id]
            )
            return True
        except:
            return False
    
    # ========== 內部方法 ==========
    
    async def _ensure_collection(self) -> None:
        """確保 collection 存在"""
        from qdrant_client.models import VectorParams, Distance
        
        try:
            collections = self.qdrant_client.get_collections()
            names = [c.name for c in collections.collections]
            
            if self.collection_name not in names:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # text-embedding-3-small 維度
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
        except Exception as e:
            logger.warning(f"Could not ensure collection: {e}")
    
    async def _get_embedding(self, text: str) -> List[float]:
        """取得文字向量"""
        if self.openai_client is None:
            raise RuntimeError("OpenAI client not initialized. Please set OPENAI_API_KEY environment variable.")
        
        text = text.replace("\n", " ")
        response = await self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    async def _search(
        self, 
        query: str, 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """語意搜尋"""
        logger.info(f"🔍 開始搜尋: query='{query[:50]}...', top_k={top_k}, filters={filters}")
        
        if self.openai_client is None:
            logger.error("❌ OpenAI client 未初始化")
            return {
                "query": query,
                "results": [],
                "sources": [],
                "error": "OPENAI_API_KEY 未設置，無法執行語意搜尋"
            }
        
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        try:
            query_vector = await self._get_embedding(query)
            logger.info(f"✅ Embedding 生成成功, 維度: {len(query_vector)}")
        except Exception as e:
            logger.error(f"❌ Embedding 生成失敗: {e}")
            return {"query": query, "results": [], "sources": [], "error": str(e)}
        
        # 建構過濾條件
        search_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                logger.info(f"📋 建構過濾條件: {key}={value}")
                if isinstance(value, list):
                    # 多值篩選 (OR)
                    conditions.append(Filter(should=[
                        FieldCondition(key=key, match=MatchValue(value=v))
                        for v in value
                    ]))
                else:
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
            if conditions:
                search_filter = Filter(must=conditions)
                logger.info(f"📋 過濾條件已建構: {len(conditions)} 個條件")
        
        # 執行搜尋
        try:
            results = self.qdrant_client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=search_filter,
                limit=top_k,
                with_payload=True
            )
            logger.info(f"✅ Qdrant 搜尋完成, 找到 {len(results.points)} 個結果")
            
            # 詳細記錄每個結果
            for i, p in enumerate(results.points):
                payload_keys = list(p.payload.keys()) if p.payload else []
                file_name = p.payload.get("file_name", "NOT_FOUND")
                text_preview = p.payload.get("text", "")[:50] if p.payload else ""
                logger.info(f"  [{i+1}] score={p.score:.4f}, file={file_name}, payload_keys={payload_keys}")
                logger.debug(f"      text_preview: {text_preview}...")
                
        except Exception as e:
            logger.error(f"❌ Qdrant 搜尋失敗: {e}")
            return {"query": query, "results": [], "sources": [], "error": str(e)}
        
        return {
            "query": query,
            "results": [
                {
                    "text": p.payload.get("text", ""),
                    "file_name": p.payload.get("file_name", "unknown"),
                    "page_label": p.payload.get("page_label", "?"),
                    "score": p.score
                }
                for p in results.points
            ],
            "sources": [
                {
                    "file_name": p.payload.get("file_name", "unknown"),
                    "page_label": p.payload.get("page_label", "?"),
                    "score": p.score,
                    "summary": p.payload.get("text", "")[:100] + "..."
                }
                for p in results.points
            ]
        }
    
    async def _search_multiple(
        self, 
        queries: List[str], 
        top_k: int = 3,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """多查詢搜尋 - 支持口語化問題的多角度檢索"""
        all_results = []
        all_sources = []
        seen_texts = set()  # 用於去重
        
        for query in queries:
            result = await self._search(query, top_k, filters)
            
            # 收集結果並去重
            unique_results = []
            for r in result["results"]:
                # 使用文本的前100字符作為去重鍵
                text_key = r["text"][:100] if r["text"] else ""
                if text_key and text_key not in seen_texts:
                    seen_texts.add(text_key)
                    unique_results.append(r)
                    
            all_results.append({
                "query": query,
                "results": unique_results
            })
            
            # 收集來源（去重）
            for source in result.get("sources", []):
                key = (source.get("file_name", ""), source.get("page_label", ""))
                if key not in [(s.get("file_name"), s.get("page_label")) for s in all_sources]:
                    all_sources.append(source)
        
        return {
            "queries": queries,
            "results": all_results,
            "sources": all_sources,
            "total_unique_results": len(seen_texts)
        }
    
    async def _ask(
        self, 
        question: str, 
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """問答生成"""
        if self.openai_client is None:
            return {
                "answer": "錯誤：OPENAI_API_KEY 未設置，無法使用問答功能。",
                "sources": []
            }
        
        # 先搜尋（傳入 filters）
        search_result = await self._search(question, top_k, filters)
        results = search_result.get("results", [])
        
        if not results:
            return {
                "answer": "知識庫中沒有找到相關資訊。",
                "sources": []
            }
        
        # 建構 context
        context_parts = []
        for i, r in enumerate(results, 1):
            context_parts.append(
                f"[{i}] 來源: {r['file_name']} (頁 {r['page_label']})\n{r['text']}"
            )
        context = "\n\n".join(context_parts)
        
        # 生成回答
        messages = [
            {
                "role": "system",
                "content": """你是一個專業的企業知識庫助手。根據提供的參考資料回答用戶問題。

規則：
- 用繁體中文回答
- 基於參考資料回答，不要編造
- 回答要有結構，清晰明確
- 如果資料不足以回答，誠實說明"""
            },
            {
                "role": "user",
                "content": f"參考資料:\n{context}\n\n問題: {question}"
            }
        ]
        
        response = await self.openai_client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=0.7
        )
        
        answer = response.choices[0].message.content
        
        return {
            "answer": answer,
            "sources": search_result.get("sources", [])
        }
    
    async def _list_documents(self) -> Dict[str, Any]:
        """列出所有文件"""
        try:
            # Scroll 取得所有文件名稱
            documents = {}
            offset = None
            
            while True:
                results, offset = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                
                for point in results:
                    file_name = point.payload.get("file_name", "unknown")
                    if file_name not in documents:
                        documents[file_name] = {
                            "name": file_name,
                            "chunks": 0
                        }
                    documents[file_name]["chunks"] += 1
                
                if offset is None:
                    break
            
            return {
                "documents": list(documents.values()),
                "total": len(documents)
            }
            
        except Exception as e:
            logger.error(f"List documents failed: {e}")
            return {"documents": [], "total": 0, "error": str(e)}
    
    async def _delete_document(self, document_name: str) -> Dict[str, Any]:
        """刪除文件"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        try:
            self.qdrant_client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="file_name",
                            match=MatchValue(value=document_name)
                        )
                    ]
                )
            )
            
            logger.info(f"Deleted document: {document_name}")
            return {"success": True, "message": f"Deleted: {document_name}"}
            
        except Exception as e:
            logger.error(f"Delete document failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _get_stats(self) -> Dict[str, Any]:
        """取得統計資訊"""
        try:
            info = self.qdrant_client.get_collection(self.collection_name)
            docs = await self._list_documents()
            
            return {
                "document_count": docs.get("total", 0),
                "total_chunks": info.points_count,
                "vector_dim": info.config.params.vectors.size,
                "index_size": f"{info.points_count * 1536 * 4 / 1024:.1f} KB"
            }
        except Exception as e:
            return {"error": str(e)}
