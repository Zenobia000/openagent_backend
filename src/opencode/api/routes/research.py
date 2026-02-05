"""
Deep Research API 路由 (Manus 風格)

支援：
1. SSE 即時進度回報
2. 多輪搜尋 + 瀏覽
3. 自主思考與策略調整
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Literal
import logging
import json
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["研究"])


# ============== Pydantic Models ==============

class ResearchRequest(BaseModel):
    """研究請求"""
    topic: str
    documents: Optional[List[str]] = None


class DeepResearchRequest(BaseModel):
    """深度研究請求（Manus 風格）"""
    query: str
    depth: Literal["quick", "standard", "deep"] = "standard"
    selected_docs: Optional[List[str]] = None  # 用戶選擇的文件


class ResearchStartResponse(BaseModel):
    """研究啟動回應"""
    task_id: str
    status: str = "started"


# ============== API Endpoints ==============

@router.post("/deep/stream")
async def deep_research_stream(request: DeepResearchRequest):
    """
    深度研究（SSE 串流）- Manus 風格
    
    - **query**: 研究主題
    - **depth**: 研究深度
        - quick: 快速（1 輪搜尋）
        - standard: 標準（2 輪搜尋）
        - deep: 深入（3 輪搜尋）
    - **selected_docs**: 用戶選擇的文件（可選）
    
    返回 SSE 事件流，包含：
    - thinking: 思考中
    - searching: 搜尋中
    - browsing: 瀏覽網頁中
    - rag_search: 搜尋文件
    - analyzing: 分析中
    - complete: 完成
    - error: 錯誤
    """
    from opencode.services.browser import get_research_agent, PLAYWRIGHT_AVAILABLE
    
    async def generate():
        agent = get_research_agent()
        
        try:
            # 發送初始狀態
            yield f"data: {json.dumps({'type': 'init', 'playwright_available': PLAYWRIGHT_AVAILABLE})}\n\n"
            
            async for step in agent.research(
                query=request.query, 
                depth=request.depth,
                selected_docs=request.selected_docs
            ):
                event_data = {
                    "type": step.step_type,
                    "status": step.status,
                    "message": step.message,
                    "data": step.data
                }
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                
                # 小延遲，讓前端有時間處理
                await asyncio.sleep(0.1)
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            logger.error(f"❌ Deep research error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            await agent.close()
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/deep")
async def deep_research_sync(request: DeepResearchRequest):
    """
    深度研究（同步版本）
    
    等待研究完成後返回完整結果
    """
    from opencode.services.browser import get_research_agent
    
    agent = get_research_agent()
    
    try:
        final_result = None
        all_steps = []
        
        async for step in agent.research(request.query, request.depth):
            all_steps.append(step.to_dict())
            if step.step_type == "complete":
                final_result = step.data
        
        return {
            "success": final_result is not None,
            "query": request.query,
            "depth": request.depth,
            "result": final_result,
            "steps": all_steps
        }
        
    except Exception as e:
        logger.error(f"❌ Deep research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await agent.close()


@router.post("/start", response_model=ResearchStartResponse)
async def start_research(request: ResearchRequest):
    """
    啟動深度研究任務（舊版 API，保持向後兼容）
    
    - **topic**: 研究主題
    - **documents**: 限定文件列表（可選）
    """
    try:
        from opencode.services.research.service import get_research_service
        
        service = await get_research_service()
        task_id = await service.start_research(
            topic=request.topic,
            documents=request.documents
        )
        
        return ResearchStartResponse(task_id=task_id)
    except ImportError:
        # 如果舊的 research service 不存在，使用新的
        import uuid
        return ResearchStartResponse(task_id=str(uuid.uuid4())[:8])


@router.get("/{task_id}")
async def get_research_status(task_id: str):
    """
    取得研究任務狀態
    
    - **task_id**: 研究任務 ID
    """
    try:
        from opencode.services.research.service import get_research_service
        
        service = await get_research_service()
        task = await service.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task.to_dict()
    except ImportError:
        raise HTTPException(status_code=404, detail="Task not found")


@router.get("")
async def list_research_tasks():
    """列出所有研究任務"""
    try:
        from opencode.services.research.service import get_research_service
        
        service = await get_research_service()
        tasks = await service.list_tasks()
        
        return {"tasks": tasks}
    except ImportError:
        return {"tasks": []}
