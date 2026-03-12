"""
Indexer - 使用 Cohere Embedding 索引文件到 Qdrant
支援 Cohere 和 OpenAI 雙 provider
新增：自動重試、速率限制處理、回退機制
"""

import os
import logging
import uuid
import time
from typing import List, Dict, Any, Optional

# 使用統一的路徑工具載入環境變數
from core.utils import load_env
load_env()

logger = logging.getLogger(__name__)

# 全域實例
_indexer_instance = None


class Indexer:
    """
    文件索引器 - 支援 Cohere 和 OpenAI embedding
    
    Cohere 優勢：
    1. 多語言支援 (embed-multilingual-v3.0)
    2. 區分 document 和 query embedding (input_type)
    3. 較低成本
    
    新增功能：
    - 自動重試 (最多 3 次，帶指數退避)
    - 速率限制處理 (429 錯誤時延遲重試)
    - 回退機制 (Cohere 失敗時使用 OpenAI)
    - 批量 embedding (減少 API 調用)
    """
    
    def __init__(
        self,
        collection_name: str = "rag_knowledge_base",
        qdrant_url: str = "http://localhost:6333"
    ):
        self.collection_name = collection_name
        self.qdrant_url = qdrant_url
        
        # API clients
        self.cohere_client = None
        self.openai_client = None
        self.qdrant_client = None
        
        # Embedding 設定
        self.embed_provider = None
        self.embed_model = None
        self.embed_dim = None
        
        # 重試設定
        self.max_retries = 3
        self.base_delay = 2  # 基礎延遲秒數
        self.batch_size = 20  # 批量處理大小
        
        # 是否有 OpenAI 作為備用
        self._has_openai_fallback = False
        
        self._initialize()
    
    def _initialize(self):
        """初始化 clients 和設定"""
        # 確保環境變數已載入
        load_env()

        cohere_key = os.getenv("COHERE_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        openai_base_url = os.getenv("BASE_URL", "https://api.openai.com")

        # 讀取用戶指定的 embedding provider (預設為 openai)
        preferred_provider = os.getenv("EMBEDDING_PROVIDER", "openai").lower()

        # 根據用戶配置初始化 provider
        if preferred_provider == "openai" and openai_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=openai_key, base_url=openai_base_url)
                self.embed_provider = "openai"
                self.embed_model = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
                # 從環境變數讀取維度，或根據模型推斷
                self.embed_dim = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
                logger.info(f"✅ [Indexer] 使用 OpenAI embedding: {self.embed_model} ({self.embed_dim}維)")
            except ImportError:
                logger.warning("⚠️ [Indexer] openai 套件未安裝")
            except Exception as e:
                logger.error(f"❌ [Indexer] OpenAI 初始化失敗: {e}")

        elif preferred_provider == "cohere" and cohere_key:
            try:
                import cohere
                self.cohere_client = cohere.Client(api_key=cohere_key)
                self.embed_provider = "cohere"
                self.embed_model = os.getenv("COHERE_EMBED_MODEL", "embed-multilingual-v3.0")
                self.embed_dim = 1024  # Cohere v3 模型固定 1024 維
                logger.info(f"✅ [Indexer] 使用 Cohere embedding: {self.embed_model} ({self.embed_dim}維)")
            except ImportError:
                logger.warning("⚠️ [Indexer] cohere 套件未安裝")
            except Exception as e:
                logger.error(f"❌ [Indexer] Cohere 初始化失敗: {e}")

        # 初始化備用 provider
        if preferred_provider == "openai" and cohere_key and not self.cohere_client:
            try:
                import cohere
                self.cohere_client = cohere.Client(api_key=cohere_key)
                self._has_openai_fallback = True
                logger.info(f"✅ [Indexer] Cohere 作為備用 embedding provider")
            except:
                pass

        elif preferred_provider == "cohere" and openai_key and not self.openai_client:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=openai_key, base_url=openai_base_url)
                self._has_openai_fallback = True
                logger.info(f"✅ [Indexer] OpenAI 作為備用 embedding provider")
            except:
                pass
        
        if not self.cohere_client and not self.openai_client:
            logger.error("❌ [Indexer] 沒有可用的 embedding provider！")
            logger.error("   請設定 COHERE_API_KEY 或 OPENAI_API_KEY")
            raise ValueError("需要設定 COHERE_API_KEY 或 OPENAI_API_KEY")
        
        # 初始化 Qdrant
        self._init_qdrant()
    
    def _init_qdrant(self):
        """初始化 Qdrant client 和 collection"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            
            self.qdrant_client = QdrantClient(url=self.qdrant_url)
            
            # 檢查 collection 是否存在
            collections = self.qdrant_client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                # 創建新 collection
                logger.info(f"📦 [Indexer] 創建新 collection: {self.collection_name}")
                logger.info(f"📦 [Indexer] 向量維度: {self.embed_dim}")
                
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embed_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ [Indexer] Collection 創建成功")
            else:
                # 檢查維度是否匹配
                collection_info = self.qdrant_client.get_collection(self.collection_name)
                existing_dim = collection_info.config.params.vectors.size
                
                if existing_dim != self.embed_dim:
                    logger.warning(f"⚠️ [Indexer] 維度不匹配！")
                    logger.warning(f"   Collection 維度: {existing_dim}")
                    logger.warning(f"   當前 provider 維度: {self.embed_dim}")
                    logger.warning(f"   請重置 collection 或切換 embedding provider")
                else:
                    logger.info(f"✅ [Indexer] Collection 已存在，維度匹配: {existing_dim}")
                    
        except Exception as e:
            logger.error(f"❌ [Indexer] Qdrant 初始化失敗: {e}")
            raise
    
    def get_embedding(self, text: str, input_type: str = "search_document") -> List[float]:
        """
        取得文字的 embedding 向量（帶重試和回退）
        
        Args:
            text: 輸入文字
            input_type: Cohere 專用
                - "search_document": 索引文件時使用
                - "search_query": 查詢時使用
                
        Returns:
            embedding 向量
        """
        if self.cohere_client and self.embed_provider == "cohere":
            try:
                return self._get_cohere_embedding_with_retry(text, input_type)
            except Exception as e:
                if self._has_openai_fallback:
                    logger.warning(f"⚠️ [Indexer] Cohere 失敗，回退到 OpenAI: {e}")
                    return self._get_openai_embedding(text)
                raise
        else:
            return self._get_openai_embedding(text)
    
    def get_embeddings_batch(self, texts: List[str], input_type: str = "search_document") -> List[List[float]]:
        """
        批量取得 embedding（減少 API 調用次數）
        
        Args:
            texts: 文字列表
            input_type: Cohere 專用
            
        Returns:
            embedding 向量列表
        """
        if self.cohere_client and self.embed_provider == "cohere":
            try:
                return self._get_cohere_embeddings_batch_with_retry(texts, input_type)
            except Exception as e:
                if self._has_openai_fallback:
                    logger.warning(f"⚠️ [Indexer] Cohere 批量失敗，回退到 OpenAI: {e}")
                    return self._get_openai_embeddings_batch(texts)
                raise
        else:
            return self._get_openai_embeddings_batch(texts)
    
    def _get_cohere_embedding_with_retry(self, text: str, input_type: str) -> List[float]:
        """使用 Cohere 取得 embedding（帶重試）"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.cohere_client.embed(
                    texts=[text],
                    model=self.embed_model,
                    input_type=input_type
                )
                return response.embeddings[0]
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                # 檢查是否是速率限制錯誤
                if "429" in error_str or "rate" in error_str.lower() or "too many" in error_str.lower():
                    delay = self.base_delay * (2 ** attempt)  # 指數退避
                    logger.warning(f"⚠️ [Indexer] 速率限制，等待 {delay} 秒後重試 (嘗試 {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                else:
                    # 其他錯誤直接拋出
                    logger.error(f"❌ [Indexer] Cohere embedding 失敗: {e}")
                    raise
        
        # 所有重試都失敗
        logger.error(f"❌ [Indexer] Cohere embedding 重試 {self.max_retries} 次後仍失敗")
        raise last_error
    
    def _get_cohere_embeddings_batch_with_retry(self, texts: List[str], input_type: str) -> List[List[float]]:
        """批量 Cohere embedding（帶重試）"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.cohere_client.embed(
                    texts=texts,
                    model=self.embed_model,
                    input_type=input_type
                )
                return response.embeddings
                
            except Exception as e:
                last_error = e
                error_str = str(e)
                
                if "429" in error_str or "rate" in error_str.lower() or "too many" in error_str.lower():
                    delay = self.base_delay * (2 ** attempt)
                    logger.warning(f"⚠️ [Indexer] 速率限制，等待 {delay} 秒後重試 (嘗試 {attempt + 1}/{self.max_retries})")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ [Indexer] Cohere 批量 embedding 失敗: {e}")
                    raise
        
        logger.error(f"❌ [Indexer] Cohere 批量 embedding 重試 {self.max_retries} 次後仍失敗")
        raise last_error
    
    def _get_openai_embedding(self, text: str) -> List[float]:
        """使用 OpenAI 取得 embedding"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"❌ [Indexer] OpenAI embedding 失敗: {e}")
            raise
    
    def _get_openai_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """批量 OpenAI embedding"""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            # 按原始順序返回
            return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        except Exception as e:
            logger.error(f"❌ [Indexer] OpenAI 批量 embedding 失敗: {e}")
            raise
    
    def index_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        索引文件到 Qdrant（使用批量處理）
        
        Args:
            documents: 文件列表，每個包含 text 和 metadata
            
        Returns:
            成功索引的數量
        """
        if not documents:
            logger.warning("⚠️ [Indexer] 沒有文件需要索引")
            return 0
        
        from qdrant_client.models import PointStruct
        
        logger.info(f"💾 [Indexer] ====== 開始索引 ======")
        logger.info(f"💾 [Indexer] 文件數量: {len(documents)}")
        logger.info(f"💾 [Indexer] Provider: {self.embed_provider}")
        logger.info(f"💾 [Indexer] 批量大小: {self.batch_size}")
        if self._has_openai_fallback:
            logger.info(f"💾 [Indexer] 備用 Provider: OpenAI")
        
        points = []
        success_count = 0
        
        # 批量處理
        for batch_start in range(0, len(documents), self.batch_size):
            batch_end = min(batch_start + self.batch_size, len(documents))
            batch = documents[batch_start:batch_end]
            
            # 準備批量文本
            texts = []
            valid_docs = []
            
            for doc in batch:
                text = doc.get("text", "")
                if text.strip():
                    texts.append(text)
                    valid_docs.append(doc)
            
            if not texts:
                continue
            
            try:
                # 批量獲取 embedding
                logger.info(f"💾 [Indexer] 處理批次 {batch_start + 1}-{batch_end}/{len(documents)}...")
                embeddings = self.get_embeddings_batch(texts, input_type="search_document")
                
                # 創建 points
                for i, (doc, vector) in enumerate(zip(valid_docs, embeddings)):
                    metadata = doc.get("metadata", {})
                    payload = {
                        "text": doc["text"],
                        **metadata
                    }
                    
                    points.append(PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload=payload
                    ))
                    success_count += 1
                
                # 每批次後短暫延遲，避免速率限制
                if batch_end < len(documents):
                    time.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"❌ [Indexer] 批次 {batch_start + 1}-{batch_end} 失敗: {e}")
                
                # 如果批量失敗，嘗試逐個處理
                logger.info(f"🔄 [Indexer] 嘗試逐個處理...")
                for doc in valid_docs:
                    try:
                        text = doc.get("text", "")
                        vector = self.get_embedding(text, input_type="search_document")
                        
                        metadata = doc.get("metadata", {})
                        payload = {
                            "text": text,
                            **metadata
                        }
                        
                        points.append(PointStruct(
                            id=str(uuid.uuid4()),
                            vector=vector,
                            payload=payload
                        ))
                        success_count += 1
                        
                        # 逐個處理時延遲更長
                        time.sleep(1)
                        
                    except Exception as e2:
                        logger.error(f"❌ [Indexer] 單個文件也失敗: {e2}")
        
        # 批次寫入 Qdrant
        if points:
            try:
                self.qdrant_client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"✅ [Indexer] 成功索引 {success_count} 個文件")
            except Exception as e:
                logger.error(f"❌ [Indexer] Qdrant 寫入失敗: {e}")
                raise
        
        return success_count
    
    def delete_by_filename(self, file_name: str) -> int:
        """
        刪除指定檔案的所有向量
        
        Args:
            file_name: 檔案名稱
            
        Returns:
            刪除的向量數量
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        try:
            # 先計算要刪除多少
            count_result = self.qdrant_client.count(
                collection_name=self.collection_name,
                count_filter=Filter(
                    must=[FieldCondition(key="file_name", match=MatchValue(value=file_name))]
                )
            )
            count = count_result.count
            
            if count > 0:
                # 執行刪除
                self.qdrant_client.delete(
                    collection_name=self.collection_name,
                    points_selector=Filter(
                        must=[FieldCondition(key="file_name", match=MatchValue(value=file_name))]
                    )
                )
                logger.info(f"🗑️ [Indexer] 已刪除 {count} 個向量 (file: {file_name})")
            
            return count
            
        except Exception as e:
            logger.error(f"❌ [Indexer] 刪除失敗: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """取得索引統計"""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return {
                "collection": self.collection_name,
                "points_count": collection_info.points_count,
                "status": str(collection_info.status),
                "embed_provider": self.embed_provider,
                "embed_model": self.embed_model,
                "embed_dim": self.embed_dim,
                "has_fallback": self._has_openai_fallback
            }
        except Exception as e:
            logger.error(f"❌ [Indexer] 取得統計失敗: {e}")
            return {"error": str(e)}


def get_indexer() -> Indexer:
    """取得全域 Indexer 實例"""
    global _indexer_instance
    if _indexer_instance is None:
        _indexer_instance = Indexer()
    return _indexer_instance


def reset_indexer():
    """重置全域 Indexer 實例"""
    global _indexer_instance
    _indexer_instance = None
