"""
Multi-Agent API 路由
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from opencode.auth import get_current_user, require_admin, TokenData
from .base import AgentType
from .coordinator import get_coordinator, AgentCoordinator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["Multi-Agent"])


# ============================================================
# Request/Response Models
# ============================================================

class Attachment(BaseModel):
    """多模態附件"""
    type: str  # 'image' | 'file'
    name: str
    mime_type: str
    data: str  # base64 encoded


class AgentRequest(BaseModel):
    """Agent 請求"""
    request: str
    context: Optional[Dict[str, Any]] = None
    stream: bool = False
    attachments: Optional[List[Attachment]] = None  # 多模態附件


class SingleAgentRequest(BaseModel):
    """單 Agent 請求"""
    agent_type: str
    task: str
    parameters: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None


# ============================================================
# API Endpoints
# ============================================================

@router.get("")
async def list_agents(
    current_user: TokenData = Depends(get_current_user)
):
    """列出所有 Agent"""
    try:
        coordinator = await get_coordinator()
        agents = coordinator.list_agents()
        return {
            "agents": agents,
            "count": len(agents)
        }
    except Exception as e:
        logger.error(f"List agents error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/types")
async def get_agent_types():
    """獲取可用的 Agent 類型"""
    return {
        "types": [
            {
                "id": t.value,
                "name": t.name,
                "description": _get_agent_description(t.value)
            }
            for t in AgentType
        ]
    }


@router.get("/tools")
async def list_tools(
    current_user: TokenData = Depends(get_current_user)
):
    """列出所有可用工具"""
    try:
        from opencode.tools import get_tool_registry
        registry = get_tool_registry()
        return {
            "tools": registry.get_all_definitions(),
            "count": len(registry.list_all())
        }
    except Exception as e:
        logger.error(f"List tools error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process")
async def process_request(
    request: AgentRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    處理用戶請求（Multi-Agent 協作）
    
    流程：
    1. Dispatcher 分析請求
    2. 拆解為子任務
    3. 分配給專業 Agent
    4. Agent 調用 Tools
    5. 聚合結果
    """
    try:
        coordinator = await get_coordinator()
        
        # 準備 context，包含附件
        context = request.context or {}
        if request.attachments:
            context["attachments"] = [
                {
                    "type": att.type,
                    "name": att.name,
                    "mime_type": att.mime_type,
                    "data": att.data
                }
                for att in request.attachments
            ]
        
        if request.stream:
            # 串流模式
            async def generate():
                async for event in coordinator.process_request(
                    request.request,
                    context if context else None,
                    stream=True
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                generate(),
                media_type="text/event-stream"
            )
        else:
            # 同步模式 - 收集所有結果
            results = []
            async for event in coordinator.process_request(
                request.request,
                context if context else None,
                stream=False
            ):
                results.append(event)
            
            # 找到最終結果
            final = next((r for r in results if r.get("type") == "final"), None)
            
            return {
                "success": True,
                "result": final.get("content") if final else "",
                "events": results
            }
            
    except Exception as e:
        logger.error(f"Process request error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/execute")
async def execute_single_agent(
    request: SingleAgentRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    執行單個 Agent（跳過 Dispatcher）
    
    用於簡單任務或測試
    """
    try:
        coordinator = await get_coordinator()
        
        result = await coordinator.execute_single_agent(
            agent_type=request.agent_type,
            task_description=request.task,
            parameters=request.parameters,
            context=request.context
        )
        
        return {
            "success": result.success,
            "agent": result.agent_type,
            "output": result.output,
            "tool_calls": result.tool_calls,
            "execution_time": result.execution_time,
            "error": result.error
        }
        
    except Exception as e:
        logger.error(f"Execute agent error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# Helper Functions
# ============================================================

def _get_agent_description(agent_type: str) -> str:
    """獲取 Agent 描述"""
    descriptions = {
        "dispatcher": "總機 Agent - 分析需求、拆解任務、分配給專業 Agent",
        "researcher": "研究者 Agent - 搜集資料、搜尋知識庫和網路",
        "writer": "寫作者 Agent - 撰寫文章、報告、文檔",
        "coder": "編碼者 Agent - 編寫程式碼、執行代碼、分析程式",
        "analyst": "分析師 Agent - 數據分析、統計計算",
        "reviewer": "審核者 Agent - 審核內容品質、提供改進建議"
    }
    return descriptions.get(agent_type, "")
