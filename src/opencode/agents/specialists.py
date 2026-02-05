"""
專業 Agents

各種專業領域的 Agent 實現
"""

import json
import logging
import time
from typing import Dict, List, Any

from .base import BaseAgent, AgentType, AgentTask, AgentResult

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """
    研究者 Agent
    
    負責搜集和分析資料
    可用工具：rag_search, rag_multi_search, web_search, web_fetch, file_read
    """
    
    def __init__(self):
        super().__init__(AgentType.RESEARCHER, "Researcher")
    
    @property
    def system_prompt(self) -> str:
        return """你是一個專業的研究者 Agent。

你的職責是：
1. 根據任務要求搜集相關資料
2. 從知識庫和網路中找到有用的信息
3. 整理和分析搜集到的資料
4. 提供結構化的研究結果

你可以使用以下工具：

**rag_search** - 搜尋本地知識庫中的文檔
  參數：
  - query (string, 必填): 搜尋查詢語句
  - top_k (integer, 可選): 返回結果數量，預設 5
  - file_filter (string, 可選): 限定搜尋的文件名，多個文件用逗號分隔
  範例：{"query": "CLIP 模型架構", "top_k": 5, "file_filter": "paper.pdf"}

**rag_multi_search** - 使用多個查詢搜尋知識庫
  參數：
  - queries (string, 必填): 多個搜尋語句，用 | 分隔
  - top_k (integer, 可選): 每個查詢返回的結果數量，預設 3
  - file_filter (string, 可選): 限定搜尋的文件名
  範例：{"queries": "方法論|實驗結果|結論", "top_k": 3}

**web_search** - 搜尋網路獲取最新資訊（當用戶要求「網路上」「最新」資訊時使用）
  參數：
  - query (string, 必填): 搜尋關鍵詞
  - max_results (integer, 可選): 最大結果數量，預設 5
  範例：{"query": "CLIP 論文 評價 影響力", "max_results": 5}

**web_fetch** - 擷取特定網頁的內容
**file_read** - 讀取文件內容

工作流程：
1. 分析任務需求
2. 判斷是搜尋本地文件(rag_search)還是搜尋網路(web_search)
3. 如果有指定文件（在 file_filter 或 selected_docs），優先搜尋該文件
4. 執行搜尋
5. 整理和分析結果
6. 輸出結構化的研究發現，包含來源引用

重要：
- 如果任務明確要求「網路上」「線上」「最新」的資訊，使用 web_search
- 如果上下文中有 selected_docs 且沒有要求網路搜尋，使用 rag_search
- 請主動使用工具來搜集資料，不要只憑記憶回答
"""
    
    async def process_task(self, task: AgentTask) -> AgentResult:
        """執行研究任務"""
        start_time = time.time()
        tool_calls = []
        
        description = task.description or task.parameters.get("topic", "")
        context = task.context or {}
        
        # 檢查是否需要網路搜尋
        use_web_search = task.parameters.get("use_web_search", False)
        search_query = task.parameters.get("search_query", "")
        
        # 處理選中的文件
        selected_docs = context.get("selected_docs", [])
        
        if use_web_search:
            # 網路搜尋模式
            query = search_query or description
            prompt = f"""研究任務：{description}

請使用 **web_search** 工具搜尋網路上的相關資訊。

搜尋建議關鍵詞：{query}

要求：
1. 使用 web_search 工具搜尋網路
2. 整理搜尋結果，提取關鍵資訊
3. **必須提供資料來源（標題和網址）**
4. 以結構化的方式呈現研究發現

輸出格式：
- 主要發現摘要
- 詳細內容
- 參考來源（列出標題和網址）"""
        else:
            # RAG 本地搜尋模式
            file_filter_hint = ""
            if selected_docs:
                file_filter_str = ",".join(selected_docs)
                file_filter_hint = f"\n\n重要：用戶選擇了以下文件，請使用 file_filter=\"{file_filter_str}\" 來搜尋：\n- " + "\n- ".join(selected_docs)
            
            prompt = f"""研究任務：{description}
{file_filter_hint}

請使用 rag_search 或 rag_multi_search 工具搜集相關資料。
{"記得設置 file_filter 參數為: " + file_filter_str if selected_docs else ""}

搜集完資料後，整理出結構化的研究發現。"""

        result = await self.think(prompt, use_tools=True)
        tool_calls = result.get("tool_calls", [])
        usage = result.get("usage", {})
        
        # 提取來源資訊
        sources = []
        for tc in tool_calls:
            tool_result = tc.get("result", {})
            if tc.get("tool") == "web_search":
                # 網路搜尋結果包含 URL
                web_results = tool_result.get("results", [])
                for wr in web_results:
                    sources.append({
                        "title": wr.get("title", ""),
                        "url": wr.get("url", ""),
                        "snippet": wr.get("snippet", ""),
                        "source_type": "web"
                    })
            else:
                # RAG 結果
                rag_results = tool_result.get("results", [])
                for rr in rag_results:
                    sources.append({
                        "file_name": rr.get("file_name", ""),
                        "text": rr.get("text", "")[:200],
                        "page": rr.get("page_label", ""),
                        "source_type": "rag"
                    })
        
        return AgentResult(
            task_id=task.id,
            agent_type=self.type.value,
            success=True,
            output={
                "research_findings": result.get("answer", ""),
                "sources": sources,
                "search_type": "web" if use_web_search else "rag"
            },
            tool_calls=tool_calls,
            thinking=f"研究主題：{description} (搜尋方式: {'網路' if use_web_search else '知識庫'})",
            execution_time=time.time() - start_time,
            usage=usage
        )


