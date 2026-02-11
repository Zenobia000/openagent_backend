# Module Dependency Analysis - OpenCode Platform

---

**Document Version:** `v2.0`
**Last Updated:** `2026-02-12`
**Status:** `Current`

---

## 1. Overview

This document defines the internal module dependency relationships of OpenCode Platform. The architecture strictly follows a unidirectional dependency structure: **API -> Core -> Services**.

---

## 2. Core Dependency Principles

- **Acyclic Dependencies**: Dependencies form a DAG. `services` never imports `core` or `api`. `core` never imports `api`.
- **Dependency Inversion**: `core` depends on abstractions (`protocols.py`, `LLMProvider` ABC), not concrete implementations.
- **Service Autonomy**: Each `services` subdirectory is self-contained. Cross-service coordination happens in `core`.

---

## 3. High-Level Module Dependency Diagram

```mermaid
graph TD
    subgraph "External"
        User[User via HTTP/CLI]
        LLM_API[LLM APIs<br/>OpenAI / Anthropic / Gemini]
        VectorDB[Qdrant]
        Web[Public Web]
        DockerD[Docker Daemon]
    end

    subgraph "API Layer"
        Routes[api.routes]
        Schemas[api.schemas]
        Streaming[api.streaming]
        APIErrors[api.errors]
        Middleware[api.middleware]
        Auth[auth.jwt + auth.dependencies]
    end

    subgraph "Core Layer"
        Engine[core.engine<br/>RefactoredEngine]
        Router[core.router<br/>DefaultRouter]
        ModelRT[core.runtime.model_runtime<br/>ModelRuntime]
        AgentRT[core.runtime.agent_runtime<br/>AgentRuntime]
        Factory[core.processor<br/>ProcessorFactory]
        Models[core.models]
        Flags[core.feature_flags]
        Cache[core.cache]
        Metrics[core.metrics]
        Errors[core.errors<br/>ErrorClassifier]
        Protocols[core.protocols]
        Logger[core.logger]
    end

    subgraph "Service Layer"
        LLMMulti[services.llm<br/>MultiProviderLLMClient]
        LLMOpenAI[services.llm.openai_client]
        LLMAnthropic[services.llm.anthropic_client]
        LLMGemini[services.llm.gemini_client]
        Knowledge[services.knowledge]
        Search[services.search]
        Sandbox[services.sandbox]
        Browser[services.browser]
        Research[services.research]
        Repo[services.repo]
    end

    %% External -> API
    User --> Routes
    User --> Auth

    %% API -> Core
    Routes --> Engine
    Routes --> Models
    Routes --> Auth
    Streaming --> Engine
    Middleware --> Logger

    %% Core internal
    Engine --> Router
    Engine --> Flags
    Engine --> Metrics
    Router --> ModelRT
    Router --> AgentRT
    ModelRT --> Factory
    ModelRT --> Cache
    AgentRT --> Factory
    AgentRT --> Errors
    Factory --> Models
    Factory --> Protocols

    %% Core -> Services (via DI)
    Factory --> LLMMulti
    Factory --> Knowledge
    Factory --> Search
    Factory --> Sandbox
    Factory --> Browser
    Factory --> Research

    %% LLM Multi-provider internal
    LLMMulti --> LLMOpenAI
    LLMMulti --> LLMAnthropic
    LLMMulti --> LLMGemini

    %% Services -> External
    LLMOpenAI --> LLM_API
    LLMAnthropic --> LLM_API
    LLMGemini --> LLM_API
    Knowledge --> VectorDB
    Search --> Web
    Sandbox --> DockerD
    Browser --> Web

    classDef api fill:#E8F4FD,stroke:#1565C0,stroke-width:2px,color:#000
    classDef core fill:#FFF8E1,stroke:#F57C00,stroke-width:2px,color:#000
    classDef service fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#000
    classDef external fill:#FAFAFA,stroke:#424242,stroke-width:2px,color:#000

    class Routes,Schemas,Streaming,APIErrors,Middleware,Auth api
    class Engine,Router,ModelRT,AgentRT,Factory,Models,Flags,Cache,Metrics,Errors,Protocols,Logger core
    class LLMMulti,LLMOpenAI,LLMAnthropic,LLMGemini,Knowledge,Search,Sandbox,Browser,Research,Repo service
    class User,LLM_API,VectorDB,Web,DockerD external
```

---

## 4. Layer Responsibility Matrix

| Layer | Responsibility | Key Dependencies | Forbidden Imports |
|:---|:---|:---|:---|
| **`src/api`** | HTTP handling, validation, SSE streaming | `fastapi`, `pydantic`, `core.engine` | `src.services` |
| **`src/auth`** | JWT encode/decode, user extraction | `python-jose`, `fastapi` | `src.core`, `src.services` |
| **`src/core`** | Engine orchestration, routing, caching, metrics, error classification | `core.models`, `core.protocols` | `src.api` |
| **`src/services`** | External API/DB integration, LLM providers | `openai`, `anthropic`, `qdrant-client`, `docker` | `src.core`, `src.api` |

---

## 5. Key Dependency Paths

### 5.1 Chat Request (System 1 - Cached)

```
api.routes -> core.engine.process(Request)
  -> core.router -> classify as SYSTEM1
  -> core.runtime.model_runtime.execute()
    -> [cache check: HIT?] -> return cached response
    -> [cache MISS] -> core.processor.ChatProcessor.process()
      -> services.llm.MultiProviderLLMClient.generate()
        -> [OpenAI success] -> return
        -> [OpenAI fail] -> [Anthropic success] -> return
      -> [cache PUT]
  -> core.metrics.record_request()
  -> return Response
```

### 5.2 Deep Research (Agent - Stateful with Retry)

```
api.routes -> core.engine.process(Request)
  -> core.router -> classify as AGENT
  -> core.runtime.agent_runtime.execute()
    -> core.processor.DeepResearchProcessor.process()
      -> [wrapped in retry_with_backoff(max_retries=2)]
      -> services.research -> services.search -> services.llm
    -> [on failure: ErrorClassifier -> record error_category]
  -> core.metrics.record_request()
  -> return Response
```

---

## 6. Dependency Risk Management

| External Service | Risk | Impact | Mitigation |
|:---|:---|:---|:---|
| **LLM APIs** | High | All AI features | Multi-provider fallback chain (OpenAI -> Anthropic -> Gemini) |
| **Qdrant DB** | Medium | RAG/Knowledge features | Abstract `VectorStoreProtocol`, local fallback possible |
| **Docker Daemon** | Low | Code sandbox only | Sandbox is optional; core system runs without it |
| **Web Search APIs** | Low | Search mode only | Multi-engine fallback (Tavily -> Serper -> DuckDuckGo) |
