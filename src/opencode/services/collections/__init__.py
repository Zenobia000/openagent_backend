"""
向量資料庫 Collection 管理
"""

from .manager import (
    CollectionConfig, EmbeddingProvider,
    CollectionManager, get_collection_manager
)
from .routes import router as collections_router

__all__ = [
    "CollectionConfig", "EmbeddingProvider",
    "CollectionManager", "get_collection_manager",
    "collections_router"
]
