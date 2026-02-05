"""
Ops Plane - 運維監控
包含 Tracer (追蹤) 和 CostTracker (成本追蹤)
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import time
import uuid

from opencode.core.protocols import TracerProtocol, CostTrackerProtocol

logger = logging.getLogger(__name__)


class SpanType(Enum):
    """Span 類型"""
    INTENT = "intent"
    PLAN = "plan"
    TASK = "task"
    TOOL_CALL = "tool_call"
    LLM_CALL = "llm_call"
    DB_QUERY = "db_query"
    HTTP_REQUEST = "http_request"


@dataclass
class Span:
    """追蹤 Span"""
    id: str
    name: str
    trace_id: str
    parent_id: Optional[str] = None
    span_type: SpanType = SpanType.TASK
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "running"  # running, completed, error
    
    @property
    def duration(self) -> Optional[float]:
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    def add_event(self, name: str, attributes: Dict[str, Any] = None) -> None:
        """添加事件"""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        })
    
    def set_attribute(self, key: str, value: Any) -> None:
        """設置屬性"""
        self.attributes[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "name": self.name,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "span_type": self.span_type.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "attributes": self.attributes,
            "events": self.events,
            "status": self.status
        }


@dataclass
class Trace:
    """追蹤"""
    id: str
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    spans: Dict[str, Span] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "running"
    
    @property
    def duration(self) -> Optional[float]:
        if self.end_time:
            return self.end_time - self.start_time
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "spans": [s.to_dict() for s in self.spans.values()],
            "attributes": self.attributes,
            "status": self.status
        }


class Tracer(TracerProtocol):
    """
    追蹤器實作
    
    功能:
    - 追蹤請求生命週期
    - 記錄 Span 層級
    - 計算執行時間
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.traces: Dict[str, Trace] = {}
        self.spans: Dict[str, Span] = {}
        self.current_trace_id: Optional[str] = None
        self.max_traces = self.config.get("max_traces", 1000)
    
    def start_trace(self, name: str) -> str:
        """
        開始追蹤
        
        Args:
            name: 追蹤名稱
            
        Returns:
            trace_id
        """
        trace_id = str(uuid.uuid4())
        trace = Trace(id=trace_id, name=name)
        
        self.traces[trace_id] = trace
        self.current_trace_id = trace_id
        
        # 限制追蹤數量
        if len(self.traces) > self.max_traces:
            oldest = min(self.traces.values(), key=lambda t: t.start_time)
            del self.traces[oldest.id]
        
        logger.debug(f"Started trace: {name} ({trace_id})")
        return trace_id
    
    def start_span(
        self, 
        name: str, 
        trace_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        span_type: SpanType = SpanType.TASK
    ) -> str:
        """
        開始 Span
        
        Args:
            name: Span 名稱
            trace_id: 追蹤 ID (可選，使用當前追蹤)
            parent_id: 父 Span ID (可選)
            span_type: Span 類型
            
        Returns:
            span_id
        """
        trace_id = trace_id or self.current_trace_id
        if not trace_id:
            trace_id = self.start_trace("auto_trace")
        
        span_id = str(uuid.uuid4())
        span = Span(
            id=span_id,
            name=name,
            trace_id=trace_id,
            parent_id=parent_id,
            span_type=span_type
        )
        
        self.spans[span_id] = span
        
        # 加入到 trace
        if trace_id in self.traces:
            self.traces[trace_id].spans[span_id] = span
        
        logger.debug(f"Started span: {name} ({span_id})")
        return span_id
    
    def end_span(
        self, 
        span_id: str, 
        result: Optional[Any] = None,
        error: Optional[str] = None
    ) -> None:
        """
        結束 Span
        
        Args:
            span_id: Span ID
            result: 執行結果 (可選)
            error: 錯誤訊息 (可選)
        """
        span = self.spans.get(span_id)
        if span:
            span.end_time = time.time()
            span.status = "error" if error else "completed"
            
            if result is not None:
                span.set_attribute("result", str(result)[:500])
            if error:
                span.set_attribute("error", error)
            
            logger.debug(f"Ended span: {span.name} ({span_id}) - {span.duration:.3f}s")
    
    def end_trace(self, trace_id: str) -> None:
        """
        結束追蹤
        
        Args:
            trace_id: 追蹤 ID
        """
        trace = self.traces.get(trace_id)
        if trace:
            trace.end_time = time.time()
            
            # 根據 spans 狀態決定 trace 狀態
            has_error = any(s.status == "error" for s in trace.spans.values())
            trace.status = "error" if has_error else "completed"
            
            logger.debug(f"Ended trace: {trace.name} ({trace_id}) - {trace.duration:.3f}s")
            
            if self.current_trace_id == trace_id:
                self.current_trace_id = None
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """取得追蹤資訊"""
        trace = self.traces.get(trace_id)
        return trace.to_dict() if trace else None
    
    def get_span(self, span_id: str) -> Optional[Dict[str, Any]]:
        """取得 Span 資訊"""
        span = self.spans.get(span_id)
        return span.to_dict() if span else None
    
    def get_summary(self) -> Dict[str, Any]:
        """取得追蹤摘要"""
        completed = [t for t in self.traces.values() if t.status == "completed"]
        errors = [t for t in self.traces.values() if t.status == "error"]
        
        avg_duration = 0
        if completed:
            durations = [t.duration for t in completed if t.duration]
            avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            "total_traces": len(self.traces),
            "completed_traces": len(completed),
            "error_traces": len(errors),
            "total_spans": len(self.spans),
            "average_duration": avg_duration
        }


