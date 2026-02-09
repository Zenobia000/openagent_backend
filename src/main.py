#!/usr/bin/env python3
"""
OpenCode Platform - Clean Architecture
主入口點 (Main Entry Point)
"""

import asyncio
import sys
from pathlib import Path

# 確保 src 在 path 中
sys.path.insert(0, str(Path(__file__).parent))

from config import API_CONFIG, DEBUG
from utils.logging_config import get_logger, LogLevel, LogContext

# 設置主程序 logger
logger = get_logger("Main", LogLevel.INFO)


def run_server():
    """運行 API 服務器"""
    from api.routes import create_app
    import uvicorn

    app = create_app()

    uvicorn.run(
        app,
        host=API_CONFIG["host"],
        port=API_CONFIG["port"],
        reload=DEBUG,
        log_level="debug" if DEBUG else "info"
    )


def run_cli():
    """運行 CLI 模式"""
    from rich.console import Console
    from rich.panel import Panel
    from core import Engine

    console = Console()

    async def cli_loop():
        print(sys.path) # Debugging print statement
        engine = Engine()
        await engine.initialize()

        console.print(Panel.fit(
            "[bold cyan]OpenCode Platform - CLI Mode[/bold cyan]",
            border_style="cyan"
        ))

        while True:
            try:
                query = console.input("\n[bold green]Query:[/bold green] ")

                if query.lower() in ["exit", "quit", "q"]:
                    break

                result = await engine.process(query)
                console.print(f"[bold blue]Result:[/bold blue] {result}")

            except KeyboardInterrupt:
                break

        console.print("[dim]Goodbye![/dim]")

    asyncio.run(cli_loop())


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="OpenCode Platform")
    parser.add_argument(
        "--mode",
        choices=["server", "cli"],
        default="server",
        help="Run mode: server or cli"
    )

    args = parser.parse_args()

    if args.mode == "server":
        run_server()
    else:
        run_cli()