class WriterAgent(BaseAgent):
    """
    寫作者 Agent
    
    負責撰寫各種內容
    可用工具：rag_search, file_read, file_write
    """
    
    def __init__(self):
        super().__init__(AgentType.WRITER, "Writer")
    
    @property
    def system_prompt(self) -> str:
        return """你是一個專業的寫作者 Agent。

你的職責是：
1. 根據提供的資料和要求撰寫內容
2. 確保內容結構清晰、邏輯連貫
3. 根據指定的風格和格式輸出

你可以使用以下工具：
- rag_search: 搜尋參考資料
- file_read: 讀取參考文件
- file_write: 將寫好的內容保存到文件

寫作風格選項：
- professional: 專業正式
- casual: 輕鬆隨意
- academic: 學術論文
- blog: 部落格文章
- email: 電子郵件
- report: 報告

請根據任務要求選擇適當的風格和格式。
"""
    
    async def process_task(self, task: AgentTask) -> AgentResult:
        """執行寫作任務"""
        start_time = time.time()
        tool_calls = []
        
        description = task.description or ""
        style = task.parameters.get("style", "professional")
        context = task.context or {}
        save_to_file = task.parameters.get("save_to_file")
        
        # 如果有前一步的結果，加入上下文
        previous_result = context.get("previous_result", "")
        
        prompt = f"""寫作任務：{description}

風格：{style}

{"參考資料：" + json.dumps(previous_result, ensure_ascii=False) if previous_result else ""}

請根據以上要求撰寫內容。
{"完成後請將內容保存到：" + save_to_file if save_to_file else ""}"""

        result = await self.think(prompt, use_tools=True)
        tool_calls = result.get("tool_calls", [])
        usage = result.get("usage", {})
        
        written_content = result.get("answer", "")
        
        # 如果需要保存到文件
        if save_to_file and written_content:
            save_result = await self.call_tool(
                "file_write",
                file_path=save_to_file,
                content=written_content
            )
            tool_calls.append({
                "tool": "file_write",
                "arguments": {"file_path": save_to_file},
                "result": save_result
            })
        
        return AgentResult(
            task_id=task.id,
            agent_type=self.type.value,
            success=True,
            output={
                "content": written_content,
                "style": style,
                "saved_to": save_to_file
            },
            tool_calls=tool_calls,
            thinking=f"撰寫風格：{style}",
            execution_time=time.time() - start_time,
            usage=usage
        )


