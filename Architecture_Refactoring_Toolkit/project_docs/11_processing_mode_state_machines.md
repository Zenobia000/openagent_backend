# Processing Mode State Machines

---

**Document Version:** `v2.0`
**Last Updated:** `2026-02-12`
**Status:** `Current (Implemented)`

---

## 1. Overview

This document visualizes the internal workflow of each `ProcessingMode` using state machine diagrams. Each mode is implemented by a corresponding `Processor` class in `src/core/processor.py`.

### Cognitive Architecture Context

Every mode is classified into a cognitive level that determines its runtime execution path:

| Cognitive Level | Modes | Runtime | Characteristics |
|:---|:---|:---|:---|
| **System 1** | CHAT, KNOWLEDGE | ModelRuntime | Fast, cached (optional), stateless |
| **System 2** | SEARCH, CODE, THINKING | ModelRuntime | Analytical, multi-step, stateless |
| **Agent** | DEEP_RESEARCH | AgentRuntime | Stateful, workflow-tracked, retry-wrapped |

### Request Lifecycle (All Modes)

```mermaid
stateDiagram-v2
    [*] --> RouteRequest
    RouteRequest: DefaultRouter.route()
    RouteRequest --> CheckRuntime: RoutingDecision

    state CheckRuntime <<choice>>
    CheckRuntime --> ModelRuntime: System 1 or System 2
    CheckRuntime --> AgentRuntime: Agent level

    state ModelRuntime {
        [*] --> CacheCheck
        CacheCheck --> CacheHit: System 1 + cache enabled
        CacheCheck --> ProcessorExec: Cache miss or System 2
        CacheHit --> [*]
        ProcessorExec --> CachePut: System 1 result
        ProcessorExec --> [*]: System 2 result
        CachePut --> [*]
    }

    state AgentRuntime {
        [*] --> WorkflowInit
        WorkflowInit --> RetryableExec: retry_with_backoff(max=2)
        RetryableExec --> WorkflowComplete: Success
        RetryableExec --> ErrorClassify: Failure
        ErrorClassify --> RetryableExec: Retryable (network/LLM)
        ErrorClassify --> WorkflowFailed: Non-retryable
        WorkflowComplete --> [*]
        WorkflowFailed --> [*]
    }

    ModelRuntime --> RecordMetrics
    AgentRuntime --> RecordMetrics
    RecordMetrics --> [*]
```

---

## 2. Chat Mode (`ProcessingMode.CHAT`)

**Processor**: `ChatProcessor`
**Cognitive Level**: System 1
**Runtime**: ModelRuntime (cacheable)

The simplest mode. Direct LLM call with system prompt.

### State Machine

```mermaid
stateDiagram-v2
    [*] --> CacheCheck
    CacheCheck: Check ResponseCache (SHA-256 key)

    state CacheCheck <<choice>>
    CacheCheck --> ReturnCached: Cache HIT
    CacheCheck --> BuildPrompt: Cache MISS

    BuildPrompt: Combine system prompt + user query
    BuildPrompt --> CallLLM: generate(prompt)
    CallLLM: MultiProviderLLMClient.generate()
    CallLLM --> CachePut: Store result
    CachePut --> ReturnResult
    ReturnCached --> [*]
    ReturnResult --> [*]
```

### State Descriptions

- **CacheCheck**: SHA-256 hash of `mode:query` checked against ResponseCache. Only when `system1.enable_cache` flag is ON.
- **BuildPrompt**: Combines CHAT system prompt template with user query.
- **CallLLM**: Calls `MultiProviderLLMClient.generate()` — OpenAI first, fallback to Anthropic/Gemini on retryable error.
- **CachePut**: Stores result in ResponseCache with TTL (default 300s).

---

## 3. Knowledge Mode (`ProcessingMode.KNOWLEDGE`)

**Processor**: `KnowledgeProcessor`
**Cognitive Level**: System 1
**Runtime**: ModelRuntime (cacheable)

RAG (Retrieval-Augmented Generation) pipeline — retrieves from vector DB before generating.

### State Machine

