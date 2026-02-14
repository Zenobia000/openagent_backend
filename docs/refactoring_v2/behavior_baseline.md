# Behavior Baseline

> **Tag**: v2.0-pre-linus-refactor  
> **Purpose**: Document expected behaviors before refactoring

---

## 🎯 Core Behaviors

### 1. Request Processing Flow

```
Request → Router → Runtime → Processor → Response
```

**Steps**:
1. Parse Request (validate query, mode)
2. Route (select actual mode if AUTO)
3. Select Runtime (ModelRuntime or AgentRuntime)
4. Execute Processor
5. Build Response (collect metrics, events)

---

## 2. Mode Resolution (AUTO → Concrete)

### Input
```python
Request(query="寫一個 Python 函數", mode=ProcessingMode.AUTO)
```

### Expected Behavior
1. Router analyzes query keywords
2. Finds "Python" and "函數" → matches CODE pattern
3. Returns `RoutingDecision(mode=ProcessingMode.CODE, ...)`

### Keyword Matching
| Keywords Found | Selected Mode |
|----------------|---------------|
| 代碼, code, 程式, function | CODE |
| 搜尋, search, 查詢, find | SEARCH |
| 知識, knowledge, 解釋, explain | KNOWLEDGE |
| 深度, deep, 分析, analyze, 思考 | THINKING |
| *(default)* | CHAT |

---

## 3. Error Handling Patterns

### Network Errors (Retryable)
```python
# LLM API timeout
→ Should: Retry with exponential backoff (3 attempts)
→ Final failure: Return Response with error message in result
```

### Business Errors (Non-retryable)
```python
# Empty query
→ Should: Validate immediately, raise ValueError
→ No retry, no LLM call
```

### LLM Errors
```python
# Rate limit exceeded
→ Should: Retry with backoff
→ Or fallback to next provider in MultiProviderLLM
```

---

## 4. Streaming Behavior

### Event Sequence
```
START → INFO (optional) → TOKEN* → RESULT → END
```

**Example**:
```json
{"event": "start", "data": {...}}
{"event": "info", "data": {"name": "opencode"}}
{"event": "token", "data": "Hello"}
{"event": "token", "data": " "}
{"event": "token", "data": "world"}
{"event": "result", "data": {"response": "Hello world", "trace_id": "..."}}
{"event": "end", "data": null}
```

### Error in Stream
```
START → INFO → TOKEN* → ERROR → END
```

---

## 5. Context & Tracing

### Context ID
- Groups related requests (e.g., conversation)
- Persists across multiple `process()` calls
- Used for cache lookups

### Trace ID
- Unique per request
- Used for logging and debugging
- Included in all events and responses

**Example**:
```python
# Same context, different traces
req1 = Request(query="Hi", context_id="conv-123")  # trace_id: uuid-A
req2 = Request(query="Bye", context_id="conv-123") # trace_id: uuid-B

# Both belong to same context but have different traces
```

---

## 6. Caching (when enabled)

### Cache Key
```
f"{mode}:{query_normalized}"
```

### Normalization
- Lowercase
- Strip whitespace
- Ignore punctuation differences

**Examples**:
```python
"What is Python?" → "what is python"
"  WHAT  IS  PYTHON?  " → "what is python"
# Both hit the same cache entry
```

### TTL
- Default: 300 seconds (5 minutes)
- Configurable via feature_flags

---

## 7. Processor Delegation

### System 1 (Fast Path)
- CHAT → ChatProcessor
- KNOWLEDGE → KnowledgeProcessor
- No state, cache-friendly

### System 2 (Thinking Path)
- SEARCH → SearchProcessor (calls web search service)
- THINKING → ThinkingProcessor (multi-step reasoning)
- CODE → CodeProcessor (may call sandbox)

### Agent (Workflow Path)
- DEEP_RESEARCH → DeepResearchProcessor
  - Multi-phase workflow
  - Generates report plan
  - Performs web searches
  - Synthesizes final report

---

## 8. Service Failures (Graceful Degradation)

### Search Service Down
```python
mode = ProcessingMode.SEARCH
# Expected: Log warning, return "[Search unavailable]" message
# Should NOT: Crash or hang
```

