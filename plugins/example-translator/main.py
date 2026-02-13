"""
示例插件 - 翻譯工具
"""

import os
import logging
from typing import Dict, Any, List

from opencode.plugins import ToolPlugin, PluginMetadata

logger = logging.getLogger(__name__)


class PluginImpl(ToolPlugin):
    """翻譯插件實現"""
    
    async def on_load(self) -> None:
        """載入時初始化"""
        logger.info(f"🔌 Loading {self.metadata.name}")
        self.default_lang = self.config.get("default_target_lang", "zh-TW")
    
    async def on_enable(self) -> None:
        """啟用"""
        logger.info(f"✅ Enabled {self.metadata.name}")
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """返回工具定義"""
        return [
            {
                "name": "translate",
                "description": "翻譯文字",
                "parameters": {
                    "text": {"type": "string", "description": "要翻譯的文字"},
                    "target_lang": {"type": "string", "description": "目標語言", "default": self.default_lang}
                },
                "plugin_id": self.metadata.id
            }
        ]
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """執行翻譯"""
        if action != "translate":
            return {"error": f"Unknown action: {action}"}
        
        text = parameters.get("text", "")
        target_lang = parameters.get("target_lang", self.default_lang)
        
        # 這裡用簡單的示例，實際可以調用翻譯 API
        try:
            # 嘗試使用 OpenAI 翻譯
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a translator. Translate the following text to {target_lang}. Only output the translation, nothing else."
                        },
                        {"role": "user", "content": text}
                    ],
                    temperature=0.3
                )
                
                translated = response.choices[0].message.content
                
                return {
                    "success": True,
                    "original": text,
                    "translated": translated,
                    "target_lang": target_lang
                }
            else:
                return {
                    "success": False,
                    "error": "OPENAI_API_KEY not set"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
