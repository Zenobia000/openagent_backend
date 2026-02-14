# API 規格與數據模型 (API Specifications)

## 文檔編號
`COGNITIVE-ARCH-11`

**版本**: 1.0.0
**最後更新**: 2026-02-12
**狀態**: 規格定義

---

## 概述

本文檔定義類人類認知架構的所有 API 契約與數據模型，確保組件之間的介面明確、穩定、可測試。

### 設計原則

1. **向後兼容**：外部 API 保持穩定，內部重構不影響使用者
2. **強類型**：使用 Pydantic 或 dataclass 進行類型驗證
3. **明確契約**：每個 API 都有清晰的輸入/輸出定義
4. **可擴展**：支持元數據擴展，不破壞現有契約
5. **可測試**：提供 JSON Schema，支持自動驗證

---

## 核心數據模型

### 1. Task - 任務

用戶提交的請求。

```python
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class Task(BaseModel):
    """
    任務：用戶提交的請求

    外部 API 契約，必須保持向後兼容
    """

    # 必需字段
    query: str = Field(
        ...,
        description="用戶的查詢或請求",
        min_length=1,
        max_length=10000,
        example="How to implement a binary search tree in Python?"
    )

    # 可選字段
    task_id: Optional[str] = Field(
        None,
        description="任務唯一標識符（自動生成）"
    )

    user_id: Optional[str] = Field(
        None,
        description="用戶ID"
    )

    session_id: Optional[str] = Field(
        None,
        description="會話ID"
    )

    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="任務創建時間"
    )

    # 配置與元數據
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="任務配置",
        example={
            "max_tokens": 5000,
            "temperature": 0.7,
            "quality_requirement": 0.8
        }
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="任務元數據（可擴展）",
        example={
            "priority": 0.8,
            "budget": 1.0,
            "type": "code_generation"
        }
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query": "Explain quantum computing to a 10-year-old",
                "config": {"temperature": 0.7},
                "metadata": {"priority": 0.5}
            }
        }
```

**JSON Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["query"],
  "properties": {
    "query": {"type": "string", "minLength": 1, "maxLength": 10000},
    "task_id": {"type": "string", "format": "uuid"},
    "user_id": {"type": "string"},
    "session_id": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"},
    "config": {"type": "object"},
    "metadata": {"type": "object"}
  }
}
```

---

### 2. ProcessingResult - 處理結果

系統返回的結果。

```python
from typing import List, Optional
from enum import Enum

class CognitiveLevel(str, Enum):
    """認知層級"""
    SYSTEM_1 = "system_1"
    SYSTEM_2 = "system_2"
    AGENT = "agent"

class ProcessingResult(BaseModel):
    """
    處理結果：系統返回的響應

    外部 API 契約
    """

    # 必需字段
    content: str = Field(
        ...,
        description="生成的內容",
        example="A binary search tree is a data structure..."
    )

    # 品質指標
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="信心度 [0, 1]",
        example=0.87
    )

    # 處理信息
    cognitive_level: CognitiveLevel = Field(
        ...,
        description="使用的認知層級"
    )

    processing_time: float = Field(
        ...,
        ge=0.0,
        description="處理時間（秒）",
        example=3.24
    )

    token_usage: Optional[int] = Field(
        None,
        description="使用的 token 數量"
    )

    # 元數據
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="處理元數據（可擴展）"
    )

    # 可選：中間步驟（用於調試）
    intermediate_steps: Optional[List[Dict]] = Field(
        None,
        description="中間步驟（僅當 config.include_steps=true 時返回）"
    )

    # 可選：元認知報告
    metacognitive_report: Optional[Dict] = Field(
        None,
        description="元認知報告（僅當 config.include_metacog=true 時返回）"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "content": "A binary search tree is...",
                "confidence": 0.87,
                "cognitive_level": "system_2",
                "processing_time": 3.24,
                "token_usage": 1250
            }
        }