class CoderAgent(BaseAgent):
    """
    編碼者 Agent
    
    負責編寫和執行程式碼
    可用工具：code_execute, code_analyze, file_read, file_write
    """
    
    def __init__(self):
        super().__init__(AgentType.CODER, "Coder")
    
    @property
    def system_prompt(self) -> str:
        return """你是一個專業的編碼者 Agent。

你的職責是：
1. 根據需求編寫程式碼
2. 執行和測試程式碼
3. 分析和優化現有程式碼
4. 解決程式相關問題

你可以使用以下工具：
- code_execute: 在沙箱中執行程式碼（Python）
- code_analyze: 分析程式碼品質
- file_read: 讀取程式碼文件
- file_write: 保存程式碼

重要：當用戶需要計算或生成圖表時，必須使用 code_execute 工具執行代碼！
不要只是輸出代碼，要實際執行它。

工作流程：
1. 理解需求
2. 編寫程式碼
3. 使用 code_execute 工具執行
4. 檢查結果，如有錯誤則修復
5. 輸出最終結果和圖表
"""
    
    async def process_task(self, task: AgentTask) -> AgentResult:
        """執行編碼任務"""
        start_time = time.time()
        tool_calls = []
        
        description = task.description or task.parameters.get("requirement", "")
        language = task.parameters.get("language", "python")
        context = task.context or {}
        
        logger.info(f"🔧 [CoderAgent] 收到任務: {description[:100]}...")
        
        # 獲取選中的文件路徑
        selected_docs = context.get("selected_docs", [])
        file_path_hint = ""
        if selected_docs:
            # 文件存放在 data/raw/ 目錄
            file_paths = [f"data/raw/{doc}" for doc in selected_docs]
            file_path_hint = f"""
重要：用戶選擇了以下文件，請使用完整路徑：
{chr(10).join(f'- {fp}' for fp in file_paths)}

例如讀取 Excel：
```python
import pandas as pd
df = pd.read_excel("{file_paths[0]}")
```
"""
        
        # 先讓 LLM 生成代碼
        prompt = f"""編程任務：{description}

程式語言：{language}
{file_path_hint}
{"參考上下文：" + json.dumps({k: v for k, v in context.items() if k != 'attachments'}, ensure_ascii=False) if context else ""}

請：
1. 編寫完整可執行的 Python 程式碼
2. 確保代碼可以直接運行
3. 如果需要生成圖表，使用 matplotlib 並調用 plt.savefig() 或 plt.show()

只輸出代碼，用 ```python 和 ``` 包裹。"""

        result = await self.think(prompt, use_tools=False)
        answer = result.get("answer", "")
        usage = result.get("usage", {})
        
        logger.info(f"🔧 [CoderAgent] LLM 回應長度: {len(answer)}")
        
        # 提取程式碼
        code = ""
        if "```python" in answer:
            code = answer.split("```python")[1].split("```")[0].strip()
        elif "```" in answer:
            code_blocks = answer.split("```")
            if len(code_blocks) > 1:
                code = code_blocks[1].strip()
                if code.startswith("python"):
                    code = code[6:].strip()
        
        logger.info(f"🔧 [CoderAgent] 提取到代碼: {len(code)} 字符")
        
        execution_result = None
        
        # 如果提取到代碼，執行它
        if code:
            logger.info(f"🔧 [CoderAgent] 準備執行代碼:\n{code[:300]}...")
            
            try:
                from opencode.tools import get_tool_registry
                registry = get_tool_registry()
                code_tool = registry.get("code_execute")  # 正確的方法名
                
                logger.info(f"🔧 [CoderAgent] code_execute 工具: {code_tool}")
                
                if code_tool:
                    logger.info(f"🔧 [CoderAgent] 調用 code_execute 工具...")
                    execution_result = await code_tool.execute(
                        code=code,
                        language=language,
                        timeout=60
                    )
                    
                    logger.info(f"🔧 [CoderAgent] 執行結果: {json.dumps(execution_result, ensure_ascii=False, default=str)[:500]}")
                    
                    tool_calls.append({
                        "tool": "code_execute",
                        "arguments": {"code": code, "language": language},
                        "result": execution_result
                    })
                    
                    logger.info(f"🔧 [CoderAgent] 執行結果: success={execution_result.get('success')}")
                    if execution_result.get('figures'):
                        logger.info(f"🔧 [CoderAgent] 生成 {len(execution_result['figures'])} 張圖表")
                    if execution_result.get('stdout'):
                        logger.info(f"🔧 [CoderAgent] stdout: {execution_result['stdout'][:200]}")
                    if execution_result.get('error'):
                        logger.error(f"🔧 [CoderAgent] error: {execution_result['error']}")
                else:
                    logger.warning("⚠️ [CoderAgent] code_execute 工具未找到")
                    logger.info(f"⚠️ [CoderAgent] 可用工具: {registry.list_all()}")
                    
            except Exception as e:
                logger.error(f"❌ [CoderAgent] 執行代碼異常: {e}")
                import traceback
                logger.error(traceback.format_exc())
                execution_result = {"success": False, "error": str(e)}
        else:
            logger.warning("⚠️ [CoderAgent] 沒有提取到代碼")
        
        # 構建輸出
        output = {
            "code": code,
            "language": language,
            "explanation": answer
        }
        
        if execution_result:
            output["execution_result"] = execution_result
            output["success"] = execution_result.get("success", False)
            output["stdout"] = execution_result.get("stdout", "")
            output["figures"] = execution_result.get("figures", [])
            if execution_result.get("error"):
                output["error"] = execution_result["error"]
        
        logger.info(f"🔧 [CoderAgent] 完成，tool_calls 數量: {len(tool_calls)}")
        
        return AgentResult(
            task_id=task.id,
            agent_type=self.type.value,
            success=bool(code),
            output=output,
            tool_calls=tool_calls,
            thinking=f"編程語言：{language}",
            execution_time=time.time() - start_time,
            usage=usage
        )


