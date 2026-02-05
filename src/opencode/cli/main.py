"""
OpenCode CLI - 命令列介面
主要入口點
"""

import asyncio
import os
import sys
from typing import Optional
from pathlib import Path

# 確保載入 .env 檔案（使用專案根目錄）
from dotenv import load_dotenv
# src/opencode/cli/main.py → 往上4層到專案根目錄
_project_root = Path(__file__).resolve().parent.parent.parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.table import Table

# 確保 src 目錄在 path 中
sys.path.insert(0, str(_project_root / "src"))

app = typer.Typer(
    name="opencode",
    help="🧠 OpenCode Intelligent Platform - CLI",
    add_completion=True,
    no_args_is_help=True
)
console = Console()

# ============== Chat 指令 ==============

@app.command()
def chat(
    message: Optional[str] = typer.Argument(None, help="直接發送訊息"),
    session: str = typer.Option("default", "--session", "-s", help="Session ID"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="串流輸出"),
    interactive: bool = typer.Option(False, "--interactive", "-i", help="互動模式"),
):
    """💬 與知識庫對話"""
    
    if interactive or message is None:
        # 互動模式
        _chat_interactive(session)
    else:
        # 單次對話
        asyncio.run(_chat_single(message, session, stream))


def _chat_interactive(session: str):
    """互動式對話"""
    console.print(Panel.fit(
        "[bold cyan]OpenCode Chat[/bold cyan]\n"
        "輸入問題與知識庫對話，輸入 [bold]quit[/bold] 或 [bold]exit[/bold] 離開",
        border_style="cyan"
    ))
    
    while True:
        try:
            message = console.input("\n[bold green]You:[/bold green] ")
            
            if message.lower() in ("quit", "exit", "q"):
                console.print("[dim]再見！[/dim]")
                break
            
            if not message.strip():
                continue
            
            asyncio.run(_chat_single(message, session, stream=True))
            
        except KeyboardInterrupt:
            console.print("\n[dim]中斷[/dim]")
            break


async def _chat_single(message: str, session: str, stream: bool):
    """單次對話"""
    from opencode.core.engine import OpenCodeEngine
    from opencode.core.protocols import Intent, Context, EventType
    
    # 初始化引擎
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console
    ) as progress:
        progress.add_task("初始化引擎...", total=None)
        
        engine = OpenCodeEngine(config={"use_redis": False})
        await engine.initialize()
    
    # 建立意圖
    context = Context(session_id=session, user_id="cli_user")
    intent = Intent.create(content=message, context=context)
    
    # 處理意圖
    console.print("\n[bold blue]Assistant:[/bold blue]")
    
    thinking_shown = False
    answer_text = ""
    sources = []
    
    async for event in engine.process_intent(intent):
        if event.type == EventType.THINKING:
            if not thinking_shown:
                console.print(f"[dim italic]💭 {event.payload.get('content', '')}[/dim italic]")
                thinking_shown = True
        
        elif event.type == EventType.TOOL_CALL:
            tool = event.payload.get("content", "")
            args = event.payload.get("data", {}).get("arguments", {})
            console.print(f"[dim]🔧 使用工具: {tool}[/dim]")
        
        elif event.type == EventType.TOOL_RESULT:
            result = event.payload.get("content", "")
            console.print(f"[dim]✅ {result}[/dim]")
        
        elif event.type == EventType.ANSWER:
            answer_text = event.payload.get("content", "")
            console.print(Markdown(answer_text))
        
        elif event.type == EventType.SOURCE:
            sources = event.payload.get("data", {}).get("sources", [])
        
        elif event.type == EventType.ERROR:
            error = event.payload.get("content", "")
            console.print(f"[bold red]錯誤: {error}[/bold red]")
    
    # 顯示來源
    if sources:
        console.print("\n[dim]📚 參考來源:[/dim]")
        for s in sources[:3]:
            console.print(f"[dim]  • {s.get('file_name', '')} (頁 {s.get('page_label', '')})[/dim]")
    
    # 關閉引擎
    await engine.shutdown()


# ============== Search 指令 ==============

@app.command()
def search(
    query: str = typer.Argument(..., help="搜尋關鍵字"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="結果數量"),
    doc_filter: Optional[str] = typer.Option(None, "--doc", "-d", help="篩選文件"),
):
    """🔍 語意搜尋知識庫"""
    asyncio.run(_search(query, top_k, doc_filter))


async def _search(query: str, top_k: int, doc_filter: Optional[str]):
    """執行搜尋"""
    from opencode.services.knowledge_base.service import KnowledgeBaseService
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console
    ) as progress:
        progress.add_task("搜尋中...", total=None)
        
        service = KnowledgeBaseService()
        await service.initialize()
        
        filters = {"file_name": doc_filter} if doc_filter else None
        result = await service.execute("rag_search", {
            "query": query,
            "top_k": top_k,
            "filters": filters
        })
    
    # 顯示結果
    results = result.get("results", [])
    
    if not results:
        console.print("[yellow]沒有找到相關結果[/yellow]")
        return
    
    console.print(f"\n[bold]找到 {len(results)} 個結果:[/bold]\n")
    
    for i, r in enumerate(results, 1):
        console.print(Panel(
            f"[bold]{r.get('file_name', 'unknown')}[/bold] (頁 {r.get('page_label', '?')})\n"
            f"相關度: {r.get('score', 0):.3f}\n\n"
            f"{r.get('text', '')[:300]}...",
            title=f"結果 {i}",
            border_style="blue"
        ))


