"""
Base Processor - Foundation for all processing strategies

Extracted from monolithic processor.py (2611 lines → modular architecture)
Following Linus philosophy: simple data structures, no special cases, ≤500 lines
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
import time

from ..models import ProcessingContext
from ..logger import structured_logger


class BaseProcessor(ABC):
    """處理器基類"""

    def __init__(self, llm_client=None, services: Optional[Dict[str, Any]] = None, mcp_client=None):
        self.llm_client = llm_client
        self.services = services or {}
        self.mcp_client = mcp_client
        self.logger = structured_logger
        self._cognitive_level: Optional[str] = None

    @abstractmethod
    async def process(self, context: ProcessingContext) -> str:
        """處理請求 - 子類必須實現"""
        pass

    async def _call_llm(self, prompt: str, context: ProcessingContext = None) -> str:
        """調用 LLM - 公共方法"""
        if not self.llm_client:
            raise RuntimeError("LLM client not configured — cannot process request")

        # # 記錄 prompt (截取前500字符用於日誌)
        # self.logger.info(
        #     f"📝 LLM Prompt: {prompt[:500]}...",
        #     "llm",
        #     "prompt",
        #     prompt_length=len(prompt),
        #     prompt_preview=prompt[:200]
        # )

        start_time = time.time()
        with self.logger.measure("llm_call"):
            # 使用 return_token_info 參數獲取 token 資訊
            result = await self.llm_client.generate(prompt, return_token_info=True)

            # 處理返回值
            if isinstance(result, tuple):
                response, token_info = result
                tokens_in = token_info.get("prompt_tokens", 0)
                tokens_out = token_info.get("completion_tokens", 0)
                total_tokens = token_info.get("total_tokens", 0)
            else:
                # 向後兼容：如果返回的是字符串
                response = result
                tokens_in = len(prompt.split())  # 粗略估算
                tokens_out = len(response.split())  # 粗略估算
                total_tokens = tokens_in + tokens_out

            duration_ms = (time.time() - start_time) * 1000

            # 記錄 LLM 調用 (包含 token 和時間資訊)
            self.logger.log_llm_call(
                model=getattr(self.llm_client, 'model_name', getattr(self.llm_client, 'provider_name', 'unknown')),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                duration_ms=duration_ms
            )

            # 記錄 LLM Response (用於 debugging，顯示實際輸出)
            # 檢查是否需要分割長內容
            try:
                from core.enhanced_logger import get_enhanced_logger
                enhanced_logger = get_enhanced_logger()

                if len(response) > 10000:  # 超過 10KB
                    # 使用增強日誌器處理長內容
                    trace_id = context.trace_id if context and hasattr(context, 'trace_id') else "unknown"
                    enhanced_logger.log_long_content(
                        "INFO",
                        f"LLM Response (Long: {len(response)} chars, {total_tokens} tokens)",
                        response,
                        trace_id,
                        "llm_response"
                    )
                    # 主日誌只記錄摘要
                    self.logger.info(
                        f"💬 LLM Response [Long content: {len(response)} chars, see segments]",
                        "llm",
                        "response",
                        response_length=len(response),
                        total_tokens=total_tokens
                    )
                else:
                    # 正常記錄
                    self.logger.info(
                        f"💬 LLM Response: {response[:5000]}...",
                        "llm",
                        "response",
                        response_length=len(response),
                        response_preview=response[:200]
                    )
            except ImportError:
                # 如果增強日誌器不可用，使用原始方式
                self.logger.info(
                    f"💬 LLM Response: {response[:5000]}...",
                    "llm",
                    "response",
                    response_length=len(response),
                    response_preview=response[:200]
                )

            # 檢查響應是否為空
            if not response or response.strip() == "":
                self.logger.warning(
                    "LLM returned empty response",
                    "llm",
                    "empty_response",
                    model=getattr(self.llm_client, 'model_name', 'unknown')
                )
                response = "[LLM returned empty response - please check API configuration]"

            # 更新上下文的 token 統計
            if context:
                context.total_tokens += total_tokens

            return response

    async def _log_tool_decision(self, tool_name: str, reason: str, confidence: float = 0.9):
        """記錄工具決策"""
        self.logger.log_tool_decision(tool_name, confidence, reason)
        self.logger.info(
            f"🔧 Tool Decision: {tool_name}",
            "processor",
            "tool_decision",
            tool=tool_name,
            confidence=confidence,
            reason=reason
        )

    async def _call_mcp_tool(
        self, server_name: str, tool_name: str, arguments: Dict[str, Any]
    ) -> Any:
        """呼叫 MCP Server 上的工具

        Args:
            server_name: MCP server 名稱
            tool_name: Tool 名稱
            arguments: Tool 參數

        Returns:
            Tool 回傳的文字內容

        Raises:
            RuntimeError: MCP client 不可用或呼叫失敗
        """
        if not self.mcp_client:
            raise RuntimeError(f"MCP client not available, cannot call {server_name}/{tool_name}")
        result = await self.mcp_client.call_tool(server_name, tool_name, arguments)
        if result.get("is_error"):
            raise RuntimeError(f"MCP tool error: {result.get('content')}")
        # Extract text from content items
        texts = [item.get("text", "") for item in result.get("content", [])]
        return "\n".join(texts)

    async def _get_mcp_tools(self) -> List[Dict[str, Any]]:
        """取得所有可用的 MCP tools"""
        if not self.mcp_client:
            return []
        return await self.mcp_client.list_tools()