```

---

### 3. CognitiveItem - 認知項目

工作空間中的信息單元。

```python
class ItemType(str, Enum):
    """認知項目類型"""
    OBSERVATION = "observation"
    THOUGHT = "thought"
    CODE_RESULT = "code_result"
    KNOWLEDGE = "knowledge"
    GOAL = "goal"
    HYPOTHESIS = "hypothesis"
    PREDICTION = "prediction"
    ERROR = "error"
    REFLECTION = "reflection"

class CognitiveItem(BaseModel):
    """認知項目：工作空間中的信息單元"""

    id: str = Field(..., description="唯一標識符")
    type: ItemType = Field(..., description="項目類型")
    content: Any = Field(..., description="實際內容")

    confidence: float = Field(..., ge=0.0, le=1.0, description="信心度")
    priority: float = Field(..., ge=0.0, le=1.0, description="優先級")

    timestamp: datetime = Field(default_factory=datetime.now)
    source: str = Field(..., description="來源 Processor")
    tags: List[str] = Field(default_factory=list, description="標籤")

    metadata: Dict[str, Any] = Field(default_factory=dict)

    # 工作記憶相關
    activation: float = Field(default=1.0, ge=0.0, le=1.0, description="激活度")
    access_count: int = Field(default=0, ge=0, description="訪問次數")
    last_access: Optional[datetime] = Field(None, description="最後訪問時間")
```

---

### 4. RouteDecision - 路由決策

OODA Router 的決策結果。

```python
class RoutingStrategy(str, Enum):
    """路由策略"""
    DIRECT_SYSTEM_1 = "direct_system_1"
    DIRECT_SYSTEM_2 = "direct_system_2"
    DIRECT_AGENT = "direct_agent"
    PROGRESSIVE = "progressive"
    PARALLEL = "parallel"
    ADAPTIVE = "adaptive"

class RouteDecision(BaseModel):
    """路由決策"""

    strategy: RoutingStrategy = Field(..., description="選擇的策略")
    initial_level: CognitiveLevel = Field(..., description="初始認知層級")
    backup_levels: List[CognitiveLevel] = Field(
        default_factory=list,
        description="備份層級（失敗時升級）"
    )

    max_iterations: int = Field(default=3, ge=1, le=10, description="最大迭代次數")
    quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="品質閾值")

    # 決策依據（可選，用於可解釋性）
    reasoning: Optional[str] = Field(None, description="決策理由")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="決策信心度")

    metadata: Dict[str, Any] = Field(default_factory=dict)
```

---

### 5. MonitoringReport - 監控報告

元認知監控的輸出。

```python
class GateResult(BaseModel):
    """品質閘門檢查結果"""
    passed: bool = Field(..., description="是否通過")
    failed_gates: List[str] = Field(default_factory=list, description="失敗的閘門")
    warnings: List[str] = Field(default_factory=list, description="警告")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="總體分數")

class MonitoringReport(BaseModel):
    """元認知監控報告"""

    confidence: float = Field(..., ge=0.0, le=1.0, description="信心度")
    gate_result: GateResult = Field(..., description="品質閘門結果")
    prediction_error: float = Field(..., ge=0.0, description="預測誤差")

    should_refine: bool = Field(..., description="是否需要精煉")
    refinement_strategy: Optional[str] = Field(None, description="推薦的精煉策略")

    warnings: List[str] = Field(default_factory=list, description="警告列表")
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

---

## REST API 端點

### 1. POST /api/v1/process

**主要的處理端點**。

#### 請求

```http
POST /api/v1/process
Content-Type: application/json

{
  "query": "Explain how neural networks learn",
  "config": {
    "max_tokens": 5000,
    "temperature": 0.7,
    "include_metacog": true
  },
  "metadata": {
    "priority": 0.8,
    "quality_requirement": 0.85
  }
}
```

