"""
Code Processor - Code generation and execution

Generates Python code and executes it in a sandbox environment.
Extracted from monolithic processor.py
"""

from typing import Dict, Any

from .base import BaseProcessor
from ..models_v2 import ProcessingContext
from ..prompts import PromptTemplates
from ..error_handler import enhanced_error_handler


class CodeProcessor(BaseProcessor):
    """代碼執行處理器"""

    @enhanced_error_handler(max_retries=1, retryable_categories=["LLM", "SANDBOX"])
    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("code-execution", "start")
        context.set_current_step("code-execution")

        # Step 1: 解析代碼請求
        self.logger.progress("code-analysis", "start")
        code_request = context.request.query
        self.logger.progress("code-analysis", "end")

        # Step 2: 生成代碼（使用專門的 prompt）
        self.logger.progress("code-generation", "start")
        prompt = PromptTemplates.get_code_generation_prompt(code_request)
        generated_code = await self._call_llm(prompt, context)

        # 清理可能的空白行
        generated_code = generated_code.strip()

        self.logger.message(f"```python\n{generated_code}\n```")
        self.logger.progress("code-generation", "end")

        # Step 3: 執行代碼（沙箱環境）
        self.logger.progress("code-execution", "start")
        result = await self._execute_code(generated_code)
        self.logger.progress("code-execution", "end", {"success": result.get("success")})

        response = f"代碼執行結果：\n{result.get('output', 'No output')}"
        self.logger.message(response)

        context.mark_step_complete("code-execution")
        self.logger.progress("code-execution", "end")

        return response

    async def _execute_code(self, code: str) -> Dict[str, Any]:
        """在沙箱中執行代碼 — 使用真實沙箱服務，無則告知使用者"""
        sandbox_service = self.services.get("sandbox")

        if sandbox_service:
            try:
                result = await sandbox_service.execute("execute_python", {
                    "code": code,
                    "timeout": 30
                })
                return {
                    "success": result.get("success", False),
                    "output": result.get("stdout", "") or result.get("error", "No output")
                }
            except Exception as e:
                self.logger.warning(f"Sandbox service error, using fallback: {e}", "code", "fallback")

        # Sandbox unavailable — return code only, do not fake execution
        self.logger.warning("Sandbox unavailable — code generated but not executed", "code", "no_sandbox")
        return {
            "success": False,
            "output": "[Sandbox unavailable] Code was generated but could not be executed. "
                      "Please set up the Docker sandbox to enable code execution."
        }
