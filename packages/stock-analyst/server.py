"""
Stock Analyst A2A Agent — 標準 A2A Agent 提供股票分析服務

Endpoints:
  GET  /.well-known/agent.json  — Agent Card
  POST /tasks/send              — 同步任務
  POST /tasks/sendSubscribe     — SSE 串流任務
  POST /tasks/get               — 查詢任務狀態
  POST /tasks/cancel            — 取消任務

Requires: yfinance, pandas
"""

import asyncio
import json
import os
import re
import uuid
from enum import Enum
from typing import Any, Dict, Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from sse_starlette.sse import EventSourceResponse

DEFAULT_MARKET = os.environ.get("STOCK_DEFAULT_MARKET", "TW")
ANALYSIS_DEPTH = os.environ.get("STOCK_ANALYSIS_DEPTH", "standard")


# ============================================================
# Agent Card
# ============================================================

AGENT_CARD = {
    "name": "stock-analyst",
    "description": "專業股票分析師，可查詢股價、進行技術分析和基本面分析",
    "url": f"http://localhost:{os.environ.get('PORT', '9001')}",
    "version": "1.0.0",
    "capabilities": {"streaming": True, "pushNotifications": False},
    "skills": [
        {
            "id": "stock-query",
            "name": "股票查詢",
            "description": "查詢股票即時價格和基本資訊",
            "input_modes": ["text"],
            "output_modes": ["text"],
        },
        {
            "id": "stock-analysis",
            "name": "股票技術分析",
            "description": "進行技術指標分析（均線、RSI、趨勢判斷）",
            "input_modes": ["text"],
            "output_modes": ["text"],
        },
        {
            "id": "stock-recommendation",
            "name": "投資建議",
            "description": "根據技術分析提供投資建議（僅供參考）",
            "input_modes": ["text"],
            "output_modes": ["text"],
        },
    ],
}


# ============================================================
# Task State Management
# ============================================================

class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


_tasks: Dict[str, Dict[str, Any]] = {}


# ============================================================
# Stock Analysis Logic (from original plugin)
# ============================================================

def _extract_symbol(text: str) -> str:
    tw_match = re.search(r'\b(\d{4,6})\b', text)
    if tw_match:
        code = tw_match.group(1)
        return f"{code}.TW" if ".TW" not in code.upper() else code

    us_match = re.search(r'\b([A-Z]{1,5})\b', text.upper())
    if us_match:
        return us_match.group(1)
    return ""


async def _query_stock(symbol: str) -> Dict[str, Any]:
    try:
        import yfinance as yf
    except ImportError:
        return {"message": "yfinance 未安裝，無法查詢即時數據", "symbol": symbol}

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
        return {"error": f"查詢失敗: {e}", "symbol": symbol}


async def _analyze_stock(symbol: str) -> Dict[str, Any]:
    try:
        import yfinance as yf
    except ImportError:
        return {"message": "yfinance 未安裝", "symbol": symbol}

    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="3mo")
        if hist.empty:
            return {"error": "無法取得歷史數據", "symbol": symbol}

        close = hist["Close"]
        ma5 = close.rolling(5).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else None

        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        current_price = close.iloc[-1]

        trend = (
            "上升" if current_price > ma20 > ma5
            else "下降" if current_price < ma20 < ma5
            else "盤整"
        )

        lines = [f"目前趨勢：{trend}"]
        if current_price > ma20:
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

        return {
            "symbol": symbol,
            "current_price": round(float(current_price), 2),
            "ma5": round(float(ma5), 2),
            "ma20": round(float(ma20), 2),
            "ma60": round(float(ma60), 2) if ma60 is not None else None,
            "rsi_14": round(float(rsi), 2),
            "trend": trend,
            "analysis": "\n".join(lines),
        }
    except Exception as e:
        return {"error": f"分析失敗: {e}", "symbol": symbol}


async def _get_recommendation(symbol: str) -> Dict[str, Any]:
    analysis = await _analyze_stock(symbol)
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
        "disclaimer": "⚠️ 本建議僅供參考，不構成投資顧問意見。投資決策請自行評估風險。",
    }