#### 響應（成功）

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "content": "Neural networks learn through a process called backpropagation...",
  "confidence": 0.89,
  "cognitive_level": "system_2",
  "processing_time": 5.67,
  "token_usage": 2340,
  "metadata": {
    "iterations": 2,
    "refinement_applied": true
  },
  "metacognitive_report": {
    "confidence": 0.89,
    "gate_result": {
      "passed": true,
      "failed_gates": [],
      "warnings": [],
      "overall_score": 0.91
    },
    "prediction_error": 0.12,
    "should_refine": false
  }
}
```

#### 響應（錯誤）

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "ValidationError",
  "message": "query field is required",
  "details": {
    "field": "query",
    "constraint": "required"
  }
}
```

---

### 2. GET /api/v1/status

**系統狀態查詢**。

#### 請求

```http
GET /api/v1/status
```

#### 響應

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "healthy",
  "version": "1.0.0",
  "cognitive_features": {
    "global_workspace": true,
    "metacognition": true,
    "ooda_router": false,
    "memory_systems": false
  },
  "metrics": {
    "total_requests": 12345,
    "avg_processing_time": 4.23,
    "success_rate": 0.94,
    "avg_confidence": 0.82
  }
}
```

---

### 3. POST /api/v1/feedback

**用戶反饋（用於學習）**。

#### 請求

```http
POST /api/v1/feedback
Content-Type: application/json

{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "rating": 4,
  "comment": "Good explanation but could be more concise",
  "helpful": true
}
```

#### 響應

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "message": "Feedback received",
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## 內部 API（組件間）

### 1. Processor Interface

所有 Processor 必須實現的介面。

```python
from abc import ABC, abstractmethod

class ProcessorInterface(ABC):
    """Processor 介面契約"""

    @abstractmethod
    async def process(self, task: Task) -> ProcessingResult:
        """
        處理任務

        Args:
            task: 輸入任務

        Returns:
            處理結果

        Raises:
            ProcessingError: 處理失敗
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Processor 名稱"""
        pass

    @property
    def version(self) -> str:
        """Processor 版本"""
        return "1.0.0"

    async def initialize(self):
        """初始化（可選）"""
        pass

    async def shutdown(self):
        """清理資源（可選）"""
        pass
```

---

### 2. Router Interface

路由器介面。

```python
class RouterInterface(ABC):
    """路由器介面契約"""

    @abstractmethod
    async def route(self, task: Task) -> RouteDecision:
        """
        路由任務到合適的認知層級

        Args:
            task: 輸入任務

        Returns:
            路由決策

        Raises:
            RoutingError: 路由失敗
        """
        pass
```

---

### 3. Memory Interface

記憶系統介面。

```python
class MemoryInterface(ABC):
    """記憶系統介面契約"""

    @abstractmethod
    async def store(self, item: Any):
        """存儲項目"""
        pass

    @abstractmethod
    async def retrieve(self, query: str, top_k: int = 5) -> List[Any]:
        """檢索項目"""
        pass

    @abstractmethod
    async def consolidate(self):
        """記憶鞏固"""
        pass
```

---

## 配置模型

### 1. FeatureFlags

特性開關配置。

```python
class FeatureFlagsConfig(BaseModel):
    """特性開關配置"""

    cognitive_enabled: bool = Field(default=False, description="總開關")

    global_workspace_enabled: bool = Field(default=False)
    global_workspace_capacity: int = Field(default=7, ge=3, le=15)

    metacognition_enabled: bool = Field(default=False)
    metacognition_quality_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    metacognition_max_iterations: int = Field(default=3, ge=1, le=10)

    ooda_router_enabled: bool = Field(default=False)

    memory_systems_enabled: bool = Field(default=False)
    episodic_memory_enabled: bool = Field(default=False)
    semantic_memory_enabled: bool = Field(default=False)

    neuromodulation_enabled: bool = Field(default=False)
    exploration_rate: float = Field(default=0.1, ge=0.0, le=0.5)

    event_driven_enabled: bool = Field(default=False)
    parallel_execution_enabled: bool = Field(default=False)

    class Config:
        json_schema_extra = {
            "example": {
                "cognitive_enabled": true,
                "global_workspace_enabled": true,
                "metacognition_enabled": true
            }
        }
