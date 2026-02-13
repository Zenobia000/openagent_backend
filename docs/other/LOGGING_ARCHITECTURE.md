# OpenCode Platform - 統一日誌架構設計

## 1. 日誌層次設計

### 1.1 核心原則
- **結構化日誌**：所有日誌必須為結構化 JSON 格式
- **可追蹤性**：每個請求有唯一 trace_id，跨服務追蹤
- **層級分離**：不同層級記錄不同詳細程度
- **性能優先**：非同步寫入，批量處理

### 1.2 日誌等級定義
```python
class LogLevel(Enum):
    TRACE = 5     # 極細粒度調試信息
    DEBUG = 10    # 調試信息
    INFO = 20     # 一般信息
    WARN = 30     # 警告
    ERROR = 40    # 錯誤
    CRITICAL = 50 # 嚴重錯誤
```

## 2. 統一日誌結構

### 2.1 基礎結構
```json
{
  "timestamp": "2024-02-10T10:30:00.123Z",
  "level": "INFO",
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "span_id": "7a2a3b4c5d6e7f8g",
  "service": "opencode.core",
  "module": "FinalUnifiedEngine",
  "function": "process",
  "message": "Processing request",
  "context": {
    "user_id": "user123",
    "session_id": "session456",
    "request_id": "req789"
  },
  "metadata": {},
  "performance": {
    "duration_ms": 123,
    "memory_mb": 45.2
  }
}
```

### 2.2 事件特定結構

#### SSE 事件日誌
```json
{
  "event_type": "sse",
  "sse": {
    "signal": "progress",
    "step": "report-plan",
    "status": "start",
    "data": {}
  }
}
```

#### AI/LLM 調用日誌
```json
{
  "event_type": "llm_call",
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "tokens_in": 1500,
    "tokens_out": 500,
    "cost_usd": 0.045,
    "latency_ms": 2300,
    "temperature": 0.7
  }
}
```

#### 工具決策日誌
```json
{
  "event_type": "tool_decision",
  "tool": {
    "selected": "web_search",
    "alternatives": ["rag_search", "memory_lookup"],
    "confidence": 0.85,
    "reason": "User query requires real-time information"
  }
}
```

#### RAG 操作日誌
```json
{
  "event_type": "rag_operation",
  "rag": {
    "operation": "retrieval",
    "collection": "knowledge_base",
    "query_embedding_time_ms": 45,
    "search_time_ms": 120,
    "results_count": 5,
    "top_score": 0.92
  }
}
```

#### Memory 操作日誌
```json
{
  "event_type": "memory_operation",
  "memory": {
    "operation": "store",
    "memory_type": "long_term",
    "key": "user_preferences",
    "size_bytes": 2048,
    "ttl_seconds": 86400
  }
}
```

## 3. 分層日誌策略

### Layer 1: Transport Layer (傳輸層)
```python
# 記錄所有 HTTP 請求/響應
logger.info("http_request", {
    "method": "POST",
    "path": "/api/sse",
    "headers": sanitized_headers,
    "body_size": len(body)
})
```

### Layer 2: Signal Dispatch Layer (訊號層)
```python
# 記錄 SSE 事件分發
logger.debug("sse_dispatch", {
    "event": event_type,
    "data_size": len(data),
    "client_id": client_id
})
```

### Layer 3: Pipeline Orchestration Layer (流程控制層)
```python
# 記錄 Pipeline 狀態轉換
logger.info("pipeline_transition", {
    "from_step": current_step,
    "to_step": next_step,
    "duration_ms": elapsed_time
})
```

### Layer 4: Content Generation Layer (內容生產層)
```python
# 記錄 AI 生成內容
logger.debug("content_generation", {
    "generator": "thinking_model",
    "prompt_tokens": token_count,
    "streaming": is_streaming
})
```

## 4. 實現方案

### 4.1 統一日誌管理器
```python
class UnifiedLogger:
    def __init__(self):
        self.trace_id = None
        self.span_stack = []
        self.context = {}

    def with_trace(self, trace_id: str):
        """設置追蹤 ID"""
        self.trace_id = trace_id
        return self

    def with_context(self, **kwargs):
        """添加上下文"""
        self.context.update(kwargs)
        return self

    def log_event(self, level: LogLevel, event_type: str, **kwargs):
        """記錄結構化事件"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.name,
            "trace_id": self.trace_id,
            "event_type": event_type,
            **kwargs
        }
        self._write(entry)
```

### 4.2 性能監控集成
```python
class PerformanceMonitor:
    @contextmanager
    def measure(self, operation: str):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss

        try:
            yield
        finally:
            duration = (time.time() - start_time) * 1000
            memory_delta = psutil.Process().memory_info().rss - start_memory

            logger.log_event(
                LogLevel.DEBUG,
                "performance",
                operation=operation,
                duration_ms=duration,
                memory_delta_bytes=memory_delta
            )
```

### 4.3 錯誤追蹤增強
```python
class ErrorTracker:
    def capture_exception(self, exc: Exception, context: dict = None):
        """捕獲並記錄異常"""
        logger.log_event(
            LogLevel.ERROR,
            "exception",
            exception_type=type(exc).__name__,
            message=str(exc),
            stack_trace=traceback.format_exc(),
            context=context or {}
        )
```

## 5. 日誌聚合與分析

### 5.1 關鍵指標
- **請求成功率**: success_count / total_count
- **平均響應時間**: avg(duration_ms)
- **LLM 成本追蹤**: sum(llm.cost_usd)
- **錯誤率**: error_count / total_count
- **工具使用分佈**: group_by(tool.selected)

### 5.2 告警規則
```yaml
alerts:
  - name: high_error_rate
    condition: error_rate > 0.05
    window: 5m

  - name: slow_response
    condition: p95_latency > 5000
    window: 10m

  - name: high_llm_cost
    condition: hourly_cost > 10
    window: 1h
```

## 6. 日誌輸出配置

### 6.1 開發環境
```python
# 彩色終端輸出，人類可讀格式
handlers:
  console:
    level: DEBUG
    formatter: colored
    filter: exclude_health_checks
```

### 6.2 生產環境
```python
# JSON 格式，輸出到檔案和監控系統
handlers:
  file:
    level: INFO
    path: /var/log/opencode/app.log
    rotation: daily
    retention: 30d

  monitoring:
    level: WARN
    endpoint: monitoring.internal
    batch_size: 100
    flush_interval: 5s
```

## 7. 最佳實踐

### DO ✅
- 使用結構化日誌
- 保持 trace_id 一致性
- 記錄業務關鍵指標
- 定期清理舊日誌
- 對敏感資料脫敏

### DON'T ❌
- 記錄密碼或 API keys
- 在生產環境使用 DEBUG level
- 同步寫入大量日誌
- 忽略日誌輪轉
- 記錄過多細節影響性能

## 8. 實施路線圖

### Phase 1: 基礎架構 (Week 1)
- [ ] 實現 UnifiedLogger
- [ ] 整合現有日誌系統
- [ ] 添加 trace_id 支援

### Phase 2: 功能整合 (Week 2)
- [ ] SSE 事件日誌
- [ ] LLM 調用追蹤
- [ ] 工具決策記錄

### Phase 3: 監控告警 (Week 3)
- [ ] 性能指標收集
- [ ] 告警規則設置
- [ ] Dashboard 建立

### Phase 4: 優化調整 (Week 4)
- [ ] 日誌聚合優化
- [ ] 成本分析報告
- [ ] 性能調優