"""
Policy Engine - 策略引擎
實作 RBAC 和工具權限控制
"""

from typing import Dict, Any, Optional, List, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import time

from opencode.core.protocols import PolicyEngineProtocol, Context

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """風險等級"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Permission(Enum):
    """權限類型"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"


@dataclass
class Role:
    """角色定義"""
    name: str
    permissions: Set[str] = field(default_factory=set)
    allowed_tools: Set[str] = field(default_factory=set)
    denied_tools: Set[str] = field(default_factory=set)
    max_risk_level: RiskLevel = RiskLevel.MEDIUM


@dataclass
class Policy:
    """策略定義"""
    name: str
    effect: str  # "allow" or "deny"
    actions: List[str]
    resources: List[str]
    conditions: Dict[str, Any] = field(default_factory=dict)


class PolicyEngine(PolicyEngineProtocol):
    """
    策略引擎實作
    
    功能:
    - RBAC (角色基礎存取控制)
    - 工具權限控制
    - 風險等級評估
    - 策略評估
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # 角色定義
        self.roles: Dict[str, Role] = {}
        
        # 策略列表
        self.policies: List[Policy] = []
        
        # 工具風險等級
        self.tool_risk_levels: Dict[str, RiskLevel] = {}
        
        # 用戶角色映射
        self.user_roles: Dict[str, List[str]] = {}
        
        # 工具黑名單/白名單
        self.tool_blacklist: Set[str] = set()
        self.tool_whitelist: Set[str] = set()
        
        # 初始化預設配置
        self._init_defaults()
    
    def _init_defaults(self) -> None:
        """初始化預設配置"""
        # 預設角色
        self.roles["user"] = Role(
            name="user",
            permissions={"read", "execute"},
            allowed_tools={"rag_search", "rag_ask", "rag_search_multiple"},
            max_risk_level=RiskLevel.MEDIUM
        )
        
        self.roles["developer"] = Role(
            name="developer",
            permissions={"read", "write", "execute"},
            allowed_tools={
                "rag_search", "rag_ask", "rag_search_multiple",
                "execute_bash", "execute_python",
                "git_clone", "git_status", "git_commit"
            },
            max_risk_level=RiskLevel.HIGH
        )
        
        self.roles["admin"] = Role(
            name="admin",
            permissions={"read", "write", "execute", "admin"},
            allowed_tools=set(),  # 空集合表示允許所有
            max_risk_level=RiskLevel.CRITICAL
        )
        
        # 預設工具風險等級
        self.tool_risk_levels = {
            # 低風險
            "rag_search": RiskLevel.LOW,
            "rag_search_multiple": RiskLevel.LOW,
            "rag_ask": RiskLevel.LOW,
            "document_list": RiskLevel.LOW,
            "get_stats": RiskLevel.LOW,
            
            # 中風險
            "document_upload": RiskLevel.MEDIUM,
            "document_delete": RiskLevel.MEDIUM,
            "file_read": RiskLevel.MEDIUM,
            "git_clone": RiskLevel.MEDIUM,
            "git_status": RiskLevel.MEDIUM,
            
            # 高風險
            "execute_bash": RiskLevel.HIGH,
            "execute_python": RiskLevel.HIGH,
            "file_write": RiskLevel.HIGH,
            "git_commit": RiskLevel.HIGH,
            "git_push": RiskLevel.HIGH,
            
            # 極高風險
            "api_call": RiskLevel.CRITICAL,
            "db_query": RiskLevel.CRITICAL
        }
        
        # 從配置載入黑名單
        blacklist = self.config.get("tool_blacklist", [])
        self.tool_blacklist = set(blacklist)
    
    async def initialize(self) -> None:
        """初始化策略引擎"""
        logger.info("✅ PolicyEngine initialized")
    
    async def check_permission(
        self, 
        actor: str, 
        resource: str, 
        action: str
    ) -> Tuple[bool, Optional[str]]:
        """
        檢查權限
        
        Args:
            actor: 執行者 (用戶 ID)
            resource: 資源
            action: 動作
            
        Returns:
            (允許, 原因)
        """
        # 取得用戶角色
        user_roles = self.user_roles.get(actor, ["user"])
        
        # 檢查每個角色的權限
        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role is None:
                continue
            
            # admin 角色有所有權限
            if "admin" in role.permissions:
                return True, None
            
            # 檢查動作權限
            if action in role.permissions:
                return True, None
        
        return False, f"Action '{action}' not allowed for actor '{actor}'"
    
    async def is_tool_allowed(
        self, 
        tool_name: str, 
        context: Optional[Context] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        檢查工具是否允許使用
        
        Args:
            tool_name: 工具名稱
            context: 執行上下文
            
        Returns:
            (允許, 原因)
        """
        # 檢查黑名單
        if tool_name in self.tool_blacklist:
            return False, f"Tool '{tool_name}' is blacklisted"
        
        # 如果有白名單，只允許白名單中的工具
        if self.tool_whitelist and tool_name not in self.tool_whitelist:
            return False, f"Tool '{tool_name}' not in whitelist"
        
        # 取得用戶角色
        user_id = context.user_id if context else "anonymous"
        user_roles = self.user_roles.get(user_id, ["user"])
        
        # 檢查工具風險等級
        tool_risk = self.tool_risk_levels.get(tool_name, RiskLevel.MEDIUM)
        
        for role_name in user_roles:
            role = self.roles.get(role_name)
            if role is None:
                continue
            
            # 檢查是否在拒絕列表
            if tool_name in role.denied_tools:
                continue
            
            # 檢查是否在允許列表 (空集合表示允許所有)
            if role.allowed_tools and tool_name not in role.allowed_tools:
                continue
            
            # 檢查風險等級
            if self._compare_risk(tool_risk, role.max_risk_level) <= 0:
                return True, None
        
        return False, f"Tool '{tool_name}' not allowed for user '{user_id}'"
    
    def get_risk_level(self, tool_name: str) -> str:
        """取得工具風險等級"""
        risk = self.tool_risk_levels.get(tool_name, RiskLevel.MEDIUM)
        return risk.value
    
    def assign_role(self, user_id: str, role_name: str) -> None:
        """指派角色給用戶"""
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []
        
        if role_name not in self.user_roles[user_id]:
            self.user_roles[user_id].append(role_name)
            logger.info(f"Assigned role '{role_name}' to user '{user_id}'")
    
    def revoke_role(self, user_id: str, role_name: str) -> None:
        """撤銷用戶角色"""
        if user_id in self.user_roles:
            if role_name in self.user_roles[user_id]:
                self.user_roles[user_id].remove(role_name)
                logger.info(f"Revoked role '{role_name}' from user '{user_id}'")
    
    def add_tool_to_blacklist(self, tool_name: str) -> None:
        """加入工具黑名單"""
        self.tool_blacklist.add(tool_name)
    
    def remove_tool_from_blacklist(self, tool_name: str) -> None:
        """從黑名單移除工具"""
        self.tool_blacklist.discard(tool_name)
    
    def _compare_risk(self, a: RiskLevel, b: RiskLevel) -> int:
        """比較風險等級，返回 -1, 0, 1"""
        order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        return order.index(a) - order.index(b)
