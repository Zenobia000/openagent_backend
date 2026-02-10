"""
用戶服務 - 用戶管理和存儲
"""

import os
import json
import logging
from typing import Optional, List
from datetime import datetime, date
from pathlib import Path

from core.utils import get_project_root
from .models import User, UserCreate, UserUpdate, UserRole, UserStatus, UserResponse
from .jwt import hash_password, verify_password

logger = logging.getLogger(__name__)


class UserService:
    """
    用戶服務
    
    使用 JSON 文件存儲（可擴展為資料庫）
    """
    
    def __init__(self):
        self.data_dir = get_project_root() / "data" / "users"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.users_file = self.data_dir / "users.json"
        self._users: dict[str, User] = {}
        self._username_index: dict[str, str] = {}  # username -> user_id
        self._load_users()
        self._ensure_admin()
    
    def _load_users(self) -> None:
        """從文件載入用戶"""
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for user_data in data:
                        user = User(**user_data)
                        self._users[user.id] = user
                        self._username_index[user.username.lower()] = user.id
                logger.info(f"✅ 載入 {len(self._users)} 個用戶")
            except Exception as e:
                logger.error(f"❌ 載入用戶失敗: {e}")
    
    def _save_users(self) -> None:
        """保存用戶到文件"""
        try:
            data = [user.model_dump() for user in self._users.values()]
            # 處理 datetime 序列化
            for user_data in data:
                for key, value in user_data.items():
                    if isinstance(value, datetime):
                        user_data[key] = value.isoformat()
            
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌ 保存用戶失敗: {e}")
    
    def _ensure_admin(self) -> None:
        """確保存在預設管理員"""
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
        
        if admin_username.lower() not in self._username_index:
            admin = User(
                username=admin_username,
                hashed_password=hash_password(admin_password),
                role=UserRole.ADMIN,
                daily_query_limit=9999,
                daily_upload_limit=9999
            )
            self._users[admin.id] = admin
            self._username_index[admin.username.lower()] = admin.id
            self._save_users()
            logger.info(f"✅ 創建預設管理員: {admin_username}")
    
    def create_user(self, user_create: UserCreate) -> User:
        """創建用戶"""
        # 檢查用戶名是否已存在
        if user_create.username.lower() in self._username_index:
            raise ValueError(f"用戶名 '{user_create.username}' 已存在")
        
        user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hash_password(user_create.password),
            role=user_create.role
        )
        
        self._users[user.id] = user
        self._username_index[user.username.lower()] = user.id
        self._save_users()
        
        logger.info(f"✅ 創建用戶: {user.username} (role: {user.role})")
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """根據 ID 獲取用戶"""
        return self._users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """根據用戶名獲取用戶"""
        user_id = self._username_index.get(username.lower())
        if user_id:
            return self._users.get(user_id)
        return None
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """驗證用戶"""
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        if user.status != UserStatus.ACTIVE:
            return None
        return user
    
    def update_user(self, user_id: str, update: UserUpdate) -> Optional[User]:
        """更新用戶"""
        user = self._users.get(user_id)
        if not user:
            return None
        
        update_data = update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        self._save_users()
        
        logger.info(f"✅ 更新用戶: {user.username}")
        return user
    
    def delete_user(self, user_id: str) -> bool:
        """刪除用戶"""
        user = self._users.get(user_id)
        if not user:
            return False
        
        # 不能刪除最後一個管理員
        if user.role == UserRole.ADMIN:
            admin_count = sum(1 for u in self._users.values() if u.role == UserRole.ADMIN)
            if admin_count <= 1:
                raise ValueError("無法刪除最後一個管理員")
        
        del self._users[user_id]
        del self._username_index[user.username.lower()]
        self._save_users()
        
        logger.info(f"✅ 刪除用戶: {user.username}")
        return True
    
    def list_users(self) -> List[User]:
        """列出所有用戶"""
        return list(self._users.values())
    
    def update_last_login(self, user_id: str) -> None:
        """更新最後登入時間"""
        user = self._users.get(user_id)
        if user:
            user.last_login = datetime.utcnow()
            self._save_users()
    
    def check_and_reset_daily_limits(self, user_id: str) -> None:
        """檢查並重置每日限制"""
        user = self._users.get(user_id)
        if not user:
            return
        
        today = date.today().isoformat()
        if user.last_reset_date != today:
            user.queries_today = 0
            user.uploads_today = 0
            user.last_reset_date = today
            self._save_users()
    
    def increment_query_count(self, user_id: str) -> bool:
        """
        增加查詢計數
        
        Returns:
            True 如果未超過限制，False 如果已達限制
        """
        user = self._users.get(user_id)
        if not user:
            return False
        
        self.check_and_reset_daily_limits(user_id)
        
        if user.queries_today >= user.daily_query_limit:
            return False
        
        user.queries_today += 1
        self._save_users()
        return True
    
    def increment_upload_count(self, user_id: str) -> bool:
        """
        增加上傳計數
        
        Returns:
            True 如果未超過限制，False 如果已達限制
        """
        user = self._users.get(user_id)
        if not user:
            return False
        
        self.check_and_reset_daily_limits(user_id)
        
        if user.uploads_today >= user.daily_upload_limit:
            return False
        
        user.uploads_today += 1
        self._save_users()
        return True
    
    def to_response(self, user: User) -> UserResponse:
        """轉換為回應格式（不含密碼）"""
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            status=user.status,
            daily_query_limit=user.daily_query_limit,
            daily_upload_limit=user.daily_upload_limit,
            queries_today=user.queries_today,
            uploads_today=user.uploads_today,
            created_at=user.created_at,
            last_login=user.last_login
        )


# 全域實例
_user_service: Optional[UserService] = None


def get_user_service() -> UserService:
    """獲取用戶服務實例"""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
