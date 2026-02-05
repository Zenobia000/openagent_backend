"""
OpenCode TUI - 終端使用者介面
基於 Textual 框架
"""

import asyncio
from typing import Optional, List
import uuid
import time

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.widgets import (
        Header, Footer, Input, Static, ListView, ListItem,
        Button, Label, ProgressBar, RichLog
    )
    from textual.binding import Binding
    from textual.message import Message
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.text import Text
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False


if TEXTUAL_AVAILABLE:
    
    class MessageWidget(Static):
        """訊息 Widget"""
        
        def __init__(self, role: str, content: str, **kwargs):
            super().__init__(**kwargs)
            self.role = role
            self.content = content
        
        def compose(self) -> ComposeResult:
            if self.role == "user":
                yield Static(
                    Panel(self.content, title="You", border_style="green"),
                    classes="message-user"
                )
            else:
                yield Static(
                    Panel(Markdown(self.content), title="Assistant", border_style="blue"),
                    classes="message-assistant"
                )
    
    
    class ThinkingWidget(Static):
        """思考中 Widget"""
        
        def __init__(self, content: str = "思考中...", **kwargs):
            super().__init__(**kwargs)
            self.content = content
        
        def compose(self) -> ComposeResult:
            yield Static(f"💭 [italic dim]{self.content}[/]", classes="thinking")
    
    
    class ToolCallWidget(Static):
        """工具呼叫 Widget"""
        
        def __init__(self, tool: str, args: dict = None, **kwargs):
            super().__init__(**kwargs)
            self.tool = tool
            self.args = args or {}
        
        def compose(self) -> ComposeResult:
            args_str = ", ".join(f"{k}={v}" for k, v in self.args.items())
            yield Static(f"🔧 [cyan]{self.tool}[/]({args_str})", classes="tool-call")
    
    
    class OpenCodeTUI(App):
        """OpenCode TUI 主應用"""
        
        CSS = """
        Screen {
            layout: grid;
            grid-size: 2;
            grid-columns: 1fr 4fr;
        }
        
        #sidebar {
            width: 100%;
            background: $surface;
            border-right: solid $primary;
            padding: 1;
        }
        
        #main {
            width: 100%;
            height: 100%;
            layout: vertical;
        }
        
        #chat-container {
            height: 1fr;
            overflow-y: auto;
            padding: 1;
        }
        
        #input-container {
            height: auto;
            dock: bottom;
            padding: 1;
        }
        
        .message-user {
            margin: 1 0;
        }
        
        .message-assistant {
            margin: 1 0;
        }
        
        .thinking {
            color: $text-muted;
            margin: 0 0 0 2;
        }
        
        .tool-call {
            color: $secondary;
            margin: 0 0 0 2;
        }
        
        .section-title {
            text-style: bold;
            color: $primary;
            margin: 1 0;
        }
        
        ListView {
            height: auto;
            max-height: 20;
        }
        
        ListItem {
            padding: 0 1;
        }
        """
        
        BINDINGS = [
            Binding("ctrl+q", "quit", "Quit"),
            Binding("ctrl+n", "new_session", "New Session"),
            Binding("ctrl+c", "clear_chat", "Clear"),
            Binding("f1", "help", "Help"),
        ]
        
        def __init__(self):
            super().__init__()
            self.engine = None
            self.session_id = str(uuid.uuid4())[:8]
            self.messages: List[dict] = []
            self.processing = False
        
        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            
            with Horizontal():
                # 側邊欄
                with Vertical(id="sidebar"):
                    yield Static("📚 [bold]Documents[/]", classes="section-title")
                    yield ListView(id="doc-list")
                    yield Static("🔧 [bold]Tools[/]", classes="section-title")
                    yield ListView(id="tool-list")
                    yield Static("📊 [bold]Stats[/]", classes="section-title")
                    yield Static(id="stats-display")
                
                # 主區域
                with Vertical(id="main"):
                    yield ScrollableContainer(id="chat-container")
                    with Container(id="input-container"):
                        yield Input(
                            placeholder="輸入訊息... (Enter 發送)",
                            id="chat-input"
                        )
            
            yield Footer()
        
        async def on_mount(self) -> None:
            """掛載時初始化"""
            self.title = "OpenCode Platform"
            self.sub_title = f"Session: {self.session_id}"
            
            # 初始化引擎
            await self._init_engine()
            
            # 載入文件列表
            await self._load_documents()
            
            # 載入工具列表
            self._load_tools()
            
            # 聚焦輸入框
            self.query_one("#chat-input").focus()
        
        async def _init_engine(self) -> None:
            """初始化引擎"""
            try:
                from opencode.core.engine import OpenCodeEngine
                
                self.engine = OpenCodeEngine(config={"use_redis": False})
                await self.engine.initialize()
                
                self.notify("引擎已就緒", severity="information")
            except Exception as e:
                self.notify(f"引擎初始化失敗: {e}", severity="error")
        
        async def _load_documents(self) -> None:
            """載入文件列表"""
            try:
                from opencode.services.knowledge_base.service import KnowledgeBaseService
                
                service = KnowledgeBaseService()
                await service.initialize()
                
                result = await service.execute("document_list", {})
                documents = result.get("documents", [])
                
                doc_list = self.query_one("#doc-list", ListView)
                doc_list.clear()
                
                for doc in documents:
                    name = doc.get("name", "unknown")
                    chunks = doc.get("chunks", 0)
                    doc_list.append(ListItem(Label(f"📄 {name} ({chunks})")))
                
                # 更新統計
                stats = await service.execute("get_stats", {})
                self.query_one("#stats-display").update(
                    f"文件: {stats.get('document_count', 0)}\n"
                    f"區塊: {stats.get('total_chunks', 0)}"
                )
                
            except Exception as e:
                self.notify(f"載入文件失敗: {e}", severity="warning")
        
        def _load_tools(self) -> None:
            """載入工具列表"""
            tools = [
                ("🔍", "rag_search"),
                ("❓", "rag_ask"),
                ("💻", "execute_bash"),
                ("🐍", "execute_python"),
            ]
            
            tool_list = self.query_one("#tool-list", ListView)
            tool_list.clear()
            
            for icon, name in tools:
                tool_list.append(ListItem(Label(f"{icon} {name}")))
        
        async def on_input_submitted(self, event: Input.Submitted) -> None:
            """處理輸入提交"""
            if self.processing:
                return
            
            message = event.value.strip()
            if not message:
                return
            
            # 清空輸入
            event.input.value = ""
            
            # 顯示用戶訊息
            await self._add_user_message(message)
            
            # 處理意圖
            self.processing = True
            await self._process_message(message)
            self.processing = False
        
        async def _add_user_message(self, content: str) -> None:
            """添加用戶訊息"""
            container = self.query_one("#chat-container")
            await container.mount(MessageWidget("user", content))
            container.scroll_end()
        
        async def _add_assistant_message(self, content: str) -> None:
            """添加助手訊息"""
            container = self.query_one("#chat-container")
            await container.mount(MessageWidget("assistant", content))
            container.scroll_end()
        
        async def _process_message(self, message: str) -> None:
            """處理訊息"""
            if self.engine is None:
                await self._add_assistant_message("引擎尚未初始化")
                return
            
            from opencode.core.protocols import Intent, Context, EventType
            
            context = Context(
                session_id=self.session_id,
                user_id="tui_user"
            )
            
            intent = Intent.create(
                content=message,
                intent_type="chat",
                context=context
            )
            
            container = self.query_one("#chat-container")
            thinking_widget = None
            
            try:
                async for event in self.engine.process_intent(intent):
                    if event.type == EventType.THINKING:
                        content = event.payload.get("content", "")
                        if thinking_widget:
                            thinking_widget.content = content
                        else:
                            thinking_widget = ThinkingWidget(content)
                            await container.mount(thinking_widget)
                            container.scroll_end()
                    
                    elif event.type == EventType.TOOL_CALL:
                        tool = event.payload.get("content", "")
                        args = event.payload.get("data", {}).get("arguments", {})
                        await container.mount(ToolCallWidget(tool, args))
                        container.scroll_end()
                    
                    elif event.type == EventType.ANSWER:
                        # 移除 thinking widget
                        if thinking_widget:
                            thinking_widget.remove()
                        
                        answer = event.payload.get("content", "")
                        await self._add_assistant_message(answer)
                    
                    elif event.type == EventType.ERROR:
                        error = event.payload.get("content", "")
                        self.notify(f"錯誤: {error}", severity="error")
                
            except Exception as e:
                self.notify(f"處理失敗: {e}", severity="error")
                if thinking_widget:
                    thinking_widget.remove()
        
        def action_new_session(self) -> None:
            """新建 Session"""
            self.session_id = str(uuid.uuid4())[:8]
            self.sub_title = f"Session: {self.session_id}"
            
            # 清空聊天
            container = self.query_one("#chat-container")
            container.remove_children()
            
            self.notify(f"新 Session: {self.session_id}")
        
        def action_clear_chat(self) -> None:
            """清空聊天"""
            container = self.query_one("#chat-container")
            container.remove_children()
            self.notify("聊天已清空")
        
        def action_help(self) -> None:
            """顯示幫助"""
            self.notify(
                "Ctrl+N: 新 Session | Ctrl+C: 清空 | Ctrl+Q: 離開",
                timeout=5
            )


def run_tui():
    """執行 TUI"""
    if not TEXTUAL_AVAILABLE:
        print("錯誤: Textual 未安裝")
        print("請執行: pip install textual")
        return
    
    app = OpenCodeTUI()
    app.run()


if __name__ == "__main__":
    run_tui()