```mermaid
stateDiagram-v2
    [*] --> CacheCheck
    state CacheCheck <<choice>>
    CacheCheck --> ReturnCached: Cache HIT
    CacheCheck --> GenerateEmbeddings: Cache MISS

    GenerateEmbeddings: Embed user query (Cohere/OpenAI)
    GenerateEmbeddings --> SearchVectorDB: Vector similarity search
    SearchVectorDB: Query Qdrant for top-k documents
    SearchVectorDB --> SynthesizeContext: Combine retrieved chunks + query
    SynthesizeContext --> CallLLM: Generate answer with context
    CallLLM: MultiProviderLLMClient.generate()
    CallLLM --> CachePut: Store in cache
    CachePut --> ReturnResult
    ReturnCached --> [*]
    ReturnResult --> [*]
```

### State Descriptions

- **GenerateEmbeddings**: Converts user query to vector using embedding provider (Cohere or OpenAI).
- **SearchVectorDB**: Performs similarity search in Qdrant, retrieves top-k document chunks.
- **SynthesizeContext**: Combines retrieved document fragments with the original query into an enriched prompt.
- **CallLLM**: Generates a knowledge-grounded answer via the multi-provider LLM chain.

---

## 4. Search Mode (`ProcessingMode.SEARCH`)

**Processor**: `SearchProcessor`
**Cognitive Level**: System 2
**Runtime**: ModelRuntime (no cache)

Multi-step web search with query expansion and result synthesis.

### State Machine

```mermaid
stateDiagram-v2
    [*] --> GenerateSearchQueries
    GenerateSearchQueries: LLM generates 2-3 optimized search queries
    GenerateSearchQueries --> ExecuteSearches: Concurrent web searches
    ExecuteSearches: Search via Tavily / Serper / DuckDuckGo
    ExecuteSearches --> SynthesizeResults: Aggregate all search results
    SynthesizeResults --> CallLLM: Generate comprehensive report
    CallLLM: MultiProviderLLMClient.generate()
    CallLLM --> [*]
```

### State Descriptions

- **GenerateSearchQueries**: LLM converts a vague user question into 2-3 precise, search-engine-optimized queries.
- **ExecuteSearches**: Executes each query through the multi-engine search service (Tavily > Serper > DuckDuckGo fallback).
- **SynthesizeResults**: Consolidates all search results into a unified context.
- **CallLLM**: Generates a comprehensive answer based on the aggregated context.

---

## 5. Code Mode (`ProcessingMode.CODE`)

**Processor**: `CodeProcessor`
**Cognitive Level**: System 2
**Runtime**: ModelRuntime (no cache)

Code generation and isolated execution in Docker sandbox.

### State Machine

```mermaid
stateDiagram-v2
    [*] --> GenerateCode
    GenerateCode: LLM generates executable code from natural language
    GenerateCode --> ExecuteInSandbox: Send to Docker container
    ExecuteInSandbox: SandboxService.execute(code, timeout)

    state ExecuteInSandbox <<choice>>
    ExecuteInSandbox --> FormatSuccess: Exit code 0
    ExecuteInSandbox --> FormatError: Non-zero exit / timeout

    FormatSuccess: Capture stdout + return value
    FormatError: Capture stderr + error message

    FormatSuccess --> [*]
    FormatError --> [*]
```

### State Descriptions

- **GenerateCode**: LLM converts natural language requirements into executable code (Python).
- **ExecuteInSandbox**: Creates an isolated Docker container with resource limits (CPU, memory, timeout). Executes the generated code.
- **FormatSuccess/Error**: Collects stdout, stderr, return value, and execution time. Returns formatted result to user.

---

## 6. Thinking Mode (`ProcessingMode.THINKING`)

**Processor**: `ThinkingProcessor`
**Cognitive Level**: System 2
**Runtime**: ModelRuntime (no cache)

Multi-stage deep thinking process for complex or abstract problems.

### State Machine

```mermaid
stateDiagram-v2
    [*] --> ProblemAnalysis

    ProblemAnalysis: Decompose and understand the problem
    ProblemAnalysis --> MultiPerspective: Analyze from multiple angles

    MultiPerspective: Critical, creative, analytical perspectives
    MultiPerspective --> DeepReasoning: Chain-of-thought reasoning

    DeepReasoning: Logical inference with step-by-step thinking
    DeepReasoning --> SynthesisAndReflection: Consolidate + self-reflect

    SynthesisAndReflection: Quality check and refinement
    SynthesisAndReflection --> FinalAnswer: Generate structured answer

    FinalAnswer --> [*]
```

### State Descriptions

