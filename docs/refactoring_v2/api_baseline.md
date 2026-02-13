# API Baseline Documentation

> **Created**: 2026-02-14  
> **Tag**: v2.0-pre-linus-refactor  
> **Purpose**: Document current public API before refactoring

---

## 📋 Public API Surface

This document captures the public interfaces that **MUST remain backward compatible** during refactoring.

---

## 1. RefactoredEngine

### Initialization
```python
from core.engine import RefactoredEngine, create_engine

# Method 1: Direct instantiation
engine = RefactoredEngine(llm_client=my_client, config={...})
await engine.initialize()

# Method 2: Factory function
engine = create_engine(llm_client=my_client, **config)
await engine.initialize()
```

### Core Methods

#### `async def process(request: Request) -> Response`
**Purpose**: Process a single request

**Parameters**:
- `request: Request` - The request object

**Returns**:
- `Response` - Processing result

**Example**:
```python
from core.models import Request, ProcessingMode

request = Request(
    query="What is Python?",
    mode=ProcessingMode.CHAT,
    temperature=0.7,
    stream=False
)

response = await engine.process(request)
print(response.result)  # LLM response text
print(response.tokens_used)  # Token count
print(response.time_ms)  # Processing time
```

#### `async def process_stream(request: Request) -> AsyncGenerator`
**Purpose**: Process request with streaming response

**Parameters**:
- `request: Request` - Request with `stream=True`

**Yields**:
- `Dict[str, Any]` - SSE events

**Example**:
```python
request = Request(query="...", stream=True)

async for event in engine.process_stream(request):
    print(f"Event: {event['event']}")
    print(f"Data: {event['data']}")
```

#### `def register_processor(mode: ProcessingMode, processor_class)`
**Purpose**: Register custom processor

**Example**:
```python
from core.processor import BaseProcessor

class CustomProcessor(BaseProcessor):
    async def process(self, context):
        return "custom result"

engine.register_processor(ProcessingMode.CHAT, CustomProcessor)
```

#### `@property def metrics`
**Purpose**: Get cognitive metrics summary

**Returns**:
- `Dict[str, Any]` - Metrics by cognitive level

**Example**:
```python
metrics = engine.metrics
print(metrics['system1']['count'])
print(metrics['system2']['avg_latency_ms'])
```

---

## 2. Request Model

```python
from core.models import Request, ProcessingMode

@dataclass
class Request:
    query: str                      # Required
    mode: ProcessingMode = AUTO     # Default: AUTO
    context_id: str = uuid4()       # Auto-generated
    trace_id: str = uuid4()         # Auto-generated
    
    # Optional parameters
    temperature: float = 0.7
    max_tokens: int = 4000
    stream: bool = False
    
    # Metadata
    metadata: Dict[str, Any] = {}
```

**Validation**:
- `query`: Non-empty string
- `mode`: Valid ProcessingMode enum
- `temperature`: 0.0 to 2.0
- `max_tokens`: Positive integer

---

## 3. Response Model

```python
from core.models import Response, ProcessingMode, EventType

@dataclass
class Response:
    result: str                     # Main response text
    mode: ProcessingMode            # Processing mode used
    trace_id: str                   # Trace ID
    
    # Usage statistics
    tokens_used: int = 0
    time_ms: float = 0
    cost_usd: float = 0
    
    # Additional data
    metadata: Dict[str, Any] = {}
    events: List[Dict[str, Any]] = []
```

**Methods**:
```python
response.add_event(EventType.INFO, data)
```

---

## 4. ProcessingMode Enum

```python
from core.models import ProcessingMode

class ProcessingMode(Enum):
    AUTO = "auto"
    CHAT = "chat"
    KNOWLEDGE = "knowledge"
    SEARCH = "search"
    CODE = "code"
    THINKING = "thinking"
    DEEP_RESEARCH = "deep_research"

# Properties
mode.cognitive_level  # "system1" | "system2" | "agent"
```

**Mapping**:
| Mode | Cognitive Level | Runtime | Description |
|------|----------------|---------|-------------|
| AUTO | system1 | model | Auto-select mode |
| CHAT | system1 | model | Quick conversation |
| KNOWLEDGE | system1 | model | KB retrieval |
| SEARCH | system2 | model | Web search |
| CODE | system2 | model | Code execution |
| THINKING | system2 | model | Deep thinking |
| DEEP_RESEARCH | agent | agent | Research workflow |

---

## 5. Processors

### BaseProcessor

```python
from core.processor import BaseProcessor

class BaseProcessor(ABC):
    def __init__(
        self, 
        llm_client=None, 
        services: Optional[Dict] = None,
        mcp_client=None
    ):
        ...
    
    @abstractmethod
    async def process(self, context: ProcessingContext) -> str:
        pass
```

### Built-in Processors

All inherit from `BaseProcessor`:

- `ChatProcessor` - Fast conversation
- `KnowledgeProcessor` - RAG retrieval
- `SearchProcessor` - Web search
- `ThinkingProcessor` - Deep analysis
- `CodeProcessor` - Code execution
- `DeepResearchProcessor` - Multi-step research

