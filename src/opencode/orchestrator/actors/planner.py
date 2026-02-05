"""
Planner Actor - 任務規劃器
將用戶意圖分解為可執行的任務序列
"""

from typing import Dict, Any, Optional, List
import asyncio
import json
import logging
import os
from pathlib import Path

# 使用統一的路徑工具載入環境變數
from opencode.core.utils import load_env, get_project_root
load_env()

from opencode.orchestrator.actors.base import Actor, ActorMessage
from opencode.core.protocols import Task, Intent

logger = logging.getLogger(__name__)


class PlannerActor(Actor):
    """
    規劃 Actor
    
    職責:
    - 分析用戶意圖
    - 選擇合適的工具
    - 建立任務執行計畫
    - 處理任務依賴關係
    """
    
    def __init__(self, name: str = "planner", config: Optional[Dict[str, Any]] = None):
        super().__init__(name=name, config=config)
        
        self.llm_client = None
        self.model = config.get("model", "gpt-4o") if config else "gpt-4o"
        
        # 可用工具定義
        self.available_tools = {
            "rag_search": {
                "service": "knowledge_base",
                "description": "在知識庫中進行語意搜尋",
                "parameters": ["query", "top_k"]
            },
            "rag_search_multiple": {
                "service": "knowledge_base", 
                "description": "用多個查詢搜尋知識庫",
                "parameters": ["queries", "top_k"]
            },
            "rag_ask": {
                "service": "knowledge_base",
                "description": "向知識庫提問並獲得 AI 回答",
                "parameters": ["question", "top_k"]
            },
            "web_search": {
                "service": "web_search",
                "description": "搜尋網路獲取最新資訊，適合查詢知識庫沒有的內容",
                "parameters": ["query", "max_results"]
            },
            "web_search_summarize": {
                "service": "web_search",
                "description": "搜尋網路並自動摘要結果",
                "parameters": ["query", "max_results"]
            },
            "sandbox_execute_python": {
                "service": "sandbox",
                "description": "安全執行 Python 程式碼，支援 numpy, pandas, matplotlib 等套件",
                "parameters": ["code", "timeout"]
            },
            "execute_python": {
                "service": "sandbox",
                "description": "執行 Python 程式碼",
                "parameters": ["code", "timeout"]
            },
            "execute_bash": {
                "service": "sandbox",
                "description": "執行 Bash 命令",
                "parameters": ["command"]
            },
            "git_clone": {
                "service": "repo_ops",
                "description": "Clone Git 倉庫到本地",
                "parameters": ["url", "path", "branch"]
            },
            "git_status": {
                "service": "repo_ops",
                "description": "查看 Git 倉庫狀態",
                "parameters": ["path"]
            },
            "git_commit": {
                "service": "repo_ops",
                "description": "提交變更到 Git",
                "parameters": ["path", "message", "files"]
            },
            "git_push": {
                "service": "repo_ops",
                "description": "推送變更到遠端",
                "parameters": ["path", "remote", "branch"]
            },
            "git_pull": {
                "service": "repo_ops",
                "description": "從遠端拉取更新",
                "parameters": ["path", "remote", "branch"]
            },
            "git_log": {
                "service": "repo_ops",
                "description": "查看 Git 提交歷史",
                "parameters": ["path", "limit"]
            },
            "git_diff": {
                "service": "repo_ops",
                "description": "查看 Git 差異",
                "parameters": ["path", "cached"]
            }
        }
        
        self.planning_prompt = """你是一個專業的智能任務規劃器，負責理解用戶的口語化問題並將其轉換為精確的任務序列。

## 你的核心能力

### 1. 語意理解
- 理解口語化、模糊的問題表達
- 識別用戶真正想要知道什麼
- 從上下文推斷隱含的需求

### 2. 問題拆解
- 將複雜問題拆解為多個子問題
- 為每個子問題生成精確的搜尋查詢
- 確保查詢覆蓋問題的各個面向

### 3. 查詢優化
- 將口語化表達轉換為精確的關鍵詞
- 生成多種角度的查詢以確保召回率
- 使用同義詞和相關術語擴展查詢

## 可用工具

{tools}

### 工具說明

#### 知識庫工具 (搜尋已上傳的文件)
- **rag_search_multiple**: 多角度搜尋知識庫，適合複雜問題
- **rag_ask**: 直接問答，適合簡單問題

#### 網路搜尋工具 (搜尋網路最新資訊)
- **web_search**: 搜尋網路，適合查詢知識庫沒有的資訊、最新消息、外部知識
- **web_search_summarize**: 搜尋網路並自動摘要結果

#### 程式碼執行工具 (sandbox_execute_python)
- 支援 numpy, pandas, matplotlib, scipy, sklearn 等套件
- 適用於：數學計算、數據分析、生成圖表、處理數據
- 將結果存入 `result` 變數會自動返回
- matplotlib 圖表會自動捕獲

#### Git 操作工具
- **git_clone**: Clone 遠端倉庫到本地
- **git_status**: 查看倉庫狀態
- **git_log**: 查看提交歷史
- **git_diff**: 查看檔案差異
- **git_commit**: 提交變更
- **git_push/git_pull**: 推送/拉取

## 口語化問題轉換範例

用戶說: "這篇論文講了什麼"
→ 拆解為:
  - 搜尋 "主要研究內容 主題 背景"
  - 搜尋 "研究方法 技術方案"
  - 搜尋 "主要貢獻 結論 結果"

用戶說: "CLIP 是怎麼訓練的"
→ 拆解為:
  - 搜尋 "CLIP training method 訓練方法"
  - 搜尋 "contrastive learning loss function 對比學習"
  - 搜尋 "dataset training data 訓練數據"

用戶說: "這個技術有什麼優缺點"
→ 拆解為:
  - 搜尋 "advantages benefits 優點 優勢"
  - 搜尋 "limitations disadvantages 缺點 限制"
  - 搜尋 "comparison benchmark 比較 性能"

用戶說: "幫我計算 1+1" 或 "用 Python 算..."
→ 使用 sandbox_execute_python 執行程式碼

用戶說: "畫一個圖表" 或 "用 matplotlib..."
→ 使用 sandbox_execute_python 生成圖表

用戶說: "最近 AI 有什麼新聞" 或 "OpenAI 最新動態"
→ 使用 web_search 搜尋網路

用戶說: "搜尋一下 xxx 是什麼" (且知識庫沒有相關文件)
→ 使用 web_search 搜尋網路

用戶說: "clone 這個 repo" 或 "下載這個專案"
→ 使用 git_clone

用戶說: "看一下 git 狀態" 或 "有什麼變更"
→ 使用 git_status

## 重要規則

1. **始終生成多個查詢**: 對於知識庫問題，至少生成 2-3 個不同角度的搜尋查詢
2. **使用 rag_search_multiple**: 當需要多角度搜尋時，使用此工具傳入多個 queries
3. **使用 rag_ask**: 當用戶需要綜合回答時（如總結、比較、解釋）
4. **使用 sandbox_execute_python**: 當用戶需要計算、分析數據、生成圖表時
5. **使用 web_search**: 當問題與知識庫無關、需要最新資訊、或明確要求搜尋網路時
6. **使用 git_* 工具**: 當用戶需要操作 Git 倉庫時
7. **查詢要具體**: 避免太模糊的查詢，加入具體的關鍵詞
8. **中英混合**: 對於技術問題，同時使用中英文關鍵詞

## 輸出格式

請以 JSON 格式返回計畫：
{{
    "analysis": "對用戶意圖的深入分析",
    "sub_questions": ["拆解出的子問題1", "子問題2", ...],
    "tasks": [
        {{
            "id": "task_1",
            "tool": "工具名稱 (rag_search_multiple/rag_ask/sandbox_execute_python)",
            "parameters": {{
                "queries": ["查詢1", "查詢2"],  // for rag_search_multiple
                "question": "問題",              // for rag_ask
                "code": "python 代碼",           // for sandbox_execute_python
                "top_k": 5
            }},
            "dependencies": [],
            "description": "任務說明"
        }}
    ],
    "reasoning": "為什麼這樣規劃"
}}

## 特殊情況

- 如果問題簡單直接，可以只用一個 rag_ask
- 如果用戶明確指定了文件，確保 filters 正確傳遞
- 如果用戶要求計算或分析，使用 sandbox_execute_python
- 對於完全不相關的問題（如閒聊），返回空 tasks 並在 analysis 中友好回應"""
    
    async def on_start(self) -> None:
        """初始化 LLM 客戶端"""
        try:
            # 確保 .env 已載入
            load_env()
            
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.llm_client = AsyncOpenAI(api_key=api_key)
                logger.info("Planner LLM client initialized")
            else:
                logger.error("OPENAI_API_KEY not set for Planner")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
    
    async def handle_message(self, message: ActorMessage) -> Optional[Any]:
        """處理訊息"""
        content = message.content
        msg_type = content.get("type")
        
        if msg_type == "create_plan":
            intent = content.get("intent", {})
            plan = await self.create_plan(intent)
            
            # 回傳計畫給 parent (Orchestrator)
            if self.parent:
                await self.tell(self.parent, {
                    "type": "plan",
                    "plan": plan
                }, message.correlation_id)
            
            return plan
        
        return None
    
    async def create_plan(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        建立執行計畫
        
        Args:
            intent_data: 意圖資料
            
        Returns:
            執行計畫
        """
        user_content = intent_data.get("content", "")
        context = intent_data.get("context", {})
        
        # 取得 selected_docs 和 attachments
        metadata = context.get("metadata", {})
        selected_docs = metadata.get("selected_docs", [])
        attachments = metadata.get("attachments", [])  # 多模態附件
        
        logger.info(f"📋 ====== 開始規劃 ======")
        logger.info(f"📋 用戶輸入: {user_content[:100]}...")
        logger.info(f"📋 選定文件: {selected_docs}")
        logger.info(f"📋 附件數量: {len(attachments) if attachments else 0}")
        logger.info(f"📋 LLM 可用: {self.llm_client is not None}")
        
        # 檢查是否有圖片附件 - 需要特殊處理
        has_images = attachments and any(a.get('type') == 'image' for a in attachments)
        has_files = attachments and any(a.get('type') == 'file' for a in attachments)
        
        if has_images:
            logger.info(f"📋 檢測到圖片附件，將使用 Vision 模式")
            # 對於圖片，返回一個特殊的 vision_analysis 計畫
            return {
                "analysis": "用戶上傳了圖片，需要進行圖片分析",
                "is_simple": False,
                "needs_vision": True,
                "tasks": [{
                    "id": "task_vision",
                    "tool": "vision_analysis",
                    "service": "vision",
                    "description": "分析用戶上傳的圖片",
                    "parameters": {
                        "query": user_content,
                        "images": [a for a in attachments if a.get('type') == 'image']
                    },
                    "dependencies": []
                }]
            }
        
        if has_files:
            logger.info(f"📋 檢測到檔案附件，將提取內容後分析")
            # 對於檔案，返回 file_analysis 計畫
            return {
                "analysis": "用戶上傳了檔案，需要提取內容進行分析",
                "is_simple": False,
                "needs_file_analysis": True,
                "tasks": [{
                    "id": "task_file_analysis",
                    "tool": "file_analysis",
                    "service": "file",
                    "description": "分析用戶上傳的檔案",
                    "parameters": {
                        "query": user_content,
                        "files": [a for a in attachments if a.get('type') == 'file']
                    },
                    "dependencies": []
                }]
            }
        
        # 建構工具說明
        tools_desc = "\n".join([
            f"- {name}: {info['description']} (參數: {', '.join(info['parameters'])})"
            for name, info in self.available_tools.items()
        ])
        
        # 建構提示
        prompt = self.planning_prompt.format(tools=tools_desc)
        
        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"用戶意圖: {user_content}"}
        ]
        
        # 加入對話歷史 (如果有)
        conversation_history = context.get("conversation_history", [])
        if conversation_history:
            history_text = "\n".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in conversation_history[-5:]  # 最近 5 條
            ])
            messages[1]["content"] += f"\n\n最近對話:\n{history_text}"
        
        try:
            if self.llm_client is None:
                logger.info(f"📋 使用簡單規劃（無 LLM）")
                plan = self._simple_plan(user_content, selected_docs)
                logger.info(f"📋 簡單規劃結果: {len(plan.get('tasks', []))} 個任務")
                for task in plan.get('tasks', []):
                    logger.info(f"  - {task.get('tool')}: {task.get('description')}")
                    logger.info(f"    參數: {task.get('parameters')}")
                return plan
            
            # 呼叫 LLM
            logger.info(f"📋 呼叫 LLM 進行規劃...")
            response = await self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            # 記錄成本
            try:
                from opencode.control_plane.cost import get_cost_service, CostType
                cost_service = get_cost_service()
                usage = response.usage
                if usage:
                    cost_service.record_usage(
                        model=self.model,
                        cost_type=CostType.LLM_INPUT,
                        input_tokens=usage.prompt_tokens,
                        output_tokens=usage.completion_tokens,
                        action="planning"
                    )
            except Exception as cost_err:
                logger.warning(f"Cost tracking failed: {cost_err}")
            
            plan_json = json.loads(response.choices[0].message.content)
            logger.info(f"📋 LLM 回應: {json.dumps(plan_json, ensure_ascii=False)[:200]}...")
            
            # 驗證和補充計畫（傳入 selected_docs）
            plan = self._validate_and_enrich_plan(plan_json, selected_docs)
            
            logger.info(f"📋 最終計畫: {len(plan.get('tasks', []))} 個任務")
            for task in plan.get('tasks', []):
                logger.info(f"  - {task.get('tool')}: {task.get('description')}")
                logger.info(f"    參數: {task.get('parameters')}")
            return plan
            
        except Exception as e:
            logger.error(f"❌ Planning error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 回退到簡單規劃
            return self._simple_plan(user_content, selected_docs)
    
    def _simple_plan(self, user_content: str, selected_docs: list = None) -> Dict[str, Any]:
        """
        智能簡單規劃 (當 LLM 不可用時)
        
        支持：
        - 口語化問題理解
        - 自動生成多角度查詢
        - 多文件查詢
        """
        content_lower = user_content.lower()
        tasks = []
        
        # 建構 filters（如果有選定文件）
        filters = None
        if selected_docs and len(selected_docs) > 0:
            filters = {"file_name": selected_docs}
        
        # 口語化關鍵詞映射
        query_expansions = {
            # 論文/文件理解
            "講了什麼": ["主要內容 研究主題 背景介紹", "研究方法 技術方案", "主要貢獻 結論 結果"],
            "是什麼": ["定義 概念 介紹", "原理 機制 方法"],
            "研究了什麼": ["研究目標 研究問題", "研究方法 實驗設計", "研究結果 發現"],
            "怎麼做": ["方法 步驟 流程", "實現 技術 算法"],
            "訓練": ["training method 訓練方法", "loss function 損失函數", "dataset 數據集"],
            "優缺點": ["advantages 優點 優勢", "limitations 缺點 限制", "comparison 比較"],
            "效果": ["performance 性能", "results 結果 效果", "benchmark 評估"],
            "創新": ["contribution 貢獻 創新", "novel 新穎 改進"],
            "應用": ["application 應用 場景", "use case 用途"],
        }
        
        # 檢測是否需要多查詢
        queries = []
        matched_pattern = None
        
        for pattern, expansions in query_expansions.items():
            if pattern in content_lower:
                matched_pattern = pattern
                # 生成多角度查詢
                base_terms = user_content.replace(pattern, "").strip()
                for expansion in expansions:
                    if base_terms:
                        queries.append(f"{base_terms} {expansion}")
                    else:
                        queries.append(expansion)
                break
        
        # 如果沒有匹配到模式，使用原始問題生成多查詢
        if not queries:
            # 提取關鍵詞並生成變體
            keywords = [w for w in user_content.split() if len(w) > 1]
            queries = [user_content]  # 原始問題
            if len(keywords) > 0:
                queries.append(" ".join(keywords))  # 僅關鍵詞
            # 加入英文關鍵詞（如果有中文）
            if any('\u4e00' <= c <= '\u9fff' for c in user_content):
                queries.append(user_content)  # 保持原文
        
        # 確保至少有查詢
        if not queries:
            queries = [user_content]
        
        # 判斷使用哪個工具
        is_question = any(kw in content_lower for kw in ["什麼", "如何", "為什麼", "怎麼", "?", "？", "嗎", "呢", "告訴我", "請問", "解釋"])
        is_search = any(kw in content_lower for kw in ["搜尋", "找", "查詢", "search", "find", "列出"])
        is_bash = any(kw in content_lower for kw in ["執行", "run", "bash", "shell", "命令"])
        is_python = any(kw in content_lower for kw in ["python", "程式碼", "code"])
        
        if is_bash:
            command = user_content.split("執行")[-1].strip() if "執行" in user_content else user_content
            tasks.append({
                "id": "task_1",
                "tool": "execute_bash",
                "parameters": {"command": command},
                "dependencies": [],
                "description": "執行命令"
            })
        elif is_python:
            tasks.append({
                "id": "task_1",
                "tool": "execute_python",
                "parameters": {"code": user_content},
                "dependencies": [],
                "description": "執行 Python 程式"
            })
        elif is_search:
            # 純搜尋 - 使用多查詢
            tasks.append({
                "id": "task_1",
                "tool": "rag_search_multiple",
                "parameters": {"queries": queries[:3], "top_k": 5, "filters": filters},
                "dependencies": [],
                "description": "多角度搜尋知識庫"
            })
        else:
            # 問答模式 - 先搜尋再回答
            if len(queries) > 1:
                # 多查詢搜尋
                tasks.append({
                    "id": "task_1",
                    "tool": "rag_search_multiple",
                    "parameters": {"queries": queries[:3], "top_k": 5, "filters": filters},
                    "dependencies": [],
                    "description": "多角度搜尋相關內容"
                })
            # 然後用 rag_ask 生成回答
            tasks.append({
                "id": "task_2" if len(queries) > 1 else "task_1",
                "tool": "rag_ask",
                "parameters": {"question": user_content, "top_k": 8, "filters": filters},
                "dependencies": ["task_1"] if len(queries) > 1 else [],
                "description": "根據搜尋結果生成回答"
            })
        
        return {
            "analysis": f"智能分析用戶意圖，生成 {len(queries)} 個查詢角度",
            "sub_questions": queries,
            "tasks": tasks,
            "execution_order": [t["id"] for t in tasks],
            "reasoning": "基於口語化理解的智能規劃"
        }
    
    def _validate_and_enrich_plan(self, plan: Dict[str, Any], selected_docs: list = None) -> Dict[str, Any]:
        """驗證和豐富計畫"""
        tasks = plan.get("tasks", [])
        
        # 建構 filters（如果有選定文件）
        filters = None
        if selected_docs and len(selected_docs) > 0:
            filters = {"file_name": selected_docs}
        
        # 確保每個任務有必要欄位
        for i, task in enumerate(tasks):
            if "id" not in task:
                task["id"] = f"task_{i+1}"
            if "dependencies" not in task:
                task["dependencies"] = []
            if "description" not in task:
                task["description"] = f"執行 {task.get('tool', 'unknown')}"
            
            # 驗證工具是否存在
            tool = task.get("tool")
            if tool and tool in self.available_tools:
                task["service"] = self.available_tools[tool]["service"]
            
            # 為 RAG 搜尋任務加入 filters
            if tool in ["rag_search", "rag_ask", "rag_search_multiple"] and filters:
                if "parameters" not in task:
                    task["parameters"] = {}
                task["parameters"]["filters"] = filters
        
        # 計算執行順序
        if "execution_order" not in plan:
            plan["execution_order"] = self._calculate_execution_order(tasks)
        
        return plan
    
    def _calculate_execution_order(self, tasks: List[Dict]) -> List[str]:
        """計算任務執行順序 (拓撲排序)"""
        if not tasks:
            return []
        
        task_map = {t["id"]: t for t in tasks}
        result = []
        remaining = set(task_map.keys())
        
        while remaining:
            # 找出沒有未完成依賴的任務
            ready = []
            for task_id in remaining:
                task = task_map[task_id]
                deps = set(task.get("dependencies", []))
                if not deps.intersection(remaining):
                    ready.append(task_id)
            
            if not ready:
                # 可能有循環依賴，強制取第一個
                ready = [list(remaining)[0]]
            
            for task_id in ready:
                result.append(task_id)
                remaining.remove(task_id)
        
        return result
