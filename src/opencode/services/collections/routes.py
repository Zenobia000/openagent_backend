"""
向量資料庫 Collection 管理 API 路由
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from opencode.auth import get_current_user, require_admin, TokenData
from .manager import get_collection_manager, CollectionManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/collections", tags=["知識庫管理"])


class CollectionCreate(BaseModel):
    """創建 Collection"""
    name: str                          # Qdrant collection 名稱（英文）
    display_name: str                  # 顯示名稱
    description: str = ""              # 描述
    embedding_provider: str = "cohere" # cohere 或 openai
    embedding_model: Optional[str] = None  # 可選，使用預設


class CollectionUpdate(BaseModel):
    """更新 Collection"""
    display_name: Optional[str] = None
    description: Optional[str] = None


@router.get("")
async def list_collections(
    manager: CollectionManager = Depends(get_collection_manager)
):
    """列出所有知識庫"""
    collections = manager.list_collections()
    default = manager.get_default_collection()
    return {
        "collections": collections,
        "count": len(collections),
        "default_id": default.id if default else None
    }


@router.post("")
async def create_collection(
    coll: CollectionCreate,
    current_user: TokenData = Depends(require_admin),
    manager: CollectionManager = Depends(get_collection_manager)
):
    """創建新知識庫（僅管理員）"""
    try:
        new_coll = manager.create_collection(
            name=coll.name,
            display_name=coll.display_name,
            description=coll.description,
            embedding_provider=coll.embedding_provider,
            embedding_model=coll.embedding_model
        )
        return new_coll.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sync")
async def sync_collections(
    current_user: TokenData = Depends(require_admin),
    manager: CollectionManager = Depends(get_collection_manager)
):
    """同步檢查（僅管理員）"""
    return manager.sync_with_qdrant()


@router.get("/{coll_id}")
async def get_collection(
    coll_id: str,
    manager: CollectionManager = Depends(get_collection_manager)
):
    """取得知識庫詳情"""
    coll = manager.get_collection(coll_id)
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    return coll.to_dict()


@router.get("/{coll_id}/stats")
async def get_collection_stats(
    coll_id: str,
    manager: CollectionManager = Depends(get_collection_manager)
):
    """取得知識庫統計"""
    stats = manager.get_collection_stats(coll_id)
    if "error" in stats:
        raise HTTPException(status_code=400, detail=stats["error"])
    return stats


@router.put("/{coll_id}")
async def update_collection(
    coll_id: str,
    updates: CollectionUpdate,
    current_user: TokenData = Depends(require_admin),
    manager: CollectionManager = Depends(get_collection_manager)
):
    """更新知識庫（僅管理員）"""
    coll = manager.update_collection(coll_id, updates.dict(exclude_unset=True))
    if not coll:
        raise HTTPException(status_code=404, detail="Collection not found")
    return coll.to_dict()


@router.delete("/{coll_id}")
async def delete_collection(
    coll_id: str,
    delete_qdrant: bool = True,
    current_user: TokenData = Depends(require_admin),
    manager: CollectionManager = Depends(get_collection_manager)
):
    """刪除知識庫（僅管理員）"""
    try:
        success = manager.delete_collection(coll_id, delete_qdrant=delete_qdrant)
        if not success:
            raise HTTPException(status_code=404, detail="Collection not found")
        return {"message": f"Collection {coll_id} deleted"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{coll_id}/set-default")
async def set_default_collection(
    coll_id: str,
    current_user: TokenData = Depends(require_admin),
    manager: CollectionManager = Depends(get_collection_manager)
):
    """設置預設知識庫（僅管理員）"""
    success = manager.set_default(coll_id)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"message": f"Collection {coll_id} set as default"}


@router.get("/{coll_id}/documents")
async def get_collection_documents(
    coll_id: str,
    manager: CollectionManager = Depends(get_collection_manager)
):
    """取得知識庫中的文檔列表"""
    result = manager.get_documents(coll_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{coll_id}/chunks")
async def get_collection_chunks(
    coll_id: str,
    limit: int = 100,
    offset: int = 0,
    file_name: Optional[str] = None,
    manager: CollectionManager = Depends(get_collection_manager)
):
    """取得知識庫中的 chunks"""
    result = manager.get_chunks(coll_id, limit=limit, offset=offset, file_name=file_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{coll_id}/chunks/{point_id}")
async def get_chunk_detail(
    coll_id: str,
    point_id: str,
    manager: CollectionManager = Depends(get_collection_manager)
):
    """取得單個 chunk 的詳情"""
    result = manager.get_chunk_detail(coll_id, point_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{coll_id}/documents")
async def get_collection_documents(
    coll_id: str,
    manager: CollectionManager = Depends(get_collection_manager)
):
    """取得知識庫中的文檔列表"""
    result = manager.get_documents(coll_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{coll_id}/chunks")
async def get_collection_chunks(
    coll_id: str,
    limit: int = 100,
    offset: int = 0,
    file_name: Optional[str] = None,
    manager: CollectionManager = Depends(get_collection_manager)
):
    """取得知識庫中的 chunks（向量點）"""
    result = manager.get_chunks(coll_id, limit=limit, offset=offset, file_name=file_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{coll_id}/chunks/{point_id}")
async def get_chunk_detail(
    coll_id: str,
    point_id: str,
    manager: CollectionManager = Depends(get_collection_manager)
):
    """取得單個 chunk 的詳情"""
    result = manager.get_chunk_detail(coll_id, point_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
