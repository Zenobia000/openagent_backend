"""
Tools 基礎架構

定義所有工具的基類和註冊機制
Agent 通過 ToolRegistry 獲取和調用工具
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ToolCategory(str, Enum):
    """工具分類"""
    SEARCH = "search"           # 搜尋類
    KNOWLEDGE = "knowledge"     # 知識庫類
    CODE = "code"               # 程式碼類
    FILE = "file"               # 文件類
    WEB = "web"                 # 網路類
    DATA = "data"               # 數據類
    UTILITY = "utility"         # 工具類


@dataclass
class ToolParameter:
    """工具參數定義"""
    name: str
    type: str                   # string, int, float, bool, list, dict
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    """工具定義"""
    name: str
    description: str
    category: ToolCategory
    parameters: List[ToolParameter] = field(default_factory=list)
    returns: str = "Dict[str, Any]"
    examples: List[Dict] = field(default_factory=list)


class BaseTool(ABC):
    """
    工具基類
    
    所有工具必須繼承此類並實現 execute 方法
    """
    
    def __init__(self):
        self._initialized = False
    
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """返回工具定義"""
        pass
    
    @property
    def name(self) -> str:
        return self.definition.name
    
    @property
    def description(self) -> str:
        return self.definition.description
    
    async def initialize(self) -> bool:
        """初始化工具（可選覆寫）"""
        self._initialized = True
        return True
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        執行工具
        
        Args:
            **kwargs: 工具參數
            
        Returns:
            執行結果
        """
        pass
    
    def validate_params(self, **kwargs) -> Optional[str]:
        """驗證參數"""
        for param in self.definition.parameters:
            if param.required and param.name not in kwargs:
                return f"Missing required parameter: {param.name}"
        return None
    
    def to_openai_function(self) -> Dict[str, Any]:
        """轉換為 OpenAI Function Calling 格式"""
        properties = {}
        required = []
        
        for param in self.definition.parameters:
            prop = {"type": param.type, "description": param.description}
            if param.default is not None:
                prop["default"] = param.default
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
        
        # 新的 OpenAI API 格式需要 type: "function"
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


class ToolRegistry:
    """
    工具註冊中心
    
    管理所有可用工具的註冊和獲取
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, BaseTool] = {}
            cls._instance._initialized = False
        return cls._instance
    
    def register(self, tool: BaseTool) -> None:
        """註冊工具"""
        self._tools[tool.name] = tool
        logger.info(f"🔧 Tool registered: {tool.name}")
    
    def unregister(self, name: str) -> bool:
        """取消註冊"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False
    
    def get(self, name: str) -> Optional[BaseTool]:
        """獲取工具"""
        return self._tools.get(name)
    
    def list_all(self) -> List[str]:
        """列出所有工具名稱"""
        return list(self._tools.keys())
    
    def list_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """按分類列出工具"""
        return [
            tool for tool in self._tools.values()
            if tool.definition.category == category
        ]
    
    def get_all_definitions(self) -> List[Dict[str, Any]]:
        """獲取所有工具定義（給 LLM 用）"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "category": tool.definition.category.value,
                "parameters": [
                    {
                        "name": p.name,
                        "type": p.type,
                        "description": p.description,
                        "required": p.required
                    }
                    for p in tool.definition.parameters
                ]
            }
            for tool in self._tools.values()
        ]
    
    def get_openai_functions(self) -> List[Dict[str, Any]]:
        """獲取所有工具的 OpenAI Function 格式"""
        return [tool.to_openai_function() for tool in self._tools.values()]
    
    async def initialize_all(self) -> None:
        """初始化所有工具"""
        for tool in self._tools.values():
            try:
                await tool.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize tool {tool.name}: {e}")
        self._initialized = True
    
    async def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """執行工具"""
        tool = self.get(tool_name)
        if not tool:
            return {"error": f"Tool not found: {tool_name}"}
        
        # 驗證參數
        error = tool.validate_params(**kwargs)
        if error:
            return {"error": error}
        
        try:
            result = await tool.execute(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Tool {tool_name} execution error: {e}")
            return {"error": str(e)}


# 全域實例
def get_tool_registry() -> ToolRegistry:
    """獲取工具註冊中心"""
    return ToolRegistry()