```

---

### 2. BudgetConfig

預算配置。

```python
class BudgetConfig(BaseModel):
    """預算配置"""

    max_tokens: int = Field(default=10000, ge=1000, le=100000)
    max_time_seconds: float = Field(default=300.0, ge=1.0, le=600.0)
    max_iterations: int = Field(default=3, ge=1, le=10)
    max_api_calls: int = Field(default=20, ge=1, le=100)
```

---

## 錯誤處理

### 錯誤響應模型

```python
class ErrorResponse(BaseModel):
    """標準錯誤響應"""

    error: str = Field(..., description="錯誤類型")
    message: str = Field(..., description="錯誤訊息")
    details: Optional[Dict[str, Any]] = Field(None, description="詳細信息")
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        json_schema_extra = {
            "example": {
                "error": "ValidationError",
                "message": "Invalid input",
                "details": {"field": "query", "constraint": "required"}
            }
        }
```

### 錯誤碼

| 錯誤碼 | HTTP 狀態 | 說明 |
|-------|---------|------|
| `ValidationError` | 400 | 輸入驗證失敗 |
| `ProcessingError` | 500 | 處理過程失敗 |
| `TimeoutError` | 504 | 處理超時 |
| `BudgetExceededError` | 429 | 預算耗盡 |
| `ConfigurationError` | 500 | 配置錯誤 |
| `NotFoundError` | 404 | 資源不存在 |

---

## OpenAPI 規格

完整的 OpenAPI 3.0 規格文件：

```yaml
openapi: 3.0.3
info:
  title: OpenAgent Cognitive API
  version: 1.0.0
  description: API for human-like cognitive processing

servers:
  - url: http://localhost:8000/api/v1
    description: Development server

paths:
  /process:
    post:
      summary: Process a task
      operationId: processTask
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Task'
      responses:
        '200':
          description: Processing successful
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ProcessingResult'
        '400':
          description: Invalid input
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ErrorResponse'

  /status:
    get:
      summary: Get system status
      operationId: getStatus
      responses:
        '200':
          description: System status
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                  version:
                    type: string

components:
  schemas:
    Task:
      type: object
      required:
        - query
      properties:
        query:
          type: string
          minLength: 1
        config:
          type: object
        metadata:
          type: object

    ProcessingResult:
      type: object
      required:
        - content
        - confidence
        - cognitive_level
        - processing_time
      properties:
        content:
          type: string
        confidence:
          type: number
          minimum: 0
          maximum: 1
        cognitive_level:
          type: string
          enum: [system_1, system_2, agent]
        processing_time:
          type: number

    ErrorResponse:
      type: object
      required:
        - error
        - message
      properties:
        error:
          type: string
        message:
          type: string
        details:
          type: object
```

---

## 測試範例

### 使用 Python Requests

```python
import requests

# 處理任務
response = requests.post(
    "http://localhost:8000/api/v1/process",
    json={
        "query": "Explain quantum computing",
        "config": {"temperature": 0.7},
        "metadata": {"priority": 0.8}
    }
)

result = response.json()
print(f"Confidence: {result['confidence']}")
print(f"Content: {result['content']}")
```

### 使用 cURL

```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is a binary search tree?",
    "config": {"max_tokens": 1000}
  }'
```

---

## 版本管理

### API 版本策略

- **當前版本**: `v1`
- **版本格式**: `/api/v{major}`
- **向後兼容**：v1 保持穩定，新功能通過元數據擴展
- **廢棄策略**：提前 6 個月通知

### 變更日誌

| 版本 | 日期 | 變更 |
|-----|------|------|
| v1.0.0 | 2026-02-12 | 初始版本 |

---

## 下一步

- **[10_code_examples.md](./10_code_examples.md)**: 完整的 API 使用範例
- **[00_overview_and_vision.md](./00_overview_and_vision.md)**: 返回總覽

---

**文檔維護者**: OpenAgent Architecture Team
**審核狀態**: Pending Review
