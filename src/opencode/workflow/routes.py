"""
工作流 API 路由
"""

import logging
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from opencode.auth import get_current_user, require_admin, TokenData
from . import get_workflow_engine, WorkflowEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflows", tags=["工作流"])


# ============== 請求模型 ==============

class CreateWorkflowRequest(BaseModel):
    """創建工作流請求"""
    name: str = Field(..., min_length=1)
    description: str = ""


class UpdateWorkflowRequest(BaseModel):
    """更新工作流請求"""
    name: Optional[str] = None
    description: Optional[str] = None
    nodes: Optional[List[Dict[str, Any]]] = None
    edges: Optional[List[Dict[str, Any]]] = None
    variables: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class ExecuteWorkflowRequest(BaseModel):
    """執行工作流請求"""
    input_data: Dict[str, Any] = Field(default_factory=dict)


# ============== API 端點 ==============

@router.get("")
async def list_workflows(
    current_user: TokenData = Depends(get_current_user),
    engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """列出所有工作流"""
    workflows = engine.list_workflows()
    return {
        "workflows": workflows,
        "count": len(workflows)
    }


@router.post("")
async def create_workflow(
    request: CreateWorkflowRequest,
    current_user: TokenData = Depends(get_current_user),
    engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """創建新工作流"""
    workflow = engine.create_workflow(
        name=request.name,
        description=request.description,
        created_by=current_user.username
    )
    return workflow.to_dict()


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_user: TokenData = Depends(get_current_user),
    engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """獲取工作流詳情"""
    workflow = engine.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    return workflow.to_dict()


@router.put("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    request: UpdateWorkflowRequest,
    current_user: TokenData = Depends(get_current_user),
    engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """更新工作流"""
    updates = request.dict(exclude_none=True)
    workflow = engine.update_workflow(workflow_id, updates)
    
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    return workflow.to_dict()


@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: TokenData = Depends(require_admin),
    engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """刪除工作流（僅管理員）"""
    success = engine.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    return {"message": f"Workflow {workflow_id} deleted"}


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: str,
    request: ExecuteWorkflowRequest,
    background_tasks: BackgroundTasks,
    current_user: TokenData = Depends(get_current_user),
    engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """
    執行工作流
    
    返回執行 ID，可用於查詢執行狀態
    """
    workflow = engine.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")
    
    # 同步執行（如果工作流簡單）
    # 或者加入背景任務（如果工作流複雜）
    context = await engine.execute_workflow(
        workflow_id=workflow_id,
        input_data=request.input_data
    )
    
    return {
        "execution_id": context.execution_id,
        "status": context.status,
        "started_at": context.started_at,
        "finished_at": context.finished_at,
        "error": context.error
    }


@router.get("/{workflow_id}/executions")
async def list_workflow_executions(
    workflow_id: str,
    current_user: TokenData = Depends(get_current_user),
    engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """列出工作流的執行記錄"""
    executions = engine.list_executions(workflow_id)
    return {
        "executions": executions,
        "count": len(executions)
    }


@router.get("/executions/{execution_id}")
async def get_execution(
    execution_id: str,
    current_user: TokenData = Depends(get_current_user),
    engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """獲取執行詳情"""
    execution = engine.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution {execution_id} not found")
    
    return {
        "execution_id": execution.execution_id,
        "workflow_id": execution.workflow_id,
        "status": execution.status,
        "variables": execution.variables,
        "current_node": execution.current_node,
        "history": execution.history,
        "started_at": execution.started_at,
        "finished_at": execution.finished_at,
        "error": execution.error
    }


# ============== 模板 API ==============

@router.get("/templates/all")
async def get_workflow_templates(
    current_user: TokenData = Depends(get_current_user)
):
    """獲取工作流模板"""
    templates = [
        {
            "id": "template_simple_qa",
            "name": "簡單問答",
            "description": "基本的 RAG 問答流程",
            "nodes": [
                {"id": "start", "type": "start", "name": "開始", "position": {"x": 100, "y": 200}},
                {"id": "search", "type": "tool", "name": "知識庫搜尋", "config": {"tool": "rag_search"}, "position": {"x": 300, "y": 200}},
                {"id": "answer", "type": "agent", "name": "生成回答", "config": {"agent_type": "writer"}, "position": {"x": 500, "y": 200}},
                {"id": "end", "type": "end", "name": "結束", "position": {"x": 700, "y": 200}}
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "search"},
                {"id": "e2", "source": "search", "target": "answer"},
                {"id": "e3", "source": "answer", "target": "end"}
            ]
        },
        {
            "id": "template_research",
            "name": "深度研究",
            "description": "多步驟研究流程：搜尋 → 分析 → 撰寫報告",
            "nodes": [
                {"id": "start", "type": "start", "name": "開始", "position": {"x": 100, "y": 200}},
                {"id": "web_search", "type": "tool", "name": "網路搜尋", "config": {"tool": "web_search"}, "position": {"x": 250, "y": 100}},
                {"id": "rag_search", "type": "tool", "name": "知識庫搜尋", "config": {"tool": "rag_search"}, "position": {"x": 250, "y": 300}},
                {"id": "analyze", "type": "agent", "name": "分析", "config": {"agent_type": "analyst"}, "position": {"x": 450, "y": 200}},
                {"id": "write", "type": "agent", "name": "撰寫報告", "config": {"agent_type": "writer"}, "position": {"x": 650, "y": 200}},
                {"id": "end", "type": "end", "name": "結束", "position": {"x": 850, "y": 200}}
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "web_search"},
                {"id": "e2", "source": "start", "target": "rag_search"},
                {"id": "e3", "source": "web_search", "target": "analyze"},
                {"id": "e4", "source": "rag_search", "target": "analyze"},
                {"id": "e5", "source": "analyze", "target": "write"},
                {"id": "e6", "source": "write", "target": "end"}
            ]
        },
        {
            "id": "template_code_review",
            "name": "代碼審查",
            "description": "自動化代碼審查流程",
            "nodes": [
                {"id": "start", "type": "start", "name": "開始", "position": {"x": 100, "y": 200}},
                {"id": "analyze", "type": "agent", "name": "代碼分析", "config": {"agent_type": "coder"}, "position": {"x": 300, "y": 200}},
                {"id": "condition", "type": "condition", "name": "有問題?", "config": {"condition": "issues_count > 0"}, "position": {"x": 500, "y": 200}},
                {"id": "fix", "type": "agent", "name": "修復建議", "config": {"agent_type": "coder"}, "position": {"x": 700, "y": 100}},
                {"id": "approve", "type": "output", "name": "審核通過", "position": {"x": 700, "y": 300}},
                {"id": "end", "type": "end", "name": "結束", "position": {"x": 900, "y": 200}}
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "analyze"},
                {"id": "e2", "source": "analyze", "target": "condition"},
                {"id": "e3", "source": "condition", "target": "fix", "label": "true"},
                {"id": "e4", "source": "condition", "target": "approve", "label": "false"},
                {"id": "e5", "source": "fix", "target": "end"},
                {"id": "e6", "source": "approve", "target": "end"}
            ]
        }
    ]
    
    return {"templates": templates}


@router.post("/from-template/{template_id}")
async def create_from_template(
    template_id: str,
    name: str,
    current_user: TokenData = Depends(get_current_user),
    engine: WorkflowEngine = Depends(get_workflow_engine)
):
    """從模板創建工作流"""
    # 獲取模板
    templates_response = await get_workflow_templates(current_user)
    templates = templates_response["templates"]
    
    template = next((t for t in templates if t["id"] == template_id), None)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
    
    # 創建工作流
    workflow = engine.create_workflow(
        name=name,
        description=template["description"],
        created_by=current_user.username
    )
    
    # 更新節點和邊
    engine.update_workflow(workflow.id, {
        "nodes": template["nodes"],
        "edges": template["edges"]
    })
    
    return engine.get_workflow(workflow.id).to_dict()
