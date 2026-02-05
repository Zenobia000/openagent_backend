"""
Agent 基類

定義所有 Agent 的通用行為和介面
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Agent 類型"""
    DISPATCHER = "dispatcher"     # 總機 - 分析需求、分配任務
    RESEARCHER = "researcher"     # 研究者 - 搜集和分析資料
    WRITER = "writer"             # 寫作者 - 撰寫內容
    CODER = "coder"               # 編碼者 - 編寫和分析程式
    ANALYST = "analyst"           # 分析師 - 數據分析
    REVIEWER = "reviewer"         # 審核者 - 審核品質


@dataclass
class AgentTask:
    """Agent 任務"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = ""
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文（來自前一步）
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class AgentResult:
    """Agent 執行結果"""
    task_id: str
    agent_type: str
    success: bool
    output: Any
    tool_calls: List[Dict] = field(default_factory=list)  # 調用的工具記錄
    thinking: str = ""  # 思考過程
    error: Optional[str] = None
    execution_time: float = 0
    usage: Dict[str, Any] = field(default_factory=dict)  # Token 使用量
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class BaseAgent(ABC):
    """
    Agent 基類
    
    所有專業 Agent 繼承此類，實現 process_task 方法
    """
    
    def __init__(self, agent_type: AgentType, name: str = None):
        self.id = f"{agent_type.value}_{uuid.uuid4().hex[:8]}"
        self.type = agent_type
        self.name = name or f"{agent_type.value.title()} Agent"
        self.model = os.getenv("LLM_MODEL", "gpt-4o")
        self._llm_client = None
        self._tool_registry = None
        self._available_tools: List[str] = []
        self._memory: List[Dict] = []  # 對話記憶
    
    async def initialize(self) -> bool:
        """初始化 Agent"""
        try:
            # 初始化 LLM 客戶端
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._llm_client = AsyncOpenAI(api_key=api_key)
            
            # 獲取工具註冊中心
            from opencode.tools import get_tool_registry, get_tools_for_agent
            self._tool_registry = get_tool_registry()
            self._available_tools = get_tools_for_agent(self.type.value)
            
            logger.info(f"🤖 Agent initialized: {self.name} with {len(self._available_tools)} tools")
            return True
        except Exception as e:
            logger.error(f"Agent init error: {e}")
            return False
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """返回 Agent 的系統提示"""
        pass
    
    @abstractmethod
    async def process_task(self, task: AgentTask) -> AgentResult:
        """
        處理任務
        
        Args:
            task: 要處理的任務
            
        Returns:
            執行結果
        """
        pass
    
    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        調用工具
        
        Args:
            tool_name: 工具名稱
            **kwargs: 工具參數
            
        Returns:
            工具執行結果
        """
        if tool_name not in self._available_tools:
            return {"error": f"Tool {tool_name} not available for this agent"}
        
        if not self._tool_registry:
            return {"error": "Tool registry not initialized"}
        
        result = await self._tool_registry.execute(tool_name, **kwargs)
        logger.info(f"🔧 {self.name} called tool: {tool_name}")
        return result
    
    async def think(self, prompt: str, use_tools: bool = True) -> Dict[str, Any]:
        """
        使用 LLM 思考
        
        Args:
            prompt: 提示
            use_tools: 是否啟用工具調用
            
        Returns:
            思考結果，包含回答、工具調用和 token 使用量
        """
        if not self._llm_client:
            logger.error(f"❌ {self.name}: LLM client not initialized")
            return {"error": "LLM client not initialized", "answer": "", "usage": {}}
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self._memory[-10:],  # 最近 10 條記憶
            {"role": "user", "content": prompt}
        ]
        
        logger.info(f"🤖 {self.name} thinking... (use_tools={use_tools})")
        logger.debug(f"📝 Prompt: {prompt[:200]}...")
        
        # Token 使用量追蹤
        total_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
        
        try:
            # 準備工具定義
            tools = None
            if use_tools and self._available_tools and self._tool_registry:
                tools = []
                for name in self._available_tools:
                    tool = self._tool_registry.get(name)
                    if tool:
                        tool_def = tool.to_openai_function()
                        tools.append(tool_def)
                        logger.debug(f"🔧 Tool loaded: {name}")
                
                if tools:
                    logger.info(f"🔧 {self.name} has {len(tools)} tools available")
            
            # 調用 LLM
            logger.info(f"📡 Calling LLM ({self.model})...")
            response = await self._llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                temperature=0.7
            )
            
            # 記錄 token 使用量
            if response.usage:
                total_usage["prompt_tokens"] += response.usage.prompt_tokens
                total_usage["completion_tokens"] += response.usage.completion_tokens
                total_usage["total_tokens"] += response.usage.total_tokens
            
            message = response.choices[0].message
            tool_calls_made = []
            
            logger.info(f"✅ LLM responded (has_tool_calls={bool(message.tool_calls)})")
            
            # 處理工具調用
            if message.tool_calls:
                logger.info(f"🔧 Processing {len(message.tool_calls)} tool calls...")
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"🔧 Calling tool: {tool_name}")
                    logger.debug(f"   Args: {tool_args}")
                    
                    # 執行工具
                    tool_result = await self.call_tool(tool_name, **tool_args)
                    
                    logger.info(f"✅ Tool {tool_name} completed")
                    
                    tool_calls_made.append({
                        "tool": tool_name,
                        "arguments": tool_args,
                        "result": tool_result
                    })
                
                # 將工具結果加入上下文，再次調用 LLM
                tool_results_prompt = "\n\n".join([
                    f"工具 {tc['tool']} 結果：\n{json.dumps(tc['result'], ensure_ascii=False, indent=2)}"
                    for tc in tool_calls_made
                ])
                
                messages.append({"role": "assistant", "content": message.content or ""})
                messages.append({"role": "user", "content": f"根據工具執行結果，請總結回答：\n\n{tool_results_prompt}"})
                
                logger.info(f"📡 Calling LLM for final answer...")
                final_response = await self._llm_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7
                )
                answer = final_response.choices[0].message.content
                
                # 累加第二次調用的 token
                if final_response.usage:
                    total_usage["prompt_tokens"] += final_response.usage.prompt_tokens
                    total_usage["completion_tokens"] += final_response.usage.completion_tokens
                    total_usage["total_tokens"] += final_response.usage.total_tokens
            else:
                answer = message.content
            
            # 更新記憶
            self._memory.append({"role": "user", "content": prompt})
            self._memory.append({"role": "assistant", "content": answer})
            
            # 計算成本估算 (GPT-4o 價格: $2.50/1M input, $10/1M output)
            estimated_cost = (
                total_usage["prompt_tokens"] * 0.0000025 +
                total_usage["completion_tokens"] * 0.00001
            )
            total_usage["estimated_cost_usd"] = round(estimated_cost, 6)
            
            logger.info(f"✅ {self.name} completed thinking")
            logger.info(f"📊 Token usage: {total_usage['total_tokens']} (${total_usage['estimated_cost_usd']:.4f})")
            logger.debug(f"📝 Answer: {answer[:200] if answer else 'None'}...")
            
            return {
                "answer": answer,
                "tool_calls": tool_calls_made,
                "usage": total_usage
            }
            
        except Exception as e:
            logger.error(f"❌ {self.name} think error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"error": str(e), "answer": "", "usage": total_usage}
    
    def clear_memory(self):
        """清空記憶"""
        self._memory = []
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "model": self.model,
            "available_tools": self._available_tools
        }
