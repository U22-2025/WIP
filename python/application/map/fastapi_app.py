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
from common.clients.location_client import LocationClient
from common.clients.query_client import QueryClient
from common.utils.config_loader import ConfigLoader
from common.utils.redis_log_handler import RedisLogHandler
import redis.asyncio as aioredis
# ドキュメントエンドポイントを有効化
app = FastAPI()
script_dir = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(script_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(script_dir / "templates"))

LOCATION_SERVER_HOST = os.getenv("LOCATION_RESOLVER_HOST", "localhost")
LOCATION_SERVER_PORT = int(os.getenv("LOCATION_RESOLVER_PORT", 4109))
QUERY_SERVER_HOST = os.getenv("QUERY_GENERATOR_HOST", "localhost")
QUERY_SERVER_PORT = int(os.getenv("QUERY_GENERATOR_PORT", 4111))

LOG_REDIS_HOST = os.getenv("LOG_REDIS_HOST", "localhost")
LOG_REDIS_PORT = int(os.getenv("LOG_REDIS_PORT", 6380))
LOG_REDIS_DB = int(os.getenv("LOG_REDIS_DB", 0))

logger = logging.getLogger("fastapi_app")
logging.basicConfig(level=logging.INFO)
redis_log_handler = RedisLogHandler(
    host=LOG_REDIS_HOST,
    port=LOG_REDIS_PORT,
    db=LOG_REDIS_DB,
)
logger.addHandler(redis_log_handler)

config_loader = ConfigLoader()
LOG_LIMIT = config_loader.getint("logging", "log_limit", default=100)
# ログ送信間隔（秒）
BROADCAST_INTERVAL = float(
    config_loader.get("logging", "broadcast_interval", default="1")
)


class ConnectionManager:
    def __init__(self, log_limit: int = 100, interval: float = 1.0) -> None:
        self.active: List[WebSocket] = []
        self.logs: List[str] = []
        self.log_limit = log_limit
        self.interval = interval
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self._task: asyncio.Task | None = None
        self.redis = aioredis.Redis(
            host=LOG_REDIS_HOST,
            port=LOG_REDIS_PORT,
            db=LOG_REDIS_DB,
            decode_responses=True,
        )
        self.pubsub = self.redis.pubsub()
        self._redis_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)
        for log in self.logs:
            await websocket.send_text(log)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def enqueue(self, message: str) -> None:
        await self.queue.put(message)

    async def _broadcast(self, message: str) -> None:
        self.logs.append(message)
        if len(self.logs) > self.log_limit:
            self.logs = self.logs[-self.log_limit:]
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(ws)

    async def _broadcast_loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.interval)
                messages: List[str] = []
                while not self.queue.empty():
                    messages.append(await self.queue.get())
                for msg in messages:
                    await self._broadcast(msg)
        except asyncio.CancelledError:
            pass

    async def _redis_listener(self) -> None:
        await self.pubsub.subscribe("wip.log")
        try:
            async for msg in self.pubsub.listen():
                if msg.get("type") == "message":
                    await self.enqueue(str(msg.get("data")))
        except asyncio.CancelledError:
            pass

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._broadcast_loop())
        if self._redis_task is None:
            self._redis_task = asyncio.create_task(self._redis_listener())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._redis_task:
            self._redis_task.cancel()
            try:
                await self._redis_task
            except asyncio.CancelledError:
                pass
            self._redis_task = None
        await self.pubsub.close()
        await self.redis.close()


manager = ConnectionManager(log_limit=LOG_LIMIT, interval=BROADCAST_INTERVAL)


@app.on_event("startup")
async def startup_event() -> None:
    manager.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await manager.stop()

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


async def log_event(
    message: str,
    *,
    level: str = "info",
    details: Optional[dict] = None,
) -> None:
    log_data = {
        "type": "log",
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
    }
    if details:
        log_data["details"] = details
    msg = json.dumps(log_data, ensure_ascii=False)
    logger.info(msg)
    await manager.enqueue(msg)
    await redis_log_handler.publish(msg)


def record_packet_metrics(duration_ms: float) -> None:
    """パケット通信のメトリクスを更新"""
    global packet_accesses, packet_response_time
    packet_accesses += 1
    packet_response_time += duration_ms


