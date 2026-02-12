# Processor State Machine 驗證與修正報告

## 1. ChatProcessor 驗證

### 文檔要求 (System 1, ModelRuntime, Cacheable):
- ✅ CacheCheck → Cache HIT/MISS 判斷
- ✅ BuildPrompt → 組合系統提示詞 + 用戶查詢
- ✅ CallLLM → MultiProviderLLMClient.generate()
- ❌ CachePut → 缺少快取存儲步驟

### 當前實現問題:
```python
# 當前沒有實現快取機制
async def process(self, context: ProcessingContext) -> str:
    # 直接調用 LLM，沒有快取檢查
```

### 修正建議:
```python
async def process(self, context: ProcessingContext) -> str:
    self.logger.progress("chat", "start")
    context.set_current_step("chat")

    # Step 1: Cache Check (System 1 特性)
    cache_key = f"chat:{context.request.query}"
    if self.cache and self.cache.get(cache_key):
        cached_response = self.cache.get(cache_key)
        self.logger.info("💾 Cache HIT", "chat", "cache_hit")
        return cached_response

    # Step 2: Build Prompt
    system_prompt = PromptTemplates.get_system_instruction()
    output_guidelines = PromptTemplates.get_output_guidelines()
    full_prompt = f"{system_prompt}\n\n{output_guidelines}\n\nUser: {context.request.query}"

    # Step 3: Call LLM
    response = await self._call_llm(full_prompt, context)

    # Step 4: Cache Put (System 1 特性)
    if self.cache:
        self.cache.put(cache_key, response, ttl=300)
        self.logger.info("💾 Cache PUT", "chat", "cache_put")

    self.logger.message(response)
    context.mark_step_complete("chat")
    self.logger.progress("chat", "end")
    return response
```

---

## 2. KnowledgeProcessor 驗證

### 文檔要求 (System 1, ModelRuntime, Cacheable):
- ❌ CacheCheck → 缺少快取檢查
- ✅ GenerateEmbeddings → 生成嵌入向量
- ✅ SearchVectorDB → Qdrant 搜索
- ✅ SynthesizeContext → 組合檢索結果
- ✅ CallLLM → 生成答案
- ❌ CachePut → 缺少快取存儲

### 當前使用的 Prompts:
- ✅ `get_search_knowledge_result_prompt` - 知識合成
- ✅ `get_citation_rules` - 引用規則
- ✅ `get_system_instruction` - 系統指令 (fallback)

### 修正建議:
```python
async def process(self, context: ProcessingContext) -> str:
    self.logger.progress("knowledge-retrieval", "start")

    # Step 1: Cache Check (System 1)
    cache_key = f"knowledge:{context.request.query}"
    if self.cache and self.cache.get(cache_key):
        return self.cache.get(cache_key)

    # Step 2-4: 現有的 RAG 流程...
    # [保持現有實現]

    # Step 5: Cache Put
    if self.cache and response:
        self.cache.put(cache_key, response, ttl=300)

    return response
```

---

## 3. SearchProcessor 驗證

### 文檔要求 (System 2, ModelRuntime, No Cache):
- ✅ GenerateSearchQueries → 生成優化查詢
- ✅ ExecuteSearches → 執行多引擎搜索
- ✅ SynthesizeResults → 整合結果
- ✅ CallLLM → 生成報告

### 當前使用的 Prompts:
- ✅ `get_serp_queries_prompt` - SERP 查詢生成
- ✅ `get_search_result_prompt` - 搜索結果處理
- ✅ `get_citation_rules` - 引用規則

### 狀態: ✅ 符合規範

---

## 4. CodeProcessor 驗證

### 文檔要求 (System 2, ModelRuntime, No Cache):
- ✅ GenerateCode → LLM 生成代碼
- ✅ ExecuteInSandbox → Docker 執行
- ✅ FormatSuccess/Error → 格式化結果

### 當前使用的 Prompts:
- ✅ `get_code_generation_prompt` - 代碼生成

### 狀態: ✅ 符合規範

---

## 5. ThinkingProcessor 驗證

