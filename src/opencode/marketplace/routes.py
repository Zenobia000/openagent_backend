"""
技能市場 API 路由
"""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import Response
from pydantic import BaseModel

from opencode.auth import get_current_user, require_admin, TokenData
from .service import get_marketplace_service, MarketplaceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketplace", tags=["技能市場"])


class SkillCreate(BaseModel):
    """創建技能請求"""
    name: str
    description: str
    category: str = "general"
    tags: List[str] = []
    prompts: List[dict] = []
    tools: List[dict] = []
    examples: List[dict] = []


class SkillUpdate(BaseModel):
    """更新技能請求"""
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    prompts: Optional[List[dict]] = None
    tools: Optional[List[dict]] = None
    examples: Optional[List[dict]] = None


class RatingRequest(BaseModel):
    """評分請求"""
    rating: float  # 1-5


@router.get("/skills")
async def list_skills(
    category: Optional[str] = Query(None, description="分類"),
    search: Optional[str] = Query(None, description="搜尋關鍵字"),
    sort_by: str = Query("downloads", description="排序方式"),
    limit: int = Query(50, ge=1, le=100),
    marketplace: MarketplaceService = Depends(get_marketplace_service)
):
    """列出技能"""
    skills = marketplace.list_skills(
        category=category,
        search=search,
        sort_by=sort_by,
        limit=limit
    )
    return {
        "skills": skills,
        "count": len(skills)
    }


@router.get("/skills/{skill_id}")
async def get_skill(
    skill_id: str,
    marketplace: MarketplaceService = Depends(get_marketplace_service)
):
    """取得技能詳情"""
    skill = marketplace.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill.to_dict()


@router.post("/skills")
async def create_skill(
    skill: SkillCreate,
    current_user: TokenData = Depends(get_current_user),
    marketplace: MarketplaceService = Depends(get_marketplace_service)
):
    """創建技能"""
    new_skill = marketplace.create_skill(
        name=skill.name,
        description=skill.description,
        author=current_user.username,
        category=skill.category,
        tags=skill.tags,
        prompts=skill.prompts,
        tools=skill.tools,
        examples=skill.examples
    )
    return new_skill.to_dict()


@router.put("/skills/{skill_id}")
async def update_skill(
    skill_id: str,
    updates: SkillUpdate,
    current_user: TokenData = Depends(get_current_user),
    marketplace: MarketplaceService = Depends(get_marketplace_service)
):
    """更新技能"""
    skill = marketplace.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # 檢查權限（作者或管理員）
    if skill.author != current_user.username and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    updated = marketplace.update_skill(skill_id, updates.dict(exclude_unset=True))
    return updated.to_dict()


@router.delete("/skills/{skill_id}")
async def delete_skill(
    skill_id: str,
    current_user: TokenData = Depends(get_current_user),
    marketplace: MarketplaceService = Depends(get_marketplace_service)
):
    """刪除技能"""
    skill = marketplace.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # 檢查權限
    if skill.author != current_user.username and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    marketplace.delete_skill(skill_id)
    return {"message": "Skill deleted"}


@router.post("/skills/{skill_id}/rate")
async def rate_skill(
    skill_id: str,
    rating: RatingRequest,
    current_user: TokenData = Depends(get_current_user),
    marketplace: MarketplaceService = Depends(get_marketplace_service)
):
    """評分技能"""
    if not (1 <= rating.rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    skill = marketplace.rate_skill(skill_id, rating.rating, current_user.user_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    return {"message": "Rating submitted", "new_rating": skill.rating}


@router.get("/skills/{skill_id}/download")
async def download_skill(
    skill_id: str,
    marketplace: MarketplaceService = Depends(get_marketplace_service)
):
    """下載技能包"""
    data = marketplace.export_skill(skill_id)
    if not data:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    marketplace.increment_download(skill_id)
    
    skill = marketplace.get_skill(skill_id)
    filename = f"{skill.name.replace(' ', '_')}-{skill.version}.zip"
    
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/skills/import")
async def import_skill(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
    marketplace: MarketplaceService = Depends(get_marketplace_service)
):
    """導入技能包"""
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")
    
    data = await file.read()
    skill = marketplace.import_skill(data, current_user.username)
    
    if not skill:
        raise HTTPException(status_code=400, detail="Failed to import skill")
    
    return skill.to_dict()


@router.get("/categories")
async def get_categories(
    marketplace: MarketplaceService = Depends(get_marketplace_service)
):
    """取得所有分類"""
    return {"categories": marketplace.get_categories()}


@router.get("/stats")
async def get_stats(
    marketplace: MarketplaceService = Depends(get_marketplace_service)
):
    """取得市場統計"""
    return marketplace.get_stats()
