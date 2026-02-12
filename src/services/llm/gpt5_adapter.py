"""
GPT-5 Series Model Adapter
專門處理 GPT-5 系列模型的特殊需求
"""

from typing import Dict, Any, Optional


class GPT5Adapter:
    """GPT-5 系列模型適配器"""

    # GPT-5 系列模型列表
    GPT5_MODELS = [
        "gpt-5",
        "gpt-5.1",
        "gpt-5-mini",
        "gpt-5-turbo",
        "gpt-5-pro"
    ]

    # GPT-5 參數限制
    CONSTRAINTS = {
        "temperature": 1.0,  # 固定值
        "top_p": 1.0,  # 固定值
        "frequency_penalty": 0.0,  # 固定值
        "presence_penalty": 0.0,  # 固定值
    }

    @classmethod
    def is_gpt5_model(cls, model_name: str) -> bool:
        """檢查是否為 GPT-5 系列模型"""
        if not model_name:
            return False
        return any(model_name.startswith(m) for m in cls.GPT5_MODELS)

    @classmethod
    def adapt_parameters(cls, model_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        適配 GPT-5 參數

        Args:
            model_name: 模型名稱
            params: 原始參數

        Returns:
            適配後的參數
        """
        if not cls.is_gpt5_model(model_name):
            return params

        adapted = params.copy()

        # 1. 替換 max_tokens 為 max_completion_tokens
        if "max_tokens" in adapted:
            adapted["max_completion_tokens"] = adapted.pop("max_tokens")

        # 2. 移除不支援的參數
        for param in ["temperature", "top_p", "frequency_penalty", "presence_penalty"]:
            if param in adapted:
                # 檢查是否為預設值，如果不是則記錄警告
                if adapted[param] != cls.CONSTRAINTS.get(param, adapted[param]):
                    print(f"⚠️ GPT-5 Warning: {param}={adapted[param]} ignored (only {cls.CONSTRAINTS[param]} supported)")
                adapted.pop(param)

        # 3. 處理特殊參數
        if "response_format" in adapted:
            # GPT-5 支援 JSON 模式
            if adapted["response_format"].get("type") == "json_object":
                # 保留 JSON 模式
                pass
            else:
                # 其他格式可能不支援
                adapted.pop("response_format")

        return adapted

    @classmethod
    def validate_response(cls, response: Dict[str, Any]) -> bool:
        """
        驗證 GPT-5 回應格式

        Args:
            response: API 回應

        Returns:
            是否有效
        """
        # 檢查基本結構
        if not response or "choices" not in response:
            return False

        # 檢查選項
        choices = response.get("choices", [])
        if not choices:
            return False

        # 檢查消息內容
        first_choice = choices[0]
        if "message" not in first_choice:
            return False

        message = first_choice["message"]
        if "content" not in message:
            return False

        return True

    @classmethod
    def extract_content(cls, response: Dict[str, Any]) -> str:
        """
        從 GPT-5 回應中提取內容

        Args:
            response: API 回應

        Returns:
            提取的內容
        """
        if not cls.validate_response(response):
            return ""

        return response["choices"][0]["message"]["content"]

    @classmethod
    def get_token_usage(cls, response: Dict[str, Any]) -> Dict[str, int]:
        """
        獲取 token 使用情況

        Args:
            response: API 回應

        Returns:
            Token 統計
        """
        usage = response.get("usage", {})

        # GPT-5 可能使用不同的字段名
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }

    @classmethod
    def format_error(cls, error: Exception) -> str:
        """
        格式化 GPT-5 錯誤信息

        Args:
            error: 錯誤對象

        Returns:
            格式化的錯誤信息
        """
        error_str = str(error)

        # 特殊錯誤處理
        if "max_tokens" in error_str:
            return "GPT-5 Error: Use 'max_completion_tokens' instead of 'max_tokens'"
        elif "temperature" in error_str:
            return "GPT-5 Error: Temperature must be 1.0 (default) for GPT-5 models"
        elif "rate_limit" in error_str:
            return "GPT-5 Error: Rate limit exceeded. Please wait and retry."
        else:
            return f"GPT-5 Error: {error_str}"

    @classmethod
    def get_model_info(cls, model_name: str) -> Dict[str, Any]:
        """
        獲取模型信息

        Args:
            model_name: 模型名稱

        Returns:
            模型信息
        """
        if not cls.is_gpt5_model(model_name):
            return {}

        # 基於模型名稱返回不同的配置
        if "mini" in model_name:
            return {
                "max_tokens": 4096,
                "context_window": 128000,
                "cost_per_1k_input": 0.00015,
                "cost_per_1k_output": 0.0006,
                "features": ["fast", "efficient", "basic_reasoning"]
            }
        elif "turbo" in model_name:
            return {
                "max_tokens": 8192,
                "context_window": 256000,
                "cost_per_1k_input": 0.0003,
                "cost_per_1k_output": 0.0012,
                "features": ["balanced", "multi-modal", "tool_use"]
            }
        elif "pro" in model_name:
            return {
                "max_tokens": 16384,
                "context_window": 512000,
                "cost_per_1k_input": 0.0006,
                "cost_per_1k_output": 0.0024,
                "features": ["advanced", "complex_reasoning", "long_context"]
            }
        else:
            # 標準 GPT-5
            return {
                "max_tokens": 8192,
                "context_window": 256000,
                "cost_per_1k_input": 0.0004,
                "cost_per_1k_output": 0.0016,
                "features": ["standard", "general_purpose", "reliable"]
            }