async def call_with_metrics(func, *args, ip: str | None = None, context=None, **kwargs):
    """クライアント呼び出しを計測して実行"""
    start = time.perf_counter()
    result = await func(*args, **kwargs)
    duration_ms = (time.perf_counter() - start) * 1000
    record_packet_metrics(duration_ms)

    details = {"response_time": round(duration_ms, 2)}
    if ip:
        details["ip"] = ip
    if context:
        details.update(context)

    name = func.__name__
    if name == "get_location_data_async":
        message = "Location"
    elif name == "get_weather_data_async":
        message = "Weather"
    else:
        message = f"packet_call {name}"

    await log_event(message, level="packet", details=details)
    return result


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    if request.client:
        request.state.ip = request.client.host

    start = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start) * 1000
    global total_accesses, total_response_time
    total_accesses += 1
    total_response_time += process_time
    avg_ms = total_response_time / total_accesses
    packet_avg = packet_response_time / packet_accesses if packet_accesses > 0 else 0
    details = {
        "endpoint": request.url.path,
        "status_code": response.status_code,
        "response_time": round(process_time, 2),
    }
    if hasattr(request.state, "ip"):
        details["ip"] = request.state.ip
    status = response.status_code
    if status >= 500:
        level = "error"
    elif status >= 400:
        level = "warning"
    else:
        level = "success"
    await log_event(
        f"{request.method} {request.url.path}",
        level=level,
        details=details,
    )
    metrics = {
        "type": "metrics",
        "total": total_accesses,
        "avg_ms": round(avg_ms, 2),
        "packet_total": packet_accesses,
        "packet_avg_ms": round(packet_avg, 2),
    }
    await manager.enqueue(json.dumps(metrics))
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

async def get_location_client() -> AsyncGenerator[LocationClient, None]:
    client = LocationClient(
        host=LOCATION_SERVER_HOST,
        port=LOCATION_SERVER_PORT,
        debug=True,
    )
    try:
        yield client
    finally:
        client.close()


async def get_query_client() -> AsyncGenerator[QueryClient, None]:
    client = QueryClient(
        host=QUERY_SERVER_HOST,
        port=QUERY_SERVER_PORT,
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
    request: Request,
    coords: Coordinates,
    loc_client: LocationClient = Depends(get_location_client),
    query_client: QueryClient = Depends(get_query_client),
):
    lat = coords.lat
    lng = coords.lng
    ip = getattr(request.state, "ip", None)
    await log_event(
        "POST /weekly_forecast",
        details={"endpoint": "/weekly_forecast", "lat": lat, "lng": lng},
    )

    if lat is None or lng is None:
        return JSONResponse(
            {"status": "error", "message": "緯度と経度が必要です"}, status_code=400
        )

    try:
        location_response, _ = await call_with_metrics(
            loc_client.get_location_data_async,
            latitude=lat,
            longitude=lng,
            use_cache=True,
            ip=ip,
            context={"coords": f"{lat},{lng}"},
        )
        if not location_response or not location_response.is_valid():
            return JSONResponse(
                {"status": "error", "message": "エリアコードの取得に失敗しました"},
                status_code=500,
            )

        area_code = location_response.get_area_code()

        async def fetch(day: int):
            try:
                flags = {
                    "weather": True,
                    "temperature": True,
                    "precipitation_prob": True,
                    "alert": True,
                    "disaster": True,
                }
                weather_data = await call_with_metrics(
                    query_client.get_weather_data_async,
                    area_code=area_code,
                    **flags,
                    day=day,
                    use_cache=True,
                    ip=ip,
                    context={
                        "area_code": area_code,
                        "day": day,
                        "flags": ",".join(k for k, v in flags.items() if v),
                    },
                )
                if not weather_data or (
                    isinstance(weather_data, dict)
                    and ("error" in weather_data or "error_code" in weather_data)
                ):
                    weather_data = _create_fallback_weather_data(area_code, day)
            except Exception as e:  # pragma: no cover
                logger.error(f"Error getting weather for day {day}: {e}")
                weather_data = _create_fallback_weather_data(area_code, day)
            return _add_date_info(weather_data, day)

        tasks = [fetch(day) for day in range(7)]
        results = await asyncio.gather(*tasks)
        weekly_forecast_list = sorted(results, key=lambda x: x["day"])

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