async def _process_task(message: str) -> str:
    symbol = _extract_symbol(message)

    if "分析" in message:
        result = await _analyze_stock(symbol) if symbol else {"error": "未找到股票代碼"}
    elif "建議" in message or "推薦" in message:
        result = await _get_recommendation(symbol) if symbol else {"error": "未找到股票代碼"}
    elif symbol:
        result = await _query_stock(symbol)
        if ANALYSIS_DEPTH in ("standard", "detailed"):
            analysis = await _analyze_stock(symbol)
            result = {"price_info": result, "technical_analysis": analysis}
    else:
        result = {"error": "未能辨識股票代碼，請提供股票代碼或名稱"}

    return json.dumps(result, ensure_ascii=False, default=str)


# ============================================================
# A2A Protocol Handlers
# ============================================================

async def agent_card(request: Request) -> JSONResponse:
    return JSONResponse(AGENT_CARD)


async def tasks_send(request: Request) -> JSONResponse:
    body = await request.json()
    params = body.get("params", body)
    task_id = params.get("id", str(uuid.uuid4()))
    message_parts = params.get("message", {}).get("parts", [])
    text = next((p.get("text", "") for p in message_parts if p.get("type") == "text"), "")

    _tasks[task_id] = {"id": task_id, "status": {"state": TaskState.WORKING}}

    try:
        output = await _process_task(text)
        _tasks[task_id] = {
            "id": task_id,
            "status": {"state": TaskState.COMPLETED},
            "artifacts": [{"parts": [{"type": "text", "text": output}]}],
        }
    except Exception as e:
        _tasks[task_id] = {
            "id": task_id,
            "status": {"state": TaskState.FAILED},
            "error": str(e),
        }

    return JSONResponse({
        "jsonrpc": "2.0",
        "id": body.get("id"),
        "result": _tasks[task_id],
    })


async def tasks_send_subscribe(request: Request) -> EventSourceResponse:
    body = await request.json()
    params = body.get("params", body)
    task_id = params.get("id", str(uuid.uuid4()))
    message_parts = params.get("message", {}).get("parts", [])
    text = next((p.get("text", "") for p in message_parts if p.get("type") == "text"), "")

    async def event_generator():
        # Status: working
        yield {
            "event": "status",
            "data": json.dumps({
                "id": task_id,
                "status": {"state": TaskState.WORKING},
            }),
        }

        try:
            output = await _process_task(text)
            # Artifact
            yield {
                "event": "artifact",
                "data": json.dumps({
                    "id": task_id,
                    "artifact": {"parts": [{"type": "text", "text": output}]},
                }),
            }
            # Status: completed
            yield {
                "event": "status",
                "data": json.dumps({
                    "id": task_id,
                    "status": {"state": TaskState.COMPLETED},
                }),
            }
            _tasks[task_id] = {
                "id": task_id,
                "status": {"state": TaskState.COMPLETED},
                "artifacts": [{"parts": [{"type": "text", "text": output}]}],
            }
        except Exception as e:
            yield {
                "event": "status",
                "data": json.dumps({
                    "id": task_id,
                    "status": {"state": TaskState.FAILED},
                    "error": str(e),
                }),
            }
            _tasks[task_id] = {
                "id": task_id,
                "status": {"state": TaskState.FAILED},
                "error": str(e),
            }

    return EventSourceResponse(event_generator())


async def tasks_get(request: Request) -> JSONResponse:
    body = await request.json()
    params = body.get("params", body)
    task_id = params.get("id")

    task = _tasks.get(task_id)
    if not task:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": body.get("id"), "error": {"message": "Task not found"}},
            status_code=404,
        )
    return JSONResponse({"jsonrpc": "2.0", "id": body.get("id"), "result": task})


async def tasks_cancel(request: Request) -> JSONResponse:
    body = await request.json()
    params = body.get("params", body)
    task_id = params.get("id")

    if task_id in _tasks:
        _tasks[task_id]["status"] = {"state": TaskState.CANCELED}
    return JSONResponse({"jsonrpc": "2.0", "id": body.get("id"), "result": {"success": True}})


app = Starlette(
    routes=[
        Route("/.well-known/agent.json", agent_card, methods=["GET"]),
        Route("/tasks/send", tasks_send, methods=["POST"]),
        Route("/tasks/sendSubscribe", tasks_send_subscribe, methods=["POST"]),
        Route("/tasks/get", tasks_get, methods=["POST"]),
        Route("/tasks/cancel", tasks_cancel, methods=["POST"]),
    ],
)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "9001"))
    uvicorn.run(app, host="0.0.0.0", port=port)
