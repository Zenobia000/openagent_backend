"""
Tools 模組

提供所有可用工具的統一入口
"""

import logging
from typing import Dict, List, Any

from .base import (
    BaseTool,
    ToolDefinition,
    ToolParameter,
    ToolCategory,
    ToolRegistry,
    get_tool_registry
)

from .rag_tool import RAGSearchTool, RAGMultiSearchTool
from .web_tool import WebSearchTool, WebFetchTool, WebSearchAndFetchTool
from .code_tool import CodeExecutorTool, CodeAnalyzeTool
from .file_tool import FileReadTool, FileWriteTool, FileListTool

logger = logging.getLogger(__name__)

# 導出
__all__ = [
    # 基類
    "BaseTool",
    "ToolDefinition",
    "ToolParameter",
    "ToolCategory",
    "ToolRegistry",
    "get_tool_registry",
    # 工具
    "RAGSearchTool",
    "RAGMultiSearchTool",
    "WebSearchTool",
    "WebFetchTool",
    "WebSearchAndFetchTool",
    "CodeExecutorTool",
    "CodeAnalyzeTool",
    "FileReadTool",
    "FileWriteTool",
    "FileListTool",
    # 函數
    "register_all_tools",
    "get_tools_for_agent"
]


async def register_all_tools() -> ToolRegistry:
    """
    註冊所有工具到 ToolRegistry
    
    在系統啟動時調用
    """
    registry = get_tool_registry()
    
    # 註冊所有工具
    tools = [
        RAGSearchTool(),
        RAGMultiSearchTool(),
        WebSearchTool(),
        WebFetchTool(),
        WebSearchAndFetchTool(),  # 新增：深度搜尋
        CodeExecutorTool(),
        CodeAnalyzeTool(),
        FileReadTool(),
        FileWriteTool(),
        FileListTool(),
    ]
    
    for tool in tools:
        registry.register(tool)
    
    # 初始化所有工具
    await registry.initialize_all()
    
    logger.info(f"✅ Registered {len(tools)} tools")
    return registry


def get_tools_for_agent(agent_type: str) -> List[str]:
    """
    根據 Agent 類型返回可用的工具列表
    
    Args:
        agent_type: Agent 類型
        
    Returns:
        工具名稱列表
    """
    tool_mapping = {
        "researcher": [
            "rag_search",
            "rag_multi_search",
            "web_search",
            "web_fetch",
            "web_deep_search",  # 新增：深度搜尋
            "file_read",
            "file_list"
        ],
        "writer": [
            "rag_search",
            "web_search",  # 寫作者也可以搜尋
            "file_read",
            "file_write",
            "file_list"
        ],
        "coder": [
            "code_execute",
            "code_analyze",
            "file_read",
            "file_write",
            "file_list",
            "web_search"
        ],
        "analyst": [
            "rag_search",
            "rag_multi_search",
            "web_search",
            "code_execute",
            "file_read",
            "file_list"
        ],
        "reviewer": [
            "rag_search",
            "web_search",
            "code_analyze",
            "file_read"
        ],
        "coordinator": [
            # 協調者可以使用所有工具
            "rag_search",
            "rag_multi_search",
            "web_search",
            "web_fetch",
            "web_deep_search",
            "code_execute",
            "code_analyze",
            "file_read",
            "file_write",
            "file_list"
        ]
    }
    
    return tool_mapping.get(agent_type, [])


def get_tool_descriptions_for_prompt(tool_names: List[str]) -> str:
    """
    生成給 LLM 的工具描述
    
    Args:
        tool_names: 工具名稱列表
        
    Returns:
        工具描述字串（給 prompt 用）
    """
    registry = get_tool_registry()
    descriptions = []
    
    for name in tool_names:
        tool = registry.get(name)
        if tool:
            params = ", ".join([
                f"{p.name}: {p.type}" + (" (optional)" if not p.required else "")
                for p in tool.definition.parameters
            ])
            descriptions.append(f"- **{tool.name}**({params}): {tool.description}")
    
    return "\n".join(descriptions)
