#!/usr/bin/env python3
"""
OpenCode Platform - 快速啟動腳本
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path

# 確保載入 .env 檔案（使用專案根目錄）
from dotenv import load_dotenv
_project_root = Path(__file__).resolve().parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)

# 設置 path - 加入 src 目錄
sys.path.insert(0, str(_project_root / "src"))


def run_cli():
    """啟動 CLI"""
    from opencode.cli.main import app
    app()


def run_tui():
    """啟動 TUI"""
    from opencode.cli.tui.app import run_tui
    run_tui()


def run_api():
    """啟動 API"""
    import uvicorn
    from opencode.config.settings import settings
    
    uvicorn.run(
        "opencode.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )


def run_demo():
    """執行演示"""
    asyncio.run(_demo())


async def _demo():
    """演示腳本"""
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    
    console = Console()
    
    console.print(Panel.fit(
        "[bold cyan]OpenCode Platform Demo[/bold cyan]\n"
        "OpenCode-Centric Intelligent Platform",
        border_style="cyan"
    ))
    
    console.print("\n[bold]1. Initializing Engine...[/bold]")
    
    try:
        from opencode.core.engine import OpenCodeEngine
        from opencode.core.protocols import Intent, Context, EventType
        
        engine = OpenCodeEngine(config={"use_redis": False})
        await engine.initialize()
        
        console.print("[green]✅ Engine initialized[/green]")
        
        # 測試對話
        console.print("\n[bold]2. Testing Chat...[/bold]")
        
        context = Context(session_id="demo", user_id="demo_user")
        intent = Intent.create(
            content="什麼是 RAG？",
            context=context
        )
        
        console.print(f"[dim]Query: {intent.content}[/dim]\n")
        
        async for event in engine.process_intent(intent):
            if event.type == EventType.THINKING:
                console.print(f"[dim]💭 {event.payload.get('content', '')}[/dim]")
            elif event.type == EventType.TOOL_CALL:
                console.print(f"[cyan]🔧 {event.payload.get('content', '')}[/cyan]")
            elif event.type == EventType.ANSWER:
                answer = event.payload.get('content', '')
                console.print(Panel(Markdown(answer), title="Answer", border_style="green"))
            elif event.type == EventType.ERROR:
                console.print(f"[red]❌ {event.payload.get('content', '')}[/red]")
        
        # 關閉
        await engine.shutdown()
        console.print("\n[green]✅ Demo complete[/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


def check_deps():
    """檢查依賴和配置"""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    
    console = Console()
    
    # 顯示標題
    console.print(Panel.fit(
        "[bold cyan]OpenCode Platform - 配置檢查[/bold cyan]",
        border_style="cyan"
    ))
    
    # 1. 依賴檢查
    console.print("\n[bold]1. 依賴套件:[/bold]")
    table = Table()
    table.add_column("Package")
    table.add_column("Status")
    
    packages = [
        ("typer", "CLI"),
        ("rich", "CLI"),
        ("fastapi", "API"),
        ("uvicorn", "Server"),
        ("openai", "LLM"),
        ("cohere", "Embedding"),
        ("qdrant_client", "Vector DB"),
        ("pydantic", "Config"),
        ("jose", "JWT"),
        ("passlib", "Password"),
    ]
    
    for pkg, purpose in packages:
        try:
            __import__(pkg)
            table.add_row(f"{pkg} ({purpose})", "[green]✓[/green]")
        except ImportError:
            table.add_row(f"{pkg} ({purpose})", "[red]✗ 未安裝[/red]")
    
    console.print(table)
    
    # 2. 配置檢查
    console.print("\n[bold]2. 當前配置:[/bold]")
    
    try:
        from opencode.config.settings import settings
        
        config_table = Table()
        config_table.add_column("配置項")
        config_table.add_column("值")
        config_table.add_column("來源")
        
        config_table.add_row("API Host", settings.api_host, "API_HOST")
        config_table.add_row("API Port", str(settings.api_port), "API_PORT")
        config_table.add_row("Qdrant Host", settings.qdrant.host, "QDRANT_HOST")
        config_table.add_row("Qdrant Port", str(settings.qdrant.port), "QDRANT_PORT")
        config_table.add_row("Embedding Provider", settings.embedding.provider, "EMBEDDING_PROVIDER")
        config_table.add_row("Log Level", settings.log_level, "LOG_LEVEL")
        
        console.print(config_table)
    except Exception as e:
        console.print(f"[red]配置載入失敗: {e}[/red]")
    
    # 3. 環境變數檢查
    console.print("\n[bold]3. 環境變數:[/bold]")
    
    env_vars = [
        ("OPENAI_API_KEY", True),
        ("COHERE_API_KEY", False),
        ("API_PORT", False),
        ("QDRANT_HOST", False),
    ]
    
    for var, required in env_vars:
        value = os.getenv(var)
        if value:
            display = value[:10] + "..." if len(value) > 10 else value
            console.print(f"  ✅ {var}: {display}")
        else:
            status = "[red]❌ 未設置 (必要)[/red]" if required else "[yellow]⚠️ 未設置 (可選)[/yellow]"
            console.print(f"  {status}: {var}")
    
    # 4. 服務連接測試
    console.print("\n[bold]4. 服務連接:[/bold]")
    
    # 測試 Qdrant
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(host=settings.qdrant.host, port=settings.qdrant.port, timeout=5)
        client.get_collections()
        console.print(f"  ✅ Qdrant: http://{settings.qdrant.host}:{settings.qdrant.port}")
    except Exception as e:
        console.print(f"  ❌ Qdrant: 連接失敗 - {e}")
    
    console.print("\n[bold green]檢查完成[/bold green]")


def main():
    parser = argparse.ArgumentParser(description="OpenCode Platform Launcher")
    parser.add_argument(
        "command",
        choices=["cli", "tui", "api", "demo", "check"],
        help="Command to run"
    )
    
    args = parser.parse_args()
    
    if args.command == "cli":
        run_cli()
    elif args.command == "tui":
        run_tui()
    elif args.command == "api":
        run_api()
    elif args.command == "demo":
        run_demo()
    elif args.command == "check":
        check_deps()


if __name__ == "__main__":
    main()
