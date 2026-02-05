"""
Multi-Agent 協作系統

架構：
- tools/: 各種工具（RAG、網路搜尋、程式執行等）
- agents/: 專業 Agent（研究者、寫作者、編碼者等）

流程：
用戶請求 → Dispatcher（分析拆解）→ 專業 Agent → 調用 Tools → 返回結果
"""

from .base import BaseAgent, AgentType, AgentTask, AgentResult
from .dispatcher import DispatcherAgent
from .specialists import (
    ResearcherAgent,
    WriterAgent,
    CoderAgent,
    AnalystAgent,
    ReviewerAgent
)
from .coordinator import AgentCoordinator, get_coordinator
from .routes import router

__all__ = [
    # 基類
    "BaseAgent",
    "AgentType",
    "AgentTask",
    "AgentResult",
    # Agents
    "DispatcherAgent",
    "ResearcherAgent",
    "WriterAgent",
    "CoderAgent",
    "AnalystAgent",
    "ReviewerAgent",
    # 協調器
    "AgentCoordinator",
    "get_coordinator",
    # 路由
    "router"
]
