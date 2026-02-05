"""
Qdrant 管理 API 路由
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qdrant", tags=["Qdrant 管理"])

COLLECTION_NAME = "rag_knowledge_base"


# ============== API Endpoints ==============

@router.get("/collections")
async def list_collections():
    """列出所有 Qdrant collections"""
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(host="localhost", port=6333)
        collections = client.get_collections().collections
        
        result = []
        for c in collections:
            info = client.get_collection(c.name)
            result.append({
                "name": c.name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": str(info.status)
            })
        
        return {"collections": result}
        
    except Exception as e:
        logger.error(f"List collections failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collection/{name}")
async def get_collection_info(name: str):
    """取得 collection 詳細資訊"""
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(host="localhost", port=6333)
        info = client.get_collection(name)
        
        # 取得文件統計
        points, _ = client.scroll(
            collection_name=name,
            limit=10000,
            with_payload=["file_name"],
            with_vectors=False
        )
        
        doc_stats = {}
        for p in points:
            source = p.payload.get("file_name", "unknown")
            doc_stats[source] = doc_stats.get(source, 0) + 1
        
        # 取得向量維度
        vector_size = None
        if hasattr(info.config.params.vectors, 'size'):
            vector_size = info.config.params.vectors.size
        
        # 取得距離類型
        distance = None
        if hasattr(info.config.params.vectors, 'distance'):
            distance = str(info.config.params.vectors.distance)
        
        return {
            "name": name,
            "vectors_count": info.vectors_count,
            "points_count": info.points_count,
            "status": str(info.status),
            "config": {
                "size": vector_size,
                "distance": distance
            },
            "documents": [
                {"name": k, "vectors": v}
                for k, v in sorted(doc_stats.items(), key=lambda x: -x[1])
            ]
        }
        
    except Exception as e:
        logger.error(f"Get collection info failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collection/{name}/points")
async def browse_points(name: str, limit: int = 20, offset: Optional[str] = None):
    """瀏覽 collection 中的 points"""
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(host="localhost", port=6333)
        
        points, next_offset = client.scroll(
            collection_name=name,
            limit=limit,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        return {
            "points": [
                {
                    "id": str(p.id),
                    "payload": {
                        "source": p.payload.get("file_name", ""),
                        "page": p.payload.get("page_label", ""),
                        "content": p.payload.get("text", "")[:300] + "..." if len(p.payload.get("text", "")) > 300 else p.payload.get("text", "")
                    }
                }
                for p in points
            ],
            "next_offset": str(next_offset) if next_offset else None,
            "count": len(points)
        }
        
    except Exception as e:
        logger.error(f"Browse points failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collection/{name}")
async def delete_collection(name: str):
    """刪除 collection"""
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(host="localhost", port=6333)
        client.delete_collection(name)
        
        return {"message": f"Collection '{name}' deleted successfully"}
        
    except Exception as e:
        logger.error(f"Delete collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/collection/{name}/optimize")
async def optimize_collection(name: str):
    """優化 collection 索引"""
    try:
        from qdrant_client import QdrantClient
        
        client = QdrantClient(host="localhost", port=6333)
        
        # 觸發優化
        client.update_collection(
            collection_name=name,
            optimizer_config={
                "indexing_threshold": 10000
            }
        )
        
        return {"message": f"Collection '{name}' optimization triggered"}
        
    except Exception as e:
        logger.error(f"Optimize collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
