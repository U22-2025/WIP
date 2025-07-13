import asyncio
import logging
import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, AsyncGenerator
import uvicorn
from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


# 直接実行時のパス調整

if __name__ == "__main__":
    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )

# Windows環境では ProactorEventLoop がデフォルトとなるが、このイベントループは
# sock_sendto が実装されていないため非同期クライアントでエラーになる。
# そのため SelectorEventLoop を使用するようにポリシーを設定する。
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:  # pragma: no cover - Windows 環境以外では実行されない
        pass
from WIP_Client import ClientAsync
from common.utils.config_loader import ConfigLoader
# ドキュメントエンドポイントを有効化
app = FastAPI()
script_dir = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(script_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(script_dir / "templates"))

WEATHER_SERVER_HOST = os.getenv("WEATHER_SERVER_HOST", "localhost")
WEATHER_SERVER_PORT = int(os.getenv("WEATHER_SERVER_PORT", 4110))

logger = logging.getLogger("fastapi_app")
logging.basicConfig(level=logging.INFO)

config_loader = ConfigLoader()
LOG_LIMIT = config_loader.getint("logging", "log_limit", default=100)


class ConnectionManager:
    def __init__(self, log_limit: int = 100) -> None:
        self.active: List[WebSocket] = []
        self.logs: List[str] = []
        self.log_limit = log_limit

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)
        for log in self.logs:
            await websocket.send_text(log)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: str) -> None:
        self.logs.append(message)
        if len(self.logs) > self.log_limit:
            self.logs = self.logs[-self.log_limit:]
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(ws)


manager = ConnectionManager(log_limit=LOG_LIMIT)

# メトリクス用グローバル変数
total_accesses = 0
total_response_time = 0.0  # milliseconds
# パケット通信のメトリクス
packet_accesses = 0
packet_response_time = 0.0  # milliseconds


class Coordinates(BaseModel):
    """リクエストボディ用の座標モデル"""

    lat: float
    lng: float


async def log_event(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    logger.info(msg)
    await manager.broadcast(msg)


def record_packet_metrics(duration_ms: float) -> None:
    """パケット通信のメトリクスを更新"""
    global packet_accesses, packet_response_time
    packet_accesses += 1
    packet_response_time += duration_ms


async def call_with_metrics(func, *args, **kwargs):
    """クライアント呼び出しを計測して実行"""
    start = time.perf_counter()
    result = await func(*args, **kwargs)
    duration_ms = (time.perf_counter() - start) * 1000
    record_packet_metrics(duration_ms)
    await log_event(f"packet_call {func.__name__} {duration_ms:.2f}ms")
    return result


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start) * 1000
    global total_accesses, total_response_time
    total_accesses += 1
    total_response_time += process_time
    avg_ms = total_response_time / total_accesses
    packet_avg = packet_response_time / packet_accesses if packet_accesses > 0 else 0
    await log_event(
        f"{request.method} {request.url.path} {response.status_code} {process_time:.2f}ms"
    )
    metrics = {
        "type": "metrics",
        "total": total_accesses,
        "avg_ms": round(avg_ms, 2),
        "packet_total": packet_accesses,
        "packet_avg_ms": round(packet_avg, 2),
    }
    await manager.broadcast(json.dumps(metrics))
    return response


def _add_date_info(weather_data: dict, day_offset: int = 0) -> dict:
    base_date = datetime.now()
    target_date = base_date + timedelta(days=day_offset)
    weather_data["date"] = target_date.strftime("%Y-%m-%d")
    weather_data["day_of_week"] = target_date.strftime("%A")
    weather_data["day"] = day_offset
    return weather_data


def _create_fallback_weather_data(area_code: str, days_offset: int = 0) -> dict:
    date = datetime.now() + timedelta(days=days_offset)
    return {
        "date": date.strftime("%Y-%m-%d"),
        "day_of_week": date.strftime("%A"),
        "weather_code": "100",
        "temperature": "--",
        "precipitation_prob": "--",
        "area_code": area_code,
    }


# ----------------------------------------------------------------------
# Dependency
# ----------------------------------------------------------------------

async def get_client() -> AsyncGenerator[ClientAsync, None]:
    client = ClientAsync(
        host=WEATHER_SERVER_HOST,
        port=WEATHER_SERVER_PORT,
        debug=True,
    )
    try:
        yield client
    finally:
        client.close()


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    await log_event("GET /")
    return templates.TemplateResponse("map.html", {"request": request})


@app.post("/weekly_forecast")
async def weekly_forecast(
    coords: Coordinates, client: ClientAsync = Depends(get_client)
):
    lat = coords.lat
    lng = coords.lng
    await log_event(f"POST /weekly_forecast lat={lat} lng={lng}")

    if lat is None or lng is None:
        return JSONResponse(
            {"status": "error", "message": "緯度と経度が必要です"}, status_code=400
        )

    try:
        client.set_coordinates(lat, lng)
        today_weather = await call_with_metrics(client.get_weather, day=0)
        if not today_weather or (
            isinstance(today_weather, dict) and "error_code" in today_weather
        ):
            return JSONResponse(
                {"status": "error", "message": "今日の天気データの取得に失敗しました"},
                status_code=500,
            )

        area_code = today_weather.get("area_code")
        if not area_code:
            return JSONResponse(
                {"status": "error", "message": "エリアコードが見つかりませんでした"},
                status_code=500,
            )

        async def fetch(day: int):
            try:
                weather_data = await call_with_metrics(
                    client.get_weather_by_area_code, area_code=area_code, day=day
                )
                if not weather_data or (
                    isinstance(weather_data, dict) and "error_code" in weather_data
                ):
                    weather_data = _create_fallback_weather_data(area_code, day)
            except Exception as e:  # pragma: no cover
                logger.error(f"Error getting weather for day {day}: {e}")
                weather_data = _create_fallback_weather_data(area_code, day)
            return _add_date_info(weather_data, day)

        tasks = [fetch(day) for day in range(1, 7)]
        results = await asyncio.gather(*tasks)
        weekly_forecast_list = [_add_date_info(today_weather.copy(), 0)] + results

        weekly_forecast_list.sort(key=lambda x: x["day"])
        return JSONResponse(
            {
                "status": "ok",
                "coordinates": {"lat": lat, "lng": lng},
                "area_code": area_code,
                "weekly_forecast": weekly_forecast_list,
            }
        )
    except Exception as e:  # pragma: no cover
        logger.error(f"Error in weekly_forecast: {e}")
        return JSONResponse(
            {"status": "error", "message": "週間予報の取得に失敗しました"},
            status_code=500,
        )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep connection
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=5000)
