"""
Deep Research Service - 深度研究服務
支援自動子問題生成、多輪搜尋、報告整合
"""

import os
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path

# 使用統一的路徑工具載入環境變數
from core.utils import load_env, get_project_root
from core.prompts import PromptTemplates
load_env()

logger = logging.getLogger(__name__)


class ResearchStatus(Enum):
    """研究狀態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ResearchStep:
    """研究步驟"""
    step: str
    status: str = "pending"  # pending, running, done, error
    result: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class ResearchTask:
    """研究任務"""
    id: str
    topic: str
    documents: Optional[List[str]] = None
    status: ResearchStatus = ResearchStatus.PENDING
    progress: int = 0
    steps: List[ResearchStep] = field(default_factory=list)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    report: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "documents": self.documents,
            "status": self.status.value,
            "progress": self.progress,
            "steps": [
                {
                    "step": s.step,
                    "status": s.status,
                    "result": s.result,
                    "error": s.error
                }
                for s in self.steps
            ],
            "findings_count": len(self.findings),
            "sources_count": len(self.sources),
            "report": self.report,
            "error": self.error,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "completed_at": datetime.fromtimestamp(self.completed_at).isoformat() if self.completed_at else None
        }


class ResearchService:
    """深度研究服務"""
    
    def __init__(self):
        self.tasks: Dict[str, ResearchTask] = {}
        self._openai_client = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化服務"""
        if self._initialized:
            return
        
        try:
            # 強制重新載入 .env（確保環境變數可用）
            load_env()
            
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._openai_client = OpenAI(api_key=api_key)
                self._initialized = True
                logger.info("✅ ResearchService initialized")
            else:
                logger.warning("⚠️ OPENAI_API_KEY not set, ResearchService limited")
        except Exception as e:
            logger.error(f"❌ ResearchService init failed: {e}")
    
    async def start_research(
        self,
        topic: str,
        documents: Optional[List[str]] = None
    ) -> str:
        """
        啟動深度研究任務
        
        Args:
            topic: 研究主題
            documents: 限定文件列表
            
        Returns:
            task_id
        """
        task_id = f"research_{int(time.time() * 1000)}"
        
        task = ResearchTask(
            id=task_id,
            topic=topic,
            documents=documents
        )
        
        self.tasks[task_id] = task
        
        # 背景執行研究
        asyncio.create_task(self._run_research(task_id))
        
        return task_id
    
    async def get_task(self, task_id: str) -> Optional[ResearchTask]:
        """取得研究任務"""
        return self.tasks.get(task_id)
    
    async def list_tasks(self) -> List[Dict[str, Any]]:
        """列出所有研究任務"""
        return [
            {
                "task_id": tid,
                "topic": task.topic,
                "status": task.status.value,
                "progress": task.progress,
                "created_at": datetime.fromtimestamp(task.created_at).isoformat()
            }
            for tid, task in self.tasks.items()
        ]
    
    async def _run_research(self, task_id: str) -> None:
        """執行深度研究"""
        task = self.tasks.get(task_id)
        if not task:
            return
        
        task.status = ResearchStatus.RUNNING
        
        try:
            # Step 1: 分析主題並生成子問題
            task.steps.append(ResearchStep(
                step="🔍 分析研究主題",
                status="running",
                started_at=time.time()
            ))
            task.progress = 5
            
            sub_questions = await self._generate_sub_questions(task.topic)
            
            task.steps[-1].status = "done"
            task.steps[-1].result = f"生成 {len(sub_questions)} 個子問題"
            task.steps[-1].completed_at = time.time()
            task.progress = 15
            
            # Step 2: 對每個子問題進行研究
            progress_per_question = 60 / max(len(sub_questions), 1)
            
            for i, question in enumerate(sub_questions):
                task.steps.append(ResearchStep(
                    step=f"📚 研究: {question[:50]}...",
                    status="running",
                    started_at=time.time()
                ))
                
                # 搜尋相關內容
                search_results = await self._search_for_research(question, task.documents)
                
                # 生成回答
                if search_results:
                    answer = await self._generate_section_answer(question, search_results)
                    
                    task.findings.append({
                        "question": question,
                        "answer": answer,
                        "sources_count": len(search_results)
                    })
                    
                    # 收集來源（去重）
                    for result in search_results:
                        source_key = f"{result.get('source', '')}_{result.get('page', '')}"
                        if not any(
                            f"{s.get('source', '')}_{s.get('page', '')}" == source_key 
                            for s in task.sources
                        ):
                            task.sources.append(result)
                    
                    task.steps[-1].result = f"找到 {len(search_results)} 個相關片段"
                else:
                    task.steps[-1].result = "未找到相關資料"
                
                task.steps[-1].status = "done"
                task.steps[-1].completed_at = time.time()
                task.progress = int(15 + progress_per_question * (i + 1))
                
                # 小延遲避免過度請求
                await asyncio.sleep(0.5)
            
            # Step 2.5: 審查研究進度，決定是否需要更多研究
            if task.findings and self._openai_client:
                task.steps.append(ResearchStep(
                    step="🔍 審查研究進度",
                    status="running",
                    started_at=time.time()
                ))
                task.progress = 75

                need_more_research = await self._review_research_progress(
                    topic=task.topic,
                    findings=task.findings,
                    documents=task.documents
                )

                if need_more_research:
                    task.steps[-1].result = "需要補充研究"
                    task.steps[-1].status = "done"
                    task.steps[-1].completed_at = time.time()

                    # 執行補充研究
                    for additional_query in need_more_research[:2]:  # 限制補充查詢數量
                        task.steps.append(ResearchStep(
                            step=f"🔄 補充研究: {additional_query['query'][:30]}...",
                            status="running",
                            started_at=time.time()
                        ))

                        search_results = await self._search_for_research(
                            additional_query['query'],
                            task.documents
                        )

                        if search_results:
                            answer = await self._generate_section_answer(
                                additional_query['query'],
                                search_results
                            )
                            task.findings.append({
                                "question": additional_query['query'],
                                "answer": answer,
                                "sources_count": len(search_results)
                            })

                        task.steps[-1].status = "done"
                        task.steps[-1].completed_at = time.time()
                else:
                    task.steps[-1].result = "研究資料充足"
                    task.steps[-1].status = "done"
                    task.steps[-1].completed_at = time.time()

            # Step 3: 生成最終報告
            task.steps.append(ResearchStep(
                step="📝 撰寫研究報告",
                status="running",
                started_at=time.time()
            ))
            task.progress = 85
            
            if task.findings:
                report = await self._generate_final_report(task.topic, task.findings)
                task.report = report
                task.steps[-1].result = "報告生成完成"
            else:
                task.report = f"# {task.topic}\n\n未能找到足夠的相關資料來生成報告。"
                task.steps[-1].result = "資料不足，生成基礎報告"
            
            task.steps[-1].status = "done"
            task.steps[-1].completed_at = time.time()
            task.progress = 100
            task.status = ResearchStatus.COMPLETED
            task.completed_at = time.time()
            
            logger.info(f"✅ Research completed: {task_id}")
            
        except Exception as e:
            logger.error(f"❌ Research failed: {e}")
            task.status = ResearchStatus.FAILED
            task.error = str(e)
            if task.steps:
                task.steps[-1].status = "error"
                task.steps[-1].error = str(e)
    
    async def _generate_sub_questions(self, topic: str) -> List[str]:
        """生成子問題 - 使用專業的系統問題 prompt"""
        if not self._openai_client:
            return [topic]  # 無 OpenAI 時直接用原主題

        try:
            # 使用專業的系統問題提示詞
            prompt = PromptTemplates.get_system_question_prompt(topic)

            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            questions = response.choices[0].message.content.strip().split('\n')
            return [
                q.strip().lstrip('0123456789.-•) ')
                for q in questions 
                if q.strip() and len(q.strip()) > 5
            ][:5]  # 最多 5 個
            
        except Exception as e:
            logger.error(f"Generate sub-questions failed: {e}")
            return [topic]
    
    async def _search_for_research(
        self,
        query: str,
        documents: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """執行向量搜尋（使用 Cohere embedding，與 RAG 系統一致）"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            import cohere
            
            # 確保 .env 已載入
            load_env()
            
            # 使用 Cohere embedding（1024 維，與 RAG 系統一致）
            cohere_key = os.getenv("COHERE_API_KEY")
            if not cohere_key:
                logger.error("COHERE_API_KEY not set for search")
                return []
            
            client = QdrantClient(host="localhost", port=6333)
            cohere_client = cohere.Client(cohere_key)
            
            # 生成查詢向量（使用 Cohere）
            embed_response = cohere_client.embed(
                texts=[query],
                model="embed-multilingual-v3.0",
                input_type="search_query"
            )
            query_vector = embed_response.embeddings[0]
            
            # 建立篩選條件
            search_filter = None
            if documents and len(documents) > 0:
                if len(documents) == 1:
                    search_filter = Filter(
                        must=[FieldCondition(key="file_name", match=MatchValue(value=documents[0]))]
                    )
                else:
                    search_filter = Filter(
                        should=[
                            FieldCondition(key="file_name", match=MatchValue(value=f))
                            for f in documents
                        ]
                    )
            
            # 執行搜尋
            results = client.query_points(
                collection_name="rag_knowledge_base",
                query=query_vector,
                query_filter=search_filter,
                limit=5,
                with_payload=True
            )
            
            return [
                {
                    "content": point.payload.get("text", ""),
                    "source": point.payload.get("file_name", ""),
                    "page": point.payload.get("page_label", "1"),
                    "score": point.score
                }
                for point in results.points
            ]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def _generate_section_answer(
        self,
        question: str,
        sources: List[Dict[str, Any]]
    ) -> str:
        """生成單個問題的答案 - 使用專業的搜索結果 prompt"""
        if not self._openai_client:
            return "無法生成答案（OpenAI 未配置）"

        try:
            context = "\n\n".join([
                f"[來源: {s['source']}, 頁碼: {s['page']}]\n{s['content']}"
                for s in sources
            ])

            # 使用專業的搜索結果提示詞
            prompt = PromptTemplates.get_search_result_prompt(
                query=question,
                research_goal="提供詳細、準確的研究發現",
                context=context
            )

            # 加上引用規則
            citation_rules = PromptTemplates.get_citation_rules()
            full_prompt = f"{prompt}\n\n{citation_rules}"

            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Generate answer failed: {e}")
            return f"生成答案時發生錯誤: {str(e)}"
    
    async def _generate_final_report(
        self,
        topic: str,
        findings: List[Dict[str, Any]]
    ) -> str:
        """生成最終報告 - 使用專業的最終報告 prompt"""
        if not self._openai_client:
            # 無 OpenAI 時生成簡單報告
            report = f"# {topic}\n\n## 研究發現\n\n"
            for f in findings:
                report += f"### {f['question']}\n\n{f['answer']}\n\n"
            return report

        try:
            # 準備研究計劃
            plan_prompt = PromptTemplates.get_report_plan_prompt(topic)
            plan_response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": plan_prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            report_plan = plan_response.choices[0].message.content

            # 整理研究發現
            learnings = "\n\n".join([
                f"- {f['question']}：{f['answer'][:200]}..."
                for f in findings
            ])

            # 整理來源
            sources_text = "\n".join([
                f"- [{i+1}] {f.get('source', 'Unknown source')}"
                for i, f in enumerate(findings)
            ])

            # 使用專業的最終報告提示詞
            final_prompt = PromptTemplates.get_final_report_prompt(
                plan=report_plan,
                learnings=learnings,
                sources=sources_text,
                images="",  # 暫時沒有圖片
                requirement="生成詳細、專業的繁體中文研究報告，包含執行摘要、主要發現、詳細分析和建議。"
            )

            # 加上引用、圖片和輸出規則
            references_prompt = PromptTemplates.get_final_report_references_prompt()
            image_prompt = PromptTemplates.get_final_report_citation_image_prompt()
            output_guidelines = PromptTemplates.get_output_guidelines()

            # 組合所有規則
            full_prompt = f"{final_prompt}\n\n{references_prompt}\n\n{image_prompt}\n\n{output_guidelines}"

            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.4,
                max_tokens=3000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Generate report failed: {e}")
            # 失敗時返回簡單報告
            report = f"# {topic}\n\n## 研究發現\n\n"
            for f in findings:
                report += f"### {f['question']}\n\n{f['answer']}\n\n"
            return report

    async def _review_research_progress(
        self,
        topic: str,
        findings: List[Dict[str, Any]],
        documents: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, str]]]:
        """審查研究進度 - 使用專業的審查 prompt"""
        if not self._openai_client:
            return None

        try:
            # 準備計劃
            plan = f"研究主題: {topic}"
            if documents:
                plan += f"\n限定文件: {', '.join(documents)}"

            # 整理已有研究發現
            learnings = "\n\n".join([
                f"Q: {f['question']}\nA: {f['answer'][:200]}..."
                for f in findings
            ])

            # 用戶建議（這裡可以加入用戶輸入）
            suggestion = "請確保涵蓋主題的所有重要方面"

            # 定義 schema
            output_schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "researchGoal": {"type": "string"}
                    }
                }
            }

            # 使用專業的審查 prompt
            review_prompt = PromptTemplates.get_review_prompt(
                plan=plan,
                learnings=learnings,
                suggestion=suggestion,
                output_schema=output_schema
            )

            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": review_prompt}],
                temperature=0.3,
                max_tokens=500
            )

            # 解析 JSON 回應
            import json
            import re
            content = response.choices[0].message.content
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
            if json_match:
                queries = json.loads(json_match.group(1))
                return queries if queries else None
            return None

        except Exception as e:
            logger.error(f"Review research progress failed: {e}")
            return None


# 全域服務實例
_research_service: Optional[ResearchService] = None


async def get_research_service() -> ResearchService:
    """取得研究服務單例"""
    global _research_service
    if _research_service is None:
        _research_service = ResearchService()
        await _research_service.initialize()
    return _research_service
