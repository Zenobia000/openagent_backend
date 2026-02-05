"""
總機 Agent（Dispatcher）

負責：
1. 分析用戶需求
2. 智能判斷：簡單查詢直接 RAG，複雜任務啟動多 Agent
3. 拆解為子任務
4. 分配給專業 Agent
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import time

from .base import BaseAgent, AgentType, AgentTask, AgentResult

logger = logging.getLogger(__name__)


@dataclass
class TaskPlan:
    """任務計劃"""
    original_request: str
    analysis: str
    is_simple_query: bool = False  # 是否為簡單查詢（直接 RAG）
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    usage: Dict[str, Any] = field(default_factory=dict)  # Token 使用量
    # subtask format: {"id": "1", "agent": "researcher", "task": "...", "depends_on": []}


class DispatcherAgent(BaseAgent):
    """
    總機 Agent
    
    智能判斷問題類型：
    - 簡單查詢：直接使用 RAG 搜尋知識庫
    - 複雜任務：多 Agent 協作
    """
    
    def __init__(self):
        super().__init__(AgentType.DISPATCHER, "Dispatcher")
        self.model = "gpt-4o"  # 總機使用較強的模型
    
    @property
    def system_prompt(self) -> str:
        return """你是一個智能任務調度系統的總機 Agent。

你的核心職責是：**判斷問題類型，選擇最高效的處理方式**

## 口語化理解（非常重要！）

用戶經常使用口語化的表達，你需要理解其真正意圖：

**「這篇」「這個」「這份」** → 指用戶選中的文件（在 context.selected_docs 中）
**「整理」「總結」「摘要」** → 對文件內容進行歸納整理
**「講什麼」「在說什麼」「主要內容」** → 詢問文件的主題和重點
**「有沒有提到」「講到...嗎」** → 搜尋特定內容
**「幫我看看」「幫我查」** → 搜尋並分析

## 🌐 網路搜尋判斷（重要！）

**當用戶明確要求網路資訊時，必須使用 web_search 而不是 rag_search：**

觸發關鍵詞：
- 「網路上」「線上」「互聯網」「網上」
- 「最新的」「最近的」「今天的」「即時」
- 「新聞」「動態」「趨勢」
- 「搜尋網路」「上網查」「Google」

範例：
- "給我網路上關於 XX 的資訊" → 使用 web_search
- "這篇論文在網路上的評價如何" → 使用 web_search
- "最新的 AI 發展趨勢" → 使用 web_search
- "幫我查查這篇論文講什麼" → 使用 rag_search（查本地文件）

## 問題分類

**簡單查詢**（只需要搜尋知識庫，is_simple_query=true）：
- 詢問文件內容："這篇文章在講什麼"、"有沒有提到 XX"
- 事實性問題："XX 的定義是什麼"、"這個數據是多少"
- 簡單摘要："幫我總結這份文件"、"整理這篇論文"

**網路搜尋**（需要搜尋網路，is_simple_query=true，但指定 use_web_search=true）：
- 網路資訊："網路上關於 XX 的資訊"、"線上評價"
- 最新資訊："最新的 XX"、"今天的新聞"

**複雜任務**（需要多步驟協作，is_simple_query=false）：
- 研究 + 寫作："研究 XX 趨勢並寫一份報告"
- 分析 + 建議："分析數據並給出改進建議"
- **程式 + 計算**："計算 XX"、"用 Python 計算"、"畫出圖表"、"繪製趨勢圖"
- 程式 + 測試："寫一個演算法並測試"
- 多來源整合："比較 A 和 B 的優缺點"

**特別注意**：當用戶要求「計算」、「用 Python」、「畫圖」、「繪製」時，必須分配給 **coder** agent！

## 可用的專業 Agent

- **researcher**: 研究者 - 搜尋知識庫(RAG)、**網路搜尋(web_search)**、整理信息
- **writer**: 寫作者 - 撰寫文章、報告、文檔
- **coder**: 編碼者 - 編寫程式碼、執行測試
- **analyst**: 分析師 - 數據分析、統計計算
- **reviewer**: 審核者 - 審核品質、改進建議