### 文檔要求 (System 2, ModelRuntime, No Cache):
- ✅ ProblemAnalysis → 問題分解
- ✅ MultiPerspective → 多角度分析
- ✅ DeepReasoning → 推理鏈
- ✅ SynthesisAndReflection → 綜合反思
- ✅ FinalAnswer → 最終答案

### 當前使用的 Prompts:
- ✅ `get_thinking_mode_prompt` - 問題分析
- ✅ `get_critical_thinking_prompt` - 批判思維
- ✅ `get_chain_of_thought_prompt` - 推理鏈
- ✅ `get_reflection_prompt` - 反思改進
- ✅ `get_output_guidelines` - 輸出指南

### 狀態: ✅ 完美符合規範

---

## 6. DeepResearchProcessor 驗證

### 文檔要求 (Agent, AgentRuntime, Stateful):
- ❌ InitWorkflow → 缺少 WorkflowState 初始化
- ❌ RetryBoundary → 缺少 retry_with_backoff 包裝
- ✅ WriteReportPlan → 生成研究計劃
- ✅ GenerateSearchQueries → 生成查詢
- ✅ ExecuteSearchTasks → 執行搜索
- ✅ WriteFinalReport → 生成報告
- ❌ ErrorHandling → 缺少 ErrorClassifier 使用
- ❌ WorkflowComplete/Failed → 缺少狀態記錄

### 當前實現問題:
1. 沒有使用 AgentRuntime 的 WorkflowState
2. 沒有 retry_with_backoff 包裝
3. 沒有使用 ErrorClassifier

### 修正建議:
```python
from core.errors import retry_with_backoff, ErrorClassifier

class DeepResearchProcessor(BaseProcessor):

    @retry_with_backoff(max_retries=2, base_delay=1.0)
    async def process(self, context: ProcessingContext) -> str:
        # Step 1: Init Workflow
        workflow_state = {
            "status": "running",
            "steps": ["plan", "search", "synthesize"],
            "current_step": None,
            "errors": []
        }
        context.intermediate_results["workflow_state"] = workflow_state

        try:
            # Step 2: 執行研究流程
            workflow_state["current_step"] = "plan"
            report_plan = await self._write_report_plan(context)

            workflow_state["current_step"] = "search"
            # [迭代搜索邏輯...]

            workflow_state["current_step"] = "synthesize"
            final_report = await self._write_final_report(...)

            # Step 3: Workflow Complete
            workflow_state["status"] = "completed"
            return final_report

        except Exception as e:
            # Step 4: Error Classification
            error_category = ErrorClassifier.classify(e)
            workflow_state["errors"].append({
                "error": str(e),
                "category": error_category,
                "step": workflow_state["current_step"]
            })

            if error_category in ["NETWORK", "LLM"]:
                raise  # Will be retried by decorator
            else:
                workflow_state["status"] = "failed"
                raise
```

---

## 7. 缺失的 Prompt 整合

### 未使用但應該使用的 Prompts:

1. **DeepResearchProcessor**:
   - ✅ `get_system_question_prompt` - 已在優化中加入
   - ✅ `get_review_prompt` - 已在優化中加入

2. **SearchProcessor 可選增強**:
   - `get_query_result_prompt` - 用於處理單個查詢結果

3. **所有處理器**:
   - `get_guidelines_prompt` - 可嵌入其他 prompts 中

---

## 總結與行動計劃

### 必須修正 (P0):
1. **ChatProcessor** - 加入快取機制
2. **KnowledgeProcessor** - 加入快取機制
3. **DeepResearchProcessor** - 加入 WorkflowState 和 retry 機制

### 建議增強 (P1):
1. 統一錯誤處理模式
2. 加強性能監控
3. 完善日誌記錄

### 驗證狀態:
- ✅ 完全符合: ThinkingProcessor, SearchProcessor, CodeProcessor
- ⚠️ 需要修正: ChatProcessor, KnowledgeProcessor
- ⚠️ 需要重構: DeepResearchProcessor (Agent 層級特性)

## 實施優先級

1. **立即執行**: 修正 System 1 處理器的快取機制
2. **短期計劃**: 完善 DeepResearchProcessor 的 Agent 特性
3. **長期優化**: 統一所有處理器的錯誤處理和監控