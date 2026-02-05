"""
天氣查詢工具插件

功能：
- 查詢即時天氣
- 天氣預報
- 空氣品質
"""

import logging
from typing import Dict, Any, List
from opencode.plugins.manager import ToolPlugin, PluginMetadata, PluginStatus

logger = logging.getLogger(__name__)


class PluginImpl(ToolPlugin):
    """天氣查詢工具插件實現"""
    
    async def on_load(self) -> None:
        """載入時初始化"""
        logger.info(f"🌤️ {self.metadata.name} 載入中...")
        self._httpx_available = False
        
        try:
            import httpx
            self._httpx_available = True
            logger.info("✅ httpx 可用")
        except ImportError:
            logger.warning("⚠️ httpx 未安裝")
    
    async def on_enable(self) -> None:
        """啟用時"""
        # 驗證 API Key
        api_key = self.config.get("api_key")
        if not api_key:
            logger.warning("⚠️ OpenWeatherMap API Key 未設置")
        logger.info(f"✅ {self.metadata.name} 已啟用")
    
    async def on_disable(self) -> None:
        """禁用時"""
        logger.info(f"🔌 {self.metadata.name} 已禁用")
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """返回工具定義"""
        return [
            {
                "name": "weather_current",
                "description": "查詢城市目前天氣",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名稱，如 Taipei, Tokyo, New York"
                        }
                    },
                    "required": ["city"]
                }
            },
            {
                "name": "weather_forecast",
                "description": "查詢未來 5 天天氣預報",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "城市名稱"
                        }
                    },
                    "required": ["city"]
                }
            }
        ]
    
    async def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """執行工具"""
        if action == "weather_current":
            return await self._get_current_weather(parameters.get("city", ""))
        elif action == "weather_forecast":
            return await self._get_forecast(parameters.get("city", ""))
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def _get_current_weather(self, city: str) -> Dict[str, Any]:
        """取得目前天氣"""
        if not self._httpx_available:
            return {"error": "httpx 未安裝"}
        
        api_key = self.config.get("api_key")
        if not api_key:
            return {"error": "API Key 未設置"}
        
        import httpx
        
        try:
            units = self.config.get("default_units", "metric")
            lang = self.config.get("language", "zh_tw")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={
                        "q": city,
                        "appid": api_key,
                        "units": units,
                        "lang": lang
                    },
                    timeout=10
                )
                
                if response.status_code != 200:
                    return {"error": f"API 錯誤: {response.status_code}"}
                
                data = response.json()
                
                temp_unit = "°C" if units == "metric" else "°F"
                
                return {
                    "city": data.get("name"),
                    "country": data.get("sys", {}).get("country"),
                    "weather": data.get("weather", [{}])[0].get("description"),
                    "temperature": f"{data.get('main', {}).get('temp')}{temp_unit}",
                    "feels_like": f"{data.get('main', {}).get('feels_like')}{temp_unit}",
                    "humidity": f"{data.get('main', {}).get('humidity')}%",
                    "wind_speed": f"{data.get('wind', {}).get('speed')} m/s",
                    "icon": data.get("weather", [{}])[0].get("icon")
                }
                
        except Exception as e:
            return {"error": str(e)}
    
    async def _get_forecast(self, city: str) -> Dict[str, Any]:
        """取得天氣預報"""
        if not self._httpx_available:
            return {"error": "httpx 未安裝"}
        
        api_key = self.config.get("api_key")
        if not api_key:
            return {"error": "API Key 未設置"}
        
        import httpx
        
        try:
            units = self.config.get("default_units", "metric")
            lang = self.config.get("language", "zh_tw")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/forecast",
                    params={
                        "q": city,
                        "appid": api_key,
                        "units": units,
                        "lang": lang
                    },
                    timeout=10
                )
                
                if response.status_code != 200:
                    return {"error": f"API 錯誤: {response.status_code}"}
                
                data = response.json()
                
                # 整理預報數據（每天取一筆）
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
                            "humidity": item.get("main", {}).get("humidity")
                        })
                
                return {
                    "city": data.get("city", {}).get("name"),
                    "country": data.get("city", {}).get("country"),
                    "forecasts": forecasts
                }
                
        except Exception as e:
            return {"error": str(e)}