- **ProblemAnalysis**: Decomposes the problem into components and identifies key aspects.
- **MultiPerspective**: Analyzes from different angles (critical, creative, analytical).
- **DeepReasoning**: Applies chain-of-thought (CoT) methodology for logical reasoning.
- **SynthesisAndReflection**: Consolidates all intermediate analysis, self-reflects to improve quality.
- **FinalAnswer**: Produces a comprehensive, structured final answer based on the full thinking process.

---

## 7. Deep Research Mode (`ProcessingMode.DEEP_RESEARCH`)

**Processor**: `DeepResearchProcessor`
**Cognitive Level**: Agent
**Runtime**: AgentRuntime (stateful, retry-wrapped)

Automated research pipeline. This is the only mode that uses AgentRuntime, which provides:
- **WorkflowState tracking**: steps = `[plan, search, synthesize]`
- **Smart retry**: `retry_with_backoff(max_retries=2, base_delay=1.0)` — retries on network/LLM errors only
- **Error classification**: Failed steps recorded with `ErrorClassifier.classify()` category

### State Machine

```mermaid
stateDiagram-v2
    [*] --> InitWorkflow
    InitWorkflow: AgentRuntime creates WorkflowState

    state RetryBoundary {
        [*] --> WriteReportPlan
        WriteReportPlan: Generate detailed research outline
        WriteReportPlan --> GenerateSearchQueries: Extract structured search tasks

        GenerateSearchQueries: Create (query, goal, priority) tuples
        GenerateSearchQueries --> ExecuteSearchTasks: Iterate through tasks

        state ExecuteSearchTasks {
            [*] --> SearchTask
            SearchTask: Execute web search for current task
            SearchTask --> ProcessResult: Collect and summarize
            ProcessResult --> SearchTask: Next task
            ProcessResult --> [*]: All tasks done
        }

        ExecuteSearchTasks --> WriteFinalReport: Synthesize all results
        WriteFinalReport: Generate structured report with citations
        WriteFinalReport --> [*]
    }

    InitWorkflow --> RetryBoundary: retry_with_backoff(max=2)

    state ErrorHandling <<choice>>
    RetryBoundary --> WorkflowComplete: Success
    RetryBoundary --> ErrorHandling: Exception

    ErrorHandling --> RetryBoundary: Retryable (network/LLM)
    ErrorHandling --> WorkflowFailed: Non-retryable or max retries exceeded

    WorkflowComplete: WorkflowState.complete()
    WorkflowFailed: ErrorClassifier.classify(error)

    WorkflowComplete --> [*]
    WorkflowFailed --> [*]
```

### State Descriptions

- **InitWorkflow**: AgentRuntime creates a `WorkflowState(steps=["plan", "search", "synthesize"])` and sets status to "running".
- **WriteReportPlan**: LLM generates a detailed research report outline based on user requirements.
- **GenerateSearchQueries**: Extracts structured search tasks (query, goal, priority) from the research plan.
- **ExecuteSearchTasks**: Iterates through each search task, executing web searches and processing results.
- **WriteFinalReport**: Synthesizes all search results with the original plan into a structured report with citations.
- **ErrorHandling**: On failure, `ErrorClassifier` categorizes the error. NETWORK/LLM errors trigger retry (up to 2 times with exponential backoff). BUSINESS/RESOURCE_LIMIT/UNKNOWN errors fail immediately.
- **WorkflowComplete/Failed**: Final workflow state is recorded in `context.intermediate_results["workflow_state"]`.

---

## 8. Mode-to-Infrastructure Mapping

| Mode | Cognitive Level | Runtime | Cache | Retry | LLM Calls | External Services |
|:---|:---|:---|:---:|:---:|:---:|:---|
| **CHAT** | System 1 | ModelRuntime | Yes | No | 1 | LLM only |
| **KNOWLEDGE** | System 1 | ModelRuntime | Yes | No | 1 | Embedding + Qdrant + LLM |
| **SEARCH** | System 2 | ModelRuntime | No | No | 2+ | Search engines + LLM |
| **CODE** | System 2 | ModelRuntime | No | No | 1 | LLM + Docker |
| **THINKING** | System 2 | ModelRuntime | No | No | 4-5 | LLM only |
| **DEEP_RESEARCH** | Agent | AgentRuntime | No | Yes (max 2) | 3+ | Search engines + LLM |
