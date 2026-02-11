"""
股票分析師 Agent 插件

功能：
- 查詢股票即時價格
- 技術分析
- 基本面分析
- 投資建議
"""

import logging
from typing import Dict, Any, List
from opencode.plugins.manager import AgentPlugin, PluginMetadata, PluginStatus

logger = logging.getLogger(__name__)


class PluginImpl(AgentPlugin):
    """股票分析師 Agent 插件實現"""
    
    @property
    def agent_name(self) -> str:
        return "stock_analyst"
    
    @property
    def agent_description(self) -> str:
        return "專業股票分析師，可查詢股價、進行技術分析和基本面分析"
    
    @property
    def system_prompt(self) -> str:
        market = self.config.get("default_market", "TW")
        depth = self.config.get("analysis_depth", "standard")
        
        return f"""你是一個專業的股票分析師 Agent。

你的職責是：
1. 查詢股票即時價格和歷史數據
2. 進行技術分析（K線、均線、MACD、RSI等）
3. 進行基本面分析（財報、本益比、殖利率等）
4. 提供投資建議（但需聲明非投資顧問意見）

預設市場：{market}
分析深度：{depth}

注意事項：
- 始終提醒用戶投資有風險
- 數據僅供參考，不構成投資建議
- 使用台灣股市時股票代碼加 .TW（如 2330.TW）
- 使用美股時直接用代碼（如 AAPL）
"""
    
    async def on_load(self) -> None:
        """載入時初始化"""
        logger.info(f"📈 {self.metadata.name} 載入中...")
        self._yf_available = False
        
        try:
            import yfinance
            self._yf_available = True
            logger.info("✅ yfinance 可用")
        except ImportError:
            logger.warning("⚠️ yfinance 未安裝，部分功能受限")
    
    async def on_enable(self) -> None:
        """啟用時"""
        logger.info(f"✅ {self.metadata.name} 已啟用")
    
    async def on_disable(self) -> None:
        """禁用時"""
        logger.info(f"🔌 {self.metadata.name} 已禁用")
    
    def get_tools(self) -> List[str]:
        """此 Agent 可用的工具"""
        return ["stock_query", "stock_analysis"]
    
    async def process_task(
        self, 
        task_description: str, 
        parameters: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        處理股票分析任務
        """
        try:
            # 解析任務
            action = parameters.get("action", "query")
            symbol = parameters.get("symbol", "")
            
            if not symbol:
                # 嘗試從描述中提取股票代碼
                symbol = self._extract_symbol(task_description)
            
            if action == "query" or "價格" in task_description or "股價" in task_description:
                result = await self._query_stock(symbol)
            elif action == "analysis" or "分析" in task_description:
                result = await self._analyze_stock(symbol)
            elif action == "recommendation" or "建議" in task_description:
                result = await self._get_recommendation(symbol)
            else:
                # 通用處理
                result = await self._general_query(task_description, symbol)
            
            return {
                "success": True,
                "output": result,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Stock analysis error: {e}")
            return {
                "success": False,
                "output": None,
                "error": str(e)
            }
    
    def _extract_symbol(self, text: str) -> str:
        """從文字中提取股票代碼"""
        import re
        
        # 台股代碼（4-6位數字）
        tw_match = re.search(r'\b(\d{4,6})\b', text)
        if tw_match:
            code = tw_match.group(1)
            if ".TW" not in code.upper():
                return f"{code}.TW"
            return code
        
        # 美股代碼（1-5位大寫字母）
        us_match = re.search(r'\b([A-Z]{1,5})\b', text.upper())
        if us_match:
            return us_match.group(1)
        
        return ""
    
    async def _query_stock(self, symbol: str) -> Dict[str, Any]:
        """查詢股票價格"""
        if not self._yf_available:
            return {
                "message": "yfinance 未安裝，無法查詢即時數據",
                "symbol": symbol
            }
        
        import yfinance as yf
        
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            return {
                "symbol": symbol,
                "name": info.get("longName", info.get("shortName", symbol)),
                "price": info.get("currentPrice", info.get("regularMarketPrice")),
                "change": info.get("regularMarketChange"),
                "change_percent": info.get("regularMarketChangePercent"),
                "volume": info.get("volume"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "dividend_yield": info.get("dividendYield"),
                "52_week_high": info.get("fiftyTwoWeekHigh"),
                "52_week_low": info.get("fiftyTwoWeekLow"),
            }
        except Exception as e:
            return {
                "error": f"查詢失敗: {e}",
                "symbol": symbol
            }
    
    async def _analyze_stock(self, symbol: str) -> Dict[str, Any]:
        """技術分析"""
        if not self._yf_available:
            return {"message": "yfinance 未安裝", "symbol": symbol}
        
        import yfinance as yf
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="3mo")
            
            if hist.empty:
                return {"error": "無法取得歷史數據", "symbol": symbol}
            
            # 計算技術指標
            close = hist['Close']
            
            # 均線
            ma5 = close.rolling(5).mean().iloc[-1]
            ma20 = close.rolling(20).mean().iloc[-1]
            ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else None
            
            # RSI (14日)
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            current_price = close.iloc[-1]
            
            # 趨勢判斷
            trend = "上升" if current_price > ma20 > ma5 else "下降" if current_price < ma20 < ma5 else "盤整"
            
            return {
                "symbol": symbol,
                "current_price": round(current_price, 2),
                "ma5": round(ma5, 2),
                "ma20": round(ma20, 2),
                "ma60": round(ma60, 2) if ma60 else None,
                "rsi_14": round(rsi, 2),
                "trend": trend,
                "analysis": self._generate_analysis_text(current_price, ma5, ma20, rsi, trend)
            }
            
        except Exception as e:
            return {"error": f"分析失敗: {e}", "symbol": symbol}
    
    def _generate_analysis_text(self, price, ma5, ma20, rsi, trend):
        """生成分析文字"""
        lines = [f"目前趨勢：{trend}"]
        
        if price > ma20:
            lines.append("股價在20日均線上方，短期偏多")
        else:
            lines.append("股價在20日均線下方，短期偏空")
        
        if rsi > 70:
            lines.append(f"RSI={rsi:.1f}，已進入超買區，注意回檔風險")
        elif rsi < 30:
            lines.append(f"RSI={rsi:.1f}，已進入超賣區，可能有反彈機會")
        else:
            lines.append(f"RSI={rsi:.1f}，處於中性區間")
        
        lines.append("\n⚠️ 以上僅供參考，不構成投資建議。投資有風險，請謹慎評估。")
        
        return "\n".join(lines)
    
    async def _get_recommendation(self, symbol: str) -> Dict[str, Any]:
        """投資建議"""
        analysis = await self._analyze_stock(symbol)
        
        if "error" in analysis:
            return analysis
        
        rsi = analysis.get("rsi_14", 50)
        trend = analysis.get("trend", "盤整")
        
        if rsi < 30 and trend != "下降":
            recommendation = "可考慮分批布局"
        elif rsi > 70 and trend != "上升":
            recommendation = "可考慮分批獲利了結"
        else:
            recommendation = "建議觀望或維持現有部位"
        
        return {
            **analysis,
            "recommendation": recommendation,
            "disclaimer": "⚠️ 本建議僅供參考，不構成投資顧問意見。投資決策請自行評估風險。"
        }
    
    async def _general_query(self, description: str, symbol: str) -> Dict[str, Any]:
        """通用查詢"""
        results = {}
        
        if symbol:
            results["price_info"] = await self._query_stock(symbol)
            
            depth = self.config.get("analysis_depth", "standard")
            if depth in ["standard", "detailed"]:
                results["technical_analysis"] = await self._analyze_stock(symbol)
        
        results["query"] = description
        return results