# ============== Docs 指令 ==============

@app.command("docs")
def docs_list():
    """📄 列出所有已索引文件"""
    asyncio.run(_docs_list())


async def _docs_list():
    """列出文件"""
    from opencode.services.knowledge_base.service import KnowledgeBaseService
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console
    ) as progress:
        progress.add_task("載入文件列表...", total=None)
        
        service = KnowledgeBaseService()
        await service.initialize()
        result = await service.execute("document_list", {})
    
    documents = result.get("documents", [])
    
    if not documents:
        console.print("[yellow]知識庫目前沒有任何文件[/yellow]")
        return
    
    # 建立表格
    table = Table(title="📚 已索引文件")
    table.add_column("#", style="dim")
    table.add_column("文件名稱", style="cyan")
    table.add_column("區塊數", justify="right")
    
    for i, doc in enumerate(documents, 1):
        table.add_row(
            str(i),
            doc.get("name", "unknown"),
            str(doc.get("chunks", "?"))
        )
    
    console.print(table)
    console.print(f"\n[dim]共 {len(documents)} 個文件[/dim]")


@app.command("docs:delete")
def docs_delete(
    name: str = typer.Argument(..., help="文件名稱"),
    force: bool = typer.Option(False, "--force", "-f", help="強制刪除，不確認")
):
    """🗑️ 從知識庫刪除文件"""
    if not force:
        confirm = typer.confirm(f"確定要刪除 '{name}'?")
        if not confirm:
            console.print("[dim]已取消[/dim]")
            return
    
    asyncio.run(_docs_delete(name))


async def _docs_delete(name: str):
    """刪除文件"""
    from opencode.services.knowledge_base.service import KnowledgeBaseService
    
    service = KnowledgeBaseService()
    await service.initialize()
    result = await service.execute("document_delete", {"document_name": name})
    
    if result.get("success"):
        console.print(f"[green]✅ 已刪除: {name}[/green]")
    else:
        console.print(f"[red]❌ 刪除失敗: {result.get('error', 'unknown')}[/red]")


# ============== Stats 指令 ==============

@app.command()
def stats():
    """📊 顯示知識庫統計"""
    asyncio.run(_stats())


async def _stats():
    """顯示統計"""
    from opencode.services.knowledge_base.service import KnowledgeBaseService
    
    service = KnowledgeBaseService()
    await service.initialize()
    result = await service.execute("get_stats", {})
    
    if "error" in result:
        console.print(f"[red]錯誤: {result['error']}[/red]")
        return
    
    console.print(Panel(
        f"📄 文件數量: [bold]{result.get('document_count', 0)}[/bold]\n"
        f"📦 總區塊數: [bold]{result.get('total_chunks', 0)}[/bold]\n"
        f"📐 向量維度: [bold]{result.get('vector_dim', 'N/A')}[/bold]\n"
        f"💾 索引大小: [bold]{result.get('index_size', 'N/A')}[/bold]",
        title="📊 知識庫統計",
        border_style="green"
    ))


# ============== Sandbox 指令 ==============

@app.command("run")
def sandbox_run(
    command: str = typer.Argument(..., help="要執行的命令"),
    python: bool = typer.Option(False, "--python", "-p", help="作為 Python 執行"),
    timeout: int = typer.Option(30, "--timeout", "-t", help="超時時間")
):
    """🐳 在沙箱中執行命令"""
    asyncio.run(_sandbox_run(command, python, timeout))


async def _sandbox_run(command: str, python: bool, timeout: int):
    """執行沙箱命令"""
    from opencode.services.sandbox.service import SandboxService
    
    service = SandboxService()
    await service.initialize()
    
    if python:
        result = await service.execute("execute_python", {
            "code": command,
            "timeout": timeout
        })
    else:
        result = await service.execute("execute_bash", {
            "command": command,
            "timeout": timeout
        })
    
    # 顯示輸出
    if result.get("stdout"):
        console.print(Panel(result["stdout"], title="stdout", border_style="green"))
    
    if result.get("stderr"):
        console.print(Panel(result["stderr"], title="stderr", border_style="red"))
    
    exit_code = result.get("exit_code", -1)
    if exit_code == 0:
        console.print(f"[green]✅ 執行成功 (exit code: {exit_code})[/green]")
    else:
        console.print(f"[red]❌ 執行失敗 (exit code: {exit_code})[/red]")


# ============== TUI 指令 ==============

@app.command()
def tui():
    """🖥️ 啟動 TUI 介面"""
    try:
        from opencode.cli.tui.app import OpenCodeTUI
        app = OpenCodeTUI()
        app.run()
    except ImportError:
        console.print("[red]TUI 模組尚未安裝，請安裝 textual[/red]")
        console.print("[dim]pip install textual[/dim]")


