"""
成本追蹤服務 - 追蹤 API 使用量和成本
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from pathlib import Path
from dataclasses import dataclass, asdict, field
from enum import Enum

from core.utils import get_project_root

logger = logging.getLogger(__name__)


class CostType(str, Enum):
    """成本類型"""
    LLM_INPUT = "llm_input"      # LLM 輸入 token
    LLM_OUTPUT = "llm_output"    # LLM 輸出 token
    EMBEDDING = "embedding"      # Embedding
    WEB_SEARCH = "web_search"    # 網路搜尋
    CODE_EXEC = "code_exec"      # 程式碼執行


# API 定價（每 1000 tokens / 每次）
PRICING = {
    # OpenAI GPT-4o
    "gpt-4o": {"input": 0.005, "output": 0.015},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    # OpenAI Embeddings
    "text-embedding-3-small": {"input": 0.00002},
    "text-embedding-3-large": {"input": 0.00013},
    # Cohere
    "embed-multilingual-v3.0": {"input": 0.0001},
    # 其他服務
    "web_search": {"per_call": 0.001},  # 假設值
    "code_exec": {"per_call": 0.0005},  # 假設值
}


@dataclass
class UsageRecord:
    """使用記錄"""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    user_id: Optional[str] = None
    username: Optional[str] = None
    
    # 模型/服務
    model: str = ""
    cost_type: str = ""
    
    # 用量
    input_tokens: int = 0
    output_tokens: int = 0
    call_count: int = 1
    
    # 成本
    cost: float = 0.0
    
    # 上下文
    action: str = ""  # 對應的操作（chat, search, etc）
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CostTrackingService:
    """
    成本追蹤服務
    
    功能:
    - 追蹤 API 使用量
    - 計算成本
    - 生成報告
    - 設定預算警告
    """
    
    def __init__(self):
        self.data_dir = get_project_root() / "data" / "cost"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 預算設定
        self.daily_budget = float(os.getenv("DAILY_BUDGET", "10.0"))
        self.monthly_budget = float(os.getenv("MONTHLY_BUDGET", "100.0"))
        
        # 快取今日使用量
        self._today_usage: Dict[str, float] = {}
        self._last_cache_date: Optional[str] = None
        
        logger.info(f"✅ CostTrackingService initialized (daily budget: ${self.daily_budget})")
    
    def _get_usage_file(self, date_obj: date = None) -> Path:
        """獲取指定日期的使用量文件"""
        if date_obj is None:
            date_obj = date.today()
        filename = f"usage_{date_obj.strftime('%Y-%m-%d')}.jsonl"
        return self.data_dir / filename
    
    def _calculate_cost(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        call_count: int = 1
    ) -> float:
        """計算成本"""
        pricing = PRICING.get(model, {})
        
        cost = 0.0
        
        # Token 計費
        if "input" in pricing and input_tokens > 0:
            cost += (input_tokens / 1000) * pricing["input"]
        if "output" in pricing and output_tokens > 0:
            cost += (output_tokens / 1000) * pricing["output"]
        
        # 按次計費
        if "per_call" in pricing:
            cost += call_count * pricing["per_call"]
        
        return round(cost, 6)
    
    def record_usage(
        self,
        model: str,
        cost_type: CostType,
        input_tokens: int = 0,
        output_tokens: int = 0,
        call_count: int = 1,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        action: str = ""
    ) -> UsageRecord:
        """
        記錄使用量
        """
        cost = self._calculate_cost(model, input_tokens, output_tokens, call_count)
        
        record = UsageRecord(
            user_id=user_id,
            username=username,
            model=model,
            cost_type=cost_type.value if isinstance(cost_type, CostType) else cost_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            call_count=call_count,
            cost=cost,
            action=action
        )
        
        # 寫入文件
        try:
            usage_file = self._get_usage_file()
            with open(usage_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"❌ 記錄使用量失敗: {e}")
        
        # 更新快取
        today = date.today().isoformat()
        if self._last_cache_date != today:
            self._today_usage = {}
            self._last_cache_date = today
        
        self._today_usage[user_id or "anonymous"] = \
            self._today_usage.get(user_id or "anonymous", 0) + cost
        
        # 檢查預算
        self._check_budget_warning(user_id, cost)
        
        return record
    
    def _check_budget_warning(self, user_id: Optional[str], cost: float) -> None:
        """檢查預算警告"""
        today_total = sum(self._today_usage.values())
        
        if today_total >= self.daily_budget * 0.8:
            logger.warning(f"⚠️ 今日成本已達 ${today_total:.4f}，接近每日預算 ${self.daily_budget}")
        
        if today_total >= self.daily_budget:
            logger.error(f"🚨 今日成本已超出每日預算！${today_total:.4f} > ${self.daily_budget}")
    
    def get_daily_usage(self, date_obj: date = None) -> Dict[str, Any]:
        """獲取每日使用量"""
        if date_obj is None:
            date_obj = date.today()
        
        usage_file = self._get_usage_file(date_obj)
        
        result = {
            "date": date_obj.isoformat(),
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_calls": 0,
            "by_model": {},
            "by_user": {},
            "by_action": {},
            "records": []
        }
        
        if not usage_file.exists():
            return result
        
        try:
            with open(usage_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        result["records"].append(record)
                        result["total_cost"] += record.get("cost", 0)
                        result["total_input_tokens"] += record.get("input_tokens", 0)
                        result["total_output_tokens"] += record.get("output_tokens", 0)
                        result["total_calls"] += record.get("call_count", 1)
                        
                        # 按模型統計
                        model = record.get("model", "unknown")
                        if model not in result["by_model"]:
                            result["by_model"][model] = {"cost": 0, "calls": 0}
                        result["by_model"][model]["cost"] += record.get("cost", 0)
                        result["by_model"][model]["calls"] += record.get("call_count", 1)
                        
                        # 按用戶統計
                        username = record.get("username", "anonymous")
                        if username not in result["by_user"]:
                            result["by_user"][username] = {"cost": 0, "calls": 0}
                        result["by_user"][username]["cost"] += record.get("cost", 0)
                        result["by_user"][username]["calls"] += record.get("call_count", 1)
                        
                        # 按操作統計
                        action = record.get("action", "unknown")
                        if action not in result["by_action"]:
                            result["by_action"][action] = {"cost": 0, "calls": 0}
                        result["by_action"][action]["cost"] += record.get("cost", 0)
                        result["by_action"][action]["calls"] += record.get("call_count", 1)
        except Exception as e:
            logger.error(f"❌ 讀取使用量失敗: {e}")
        
        # 四捨五入
        result["total_cost"] = round(result["total_cost"], 4)
        
        return result
    
    def get_monthly_usage(self, year: int = None, month: int = None) -> Dict[str, Any]:
        """獲取每月使用量"""
        if year is None or month is None:
            today = date.today()
            year = today.year
            month = today.month
        
        result = {
            "year": year,
            "month": month,
            "total_cost": 0.0,
            "total_calls": 0,
            "daily_breakdown": [],
            "budget": self.monthly_budget,
            "budget_remaining": self.monthly_budget
        }
        
        # 遍歷該月每一天
        current = date(year, month, 1)
        while current.month == month:
            daily = self.get_daily_usage(current)
            if daily["total_cost"] > 0:
                result["daily_breakdown"].append({
                    "date": current.isoformat(),
                    "cost": daily["total_cost"],
                    "calls": daily["total_calls"]
                })
                result["total_cost"] += daily["total_cost"]
                result["total_calls"] += daily["total_calls"]
            
            current += timedelta(days=1)
            if current.month != month:
                break
        
        result["total_cost"] = round(result["total_cost"], 4)
        result["budget_remaining"] = round(self.monthly_budget - result["total_cost"], 4)
        
        return result
    
    def get_user_usage(
        self,
        user_id: str,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """獲取用戶使用量"""
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=30)
        
        result = {
            "user_id": user_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_cost": 0.0,
            "total_calls": 0,
            "daily_breakdown": []
        }
        
        current = start_date
        while current <= end_date:
            daily = self.get_daily_usage(current)
            user_cost = daily["by_user"].get(user_id, {}).get("cost", 0)
            user_calls = daily["by_user"].get(user_id, {}).get("calls", 0)
            
            if user_cost > 0:
                result["daily_breakdown"].append({
                    "date": current.isoformat(),
                    "cost": user_cost,
                    "calls": user_calls
                })
                result["total_cost"] += user_cost
                result["total_calls"] += user_calls
            
            current += timedelta(days=1)
        
        result["total_cost"] = round(result["total_cost"], 4)
        
        return result
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """獲取儀表板數據"""
        today = date.today()
        
        # 今日數據
        today_usage = self.get_daily_usage(today)
        
        # 本月數據
        monthly_usage = self.get_monthly_usage(today.year, today.month)
        
        # 最近 7 天趨勢
        trend = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            daily = self.get_daily_usage(d)
            trend.append({
                "date": d.isoformat(),
                "cost": daily["total_cost"],
                "calls": daily["total_calls"]
            })
        
        return {
            "today": {
                "cost": today_usage["total_cost"],
                "calls": today_usage["total_calls"],
                "budget": self.daily_budget,
                "budget_used_percent": round(today_usage["total_cost"] / self.daily_budget * 100, 1)
            },
            "month": {
                "cost": monthly_usage["total_cost"],
                "calls": monthly_usage["total_calls"],
                "budget": self.monthly_budget,
                "budget_used_percent": round(monthly_usage["total_cost"] / self.monthly_budget * 100, 1)
            },
            "trend": trend,
            "by_model": today_usage["by_model"],
            "by_action": today_usage["by_action"]
        }


# 全域實例
_cost_service: Optional[CostTrackingService] = None


def get_cost_service() -> CostTrackingService:
    """獲取成本追蹤服務實例"""
    global _cost_service
    if _cost_service is None:
        _cost_service = CostTrackingService()
    return _cost_service
