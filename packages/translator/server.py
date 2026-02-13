"""
Translator MCP Server — 標準 MCP Server 暴露翻譯工具

Tools:
  - translate: 翻譯文字到目標語言

Requires: OPENAI_API_KEY environment variable
"""

import json
import os

from mcp.server import Server
from mcp.server.stdio import run_server
from mcp.types import TextContent, Tool

server = Server("translator")

DEFAULT_TARGET_LANG = os.environ.get("TRANSLATOR_DEFAULT_LANG", "zh-TW")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="translate",
            description="翻譯文字到目標語言",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "要翻譯的文字",
                    },
                    "target_lang": {
                        "type": "string",
                        "description": "目標語言，如 zh-TW, en, ja",
                        "default": DEFAULT_TARGET_LANG,
                    },
                },
                "required": ["text"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "translate":
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    text = arguments.get("text", "")
    target_lang = arguments.get("target_lang", DEFAULT_TARGET_LANG)

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        result = {"success": False, "error": "OPENAI_API_KEY not set"}
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"You are a translator. Translate the following text to {target_lang}. Only output the translation, nothing else.",
                },
                {"role": "user", "content": text},
            ],
            temperature=0.3,
        )
        translated = response.choices[0].message.content

        result = {
            "success": True,
            "original": text,
            "translated": translated,
            "target_lang": target_lang,
        }
    except Exception as e:
        result = {"success": False, "error": str(e)}

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_server(server))
