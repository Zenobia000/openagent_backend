"""
工作流編排系統

支援：
- 視覺化工作流編輯
- 多 Agent 協作
- 條件分支
- 循環執行
- 變數傳遞
"""

import logging
import asyncio
import uuid
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """節點類型"""
    START = "start"
    END = "end"
    AGENT = "agent"
    TOOL = "tool"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL = "parallel"
    INPUT = "input"
    OUTPUT = "output"
    CODE = "code"
    DELAY = "delay"


class WorkflowStatus(str, Enum):
    """工作流狀態"""
    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WorkflowNode:
    """工作流節點"""
    id: str
    type: NodeType
    name: str
    config: Dict[str, Any] = field(default_factory=dict)
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0, "y": 0})
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "config": self.config,
            "position": self.position
        }


@dataclass
class WorkflowEdge:
    """工作流邊（連接）"""
    id: str
    source: str  # 源節點 ID
    target: str  # 目標節點 ID
    condition: Optional[str] = None  # 條件表達式
    label: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "condition": self.condition,
            "label": self.label
        }


@dataclass
class Workflow:
    """工作流定義"""
    id: str
    name: str
    description: str = ""
    nodes: List[WorkflowNode] = field(default_factory=list)
    edges: List[WorkflowEdge] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    created_by: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "variables": self.variables,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "created_by": self.created_by
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Workflow':
        nodes = [
            WorkflowNode(
                id=n["id"],
                type=NodeType(n["type"]),
                name=n["name"],
                config=n.get("config", {}),
                position=n.get("position", {"x": 0, "y": 0})
            )
            for n in data.get("nodes", [])
        ]
        edges = [
            WorkflowEdge(
                id=e["id"],
                source=e["source"],
                target=e["target"],
                condition=e.get("condition"),
                label=e.get("label")
            )
            for e in data.get("edges", [])
        ]
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            nodes=nodes,
            edges=edges,
            variables=data.get("variables", {}),
            status=WorkflowStatus(data.get("status", "draft")),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            created_by=data.get("created_by", "")
        )


@dataclass
class ExecutionContext:
    """執行上下文"""
    workflow_id: str
    execution_id: str
    variables: Dict[str, Any] = field(default_factory=dict)
    current_node: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "running"
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    finished_at: Optional[str] = None