class AnalystAgent(BaseAgent):
    """
    分析師 Agent
    
    負責數據分析
    可用工具：rag_search, code_execute, file_read
    """
    
    def __init__(self):
        super().__init__(AgentType.ANALYST, "Analyst")
    
    @property
    def system_prompt(self) -> str:
        return """你是一個專業的數據分析師 Agent。

你的職責是：
1. 分析數據和資料
2. 發現趨勢和模式
3. 提供洞察和建議
4. 用程式碼進行統計計算

你可以使用以下工具：
- rag_search: 搜尋相關資料
- rag_multi_search: 多角度搜尋
- code_execute: 執行數據分析程式碼（pandas, numpy 等）
- file_read: 讀取數據文件

請用數據說話，提供具體的分析結果和可視化。
"""
    
    async def process_task(self, task: AgentTask) -> AgentResult:
        """執行分析任務"""
        start_time = time.time()
        tool_calls = []
        
        description = task.description or ""
        context = task.context or {}
        
        # 獲取選中的文件路徑
        selected_docs = context.get("selected_docs", [])
        file_path_hint = ""
        if selected_docs:
            # 文件存放在 data/raw/ 目錄
            file_paths = [f"data/raw/{doc}" for doc in selected_docs]
            file_path_hint = f"""
重要：用戶選擇了以下文件，請使用完整路徑：
{chr(10).join(f'- {fp}' for fp in file_paths)}
"""
        
        prompt = f"""分析任務：{description}
{file_path_hint}
{"數據/上下文：" + json.dumps({k: v for k, v in context.items() if k != 'attachments'}, ensure_ascii=False) if context else ""}

請：
1. 搜集需要的數據
2. 進行分析（必要時使用程式碼）
3. 發現關鍵洞察
4. 提供結論和建議"""

        result = await self.think(prompt, use_tools=True)
        tool_calls = result.get("tool_calls", [])
        usage = result.get("usage", {})
        
        return AgentResult(
            task_id=task.id,
            agent_type=self.type.value,
            success=True,
            output={
                "analysis": result.get("answer", ""),
                "insights": []
            },
            tool_calls=tool_calls,
            thinking="數據分析",
            execution_time=time.time() - start_time,
            usage=usage
        )


class ReviewerAgent(BaseAgent):
    """
    審核者 Agent
    
    負責審核內容品質
    可用工具：rag_search, code_analyze, file_read
    """
    
    def __init__(self):
        super().__init__(AgentType.REVIEWER, "Reviewer")
    
    @property
    def system_prompt(self) -> str:
        return """你是一個專業的審核者 Agent。

你的職責是：
1. 審核內容的品質和準確性
2. 檢查程式碼的問題和改進空間
3. 提供具體的改進建議
4. 給出評分和總結

審核維度：
- 準確性：信息是否正確
- 完整性：是否涵蓋所有要點
- 清晰度：表達是否清楚
- 品質：整體品質如何

請提供：
1. 整體評分（1-10）
2. 優點
3. 問題
4. 改進建議
"""
    
    async def process_task(self, task: AgentTask) -> AgentResult:
        """執行審核任務"""
        start_time = time.time()
        tool_calls = []
        
        description = task.description or ""
        review_type = task.parameters.get("type", "general")
        context = task.context or {}
        content_to_review = context.get("previous_result", context.get("content", ""))
        
        prompt = f"""審核任務：{description}

審核類型：{review_type}

要審核的內容：
{json.dumps(content_to_review, ensure_ascii=False) if isinstance(content_to_review, dict) else content_to_review}

請審核以上內容，提供：
1. 整體評分（1-10）
2. 優點列表
3. 問題列表
4. 改進建議"""

        result = await self.think(prompt, use_tools=True)
        tool_calls = result.get("tool_calls", [])
        usage = result.get("usage", {})
        
        return AgentResult(
            task_id=task.id,
            agent_type=self.type.value,
            success=True,
            output={
                "review": result.get("answer", ""),
                "type": review_type
            },
            tool_calls=tool_calls,
            thinking=f"審核類型：{review_type}",
            execution_time=time.time() - start_time,
            usage=usage
        )
