"""
Weather MCP Server — 標準 MCP Server 暴露天氣查詢工具

Tools:
  - weather_current: 查詢城市目前天氣
  - weather_forecast: 查詢未來 5 天天氣預報

Requires: OPENWEATHERMAP_API_KEY environment variable
"""

import json
import os

import httpx
from mcp.server import Server
from mcp.server.stdio import run_server
from mcp.types import TextContent, Tool

server = Server("weather")

API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY", "")
DEFAULT_UNITS = os.environ.get("WEATHER_UNITS", "metric")
DEFAULT_LANG = os.environ.get("WEATHER_LANG", "zh_tw")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="weather_current",
            description="查詢城市目前天氣",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名稱，如 Taipei, Tokyo, New York",
                    }
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="weather_forecast",
            description="查詢未來 5 天天氣預報",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名稱",
                    }
                },
                "required": ["city"],
            },
        ),
    ]


async def _get_current_weather(city: str) -> dict:
    if not API_KEY:
        return {"error": "OPENWEATHERMAP_API_KEY not set"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": API_KEY, "units": DEFAULT_UNITS, "lang": DEFAULT_LANG},
            timeout=10,
        )
        if response.status_code != 200:
            return {"error": f"API error: {response.status_code}"}

        data = response.json()
        temp_unit = "°C" if DEFAULT_UNITS == "metric" else "°F"

        return {
            "city": data.get("name"),
            "country": data.get("sys", {}).get("country"),
            "weather": data.get("weather", [{}])[0].get("description"),
            "temperature": f"{data.get('main', {}).get('temp')}{temp_unit}",
            "feels_like": f"{data.get('main', {}).get('feels_like')}{temp_unit}",
            "humidity": f"{data.get('main', {}).get('humidity')}%",
            "wind_speed": f"{data.get('wind', {}).get('speed')} m/s",
        }


async def _get_forecast(city: str) -> dict:
    if not API_KEY:
        return {"error": "OPENWEATHERMAP_API_KEY not set"}

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"q": city, "appid": API_KEY, "units": DEFAULT_UNITS, "lang": DEFAULT_LANG},
            timeout=10,
        )
        if response.status_code != 200:
            return {"error": f"API error: {response.status_code}"}

        data = response.json()
        forecasts = []
        seen_dates = set()

        for item in data.get("list", []):
            date = item.get("dt_txt", "").split(" ")[0]
            if date not in seen_dates and len(forecasts) < 5:
                seen_dates.add(date)
                forecasts.append({
                    "date": date,
                    "weather": item.get("weather", [{}])[0].get("description"),
                    "temp_max": item.get("main", {}).get("temp_max"),
                    "temp_min": item.get("main", {}).get("temp_min"),
                    "humidity": item.get("main", {}).get("humidity"),
                })

        return {
            "city": data.get("city", {}).get("name"),
            "country": data.get("city", {}).get("country"),
            "forecasts": forecasts,
        }


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "weather_current":
        result = await _get_current_weather(arguments["city"])
    elif name == "weather_forecast":
        result = await _get_forecast(arguments["city"])
    else:
        result = {"error": f"Unknown tool: {name}"}

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_server(server))