**Import**:
```python
from core.processor import (
    ChatProcessor,
    KnowledgeProcessor,
    SearchProcessor,
    CodeProcessor,
    DeepResearchProcessor,
)
```

---

## 6. ProcessorFactory

```python
from core.processor import ProcessorFactory

factory = ProcessorFactory(
    llm_client=client,
    services=services,
    mcp_client=mcp_client
)

processor = factory.get_processor(ProcessingMode.CHAT)
result = await processor.process(context)
```

---

## 7. Feature Flags

```python
from core.feature_flags import feature_flags

# Check if enabled
if feature_flags.is_enabled("routing.smart_routing"):
    # Use new routing

# Get value
cache_ttl = feature_flags.get_value("system1.cache_ttl", default=300)

# Master switch
if feature_flags.enabled:
    # Cognitive features enabled
```

---

## 8. Error Handling

### Error Types

```python
from core.errors import ErrorCategory, ErrorClassifier

# Categories
ErrorCategory.NETWORK
ErrorCategory.LLM
ErrorCategory.RESOURCE
ErrorCategory.BUSINESS
ErrorCategory.UNKNOWN

# Classify
category = ErrorClassifier.classify(exception)
is_retryable = ErrorClassifier.is_retryable(exception)
```

### Retry Decorator

```python
from core.error_handler import retry_with_backoff

@retry_with_backoff(max_retries=3, initial_delay=1.0)
async def may_fail():
    ...
```

---

## 9. Quick Process Function

```python
from core.engine import quick_process

result = await quick_process("What is Python?", mode="chat")
print(result)  # Direct string result
```

---

## 📝 Behavioral Contracts

### 1. Mode Selection (AUTO mode)

When `mode=ProcessingMode.AUTO`, the router should:
1. Analyze query keywords
2. Select appropriate mode
3. Fall back to CHAT if unclear

**Keywords**:
- Code: `代碼`, `code`, `程式`, `function`
- Search: `搜尋`, `search`, `查詢`, `find`
- Knowledge: `知識`, `knowledge`, `解釋`, `explain`
- Thinking: `深度`, `deep`, `分析`, `analyze`

### 2. Error Handling

All methods should:
- Return valid Response on success
- Not throw exceptions for LLM failures (return error in result)
- Log errors appropriately
- Maintain context/trace IDs

### 3. Streaming

When `stream=True`:
- Yield events in order: START → INFO/TOKEN → RESULT → END
- Include trace_id in all events
- Handle errors gracefully (emit ERROR event)

### 4. Context Preservation

- `context_id` groups related requests
- `trace_id` tracks individual request
- Both should be preserved in logs and responses

---

## ⚠️ Breaking Changes Policy

During refactoring, we **MUST NOT**:

❌ Change public method signatures  
❌ Remove public classes/functions  
❌ Change default behaviors  
❌ Break existing imports  

We **MAY**:

✅ Add new optional parameters (with defaults)  
✅ Add new methods  
✅ Improve performance  
✅ Fix bugs  
✅ Refactor internals (if API unchanged)  

---

## 🧪 API Validation Tests

These tests must pass before and after refactoring:

```python
# tests/integration/test_api_compatibility.py (TODO)

async def test_engine_initialization():
    engine = RefactoredEngine()
    await engine.initialize()
    assert engine.initialized

async def test_process_returns_response():
    request = Request(query="test", mode=ProcessingMode.CHAT)
    response = await engine.process(request)
    assert isinstance(response, Response)
    assert response.result

async def test_process_stream_yields_events():
    request = Request(query="test", stream=True)
    events = [e async for e in engine.process_stream(request)]
    assert len(events) > 0
    assert any(e['event'] == 'result' for e in events)
```

---

## 📊 Edge Cases

### Empty Query
```python
request = Request(query="", mode=ProcessingMode.CHAT)
# Should: Validate and raise ValueError
```

### Invalid Mode
```python
request = Request(query="test", mode="invalid")
# Should: Raise ValueError
```

### Extremely Long Query
```python
request = Request(query="x" * 100000)  # 100k chars
# Should: Handle gracefully (truncate or reject)
```

### No LLM Client
```python
engine = RefactoredEngine(llm_client=None)
request = Request(query="test")
# Should: Raise RuntimeError with clear message
```

---

## 🔍 Deprecation Policy

If we need to deprecate an API:

1. Add `@deprecated` decorator
2. Log warning on first use
3. Update docs with migration path
4. Keep for at least 2 minor versions
5. Remove in major version

**Example**:
```python
import warnings

@deprecated("Use new_method() instead. Will be removed in v3.0")
def old_method():
    warnings.warn("old_method is deprecated", DeprecationWarning)
    return new_method()
```

---

## 📚 Related Documents

- [Behavior Baseline](./behavior_baseline.md) - Expected behaviors (TODO)
- [Performance Baseline](./performance_baseline.md) - Performance metrics (TODO)
- [Migration Guide](./migration_guide_template.md) - For users (TODO)

---

**Baseline Captured**: 2026-02-14  
**Git Tag**: v2.0-pre-linus-refactor  
**Next Review**: After Phase 1 (models_v2.py)

**Maintainers**: Verify this document matches actual code behavior
