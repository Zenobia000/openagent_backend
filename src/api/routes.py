"""
API Routes
API 路由定義
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from config import API_CONFIG, DEBUG


def create_app() -> FastAPI:
    """創建 FastAPI 應用"""

    app = FastAPI(
        title=API_CONFIG.get("title", "OpenCode Platform"),
        version=API_CONFIG.get("version", "1.0.0"),
        docs_url="/docs" if API_CONFIG.get("docs_enabled", True) else None,
        redoc_url="/redoc" if API_CONFIG.get("docs_enabled", True) else None
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=API_CONFIG.get("cors_origins", ["*"]),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 根路徑
    @app.get("/")
    async def root():
        return {
            "message": "OpenCode Platform API",
            "version": API_CONFIG.get("version", "1.0.0"),
            "status": "running"
        }

    # 健康檢查
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "environment": "debug" if DEBUG else "production"
        }

    # API 狀態
    @app.get("/api/status")
    async def api_status():
        return {
            "api": "operational",
            "services": {
                "knowledge": "ready",
                "sandbox": "ready",
                "search": "ready",
                "repo": "ready"
            }
        }

    # 簡單的處理端點
    @app.post("/api/process")
    async def process_request(query: str):
        """處理請求"""
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")

        # 簡單的回應
        return {
            "query": query,
            "response": f"Processed: {query}",
            "status": "success"
        }

    return app