## 輸出格式（JSON）

簡單查詢（本地 RAG）：
{
  "analysis": "用戶想要了解選中文件的內容",
  "is_simple_query": true,
  "subtasks": [
    {
      "id": "1",
      "agent": "researcher",
      "task": "搜尋並整理文件內容",
      "description": "搜尋知識庫中的相關內容並進行整理摘要",
      "use_web_search": false,
      "depends_on": []
    }
  ]
}

網路搜尋：
{
  "analysis": "用戶想要獲取網路上的相關資訊",
  "is_simple_query": true,
  "subtasks": [
    {
      "id": "1",
      "agent": "researcher",
      "task": "搜尋網路資訊",
      "description": "使用 web_search 搜尋網路上的相關資訊並整理",
      "use_web_search": true,
      "search_query": "CLIP 論文 評價 影響",
      "depends_on": []
    }
  ]
}

## 重要原則

1. **理解口語**：用戶說「這篇」就是指 selected_docs 中的文件
2. **區分搜尋來源**：「網路上」→ web_search，「文件中」→ rag_search
3. **效率優先**：能用 RAG 直接解決的，設置 is_simple_query=true
4. **不要追問**：如果用戶已選中文件並說「整理這篇」，直接執行，不要要求更多細節
5. **任務精簡**：不要過度拆分，2-4 個步驟最佳
"""
    
    async def analyze_request(self, user_request: str, context: Dict = None) -> TaskPlan:
        """
        分析用戶請求，生成任務計劃
        
        Args:
            user_request: 用戶請求
            context: 上下文（如選中的文件、知識庫等）
            
        Returns:
            任務計劃
        """
        prompt = f"""用戶請求：{user_request}

{"上下文：" + json.dumps(context, ensure_ascii=False) if context else ""}

請分析這個請求：
1. 判斷是「簡單查詢」還是「複雜任務」
2. 如果是簡單查詢，設置 is_simple_query=true，只分配給 researcher
3. 如果是複雜任務，拆解為多個子任務

輸出 JSON 格式。"""

        result = await self.think(prompt, use_tools=False)
        usage = result.get("usage", {})
        
        try:
            # 解析 JSON
            answer = result.get("answer", "")
            # 提取 JSON
            if "```json" in answer:
                json_str = answer.split("```json")[1].split("```")[0]
            elif "```" in answer:
                json_str = answer.split("```")[1].split("```")[0]
            else:
                json_str = answer
            
            plan_data = json.loads(json_str.strip())
            
            return TaskPlan(
                original_request=user_request,
                analysis=plan_data.get("analysis", ""),
                is_simple_query=plan_data.get("is_simple_query", False),
                subtasks=plan_data.get("subtasks", []),
                usage=usage
            )
        except Exception as e:
            logger.error(f"Failed to parse task plan: {e}")
            # 預設為簡單查詢
            return TaskPlan(
                original_request=user_request,
                analysis="預設為知識查詢",
                is_simple_query=True,
                subtasks=[{
                    "id": "1",
                    "agent": "researcher",
                    "task": "搜尋知識庫",
                    "description": user_request,
                    "depends_on": []
                }],
                usage=usage
            )
    
    async def process_task(self, task: AgentTask) -> AgentResult:
        """處理任務（生成任務計劃）"""
        start_time = time.time()
        
        user_request = task.parameters.get("request", "")
        context = task.context
        
        plan = await self.analyze_request(user_request, context)
        
        return AgentResult(
            task_id=task.id,
            agent_type=self.type.value,
            success=len(plan.subtasks) > 0,
            output={
                "analysis": plan.analysis,
                "is_simple_query": plan.is_simple_query,
                "subtasks": plan.subtasks,
                "total_steps": len(plan.subtasks)
            },
            thinking=plan.analysis,
            execution_time=time.time() - start_time,
            usage=plan.usage
        )