class WorkflowEngine:
    """工作流執行引擎"""
    
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or Path("data/workflows")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self._workflows: Dict[str, Workflow] = {}
        self._executions: Dict[str, ExecutionContext] = {}
        
        # 載入已保存的工作流
        self._load_workflows()
        
        logger.info(f"✅ WorkflowEngine initialized, {len(self._workflows)} workflows loaded")
    
    def _load_workflows(self) -> None:
        """載入已保存的工作流"""
        for file in self.data_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                workflow = Workflow.from_dict(data)
                self._workflows[workflow.id] = workflow
            except Exception as e:
                logger.error(f"Failed to load workflow {file}: {e}")
    
    def _save_workflow(self, workflow: Workflow) -> None:
        """保存工作流"""
        file_path = self.data_dir / f"{workflow.id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(workflow.to_dict(), f, ensure_ascii=False, indent=2)
    
    def create_workflow(self, name: str, description: str = "", created_by: str = "") -> Workflow:
        """創建新工作流"""
        workflow_id = f"wf_{uuid.uuid4().hex[:8]}"
        
        # 創建預設節點
        start_node = WorkflowNode(
            id="start_1",
            type=NodeType.START,
            name="開始",
            position={"x": 100, "y": 200}
        )
        end_node = WorkflowNode(
            id="end_1",
            type=NodeType.END,
            name="結束",
            position={"x": 500, "y": 200}
        )
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            nodes=[start_node, end_node],
            edges=[],
            created_by=created_by
        )
        
        self._workflows[workflow_id] = workflow
        self._save_workflow(workflow)
        
        logger.info(f"📋 Created workflow: {name} ({workflow_id})")
        return workflow
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """獲取工作流"""
        return self._workflows.get(workflow_id)
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """列出所有工作流"""
        return [wf.to_dict() for wf in self._workflows.values()]
    
    def update_workflow(self, workflow_id: str, updates: Dict[str, Any]) -> Optional[Workflow]:
        """更新工作流"""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return None
        
        # 更新基本資訊
        if "name" in updates:
            workflow.name = updates["name"]
        if "description" in updates:
            workflow.description = updates["description"]
        if "variables" in updates:
            workflow.variables = updates["variables"]
        if "status" in updates:
            workflow.status = WorkflowStatus(updates["status"])
        
        # 更新節點
        if "nodes" in updates:
            workflow.nodes = [
                WorkflowNode(
                    id=n["id"],
                    type=NodeType(n["type"]),
                    name=n["name"],
                    config=n.get("config", {}),
                    position=n.get("position", {"x": 0, "y": 0})
                )
                for n in updates["nodes"]
            ]
        
        # 更新邊
        if "edges" in updates:
            workflow.edges = [
                WorkflowEdge(
                    id=e["id"],
                    source=e["source"],
                    target=e["target"],
                    condition=e.get("condition"),
                    label=e.get("label")
                )
                for e in updates["edges"]
            ]
        
        workflow.updated_at = datetime.now().isoformat()
        self._save_workflow(workflow)
        
        logger.info(f"📝 Updated workflow: {workflow.name}")
        return workflow
    
    def delete_workflow(self, workflow_id: str) -> bool:
        """刪除工作流"""
        if workflow_id not in self._workflows:
            return False
        
        # 刪除文件
        file_path = self.data_dir / f"{workflow_id}.json"
        if file_path.exists():
            file_path.unlink()
        
        del self._workflows[workflow_id]
        logger.info(f"🗑️ Deleted workflow: {workflow_id}")
        return True
    
    async def execute_workflow(
        self, 
        workflow_id: str, 
        input_data: Dict[str, Any] = None,
        callback = None
    ) -> ExecutionContext:
        """
        執行工作流
        
        Args:
            workflow_id: 工作流 ID
            input_data: 輸入數據
            callback: 執行回調（用於通知進度）
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        # 創建執行上下文
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        context = ExecutionContext(
            workflow_id=workflow_id,
            execution_id=execution_id,
            variables={**workflow.variables, **(input_data or {})}
        )
        self._executions[execution_id] = context
        
        try:
            # 找到開始節點
            start_node = next(
                (n for n in workflow.nodes if n.type == NodeType.START),
                None
            )
            if not start_node:
                raise ValueError("No START node found")
            
            # 執行工作流
            await self._execute_node(workflow, start_node.id, context, callback)
            
            context.status = "completed"
            context.finished_at = datetime.now().isoformat()
            
        except Exception as e:
            context.status = "failed"
            context.error = str(e)
            context.finished_at = datetime.now().isoformat()
            logger.error(f"Workflow execution failed: {e}")
        
        return context
    
    async def _execute_node(
        self, 
        workflow: Workflow, 
        node_id: str, 
        context: ExecutionContext,
        callback = None
    ) -> Any:
        """執行單個節點"""
        node = next((n for n in workflow.nodes if n.id == node_id), None)
        if not node:
            raise ValueError(f"Node {node_id} not found")
        
        context.current_node = node_id
        
        # 記錄歷史
        context.history.append({
            "node_id": node_id,
            "node_name": node.name,
            "type": node.type.value,
            "timestamp": datetime.now().isoformat(),
            "status": "started"
        })
        
        # 通知回調
        if callback:
            await callback({
                "event": "node_started",
                "node_id": node_id,
                "node_name": node.name
            })
        
        result = None
        
        # 根據節點類型執行
        if node.type == NodeType.START:
            result = context.variables
            
        elif node.type == NodeType.END:
            result = context.variables
            return result
            
        elif node.type == NodeType.AGENT:
            result = await self._execute_agent_node(node, context)
            
        elif node.type == NodeType.TOOL:
            result = await self._execute_tool_node(node, context)
            
        elif node.type == NodeType.CONDITION:
            result = await self._execute_condition_node(node, context, workflow, callback)
            return result  # 條件節點自己處理下一步
            
        elif node.type == NodeType.CODE:
            result = await self._execute_code_node(node, context)
            
        elif node.type == NodeType.DELAY:
            delay_seconds = node.config.get("seconds", 1)
            await asyncio.sleep(delay_seconds)
            result = {"delayed": delay_seconds}
            
        elif node.type == NodeType.PARALLEL:
            result = await self._execute_parallel_node(node, context, workflow, callback)
        
        # 更新變數
        if result and isinstance(result, dict):
            output_var = node.config.get("output_variable")
            if output_var:
                context.variables[output_var] = result
            else:
                context.variables.update(result)
        
        # 更新歷史
        context.history[-1]["status"] = "completed"
        context.history[-1]["result"] = result
        
        # 通知回調
        if callback:
            await callback({
                "event": "node_completed",
                "node_id": node_id,
                "result": result
            })
        
        # 找到下一個節點
        next_edges = [e for e in workflow.edges if e.source == node_id]
        
        for edge in next_edges:
            # 檢查條件
            if edge.condition:
                if not self._evaluate_condition(edge.condition, context.variables):
                    continue
            
            await self._execute_node(workflow, edge.target, context, callback)
            break  # 只執行第一個匹配的邊
        
        return result
    
    async def _execute_agent_node(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        """執行 Agent 節點"""
        agent_type = node.config.get("agent_type", "researcher")
        task = node.config.get("task", "")
        
        # 替換變數
        task = self._interpolate_variables(task, context.variables)
        
        try:
            from opencode.agents.coordinator import get_coordinator
            
            coordinator = await get_coordinator()
            
            # 這裡簡化處理，實際應該調用完整的 Agent 流程
            result = await coordinator.process_request(
                user_request=task,
                context=context.variables
            )
            
            return {"output": result.get("final_response", "")}
            
        except Exception as e:
            logger.error(f"Agent node error: {e}")
            return {"error": str(e)}
    
    async def _execute_tool_node(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        """執行工具節點"""
        tool_name = node.config.get("tool", "")
        parameters = node.config.get("parameters", {})
        
        # 替換變數
        for key, value in parameters.items():
            if isinstance(value, str):
                parameters[key] = self._interpolate_variables(value, context.variables)
        
        try:
            from opencode.tools import get_tool_registry
            
            registry = get_tool_registry()
            tool = registry.get_tool(tool_name)
            
            if not tool:
                return {"error": f"Tool {tool_name} not found"}
            
            result = await tool.execute(parameters)
            return result
            
        except Exception as e:
            logger.error(f"Tool node error: {e}")
            return {"error": str(e)}
    
    async def _execute_condition_node(
        self, 
        node: WorkflowNode, 
        context: ExecutionContext,
        workflow: Workflow,
        callback
    ) -> Any:
        """執行條件節點"""
        condition = node.config.get("condition", "true")
        result = self._evaluate_condition(condition, context.variables)
        
        # 找到對應的邊
        edges = [e for e in workflow.edges if e.source == node.id]
        
        for edge in edges:
            edge_condition = edge.condition or edge.label
            if edge_condition:
                if edge_condition.lower() == "true" and result:
                    await self._execute_node(workflow, edge.target, context, callback)
                    break
                elif edge_condition.lower() == "false" and not result:
                    await self._execute_node(workflow, edge.target, context, callback)
                    break
            else:
                # 無條件的邊，根據結果決定
                if result:
                    await self._execute_node(workflow, edge.target, context, callback)
                    break
        
        return {"condition_result": result}
    
    async def _execute_code_node(self, node: WorkflowNode, context: ExecutionContext) -> Dict[str, Any]:
        """執行代碼節點"""
        code = node.config.get("code", "")
        language = node.config.get("language", "python")
        
        try:
            from opencode.sandbox import get_sandbox
            
            sandbox = get_sandbox()
            result = await sandbox.execute(
                code=code,
                language=language,
                context=context.variables
            )
            
            return {
                "stdout": result.stdout,
                "return_value": result.return_value
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    async def _execute_parallel_node(
        self,
        node: WorkflowNode,
        context: ExecutionContext,
        workflow: Workflow,
        callback
    ) -> Dict[str, Any]:
        """執行並行節點"""
        edges = [e for e in workflow.edges if e.source == node.id]
        
        # 並行執行所有分支
        tasks = []
        for edge in edges:
            tasks.append(
                self._execute_node(workflow, edge.target, context, callback)
            )
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {"parallel_results": results}
    
    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """評估條件表達式"""
        try:
            # 安全的表達式評估
            # 支援: ==, !=, >, <, >=, <=, and, or, not, in
            safe_dict = {
                "true": True,
                "false": False,
                "True": True,
                "False": False,
                **variables
            }
            return bool(eval(condition, {"__builtins__": {}}, safe_dict))
        except Exception as e:
            logger.warning(f"Condition evaluation error: {e}")
            return False
    
    def _interpolate_variables(self, text: str, variables: Dict[str, Any]) -> str:
        """替換文字中的變數 {{var_name}}"""
        import re
        
        def replace(match):
            var_name = match.group(1).strip()
            return str(variables.get(var_name, match.group(0)))
        
        return re.sub(r'\{\{(\s*\w+\s*)\}\}', replace, text)
    
    def get_execution(self, execution_id: str) -> Optional[ExecutionContext]:
        """獲取執行上下文"""
        return self._executions.get(execution_id)
    
    def list_executions(self, workflow_id: str = None) -> List[Dict[str, Any]]:
        """列出執行記錄"""
        executions = self._executions.values()
        
        if workflow_id:
            executions = [e for e in executions if e.workflow_id == workflow_id]
        
        return [
            {
                "execution_id": e.execution_id,
                "workflow_id": e.workflow_id,
                "status": e.status,
                "started_at": e.started_at,
                "finished_at": e.finished_at,
                "error": e.error
            }
            for e in executions
        ]


# 全域實例
_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """獲取工作流引擎實例"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine
