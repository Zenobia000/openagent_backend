"""
Thinking Processor - Deep multi-stage reasoning

Conducts deep analysis through problem decomposition, critical thinking,
chain of thought reasoning, and synthesis.
Extracted from monolithic processor.py
"""

from .base import BaseProcessor
from ..models import ProcessingContext
from ..prompts import PromptTemplates
from ..logger import LogCategory
from ..error_handler import enhanced_error_handler


class ThinkingProcessor(BaseProcessor):
    """深度思考處理器"""

    @enhanced_error_handler(max_retries=1, retryable_categories=["LLM"])
    async def process(self, context: ProcessingContext) -> str:
        self.logger.progress("deep-thinking", "start")
        context.set_current_step("deep-thinking")

        # 記錄思考決策
        await self._log_tool_decision(
            "deep_thinking",
            "複雜問題需要深度分析和推理",
            0.95
        )

        # 記錄思考計劃
        self.logger.info(
            f"🧠 Deep Thinking: Analyzing '{context.request.query[:50]}...'",
            "thinking",
            "start",
            category=LogCategory.TOOL,
            approach="multi-perspective-reasoning"
        )

        # Step 1: Problem decomposition and understanding
        self.logger.progress("problem-analysis", "start")
        self.logger.reasoning("Decomposing and understanding core elements...", streaming=True)

        # 記錄階段開始 (只在日誌中顯示)
        self.logger.info(
            f"🔍 Stage 1: Problem Understanding & Decomposition",
            "thinking",
            "stage1",
            query=context.request.query[:100]
        )

        # 使用思考模式的專業提示詞
        thinking_prompt = PromptTemplates.get_thinking_mode_prompt(context.request.query)

        # 執行深度思考
        thinking_response = await self._call_llm(thinking_prompt, context)

        # 將結果輸出到日誌 (不是 message)
        self.logger.info(
            f"💭 Stage 1 Result: {thinking_response[:500]}...",
            "thinking",
            "stage1_result",
            full_length=len(thinking_response)
        )

        # 記錄階段完成
        self.logger.info(
            f"✅ Stage 1: Problem Analysis Complete",
            "thinking",
            "stage1_complete",
            response_length=len(thinking_response)
        )

        self.logger.progress("problem-analysis", "end", {"analyzed": True})

        # Step 2: Multi-perspective analysis
        self.logger.progress("multi-perspective", "start")
        self.logger.reasoning("Analyzing from multiple perspectives...", streaming=True)

        # 記錄第二階段開始 (只在日誌中顯示)
        self.logger.info(
            f"🔍 Stage 2: Critical Multi-Perspective Analysis",
            "thinking",
            "stage2"
        )

        # 使用批判性思維提示詞
        critical_prompt = PromptTemplates.get_critical_thinking_prompt(
            question=context.request.query,
            context=thinking_response
        )

        critical_analysis = await self._call_llm(critical_prompt, context)

        # 將結果輸出到日誌 (不是 message)
        self.logger.info(
            f"💭 Stage 2 Result: {critical_analysis[:500]}...",
            "thinking",
            "stage2_result",
            full_length=len(critical_analysis)
        )

        self.logger.progress("multi-perspective", "end", {"perspectives": 5})

        # Step 3: Deep reasoning
        self.logger.progress("deep-reasoning", "start")
        self.logger.reasoning("Conducting deep reasoning and logical analysis...", streaming=True)

        # 記錄第三階段開始 (只在日誌中顯示)
        self.logger.info(
            f"🔍 Stage 3: Chain of Deep Reasoning",
            "thinking",
            "stage3"
        )

        # 使用推理鏈提示詞
        reasoning_prompt = PromptTemplates.get_chain_of_thought_prompt(context.request.query)

        chain_reasoning = await self._call_llm(reasoning_prompt, context)

        # 將結果輸出到日誌 (不是 message)
        self.logger.info(
            f"💭 Stage 3 Result: {chain_reasoning[:500]}...",
            "thinking",
            "stage3_result",
            full_length=len(chain_reasoning)
        )

        self.logger.progress("deep-reasoning", "end")

        # Step 4: Synthesis and reflection
        self.logger.progress("synthesis-reflection", "start")
        self.logger.reasoning("Synthesizing all analysis and reflecting...", streaming=True)

        # 記錄第四階段開始 (只在日誌中顯示)
        self.logger.info(
            f"🔍 Stage 4: Synthesis & Reflection",
            "thinking",
            "stage4"
        )

        # 使用反思提示詞
        reflection_prompt = PromptTemplates.get_reflection_prompt(
            original_response=f"{thinking_response}\n\n{critical_analysis}\n\n{chain_reasoning}",
            question=context.request.query
        )

        reflection = await self._call_llm(reflection_prompt, context)

        # 將結果輸出到日誌 (不是 message)
        self.logger.info(
            f"💭 Stage 4 Result: {reflection[:500]}...",
            "thinking",
            "stage4_result",
            full_length=len(reflection)
        )

        self.logger.progress("synthesis-reflection", "end")

        # Step 5: Final answer generation
        self.logger.progress("final-synthesis", "start")

        # 記錄最終階段開始 (只在日誌中顯示)
        self.logger.info(
            f"🎯 Stage 5: Final Comprehensive Answer",
            "thinking",
            "stage5"
        )

        # 準備最終答案提示詞
        final_synthesis_prompt = f"""
Based on the following deep thinking process, provide a comprehensive final answer to the question: "{context.request.query}"

Thinking Process Summary:
1. Problem Understanding: {thinking_response[:200]}...
2. Critical Analysis: {critical_analysis[:200]}...
3. Chain of Reasoning: {chain_reasoning[:200]}...
4. Reflection: {reflection[:200]}...

Please provide a complete, well-structured answer that synthesizes all insights from the above analysis.
"""

        # 使用輸出指南確保答案品質
        output_guidelines = PromptTemplates.get_output_guidelines()
        final_prompt = f"{final_synthesis_prompt}\n\n{output_guidelines}"

        final_response = await self._call_llm(final_prompt, context)

        # 只輸出最終答案作為回應
        self.logger.message(final_response)

        self.logger.progress("final-synthesis", "end")

        context.mark_step_complete("deep-thinking")
        self.logger.progress("deep-thinking", "end")

        # 只返回最終答案
        return final_response
