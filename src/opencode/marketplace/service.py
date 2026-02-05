"""
技能市場 - 分享和下載技能包

功能:
- 瀏覽技能市場
- 上傳技能包
- 下載和安裝技能
- 評分和評論
"""

import os
import json
import shutil
import hashlib
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import zipfile
import tempfile

from opencode.core.utils import get_project_root

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """技能定義"""
    id: str
    name: str
    version: str
    description: str
    author: str
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: Optional[str] = None
    
    # 技能內容
    prompts: List[Dict[str, Any]] = field(default_factory=list)  # 提示詞模板
    tools: List[Dict[str, Any]] = field(default_factory=list)    # 工具定義
    examples: List[Dict[str, Any]] = field(default_factory=list) # 示例
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MarketplaceService:
    """
    技能市場服務
    
    支援:
    - 本地技能庫
    - 技能打包和安裝
    - 基本的評分系統
    """
    
    # 技能分類
    CATEGORIES = [
        "general",      # 通用
        "writing",      # 寫作
        "coding",       # 編程
        "analysis",     # 分析
        "translation",  # 翻譯
        "research",     # 研究
        "creative",     # 創意
    ]
    
    def __init__(self):
        self.data_dir = get_project_root() / "data" / "marketplace"
        self.skills_dir = self.data_dir / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        
        self._skills: Dict[str, Skill] = {}
        self._load_skills()
        
        logger.info(f"✅ MarketplaceService initialized, {len(self._skills)} skills loaded")
    
    def _load_skills(self) -> None:
        """載入所有技能"""
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir():
                manifest_file = skill_dir / "skill.json"
                if manifest_file.exists():
                    try:
                        with open(manifest_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        skill = Skill(**data)
                        self._skills[skill.id] = skill
                    except Exception as e:
                        logger.error(f"Failed to load skill {skill_dir.name}: {e}")
    
    def _save_skill(self, skill: Skill) -> None:
        """保存技能到文件"""
        skill_dir = self.skills_dir / skill.id
        skill_dir.mkdir(exist_ok=True)
        
        manifest_file = skill_dir / "skill.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(skill.to_dict(), f, ensure_ascii=False, indent=2)
    
    def list_skills(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "downloads",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """列出技能"""
        skills = list(self._skills.values())
        
        # 過濾分類
        if category:
            skills = [s for s in skills if s.category == category]
        
        # 搜尋
        if search:
            search_lower = search.lower()
            skills = [
                s for s in skills
                if search_lower in s.name.lower()
                or search_lower in s.description.lower()
                or any(search_lower in tag.lower() for tag in s.tags)
            ]
        
        # 排序
        if sort_by == "downloads":
            skills.sort(key=lambda s: s.downloads, reverse=True)
        elif sort_by == "rating":
            skills.sort(key=lambda s: s.rating, reverse=True)
        elif sort_by == "newest":
            skills.sort(key=lambda s: s.created_at, reverse=True)
        
        return [s.to_dict() for s in skills[:limit]]
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """取得技能詳情"""
        return self._skills.get(skill_id)
    
    def create_skill(
        self,
        name: str,
        description: str,
        author: str,
        category: str = "general",
        tags: List[str] = None,
        prompts: List[Dict] = None,
        tools: List[Dict] = None,
        examples: List[Dict] = None
    ) -> Skill:
        """創建新技能"""
        # 生成 ID
        skill_id = hashlib.md5(f"{name}-{author}-{datetime.utcnow().timestamp()}".encode()).hexdigest()[:12]
        
        skill = Skill(
            id=skill_id,
            name=name,
            version="1.0.0",
            description=description,
            author=author,
            category=category,
            tags=tags or [],
            prompts=prompts or [],
            tools=tools or [],
            examples=examples or []
        )
        
        self._skills[skill_id] = skill
        self._save_skill(skill)
        
        logger.info(f"✅ Created skill: {name} ({skill_id})")
        return skill
    
    def update_skill(
        self,
        skill_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Skill]:
        """更新技能"""
        skill = self._skills.get(skill_id)
        if not skill:
            return None
        
        for key, value in updates.items():
            if hasattr(skill, key) and key not in ['id', 'created_at']:
                setattr(skill, key, value)
        
        skill.updated_at = datetime.utcnow().isoformat()
        self._save_skill(skill)
        
        return skill
    
    def delete_skill(self, skill_id: str) -> bool:
        """刪除技能"""
        if skill_id not in self._skills:
            return False
        
        skill_dir = self.skills_dir / skill_id
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
        
        del self._skills[skill_id]
        logger.info(f"🗑️ Deleted skill: {skill_id}")
        return True
    
    def rate_skill(
        self,
        skill_id: str,
        rating: float,
        user_id: str
    ) -> Optional[Skill]:
        """評分技能"""
        skill = self._skills.get(skill_id)
        if not skill or not (1 <= rating <= 5):
            return None
        
        # 簡單的平均計算（實際應該追蹤每個用戶的評分）
        total_rating = skill.rating * skill.rating_count + rating
        skill.rating_count += 1
        skill.rating = round(total_rating / skill.rating_count, 2)
        
        self._save_skill(skill)
        return skill
    
    def increment_download(self, skill_id: str) -> None:
        """增加下載計數"""
        skill = self._skills.get(skill_id)
        if skill:
            skill.downloads += 1
            self._save_skill(skill)
    
    def export_skill(self, skill_id: str) -> Optional[bytes]:
        """導出技能為 zip"""
        skill = self._skills.get(skill_id)
        if not skill:
            return None
        
        skill_dir = self.skills_dir / skill_id
        if not skill_dir.exists():
            return None
        
        # 創建臨時 zip
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            with zipfile.ZipFile(tmp.name, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in skill_dir.rglob('*'):
                    if file.is_file():
                        arcname = file.relative_to(skill_dir)
                        zf.write(file, arcname)
            
            with open(tmp.name, 'rb') as f:
                data = f.read()
            
            os.unlink(tmp.name)
            return data
    
    def import_skill(self, zip_data: bytes, author: str) -> Optional[Skill]:
        """從 zip 導入技能"""
        try:
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                tmp.write(zip_data)
                tmp_path = tmp.name
            
            with zipfile.ZipFile(tmp_path, 'r') as zf:
                # 讀取 manifest
                if 'skill.json' not in zf.namelist():
                    raise ValueError("Invalid skill package: skill.json not found")
                
                with zf.open('skill.json') as f:
                    data = json.load(f)
                
                # 創建新技能（使用新 ID）
                skill = self.create_skill(
                    name=data.get('name', 'Imported Skill'),
                    description=data.get('description', ''),
                    author=author,
                    category=data.get('category', 'general'),
                    tags=data.get('tags', []),
                    prompts=data.get('prompts', []),
                    tools=data.get('tools', []),
                    examples=data.get('examples', [])
                )
                
            os.unlink(tmp_path)
            return skill
            
        except Exception as e:
            logger.error(f"Failed to import skill: {e}")
            return None
    
    def get_categories(self) -> List[str]:
        """取得所有分類"""
        return self.CATEGORIES
    
    def get_stats(self) -> Dict[str, Any]:
        """取得市場統計"""
        skills = list(self._skills.values())
        return {
            "total_skills": len(skills),
            "total_downloads": sum(s.downloads for s in skills),
            "by_category": {
                cat: len([s for s in skills if s.category == cat])
                for cat in self.CATEGORIES
            },
            "top_rated": [
                {"id": s.id, "name": s.name, "rating": s.rating}
                for s in sorted(skills, key=lambda x: x.rating, reverse=True)[:5]
            ],
            "most_downloaded": [
                {"id": s.id, "name": s.name, "downloads": s.downloads}
                for s in sorted(skills, key=lambda x: x.downloads, reverse=True)[:5]
            ]
        }


# 全域實例
_marketplace_service: Optional[MarketplaceService] = None


def get_marketplace_service() -> MarketplaceService:
    """取得技能市場服務實例"""
    global _marketplace_service
    if _marketplace_service is None:
        _marketplace_service = MarketplaceService()
    return _marketplace_service
