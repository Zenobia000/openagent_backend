"""
向量資料庫 Collection 管理服務

讓用戶可以:
- 創建多個 Collection（知識庫）
- 為不同類型的資料建立獨立的向量空間
- 管理和切換不同的知識庫
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from opencode.core.utils import get_project_root, load_env

load_env()
logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Embedding 提供者"""
    COHERE = "cohere"
    OPENAI = "openai"


@dataclass
class CollectionConfig:
    """Collection 配置"""
    id: str
    name: str
    display_name: str
    description: str = ""
    embedding_provider: EmbeddingProvider = EmbeddingProvider.COHERE
    embedding_model: str = "embed-multilingual-v3.0"
    vector_size: int = 1024
    distance: str = "Cosine"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    document_count: int = 0
    is_default: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["embedding_provider"] = self.embedding_provider.value
        return data


class CollectionManager:
    """
    Collection 管理器
    
    管理多個 Qdrant Collection
    """
    
    # 預設配置
    DEFAULT_CONFIGS = {
        "cohere": {
            "model": "embed-multilingual-v3.0",
            "vector_size": 1024
        },
        "openai": {
            "model": "text-embedding-3-small",
            "vector_size": 1536
        }
    }
    
    def __init__(self):
        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
        
        self.data_dir = get_project_root() / "data" / "collections"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.data_dir / "collections.json"
        
        self._collections: Dict[str, CollectionConfig] = {}
        self._client: Optional[QdrantClient] = None
        
        self._init_client()
        self._load_collections()
        self._ensure_default_collection()
        
        logger.info(f"✅ CollectionManager initialized, {len(self._collections)} collections")
    
    def _init_client(self) -> None:
        """初始化 Qdrant 客戶端"""
        try:
            self._client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
            self._client.get_collections()
            logger.info(f"✅ Qdrant connected: {self.qdrant_host}:{self.qdrant_port}")
        except Exception as e:
            logger.error(f"❌ Qdrant connection failed: {e}")
            self._client = None
    
    def _load_collections(self) -> None:
        """載入 Collection 配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for coll_data in data.get("collections", []):
                    coll = CollectionConfig(
                        id=coll_data["id"],
                        name=coll_data["name"],
                        display_name=coll_data.get("display_name", coll_data["name"]),
                        description=coll_data.get("description", ""),
                        embedding_provider=EmbeddingProvider(coll_data.get("embedding_provider", "cohere")),
                        embedding_model=coll_data.get("embedding_model", "embed-multilingual-v3.0"),
                        vector_size=coll_data.get("vector_size", 1024),
                        distance=coll_data.get("distance", "Cosine"),
                        created_at=coll_data.get("created_at", datetime.utcnow().isoformat()),
                        document_count=coll_data.get("document_count", 0),
                        is_default=coll_data.get("is_default", False)
                    )
                    self._collections[coll.id] = coll
                    
            except Exception as e:
                logger.error(f"Failed to load collections config: {e}")
    
    def _save_collections(self) -> None:
        """保存 Collection 配置"""
        try:
            data = {
                "collections": [coll.to_dict() for coll in self._collections.values()]
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save collections config: {e}")
    
    def _ensure_default_collection(self) -> None:
        """確保有預設 Collection"""
        # 檢查是否有預設
        has_default = any(c.is_default for c in self._collections.values())
        
        if not has_default:
            # 創建預設 Collection
            default_name = "rag_knowledge_base"
            if default_name not in [c.name for c in self._collections.values()]:
                self.create_collection(
                    name=default_name,
                    display_name="預設知識庫",
                    description="預設的 RAG 知識庫",
                    embedding_provider="cohere",
                    is_default=True
                )
            else:
                # 將現有的設為預設
                for coll in self._collections.values():
                    if coll.name == default_name:
                        coll.is_default = True
                        self._save_collections()
                        break
    
    def create_collection(
        self,
        name: str,
        display_name: str,
        description: str = "",
        embedding_provider: str = "cohere",
        embedding_model: str = None,
        is_default: bool = False
    ) -> CollectionConfig:
        """創建新 Collection"""
        if not self._client:
            raise RuntimeError("Qdrant not connected")
        
        # 根據 provider 設定
        provider = EmbeddingProvider(embedding_provider)
        config = self.DEFAULT_CONFIGS.get(embedding_provider, self.DEFAULT_CONFIGS["cohere"])
        
        if embedding_model:
            model = embedding_model
            # 根據模型推斷維度
            if "3-large" in model:
                vector_size = 3072
            elif "3-small" in model:
                vector_size = 1536
            elif "ada" in model:
                vector_size = 1536
            else:
                vector_size = config["vector_size"]
        else:
            model = config["model"]
            vector_size = config["vector_size"]
        
        # 生成 ID
        import hashlib
        coll_id = hashlib.md5(f"{name}-{datetime.utcnow().timestamp()}".encode()).hexdigest()[:12]
        
        # 在 Qdrant 創建 Collection
        try:
            # 檢查是否已存在
            existing = self._client.get_collections().collections
            existing_names = [c.name for c in existing]
            
            if name not in existing_names:
                self._client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Created Qdrant collection: {name}")
            else:
                logger.info(f"ℹ️ Collection already exists: {name}")
        except Exception as e:
            logger.error(f"Failed to create Qdrant collection: {e}")
            raise
        
        # 如果設為預設，取消其他的預設
        if is_default:
            for coll in self._collections.values():
                coll.is_default = False
        
        # 創建配置
        coll = CollectionConfig(
            id=coll_id,
            name=name,
            display_name=display_name,
            description=description,
            embedding_provider=provider,
            embedding_model=model,
            vector_size=vector_size,
            is_default=is_default
        )
        
        self._collections[coll_id] = coll
        self._save_collections()
        
        logger.info(f"✅ Created collection config: {display_name} ({coll_id})")
        return coll
    
    def delete_collection(self, coll_id: str, delete_qdrant: bool = True) -> bool:
        """刪除 Collection"""
        coll = self._collections.get(coll_id)
        if not coll:
            return False
        
        if coll.is_default:
            raise ValueError("Cannot delete default collection")
        
        # 從 Qdrant 刪除
        if delete_qdrant and self._client:
            try:
                self._client.delete_collection(coll.name)
                logger.info(f"🗑️ Deleted Qdrant collection: {coll.name}")
            except Exception as e:
                logger.warning(f"Failed to delete Qdrant collection: {e}")
        
        del self._collections[coll_id]
        self._save_collections()
        
        return True
    
    def update_collection(self, coll_id: str, updates: Dict[str, Any]) -> Optional[CollectionConfig]:
        """更新 Collection 配置"""
        coll = self._collections.get(coll_id)
        if not coll:
            return None
        
        for key, value in updates.items():
            if hasattr(coll, key) and key not in ['id', 'name', 'created_at', 'vector_size']:
                if key == 'embedding_provider':
                    value = EmbeddingProvider(value)
                setattr(coll, key, value)
        
        # 如果設為預設
        if updates.get("is_default"):
            for c in self._collections.values():
                if c.id != coll_id:
                    c.is_default = False
        
        self._save_collections()
        return coll
    
    def set_default(self, coll_id: str) -> bool:
        """設置預設 Collection"""
        coll = self._collections.get(coll_id)
        if not coll:
            return False
        
        for c in self._collections.values():
            c.is_default = (c.id == coll_id)
        
        self._save_collections()
        return True
    
    def get_default_collection(self) -> Optional[CollectionConfig]:
        """取得預設 Collection"""
        for coll in self._collections.values():
            if coll.is_default:
                return coll
        return None
    
    def list_collections(self) -> List[Dict[str, Any]]:
        """列出所有 Collection"""
        result = []
        for coll in self._collections.values():
            data = coll.to_dict()
            
            # 從 Qdrant 取得統計
            if self._client:
                try:
                    info = self._client.get_collection(coll.name)
                    data["points_count"] = info.points_count
                    data["status"] = info.status.value if info.status else "unknown"
                except Exception:
                    data["points_count"] = 0
                    data["status"] = "error"
            
            result.append(data)
        
        return result
    
    def get_collection(self, coll_id: str) -> Optional[CollectionConfig]:
        """取得 Collection"""
        return self._collections.get(coll_id)
    
    def get_collection_by_name(self, name: str) -> Optional[CollectionConfig]:
        """根據名稱取得 Collection"""
        for coll in self._collections.values():
            if coll.name == name:
                return coll
        return None
    
    def get_collection_stats(self, coll_id: str) -> Dict[str, Any]:
        """取得 Collection 統計"""
        coll = self._collections.get(coll_id)
        if not coll:
            return {"error": "Collection not found"}
        
        if not self._client:
            return {"error": "Qdrant not connected"}
        
        try:
            info = self._client.get_collection(coll.name)
            return {
                "name": coll.name,
                "display_name": coll.display_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status.value if info.status else "unknown",
                "config": {
                    "vector_size": coll.vector_size,
                    "distance": coll.distance,
                    "embedding_provider": coll.embedding_provider.value,
                    "embedding_model": coll.embedding_model
                }
            }
        except Exception as e:
            return {"error": str(e)}
    
    def sync_with_qdrant(self) -> Dict[str, Any]:
        """與 Qdrant 同步 Collection 列表"""
        if not self._client:
            return {"error": "Qdrant not connected"}
        
        try:
            qdrant_collections = self._client.get_collections().collections
            qdrant_names = {c.name for c in qdrant_collections}
            config_names = {c.name for c in self._collections.values()}
            
            # 找出只在 Qdrant 存在的
            only_qdrant = qdrant_names - config_names
            # 找出只在配置存在的
            only_config = config_names - qdrant_names
            
            return {
                "qdrant_collections": list(qdrant_names),
                "config_collections": list(config_names),
                "only_in_qdrant": list(only_qdrant),
                "only_in_config": list(only_config),
                "synced": len(only_qdrant) == 0 and len(only_config) == 0
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_documents(self, coll_id: str) -> Dict[str, Any]:
        """取得 Collection 中的文檔列表"""
        coll = self._collections.get(coll_id)
        if not coll:
            return {"error": "Collection not found"}
        
        if not self._client:
            return {"error": "Qdrant not connected"}
        
        try:
            # 使用 scroll 獲取所有點，然後按 file_name 分組
            documents = {}
            offset = None
            
            while True:
                results, offset = self._client.scroll(
                    collection_name=coll.name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False
                )
                
                for point in results:
                    file_name = point.payload.get("file_name", "unknown")
                    if file_name not in documents:
                        documents[file_name] = {
                            "file_name": file_name,
                            "chunk_count": 0,
                            "pages": set(),
                            "first_chunk_id": str(point.id)
                        }
                    documents[file_name]["chunk_count"] += 1
                    page = point.payload.get("page_label") or point.payload.get("page_number")
                    if page:
                        documents[file_name]["pages"].add(str(page))
                
                if offset is None:
                    break
            
            # 轉換 pages set 為 list
            doc_list = []
            for doc in documents.values():
                doc["pages"] = sorted(list(doc["pages"]))
                doc["page_count"] = len(doc["pages"])
                doc_list.append(doc)
            
            return {
                "collection_id": coll_id,
                "collection_name": coll.name,
                "documents": doc_list,
                "total_documents": len(doc_list)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_chunks(
        self, 
        coll_id: str, 
        limit: int = 100, 
        offset: int = 0,
        file_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """取得 Collection 中的 chunks"""
        coll = self._collections.get(coll_id)
        if not coll:
            return {"error": "Collection not found"}
        
        if not self._client:
            return {"error": "Qdrant not connected"}
        
        try:
            # 構建過濾條件
            scroll_filter = None
            if file_name:
                from qdrant_client.http.models import Filter, FieldCondition, MatchValue
                scroll_filter = Filter(
                    must=[FieldCondition(key="file_name", match=MatchValue(value=file_name))]
                )
            
            # 獲取 chunks
            results, next_offset = self._client.scroll(
                collection_name=coll.name,
                limit=limit,
                offset=offset if offset > 0 else None,
                scroll_filter=scroll_filter,
                with_payload=True,
                with_vectors=False
            )
            
            chunks = []
            for point in results:
                chunk = {
                    "id": str(point.id),
                    "text": point.payload.get("text", "")[:500],  # 截斷顯示
                    "full_text_length": len(point.payload.get("text", "")),
                    "file_name": point.payload.get("file_name", "unknown"),
                    "page_label": point.payload.get("page_label"),
                    "page_number": point.payload.get("page_number"),
                    "chunk_index": point.payload.get("chunk_index"),
                    "metadata": {
                        k: v for k, v in point.payload.items() 
                        if k not in ["text", "file_name", "page_label", "page_number", "chunk_index"]
                    }
                }
                chunks.append(chunk)
            
            return {
                "collection_id": coll_id,
                "collection_name": coll.name,
                "chunks": chunks,
                "count": len(chunks),
                "limit": limit,
                "offset": offset,
                "has_more": next_offset is not None
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_chunk_detail(self, coll_id: str, point_id: str) -> Dict[str, Any]:
        """取得單個 chunk 的完整詳情"""
        coll = self._collections.get(coll_id)
        if not coll:
            return {"error": "Collection not found"}
        
        if not self._client:
            return {"error": "Qdrant not connected"}
        
        try:
            # 獲取指定點
            results = self._client.retrieve(
                collection_name=coll.name,
                ids=[point_id],
                with_payload=True,
                with_vectors=True
            )
            
            if not results:
                return {"error": "Chunk not found"}
            
            point = results[0]
            return {
                "id": str(point.id),
                "text": point.payload.get("text", ""),
                "file_name": point.payload.get("file_name", "unknown"),
                "page_label": point.payload.get("page_label"),
                "page_number": point.payload.get("page_number"),
                "chunk_index": point.payload.get("chunk_index"),
                "vector_preview": point.vector[:10] if point.vector else None,
                "vector_dimension": len(point.vector) if point.vector else 0,
                "metadata": point.payload
            }
        except Exception as e:
            return {"error": str(e)}


# 全域實例
_collection_manager: Optional[CollectionManager] = None


def get_collection_manager() -> CollectionManager:
    """取得 Collection 管理器實例"""
    global _collection_manager
    if _collection_manager is None:
        _collection_manager = CollectionManager()
    return _collection_manager