# ============== Cost Tracker ==============

@dataclass
class UsageRecord:
    """使用量記錄"""
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


class CostTracker(CostTrackerProtocol):
    """
    成本追蹤器
    
    功能:
    - 追蹤 LLM API 使用量
    - 計算成本
    - 預算管理
    """
    
    # Token 價格 (每 1K tokens，美元)
    MODEL_PRICING = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "text-embedding-3-small": {"input": 0.00002, "output": 0},
        "text-embedding-3-large": {"input": 0.00013, "output": 0}
    }
    
    def __init__(
        self, 
        budget: Optional[float] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.budget = budget
        self.config = config or {}
        self.records: List[UsageRecord] = []
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
    
    def record(
        self, 
        input_tokens: int, 
        output_tokens: int, 
        model: str
    ) -> None:
        """
        記錄使用量
        
        Args:
            input_tokens: 輸入 tokens
            output_tokens: 輸出 tokens
            model: 模型名稱
        """
        # 計算成本
        pricing = self.MODEL_PRICING.get(model, {"input": 0.01, "output": 0.03})
        cost = (input_tokens / 1000 * pricing["input"] + 
                output_tokens / 1000 * pricing["output"])
        
        # 記錄
        record = UsageRecord(
            timestamp=time.time(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
        self.records.append(record)
        
        # 更新總計
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += cost
        
        logger.debug(f"Recorded usage: {model} {input_tokens}/{output_tokens} tokens, ${cost:.6f}")
    
    def get_total_cost(self) -> float:
        """取得總成本"""
        return self.total_cost
    
    def is_over_budget(self, budget: Optional[float] = None) -> bool:
        """檢查是否超出預算"""
        budget = budget or self.budget
        if budget is None:
            return False
        return self.total_cost >= budget
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """取得使用量摘要"""
        # 按模型統計
        by_model: Dict[str, Dict] = {}
        for record in self.records:
            if record.model not in by_model:
                by_model[record.model] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0,
                    "count": 0
                }
            by_model[record.model]["input_tokens"] += record.input_tokens
            by_model[record.model]["output_tokens"] += record.output_tokens
            by_model[record.model]["cost"] += record.cost
            by_model[record.model]["count"] += 1
        
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
            "budget": self.budget,
            "over_budget": self.is_over_budget(),
            "by_model": by_model,
            "record_count": len(self.records)
        }
    
    def reset(self) -> None:
        """重置計數器"""
        self.records.clear()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0