# ============== Config 指令 ==============

@app.command()
def config(
    key: Optional[str] = typer.Argument(None, help="配置 Key"),
    value: Optional[str] = typer.Argument(None, help="配置 Value"),
    list_all: bool = typer.Option(False, "--list", "-l", help="列出所有配置"),
):
    """⚙️ 配置管理"""
    if list_all or (key is None and value is None):
        _show_config()
    elif key and value:
        _set_config(key, value)
    elif key:
        _get_config(key)


def _show_config():
    """顯示所有配置"""
    from opencode.config.settings import settings
    
    table = Table(title="⚙️ 配置")
    table.add_column("Key", style="cyan")
    table.add_column("Value")
    
    config_items = [
        ("app_name", settings.app_name),
        ("debug", str(settings.debug)),
        ("log_level", settings.log_level),
        ("redis.host", settings.redis.host),
        ("redis.port", str(settings.redis.port)),
        ("qdrant.host", settings.qdrant.host),
        ("qdrant.port", str(settings.qdrant.port)),
        ("api.host", settings.api_host),
        ("api.port", str(settings.api_port)),
    ]
    
    for key, value in config_items:
        table.add_row(key, value)
    
    console.print(table)


def _get_config(key: str):
    """取得配置值"""
    from opencode.config.settings import settings
    
    try:
        parts = key.split(".")
        value = settings
        for part in parts:
            value = getattr(value, part)
        console.print(f"{key} = {value}")
    except AttributeError:
        console.print(f"[red]配置不存在: {key}[/red]")


def _set_config(key: str, value: str):
    """設置配置 (透過環境變數)"""
    env_key = f"OPENCODE_{key.upper().replace('.', '__')}"
    console.print(f"[dim]設置環境變數: {env_key}={value}[/dim]")
    console.print(f"[yellow]請手動設置: export {env_key}={value}[/yellow]")


# ============== API 指令 ==============

@app.command()
def api(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="監聽地址"),
    port: int = typer.Option(8000, "--port", "-p", help="監聽埠"),
    reload: bool = typer.Option(False, "--reload", "-r", help="自動重載"),
):
    """🚀 啟動 API 伺服器"""
    console.print(Panel(
        f"[bold green]Starting OpenCode API Server[/bold green]\n\n"
        f"Host: [cyan]{host}[/cyan]\n"
        f"Port: [cyan]{port}[/cyan]\n"
        f"Reload: [cyan]{reload}[/cyan]\n\n"
        f"API Docs: [link]http://{host if host != '0.0.0.0' else 'localhost'}:{port}/docs[/link]",
        title="🚀 OpenCode API",
        border_style="green"
    ))
    
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=reload
    )


# ============== Upload 指令 ==============

@app.command()
def upload(
    files: Optional[list[str]] = typer.Argument(None, help="要上傳的 PDF 檔案"),
    folder: str = typer.Option("data/documents", "--folder", "-f", help="上傳資料夾"),
):
    """📤 上傳 PDF 文件到知識庫"""
    from pathlib import Path
    
    # 收集要上傳的檔案
    pdf_files = []
    
    if files:
        # 指定檔案
        for f in files:
            path = Path(f)
            if path.exists() and path.suffix.lower() == '.pdf':
                pdf_files.append(path)
            else:
                console.print(f"[yellow]跳過: {f} (不存在或非 PDF)[/yellow]")
    else:
        # 從資料夾讀取
        folder_path = Path(folder)
        if folder_path.exists():
            pdf_files = list(folder_path.glob("*.pdf"))
        else:
            console.print(f"[yellow]資料夾不存在: {folder}[/yellow]")
    
    if not pdf_files:
        console.print("[yellow]沒有找到 PDF 檔案[/yellow]")
        return
    
    console.print(f"\n[bold]找到 {len(pdf_files)} 個 PDF 檔案[/bold]\n")
    
    for f in pdf_files:
        console.print(f"  • {f.name}")
    
    if not typer.confirm("\n確定要上傳?"):
        console.print("[dim]已取消[/dim]")
        return
    
    asyncio.run(_upload_files(pdf_files))


async def _upload_files(files):
    """上傳檔案"""
    from opencode.services.knowledge_base.ingestion.pipeline import process_pdf_to_qdrant
    
    for f in files:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console
        ) as progress:
            progress.add_task(f"上傳 {f.name}...", total=None)
            
            try:
                result = await process_pdf_to_qdrant(str(f), f.name)
                chunks = result.get("chunks", 0)
                console.print(f"[green]✅ {f.name} ({chunks} 區塊)[/green]")
            except Exception as e:
                console.print(f"[red]❌ {f.name}: {e}[/red]")


# ============== Version 指令 ==============

@app.command()
def version():
    """顯示版本資訊"""
    console.print(Panel(
        "[bold cyan]OpenCode Platform[/bold cyan]\n"
        "Version: 1.0.0\n"
        "Python: " + sys.version.split()[0],
        title="🧠 OpenCode",
        border_style="cyan"
    ))


# ============== 主程式 ==============

def main():
    """主程式入口"""
    app()


if __name__ == "__main__":
    main()
