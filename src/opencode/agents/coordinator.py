"""
Agent 協調器

負責：
1. 管理所有 Agent
2. 協調任務執行流程
3. 傳遞上下文
4. 聚合結果
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from .base import BaseAgent, AgentType, AgentTask, AgentResult
from .dispatcher import DispatcherAgent
from .specialists import (
    ResearcherAgent, 
    WriterAgent, 
    CoderAgent, 
    AnalystAgent, 
    ReviewerAgent
)

logger = logging.getLogger(__name__)


class PluginAgentWrapper:
    """
    插件 Agent 包裝器
    
    將插件 Agent 包裝成與內建 Agent 相同的介面
    """
    
    def __init__(self, plugin):
        self.plugin = plugin
        self.type = AgentType.REVIEWER  # 使用通用類型
        self._custom_type = plugin.agent_name
    
    @property
    def name(self) -> str:
        return self.plugin.agent_name
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self._custom_type,
            "name": self.plugin.metadata.name,
            "description": self.plugin.agent_description,
            "status": "active",
            "is_plugin": True,
            "plugin_id": self.plugin.metadata.id
        }
    
    async def initialize(self) -> bool:
        return True
    
    async def process_task(self, task: AgentTask) -> AgentResult:
        """執行任務"""
        import time
        start_time = time.time()
        
        try:
            result = await self.plugin.process_task(
                task_description=task.description,
                parameters=task.parameters,
                context=task.context
            )
            
            return AgentResult(
                task_id=task.id,
                agent_type=self._custom_type,
                success=result.get("success", False),
                output=result.get("output", {}),
                tool_calls=[],
                thinking=f"Plugin agent: {self.name}",
                execution_time=time.time() - start_time,
                error=result.get("error")
            )
            
        except Exception as e:
            logger.error(f"Plugin agent {self.name} error: {e}")
            return AgentResult(
                task_id=task.id,
                agent_type=self._custom_type,
                success=False,
                output={},
                tool_calls=[],
                thinking="",
                execution_time=time.time() - start_time,
                error=str(e)
            )


@dataclass
class WorkflowStep:
    """工作流程步驟"""
    step_id: str
    agent_type: str
    task: AgentTask
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[AgentResult] = None
    depends_on: List[str] = field(default_factory=list)


@dataclass
class WorkflowExecution:
    """工作流程執行記錄"""
    id: str
    original_request: str
    steps: List[WorkflowStep]
    status: str = "pending"  # pending, running, completed, failed
    final_result: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class AgentCoordinator:
    """
    Agent 協調器
    
    核心職責：
    1. 接收用戶請求
    2. 調用 Dispatcher 分析和拆解任務
    3. 按順序調用專業 Agent 執行
    4. 在 Agent 之間傳遞上下文
    5. 聚合最終結果
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._dispatcher: Optional[DispatcherAgent] = None
        self._initialized = False
        self._executions: Dict[str, WorkflowExecution] = {}
    
    async def initialize(self) -> bool:
        """初始化協調器和所有 Agent"""
        try:
            # 先初始化工具
            from opencode.tools import register_all_tools
            await register_all_tools()
            
            # 創建總機 Agent
            self._dispatcher = DispatcherAgent()
            await self._dispatcher.initialize()
            
            # 創建專業 Agent
            agent_classes = [
                ResearcherAgent,
                WriterAgent,
                CoderAgent,
                AnalystAgent,
                ReviewerAgent
            ]
            
            for agent_class in agent_classes:
                agent = agent_class()
                await agent.initialize()
                self._agents[agent.type.value] = agent
            
            # 載入插件 Agent
            await self._load_plugin_agents()
            
            self._initialized = True
            logger.info(f"✅ AgentCoordinator initialized with {len(self._agents)} agents")
            return True
            
        except Exception as e:
            logger.error(f"AgentCoordinator init error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    async def _load_plugin_agents(self) -> None:
        """載入插件 Agent"""
        try:
            from opencode.plugins.manager import get_plugin_manager, PluginStatus, PluginType
            
            pm = get_plugin_manager()
            
            # 發現並載入插件
            pm.discover_plugins()
            
            for plugin_id, metadata in pm._metadata.items():
                if metadata.plugin_type == PluginType.AGENT:
                    try:
                        # 載入並啟用插件
                        if await pm.load_plugin(plugin_id):
                            await pm.enable_plugin(plugin_id)
                            
                            # 包裝成 Agent
                            plugin = pm.get_plugin(plugin_id)
                            if plugin and hasattr(plugin, 'agent_name'):
                                wrapper = PluginAgentWrapper(plugin)
                                self._agents[plugin.agent_name] = wrapper
                                logger.info(f"🔌 Loaded plugin agent: {plugin.agent_name}")
                    except Exception as e:
                        logger.error(f"Failed to load plugin agent {plugin_id}: {e}")
                        
        except ImportError:
            logger.warning("Plugin system not available")
        except Exception as e:
            logger.error(f"Error loading plugin agents: {e}")
    
    async def reload_plugin_agents(self) -> None:
        """熱重載插件 Agent（不需重啟）"""
        # 移除現有的插件 Agent
        plugin_agents = [
            name for name, agent in self._agents.items() 
            if isinstance(agent, PluginAgentWrapper)
        ]
        for name in plugin_agents:
            del self._agents[name]
        
        # 重新載入
        await self._load_plugin_agents()
        logger.info(f"🔄 Reloaded plugin agents, total: {len(self._agents)}")
    
    def get_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """獲取指定類型的 Agent"""
        return self._agents.get(agent_type)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有 Agent"""
        agents = [self._dispatcher.to_dict()] if self._dispatcher else []
        agents.extend([agent.to_dict() for agent in self._agents.values()])
        return agents
    
    async def process_request(
        self, 
        user_request: str,
        context: Dict[str, Any] = None,
        stream: bool = False
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        處理用戶請求（完整流程）
        
        Args:
            user_request: 用戶請求
            context: 上下文（如選中的文件、附件）
            stream: 是否串流輸出
            
        Yields:
            執行進度和結果
        """
        if not self._initialized:
            logger.error("❌ Coordinator not initialized")
            yield {"type": "error", "content": "Coordinator not initialized"}
            return
        
        execution_id = str(uuid.uuid4())[:8]
        logger.info(f"{'='*50}")
        logger.info(f"🚀 Processing request [{execution_id}]")
        logger.info(f"📝 Request: {user_request[:100]}...")
        logger.info(f"📦 Context: {context}")
        logger.info(f"{'='*50}")
        
        # 檢查是否有多模態附件
        attachments = (context or {}).get("attachments", [])
        has_images = any(a.get("type") == "image" for a in attachments) if attachments else False
        has_files = any(a.get("type") == "file" for a in attachments) if attachments else False
        
        logger.info(f"[{execution_id}] 📎 Attachments: {len(attachments) if attachments else 0}")
        logger.info(f"[{execution_id}] 🖼️ Has images: {has_images}")
        
        # 如果有圖片附件，直接使用 Vision 處理
        if has_images:
            async for event in self._process_vision_request(
                execution_id, user_request, attachments, context
            ):
                yield event
            return
        
        # 如果有文件附件，先提取內容再處理
        if has_files:
            async for event in self._process_file_request(
                execution_id, user_request, attachments, context
            ):
                yield event
            return
        
        # Token 使用量追蹤
        total_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0
        }
        
        def accumulate_usage(result: AgentResult):
            """累加 Agent 的 token 使用量"""
            # 從 AgentResult.usage 獲取（新版本）
            if hasattr(result, 'usage') and result.usage:
                usage = result.usage
                total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                total_usage["total_tokens"] += usage.get("total_tokens", 0)
                total_usage["estimated_cost_usd"] += usage.get("estimated_cost_usd", 0)
                logger.info(f"📊 累加 usage: +{usage.get('total_tokens', 0)} tokens")
            # 向後兼容：從 output.usage 獲取
            elif hasattr(result, 'output') and isinstance(result.output, dict):
                usage = result.output.get('usage', {})
                if usage:
                    total_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    total_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                    total_usage["total_tokens"] += usage.get("total_tokens", 0)
                    total_usage["estimated_cost_usd"] += usage.get("estimated_cost_usd", 0)
        
        # 1. 分析請求 - 發送思考事件
        logger.info(f"[{execution_id}] Step 1: Analyzing request...")
        yield {
            "type": "thinking",
            "step": "analyzing",
            "content": "正在理解您的問題...",
            "details": f"分析請求內容：{user_request[:100]}..."
        }
        
        dispatch_task = AgentTask(
            type="dispatch",
            description="分析用戶請求",
            parameters={"request": user_request},
            context=context or {}
        )
        
        dispatch_result = await self._dispatcher.process_task(dispatch_task)
        accumulate_usage(dispatch_result)
        
        logger.info(f"[{execution_id}] Dispatcher result: success={dispatch_result.success}")
        logger.debug(f"[{execution_id}] Dispatcher output: {dispatch_result.output}")
        
        if not dispatch_result.success:
            logger.error(f"[{execution_id}] ❌ Dispatcher failed: {dispatch_result.error}")
            yield {"type": "error", "content": "無法理解您的請求"}
            return
        
        analysis = dispatch_result.output.get("analysis", "")
        subtasks = dispatch_result.output.get("subtasks", [])
        is_simple_query = dispatch_result.output.get("is_simple_query", False)
        
        logger.info(f"[{execution_id}] Analysis: {analysis[:100]}...")
        logger.info(f"[{execution_id}] Is simple query: {is_simple_query}")
        logger.info(f"[{execution_id}] Subtasks: {len(subtasks)}")
        for st in subtasks:
            logger.info(f"[{execution_id}]   - {st.get('agent')}: {st.get('task', st.get('description', ''))[:50]}")
        
        # 發送分析完成事件
        yield {
            "type": "analysis_complete",
            "content": analysis,
            "is_simple_query": is_simple_query
        }
        
        # 發送規劃事件
        yield {
            "type": "plan",
            "content": analysis,
            "subtasks": subtasks,
            "total_steps": len(subtasks),
            "is_simple_query": is_simple_query
        }
        
        if not subtasks:
            logger.error(f"[{execution_id}] ❌ No subtasks generated")
            yield {"type": "error", "content": "無法拆解任務"}
            return
        
        # 2. 按順序執行子任務
        logger.info(f"[{execution_id}] Step 2: Executing {len(subtasks)} subtasks...")
        results = {}  # task_id -> result
        
        for i, subtask in enumerate(subtasks):
            task_id = subtask.get("id", str(i))
            agent_type = subtask.get("agent", "researcher")
            task_description = subtask.get("description", subtask.get("task", ""))
            depends_on = subtask.get("depends_on", [])
            
            # 發送開始執行事件
            yield {
                "type": "agent_start",
                "step": i + 1,
                "total": len(subtasks),
                "agent": agent_type,
                "task": task_description,
                "is_simple_query": is_simple_query
            }
            
            logger.info(f"[{execution_id}] Executing subtask {i+1}/{len(subtasks)}: {agent_type}")
            logger.info(f"[{execution_id}]   Task: {task_description[:100]}")
            
            # 獲取 Agent
            agent = self.get_agent(agent_type)
            if not agent:
                logger.warning(f"[{execution_id}] ⚠️ Agent {agent_type} not found, skipping")
                yield {
                    "type": "warning",
                    "content": f"Agent {agent_type} not found, skipping"
                }
                continue
            
            # 構建上下文（包含依賴任務的結果）
            task_context = dict(context or {})
            for dep_id in depends_on:
                if dep_id in results:
                    task_context["previous_result"] = results[dep_id].output
            
            # 構建任務參數（合併 subtask 中的特殊欄位）
            task_params = subtask.get("parameters", {})
            # 傳遞網路搜尋相關參數
            if subtask.get("use_web_search"):
                task_params["use_web_search"] = True
            if subtask.get("search_query"):
                task_params["search_query"] = subtask.get("search_query")
            
            # 創建任務
            agent_task = AgentTask(
                id=task_id,
                type=agent_type,
                description=task_description,
                parameters=task_params,
                context=task_context
            )
            
            # 執行任務
            try:
                logger.info(f"[{execution_id}] 🤖 Agent {agent_type} processing task...")
                result = await agent.process_task(agent_task)
                results[task_id] = result
                
                logger.info(f"[{execution_id}] ✅ Agent {agent_type} completed: success={result.success}")
                logger.info(f"[{execution_id}]   Tool calls: {len(result.tool_calls)}")
                logger.info(f"[{execution_id}]   Execution time: {result.execution_time:.2f}s")
                
                # 發送每個工具呼叫的事件
                for tc in result.tool_calls:
                    tool_name = tc.get("tool", "unknown")
                    tool_args = tc.get("arguments", {})
                    tool_result = tc.get("result", {})
                    
                    yield {
                        "type": "tool_call",
                        "agent": agent_type,
                        "tool": tool_name,
                        "arguments": tool_args,
                        "result": tool_result,
                        "success": tool_result.get("success", True) if isinstance(tool_result, dict) else True
                    }
                    
                    # 如果是程式碼執行，發送特殊事件
                    if "sandbox" in tool_name.lower() or "execute" in tool_name.lower():
                        yield {
                            "type": "code_execution",
                            "agent": agent_type,
                            "code": tool_args.get("code", ""),
                            "result": tool_result
                        }
                
                # 發送步驟完成事件
                yield {
                    "type": "step_result",
                    "step": i + 1,
                    "agent": agent_type,
                    "success": result.success,
                    "output": result.output,
                    "tool_calls": result.tool_calls,
                    "execution_time": result.execution_time
                }
                
                # 累加 token 使用量
                accumulate_usage(result)
                
            except Exception as e:
                logger.error(f"[{execution_id}] ❌ Task {task_id} failed: {e}")
                import traceback
                logger.error(f"[{execution_id}] Traceback: {traceback.format_exc()}")
                yield {
                    "type": "step_error",
                    "step": i + 1,
                    "agent": agent_type,
                    "error": str(e)
                }
        
        # 3. 聚合最終結果
        yield {
            "type": "summarizing",
            "content": "正在整理最終結果..."
        }
        
        summary_result = await self._summarize_results(user_request, results)
        final_result = summary_result.get("answer", "處理完成")
        summary_usage = summary_result.get("usage", {})
        
        # 累加總結步驟的 token
        if summary_usage:
            total_usage["prompt_tokens"] += summary_usage.get("prompt_tokens", 0)
            total_usage["completion_tokens"] += summary_usage.get("completion_tokens", 0)
            total_usage["total_tokens"] += summary_usage.get("total_tokens", 0)
            total_usage["estimated_cost_usd"] += summary_usage.get("estimated_cost_usd", 0)
        
        logger.info(f"[{execution_id}] 📊 Total token usage: {total_usage}")
        
        yield {
            "type": "final",
            "content": final_result,
            "execution_id": execution_id,
            "total_steps": len(subtasks),
            "completed_steps": len(results),
            "usage": total_usage
        }
    
    async def _summarize_results(
        self, 
        original_request: str, 
        results: Dict[str, AgentResult]
    ) -> Dict[str, Any]:
        """
        聚合所有 Agent 的結果為最終回答
        
        Returns:
            {"answer": str, "usage": dict}
        """
        if not results:
            return {"answer": "無法完成任務", "usage": {}}
        
        # 使用 Dispatcher 的 LLM 來總結
        results_summary = []
        for task_id, result in results.items():
            agent_type = result.agent_type
            output = result.output
            
            # 截斷過長的內容，避免 token 超限
            if isinstance(output, dict):
                # 移除 base64 圖片和過長的代碼
                summary_output = {}
                for key, value in output.items():
                    if key == 'figures':
                        # 只記錄圖片數量
                        summary_output[key] = f"[{len(value)} 張圖表已生成]"
                    elif key == 'code':
                        # 截斷代碼
                        if len(str(value)) > 500:
                            summary_output[key] = str(value)[:500] + "... [代碼已截斷]"
                        else:
                            summary_output[key] = value
                    elif key == 'execution_result':
                        # 只保留關鍵信息
                        if isinstance(value, dict):
                            summary_output[key] = {
                                'success': value.get('success'),
                                'stdout': str(value.get('stdout', ''))[:300],
                                'error': value.get('error')
                            }
                        else:
                            summary_output[key] = str(value)[:300]
                    elif key in ['explanation', 'content']:
                        # 截斷長文本
                        if len(str(value)) > 1000:
                            summary_output[key] = str(value)[:1000] + "... [已截斷]"
                        else:
                            summary_output[key] = value
                    else:
                        summary_output[key] = value
                output_str = str(summary_output)
            else:
                output_str = str(output)[:2000]
            
            results_summary.append(f"**{agent_type}**:\n{output_str}")
        
        prompt = f"""用戶原始請求：{original_request}

各 Agent 的執行結果：
{chr(10).join(results_summary)}

請根據以上所有結果，給用戶一個完整、清晰的最終回答。
直接回答用戶的問題，不要提及 Agent 或工作流程的細節。
如果有計算結果，請明確說明計算結果。"""

        result = await self._dispatcher.think(prompt, use_tools=False)
        return {
            "answer": result.get("answer", "處理完成"),
            "usage": result.get("usage", {})
        }
    
    async def _process_vision_request(
        self,
        execution_id: str,
        user_request: str,
        attachments: List[Dict],
        context: Dict = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        處理包含圖片的請求（使用 GPT-4 Vision）
        """
        import os
        from openai import AsyncOpenAI
        
        images = [a for a in attachments if a.get("type") == "image"]
        logger.info(f"[{execution_id}] 🖼️ Processing {len(images)} images with Vision...")
        
        # 發送思考事件
        yield {
            "type": "thinking",
            "step": "analyzing",
            "content": f"正在分析 {len(images)} 張圖片...",
            "details": "使用 GPT-4 Vision 進行圖片識別"
        }
        
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                yield {"type": "error", "content": "OPENAI_API_KEY 未設置"}
                return
            
            client = AsyncOpenAI(api_key=api_key)
            
            # 構建多模態消息
            content = []
            
            # 添加文字提示
            content.append({
                "type": "text",
                "text": user_request if user_request else "請描述這張圖片的內容。"
            })
            
            # 添加圖片
            for img in images:
                img_data = img.get("data", "")
                mime_type = img.get("mime_type", "image/jpeg")
                
                if img_data:
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{img_data}",
                            "detail": "auto"
                        }
                    })
                    logger.info(f"[{execution_id}] Added image: {img.get('name', 'unknown')}")
            
            # 發送處理中事件
            yield {
                "type": "step_start",
                "agent": "vision",
                "task": "分析圖片內容"
            }
            
            # 調用 GPT-4 Vision
            response = await client.chat.completions.create(
                model="gpt-4o",  # GPT-4 Vision
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            logger.info(f"[{execution_id}] ✅ Vision analysis completed")
            
            # 計算使用量
            usage = {}
            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                total_tokens = input_tokens + output_tokens
                
                # GPT-4o 價格估算
                estimated_cost = (input_tokens * 0.005 + output_tokens * 0.015) / 1000
                
                usage = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "estimated_cost_usd": estimated_cost
                }
                logger.info(f"[{execution_id}] 📊 Vision usage: {total_tokens} tokens (${estimated_cost:.4f})")
            
            # 發送完成事件
            yield {
                "type": "step_complete",
                "agent": "vision",
                "task": "分析圖片內容",
                "success": True
            }
            
            # 發送最終結果
            yield {
                "type": "final",
                "content": answer,
                "usage": usage
            }
            
        except Exception as e:
            logger.error(f"[{execution_id}] ❌ Vision error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            yield {
                "type": "final",
                "content": f"圖片分析失敗: {str(e)}",
                "usage": {}
            }
    
    async def _process_file_request(
        self,
        execution_id: str,
        user_request: str,
        attachments: List[Dict],
        context: Dict = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        處理包含文件的請求（提取內容後分析）
        """
        import os
        import base64
        from openai import AsyncOpenAI
        
        files = [a for a in attachments if a.get("type") == "file"]
        logger.info(f"[{execution_id}] 📄 Processing {len(files)} files...")
        
        # 發送思考事件
        yield {
            "type": "thinking",
            "step": "analyzing",
            "content": f"正在分析 {len(files)} 個文件...",
            "details": "提取文件內容進行分析"
        }
        
        # 提取文件內容
        file_contents = []
        for f in files:
            name = f.get("name", "未知文件")
            mime_type = f.get("mime_type", "")
            data = f.get("data", "")
            
            content = ""
            try:
                if mime_type.startswith("text/") or name.endswith((".txt", ".md", ".csv", ".json")):
                    # 文字文件直接解碼
                    content = base64.b64decode(data).decode("utf-8")[:10000]
                elif "excel" in mime_type or "spreadsheet" in mime_type or name.endswith((".xls", ".xlsx")):
                    # Excel 文件嘗試讀取
                    try:
                        import io
                        import pandas as pd
                        
                        file_bytes = base64.b64decode(data)
                        df = pd.read_excel(io.BytesIO(file_bytes))
                        content = f"Excel 內容（前 50 行）:\n\n{df.head(50).to_string()}"
                    except Exception as e:
                        content = f"[無法讀取 Excel: {e}]"
                else:
                    content = f"[不支援的文件類型: {mime_type}]"
            except Exception as e:
                content = f"[文件解碼錯誤: {e}]"
            
            file_contents.append(f"### 文件: {name}\n\n{content}")
            logger.info(f"[{execution_id}] Extracted content from: {name}")
        
        # 發送處理中事件
        yield {
            "type": "step_start",
            "agent": "analyst",
            "task": "分析文件內容"
        }
        
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                yield {"type": "error", "content": "OPENAI_API_KEY 未設置"}
                return
            
            client = AsyncOpenAI(api_key=api_key)
            
            combined_content = "\n\n---\n\n".join(file_contents)
            
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一個專業的文件分析助手。根據用戶上傳的文件內容和問題，提供詳細的分析和回答。使用繁體中文。"
                    },
                    {
                        "role": "user",
                        "content": f"## 用戶問題\n{user_request}\n\n## 文件內容\n{combined_content}\n\n請分析這些文件並回答問題。"
                    }
                ],
                max_tokens=2000,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            logger.info(f"[{execution_id}] ✅ File analysis completed")
            
            # 計算使用量
            usage = {}
            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                total_tokens = input_tokens + output_tokens
                estimated_cost = (input_tokens * 0.005 + output_tokens * 0.015) / 1000
                
                usage = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "estimated_cost_usd": estimated_cost
                }
            
            # 發送完成事件
            yield {
                "type": "step_complete",
                "agent": "analyst",
                "task": "分析文件內容",
                "success": True
            }
            
            # 發送最終結果
            yield {
                "type": "final",
                "content": answer,
                "usage": usage
            }
            
        except Exception as e:
            logger.error(f"[{execution_id}] ❌ File analysis error: {e}")
            yield {
                "type": "final",
                "content": f"文件分析失敗: {str(e)}",
                "usage": {}
            }

    async def execute_single_agent(
        self,
        agent_type: str,
        task_description: str,
        parameters: Dict = None,
        context: Dict = None
    ) -> AgentResult:
        """
        直接執行單個 Agent（跳過 Dispatcher）
        
        用於簡單任務或測試
        """
        agent = self.get_agent(agent_type)
        if not agent:
            return AgentResult(
                task_id="",
                agent_type=agent_type,
                success=False,
                output={},
                error=f"Agent {agent_type} not found"
            )
        
        task = AgentTask(
            type=agent_type,
            description=task_description,
            parameters=parameters or {},
            context=context or {}
        )
        
        return await agent.process_task(task)


# 全域實例
_coordinator: Optional[AgentCoordinator] = None


async def get_coordinator() -> AgentCoordinator:
    """獲取協調器實例"""
    global _coordinator
    if _coordinator is None:
        _coordinator = AgentCoordinator()
        await _coordinator.initialize()
    return _coordinator
