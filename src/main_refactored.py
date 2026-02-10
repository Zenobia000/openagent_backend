#!/usr/bin/env python3
"""
OpenCode Platform - 重構版主程序
簡化的入口點
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

# 確保 src 在路徑中
sys.path.insert(0, str(Path(__file__).parent))

from core import (
    RefactoredEngine as Engine,
    Request,
    ProcessingMode,
    structured_logger
)
from services.llm_service import get_llm_service
from config import API_CONFIG


async def cli_mode():
    """CLI 模式"""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()

    # 初始化引擎
    llm_service = get_llm_service()
    engine = Engine(llm_client=llm_service)
    await engine.initialize()

    console.print(Panel.fit(
        "[bold green]OpenCode Platform - CLI Mode[/bold green]",
        border_style="cyan"
    ))

    while True:
        try:
            # 獲取用戶輸入
            query = console.input("\n[bold cyan]Query:[/bold cyan] ")

            if query.lower() in ['exit', 'quit', 'bye']:
                console.print("[yellow]Goodbye![/yellow]")
                break

            # 處理請求
            request = Request(query=query, mode=ProcessingMode.AUTO)
            response = await engine.process(request)

            # 顯示結果
            console.print(f"\n[green]Response:[/green] {response.result}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
            break
        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")


def api_mode():
    """API 服務器模式"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from contextlib import asynccontextmanager
    from pydantic import BaseModel
    import uvicorn

    # 初始化引擎
    llm_service = get_llm_service()
    engine = Engine(llm_client=llm_service)

    # 使用 lifespan 替代 on_event
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        await engine.initialize()
        structured_logger.info("API server started")
        yield
        # Shutdown
        structured_logger.info("API server shutdown")

    # 創建 FastAPI 應用
    app = FastAPI(
        title="OpenCode Platform API",
        version="2.0",
        description="Refactored OpenCode Platform API",
        lifespan=lifespan
    )

    # CORS 配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class QueryRequest(BaseModel):
        query: str
        mode: Optional[str] = "auto"

    class QueryResponse(BaseModel):
        result: str
        mode: str
        trace_id: str
        time_ms: float

    @app.get("/health")
    async def health():
        return {"status": "healthy", "version": "2.0"}

    @app.post("/api/query", response_model=QueryResponse)
    async def query(request: QueryRequest):
        try:
            # 處理請求
            req = Request(
                query=request.query,
                mode=ProcessingMode(request.mode)
            )
            response = await engine.process(req)

            return QueryResponse(
                result=response.result,
                mode=response.mode.value,
                trace_id=response.trace_id,
                time_ms=response.time_ms
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/sse")
    async def sse_endpoint():
        """SSE 端點 - 流式響應"""
        from fastapi.responses import StreamingResponse

        async def event_generator():
            # 這裡應該實現完整的 SSE 事件流
            yield "event: info\ndata: {\"name\": \"opencode\", \"version\": \"2.0\"}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream"
        )

    # 啟動服務器
    uvicorn.run(
        app,
        host=API_CONFIG.get("host", "0.0.0.0"),
        port=API_CONFIG.get("port", 8000),
        reload=False
    )


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description="OpenCode Platform")
    parser.add_argument(
        "--mode",
        choices=["cli", "api"],
        default="cli",
        help="運行模式"
    )
    args = parser.parse_args()

    if args.mode == "cli":
        asyncio.run(cli_mode())
    else:
        api_mode()


if __name__ == "__main__":
    main()