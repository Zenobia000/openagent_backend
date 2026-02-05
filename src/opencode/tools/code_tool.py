"""
程式碼執行工具

在 Docker 沙箱中安全執行程式碼
"""

import logging
from typing import Dict, List, Any

from .base import BaseTool, ToolDefinition, ToolParameter, ToolCategory

logger = logging.getLogger(__name__)


class CodeExecutorTool(BaseTool):
    """程式碼執行工具"""
    
    def __init__(self):
        super().__init__()
        self._service = None
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="code_execute",
            description="在安全沙箱中執行 Python 或 JavaScript 程式碼。適用於數據分析、計算、或驗證程式邏輯。",
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="要執行的程式碼",
                    required=True
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="程式語言：python 或 javascript",
                    required=False,
                    default="python"
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="執行超時時間（秒）",
                    required=False,
                    default=30
                )
            ],
            returns="執行結果，包含 stdout、stderr 和執行狀態",
            examples=[
                {
                    "code": "print('Hello World')",
                    "language": "python"
                },
                {
                    "code": "import pandas as pd\ndf = pd.DataFrame({'a': [1,2,3]})\nprint(df.describe())",
                    "language": "python"
                }
            ]
        )
    
    async def initialize(self) -> bool:
        try:
            from opencode.services.sandbox.service import SandboxService
            self._service = SandboxService()
            # 確保初始化
            await self._service.initialize()
            self._initialized = True
            logger.info("✅ CodeExecutorTool initialized successfully")
            return True
        except Exception as e:
            logger.error(f"❌ CodeExecutorTool init error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 還是標記為初始化，讓它可以嘗試本地執行
            self._initialized = True
            return True
    
    async def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int = 30,
        **kwargs
    ) -> Dict[str, Any]:
        """執行程式碼"""
        if not self._service:
            # 嘗試初始化
            await self.initialize()
            
        if not self._service:
            return {"success": False, "error": "Sandbox service not initialized"}
        
        try:
            # 確保 service 初始化
            if not self._service._initialized:
                await self._service.initialize()
            
            # 根據語言選擇執行方法
            if language.lower() == "python":
                result = await self._service.execute(
                    method="execute_python",
                    params={
                        "code": code,
                        "timeout": timeout
                    }
                )
            else:
                result = await self._service.execute(
                    method="execute_bash",
                    params={
                        "command": f"node -e '{code}'",
                        "timeout": timeout
                    }
                )
            
            return {
                "success": result.get("success", False),
                "stdout": result.get("stdout", ""),
                "stderr": result.get("stderr", ""),
                "figures": result.get("figures", []),
                "return_value": result.get("return_value"),
                "execution_time": result.get("execution_time", 0),
                "error": result.get("error")
            }
        except Exception as e:
            logger.error(f"Code execution error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e)}


class CodeAnalyzeTool(BaseTool):
    """程式碼分析工具"""
    
    def __init__(self):
        super().__init__()
        self._llm_client = None
    
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="code_analyze",
            description="分析程式碼，提供結構、問題和改進建議。",
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="要分析的程式碼",
                    required=True
                ),
                ToolParameter(
                    name="language",
                    type="string",
                    description="程式語言",
                    required=False,
                    default="python"
                ),
                ToolParameter(
                    name="focus",
                    type="string",
                    description="分析重點：quality, security, performance, all",
                    required=False,
                    default="all"
                )
            ],
            returns="程式碼分析報告",
            examples=[
                {
                    "code": "def add(a, b): return a + b",
                    "focus": "quality"
                }
            ]
        )
    
    async def initialize(self) -> bool:
        try:
            import os
            from openai import AsyncOpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._llm_client = AsyncOpenAI(api_key=api_key)
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"CodeAnalyzeTool init error: {e}")
            return False
    
    async def execute(
        self,
        code: str,
        language: str = "python",
        focus: str = "all",
        **kwargs
    ) -> Dict[str, Any]:
        """分析程式碼"""
        if not self._llm_client:
            return {"error": "LLM client not initialized"}
        
        try:
            prompt = f"""分析以下 {language} 程式碼：

```{language}
{code}
```

分析重點：{focus}

請提供：
1. 程式碼結構概述
2. 發現的問題
3. 改進建議
4. 整體評分（1-10）
"""
            
            response = await self._llm_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一位資深程式碼審核專家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            analysis = response.choices[0].message.content
            
            return {
                "success": True,
                "language": language,
                "focus": focus,
                "analysis": analysis
            }
        except Exception as e:
            logger.error(f"Code analysis error: {e}")
            return {"error": str(e)}