### Knowledge Service Down
```python
mode = ProcessingMode.KNOWLEDGE
# Expected: Fall back to LLM-only response (no RAG)
# Should NOT: Return empty result
```

### Sandbox Service Down
```python
mode = ProcessingMode.CODE
# Expected: Generate code but skip execution
# Result includes: "Code generated (execution unavailable)"
```

---

## 9. Multi-Provider Fallback

### Primary Provider Fails
```python
providers = [OpenAIClient, AnthropicClient]
# Primary (OpenAI) rate limited
→ Should: Automatically try Anthropic
→ Log: "Fallback succeeded: anthropic (after 1 failed)"
```

### All Providers Fail
```python
# Both providers unavailable
→ Should: Raise exception with clear message
→ Response: Error message in result
```

---

## 10. Metrics Collection

### Per Request
```python
response.tokens_used  # Total tokens (input + output)
response.time_ms      # Processing duration
response.cost_usd     # Estimated cost (if available)
```

### Aggregate (engine.metrics)
```python
{
  "system1": {
    "count": 150,
    "total_tokens": 45000,
    "avg_latency_ms": 850,
    "success_rate": 0.99
  },
  "system2": {
    "count": 50,
    "total_tokens": 120000,
    "avg_latency_ms": 4500,
    "success_rate": 0.95
  }
}
```

---

## 🧪 Regression Tests

These behaviors MUST be preserved:

```python
# Test 1: AUTO mode selects CODE for code query
request = Request(query="寫一個 Python 函數計算階乘", mode=ProcessingMode.AUTO)
response = await engine.process(request)
assert response.mode == ProcessingMode.CODE

# Test 2: Empty query raises error
with pytest.raises(ValueError):
    Request(query="", mode=ProcessingMode.CHAT)

# Test 3: Streaming yields events in order
events = [e async for e in engine.process_stream(...)]
event_types = [e['event'] for e in events]
assert event_types[0] == 'start'
assert event_types[-1] == 'end'
assert 'result' in event_types

# Test 4: Service failure doesn't crash
# (Mock search service to raise exception)
response = await engine.process(Request(..., mode=ProcessingMode.SEARCH))
assert "[Search unavailable]" in response.result or response.result != ""

# Test 5: Trace ID preserved
request = Request(query="test")
response = await engine.process(request)
assert response.trace_id == request.trace_id
```

---

## 🚨 Known Issues (Baseline)

Document current bugs/quirks to NOT reproduce:

1. **Multi-provider soft error detection** ⚠️  
   - Currently uses string checking: `result.startswith("[")`
   - This is a BUG, will be fixed in Phase 3

2. **Processor.py 2611 lines** ⚠️  
   - Monolithic file, hard to maintain
   - Will be split in Phase 2

3. **ProcessingMode cognitive_level** ⚠️  
   - Uses dict mapping (special case)
   - Will use data-driven approach in Phase 1

---

## 📊 Performance Expectations

### Latency (P95)
- System 1 (CHAT, KNOWLEDGE): < 3s
- System 2 (SEARCH, CODE, THINKING): < 15s
- Agent (DEEP_RESEARCH): < 60s (depends on depth)

### Throughput
- Concurrent requests: ~10 RPS (with LLM rate limits)
- Cache hit rate: ~15% (typical)

### Resource Usage
- Memory: ~500MB baseline
- CPU: Low (most time waiting on LLM)

---

## 📝 Logging Expectations

### Info Level
```
Processing request: {query[:50]}...
🔧 Tool Decision: search (confidence: 0.9)
💬 LLM Response: {response[:100]}...
Request processed successfully (time_ms: 1234, tokens: 567)
```

### Debug Level (when enabled)
```
📝 LLM Prompt: {full_prompt}
🔗 Web Results: Retrieved 5 sources
💾 Cache HIT for chat query
```

### Error Level
```
❌ LLM Error: Rate limit exceeded (provider: openai)
⚠️ Search service unavailable: Connection refused
```

---

**Baseline Captured**: 2026-02-14  
**Next Verification**: After each Phase completion
