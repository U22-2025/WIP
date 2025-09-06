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
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates


# Windows環境では ProactorEventLoop がデフォルトとなるが、このイベントループは
# sock_sendto が実装されていないため非同期クライアントでエラーになる。
# そのため SelectorEventLoop を使用するようにポリシーを設定する。
if sys.platform.startswith("win"):
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception:  # pragma: no cover - Windows 環境以外では実行されない
        pass
from WIPClientPy import ClientAsync
from WIPCommonPy.utils.config_loader import ConfigLoader
from WIPCommonPy.utils.redis_log_handler import RedisLogHandler
import redis.asyncio as aioredis

# ドキュメントエンドポイントを有効化
app = FastAPI()
script_dir = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(script_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(script_dir / "templates"))
app.add_middleware(GZipMiddleware, minimum_size=500)

# Health endpoint for compatibility when API is mounted under /api
@app.get("/health")
async def health_root() -> dict:
    return {"status": "ok"}


LOG_REDIS_HOST = os.getenv("LOG_REDIS_HOST", "localhost")
LOG_REDIS_PORT = int(os.getenv("LOG_REDIS_PORT", 6380))
LOG_REDIS_DB = int(os.getenv("LOG_REDIS_DB", 0))

logger = logging.getLogger("fastapi_app")
# ルートロガーにハンドラが未設定の場合のみ基本設定を行う
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO)

# 重複ハンドラ追加を防止し、二重送信を抑止
has_redis_handler = any(
    isinstance(h, RedisLogHandler) for h in logger.handlers
)
if not has_redis_handler:
    redis_log_handler = RedisLogHandler(
        host=LOG_REDIS_HOST,
        port=LOG_REDIS_PORT,
        db=LOG_REDIS_DB,
    )
    logger.addHandler(redis_log_handler)

# 上位ロガーへの伝播を止め、重複出力を回避
logger.propagate = False

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
        """単発メッセージ配信（互換用）。"""
        self.logs.append(message)
        if len(self.logs) > self.log_limit:
            self.logs = self.logs[-self.log_limit :]

        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(ws)

    async def _broadcast_batch(self, batch: List[str]) -> None:
        """まとめて配信（1秒ごと）。JSON文字列→オブジェクト化して送る。"""
        # 履歴は個別ログ文字列で保持（新規 WS 接続時の replay 用）
        self.logs.extend(batch)
        if len(self.logs) > self.log_limit:
            self.logs = self.logs[-self.log_limit :]

        objs = []
        for s in batch:
            try:
                objs.append(json.loads(s))
            except Exception:
                # parse できなかった行もログ化して捨てない
                objs.append(
                    {
                        "type": "log",
                        "timestamp": datetime.now().isoformat(),
                        "level": "info",
                        "message": s,
                        "details": {"raw": True},
                    }
                )

        payload = json.dumps(
            {
                "type": "bulk",
                "count": len(objs),
                "logs": objs,  # ← ここがオブジェクト配列になる！
            },
            ensure_ascii=False,
        )

        for ws in list(self.active):
            try:
                await ws.send_text(payload)
            except WebSocketDisconnect:
                self.disconnect(ws)

    async def _broadcast_loop(self) -> None:
        """self.interval ごとにキューを読み出し、更新があれば 1 回だけ送信。"""
        try:
            while True:
                await asyncio.sleep(self.interval)  # interval=1.0 で 1秒レート
                if self.queue.empty():
                    continue  # この周期は送るものなし

                batch: List[str] = []
                while not self.queue.empty():
                    batch.append(await self.queue.get())

                if len(batch) == 1:
                    await self._broadcast(batch[0])  # 従来互換
                else:
                    await self._broadcast_batch(batch)  # bulk 送信
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


# 簡易TTLキャッシュ（週予報）。キーは area_code。値は {expires, weekly_forecast}
_WEEKLY_CACHE: dict[str, dict] = {}
_WEEKLY_TTL_SEC = int(os.getenv("WEEKLY_CACHE_TTL", "60"))

def _get_cached_weekly(area_code: str):
    now = time.time()
    ent = _WEEKLY_CACHE.get(area_code)
    if ent and ent.get("expires", 0) > now:
        return ent.get("weekly_forecast")
    return None

def _set_cached_weekly(area_code: str, weekly_forecast_list: list):
    _WEEKLY_CACHE[area_code] = {
        "expires": time.time() + _WEEKLY_TTL_SEC,
        "weekly_forecast": weekly_forecast_list,
    }


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
    # await manager.enqueue(msg)
    # await redis_log_handler.publish(msg)


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


async def get_wip_client() -> AsyncGenerator[ClientAsync, None]:
    client = ClientAsync(debug=True)
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

# ----------------------------------------------------------------------
# Mount External Weather API under /api
# ----------------------------------------------------------------------
# application/weather_api を import できるようにパスを追加
try:
    sys.path.insert(0, str(script_dir.parent))  # python/application
    from weather_api.app import (
        app as weather_api_app,  # type: ignore
        list_areas as _api_list_areas,
        get_weather as _api_get_weather,
        update_weather as _api_update_weather,
        update_disaster as _api_update_disaster,
    )

    # サブアプリとして /api にマウント
    app.mount("/api", weather_api_app)
    logger.info("Mounted External Weather API at /api")

    # 互換エイリアス: 既存テストやクライアントが / に向けて叩くため
    @app.post("/update/weather")
    async def _alias_update_weather():  # type: ignore
        return _api_update_weather()

    @app.post("/update/disaster")
    async def _alias_update_disaster():  # type: ignore
        return _api_update_disaster()

    @app.get("/areas")
    async def _alias_list_areas():  # type: ignore
        return _api_list_areas()

    @app.get("/weather")
    async def _alias_get_weather(
        area_code: str,
        day: int = 0,
        weather_flag: int = 1,
        temperature_flag: int = 1,
        pop_flag: int = 1,
        alert_flag: int = 1,
        disaster_flag: int = 1,
    ):  # type: ignore
        return _api_get_weather(
            area_code=area_code,
            day=day,
            weather_flag=weather_flag,
            temperature_flag=temperature_flag,
            pop_flag=pop_flag,
            alert_flag=alert_flag,
            disaster_flag=disaster_flag,
        )
except Exception as e:  # pragma: no cover
    logger.error(f"Failed to mount External Weather API at /api: {e}")




@app.post("/weekly_forecast")
async def weekly_forecast(
    request: Request,
    coords: Coordinates,
    client: ClientAsync = Depends(get_wip_client),
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
        today_weather = await call_with_metrics(
            client.get_weather_by_coordinates,
            lat,
            lng,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            wind=True,
            alert=True,
            disaster=True,
            day=0,
            ip=ip,
            context={"coords": f"{lat},{lng}", "day": 0},
        )
        if not today_weather or (
            isinstance(today_weather, dict)
            and ("error" in today_weather or "error_code" in today_weather)
        ):
            return JSONResponse(
                {"status": "error", "message": "エリアコードの取得に失敗しました"},
                status_code=500,
            )

        area_code = today_weather.get("area_code")
        if not area_code:
            return JSONResponse(
                {"status": "error", "message": "エリアコードの取得に失敗しました"},
                status_code=500,
            )

        async def fetch(day: int):
            try:
                flags = {
                    "weather": True,
                    "temperature": True,
                    "precipitation_prob": True,
                    "wind": True,
                    "alert": True,
                    "disaster": True,
                }
                weather_data = await call_with_metrics(
                    client.get_weather_by_area_code,
                    area_code=area_code,
                    **flags,
                    day=day,
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
                
                # Redisから直接風速データを取得して追加
                if "wind" not in weather_data or weather_data.get("wind") is None:
                    try:
                        import redis
                        import json as json_lib
                        _host = os.getenv("REDIS_HOST", "localhost")
                        _port = int(os.getenv("REDIS_PORT", 6379))
                        _db = int(os.getenv("REDIS_DB", 0))
                        _prefix = os.getenv("REPORT_DB_KEY_PREFIX", os.getenv("REDIS_KEY_PREFIX", "")) or ""

                        redis_client = redis.Redis(host=_host, port=_port, db=_db, decode_responses=True)
                        redis_key = f"{_prefix}weather:{area_code}"
                        
                        weather_info = None
                        try:
                            redis_data = redis_client.execute_command("JSON.GET", redis_key)
                            if redis_data:
                                weather_info = json_lib.loads(redis_data)
                        except Exception:
                            pass
                        if weather_info is None:
                            raw = redis_client.get(redis_key)
                            if raw:
                                try:
                                    weather_info = json_lib.loads(raw)
                                except Exception:
                                    weather_info = None
                        
                        if weather_info:
                            wind_list = weather_info.get("wind", [])
                            if wind_list and len(wind_list) > day and wind_list[day]:
                                weather_data["wind"] = wind_list[day]
                    except Exception as e:
                        logger.error(f"Error fetching wind data from Redis for day {day}: {e}")
            except Exception as e:  # pragma: no cover
                logger.error(f"Error getting weather for day {day}: {e}")
                weather_data = _create_fallback_weather_data(area_code, day)
            return _add_date_info(weather_data, day)

        # 週予報は area_code 単位で短期キャッシュ
        weekly_forecast_list = _get_cached_weekly(area_code)
        if not weekly_forecast_list:
          tasks = [fetch(day) for day in range(1, 7)]
          results = await asyncio.gather(*tasks)
          
          # today_weatherにも風速データを追加
          today_with_wind = today_weather.copy()
          if "wind" not in today_with_wind or today_with_wind.get("wind") is None:
              try:
                  import redis
                  import json as json_lib
                  _host = os.getenv("REDIS_HOST", "localhost")
                  _port = int(os.getenv("REDIS_PORT", 6379))
                  _db = int(os.getenv("REDIS_DB", 0))
                  _prefix = os.getenv("REPORT_DB_KEY_PREFIX", os.getenv("REDIS_KEY_PREFIX", "")) or ""

                  redis_client = redis.Redis(host=_host, port=_port, db=_db, decode_responses=True)
                  redis_key = f"{_prefix}weather:{area_code}"
                  
                  weather_info = None
                  try:
                      redis_data = redis_client.execute_command("JSON.GET", redis_key)
                      if redis_data:
                          weather_info = json_lib.loads(redis_data)
                  except Exception:
                      pass
                  if weather_info is None:
                      raw = redis_client.get(redis_key)
                      if raw:
                          try:
                              weather_info = json_lib.loads(raw)
                          except Exception:
                              weather_info = None
                  
                  if weather_info:
                      wind_list = weather_info.get("wind", [])
                      if wind_list and len(wind_list) > 0 and wind_list[0]:
                          today_with_wind["wind"] = wind_list[0]
              except Exception as e:
                  logger.error(f"Error fetching wind data from Redis for today: {e}")
          
          weekly_forecast_list = [_add_date_info(today_with_wind, 0)] + results
          weekly_forecast_list = sorted(weekly_forecast_list, key=lambda x: x["day"])
          _set_cached_weekly(area_code, weekly_forecast_list)

        # 追加: ランドマーク情報を取得して同梱（ex_field のみ対応）
        area_name: str = "不明"
        landmarks_with_distance = []
        try:
            import json as json_lib
            import math
            import os as _os

            def calculate_distance(lat1, lng1, lat2, lng2):
                R = 6371
                lat1_rad = math.radians(lat1)
                lng1_rad = math.radians(lng1)
                lat2_rad = math.radians(lat2)
                lng2_rad = math.radians(lng2)
                dlat = lat2_rad - lat1_rad
                dlng = lng2_rad - lng1_rad
                a = (
                    math.sin(dlat / 2) * math.sin(dlat / 2)
                    + math.cos(lat1_rad)
                    * math.cos(lat2_rad)
                    * math.sin(dlng / 2)
                    * math.sin(dlng / 2)
                )
                c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
                return round((R * c) * 10) / 10

            # ランドマークデータ（ex_field のみ）: today_weather は辞書のため、パケットを別リクエストで取得
            packet = await call_with_metrics(
                client.get_weather_by_area_code,
                area_code=area_code,
                # フラグは警報/災害のみ不要。landmarks取得のためwindを明示
                weather=True,  # 妥当性チェック上、最低1つはTrue
                wind=True,
                temperature=False,
                precipitation_prob=False,
                alert=False,
                disaster=False,
                day=0,
                raw_packet=True,
                ip=ip,
                context={"area_code": area_code, "purpose": "landmarks"},
            )
            logger.info(f"Packet type: {type(packet)}, has ex_field: {hasattr(packet, 'ex_field')}")
            if hasattr(packet, 'ex_field'):
                logger.info(f"ex_field type: {type(packet.ex_field)}, has landmarks: {hasattr(packet.ex_field, 'landmarks') if packet.ex_field else False}")
                if packet.ex_field and hasattr(packet.ex_field, 'landmarks'):
                    logger.info(f"landmarks content: {packet.ex_field.landmarks}")
            
            if hasattr(packet, 'ex_field') and packet.ex_field and hasattr(packet.ex_field, 'landmarks') and packet.ex_field.landmarks:
                try:
                    raw_landmarks = json_lib.loads(packet.ex_field.landmarks)
                    logger.info(f"Successfully parsed landmarks: {len(raw_landmarks)} items")
                    for landmark in raw_landmarks:
                        if "latitude" in landmark and "longitude" in landmark:
                            distance = calculate_distance(
                                lat, lng, landmark["latitude"], landmark["longitude"]
                            )
                            item = landmark.copy()
                            item["distance"] = distance
                            landmarks_with_distance.append(item)

                    landmarks_with_distance.sort(
                        key=lambda x: x.get("distance", float("inf"))
                    )
                    # 近傍上位N件のみを返却（転送/描画コストを抑制）
                    MAX_LANDMARKS = int(_os.getenv("LANDMARKS_TOPN", "100"))
                    if len(landmarks_with_distance) > MAX_LANDMARKS:
                        landmarks_with_distance = landmarks_with_distance[:MAX_LANDMARKS]
                except (json_lib.JSONDecodeError, KeyError) as e:
                    logger.error(f"Error parsing landmarks from WIP packet: {e}")

            # エリア名を取得するためにRedisから基本情報を取得（landmarkは使わない）
            try:
                import redis
                _host = _os.getenv("REDIS_HOST", "localhost")
                _port = int(_os.getenv("REDIS_PORT", 6379))
                _db = int(_os.getenv("REDIS_DB", 0))
                _prefix = _os.getenv("REPORT_DB_KEY_PREFIX", _os.getenv("REDIS_KEY_PREFIX", "")) or ""

                redis_client = redis.Redis(host=_host, port=_port, db=_db, decode_responses=True)
                redis_key = f"{_prefix}weather:{area_code}"

                weather_info = None
                try:
                    redis_data = redis_client.execute_command("JSON.GET", redis_key)
                    if redis_data:
                        weather_info = json_lib.loads(redis_data)
                except Exception:
                    pass
                if weather_info is None:
                    raw = redis_client.get(redis_key)
                    if raw:
                        try:
                            weather_info = json_lib.loads(raw)
                        except Exception:
                            weather_info = None

                if weather_info:
                    area_name = weather_info.get("area_name", "不明")
            except Exception as e:
                logger.error(f"Error getting area name from Redis: {e}")
        except Exception as e:  # pragma: no cover
            logger.error(f"Error embedding landmarks in weekly_forecast: {e}")

        # landmarksを各weekly_forecast項目に移動（alertと同レベル）
        for forecast_item in weekly_forecast_list:
            if forecast_item.get("day") == 0:  # 今日の予報にのみランドマークを追加
                forecast_item["landmarks"] = landmarks_with_distance
        
        return JSONResponse(
            {
                "status": "ok",
                "coordinates": {"lat": lat, "lng": lng},
                "area_code": area_code,
                "area_name": area_name,
                "weekly_forecast": weekly_forecast_list,
                # 互換性のためトップレベルにもlandmarksを含める
                "landmarks": landmarks_with_distance,
            }
        )

    except Exception as e:  # pragma: no cover
        logger.error(f"Error in weekly_forecast: {e}")
        return JSONResponse(
            {"status": "error", "message": "週間予報の取得に失敗しました"},
            status_code=500,
        )


@app.post("/current_weather")
async def current_weather(
    request: Request,
    coords: Coordinates,
    client: ClientAsync = Depends(get_wip_client),
):
    lat = coords.lat
    lng = coords.lng
    ip = getattr(request.state, "ip", None)
    await log_event(
        "POST /current_weather",
        details={"endpoint": "/current_weather", "lat": lat, "lng": lng},
    )

    if lat is None or lng is None:
        return JSONResponse(
            {"status": "error", "message": "緯度と経度が必要です"}, status_code=400
        )

    try:
        today_weather = await call_with_metrics(
            client.get_weather_by_coordinates,
            lat,
            lng,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            wind=True,
            alert=True,
            disaster=True,
            day=0,
            ip=ip,
            context={"coords": f"{lat},{lng}", "purpose": "current"},
        )

        if not today_weather or (
            isinstance(today_weather, dict)
            and ("error" in today_weather or "error_code" in today_weather)
        ):
            return JSONResponse(
                {"status": "error", "message": "天気情報の取得に失敗しました"},
                status_code=500,
            )

        area_code = today_weather.get("area_code")
        
        # Redis から直接風速データを取得して追加
        wind_data = None
        try:
            import redis
            import json as json_lib
            _host = os.getenv("REDIS_HOST", "localhost")
            _port = int(os.getenv("REDIS_PORT", 6379))
            _db = int(os.getenv("REDIS_DB", 0))
            _prefix = os.getenv("REPORT_DB_KEY_PREFIX", os.getenv("REDIS_KEY_PREFIX", "")) or ""

            redis_client = redis.Redis(host=_host, port=_port, db=_db, decode_responses=True)
            redis_key = f"{_prefix}weather:{area_code}"
            
            # RedisJSONまたは通常のキーからデータを取得
            weather_info = None
            try:
                redis_data = redis_client.execute_command("JSON.GET", redis_key)
                if redis_data:
                    weather_info = json_lib.loads(redis_data)
            except Exception:
                pass
            if weather_info is None:
                raw = redis_client.get(redis_key)
                if raw:
                    try:
                        weather_info = json_lib.loads(raw)
                    except Exception:
                        weather_info = None
            
            if weather_info:
                wind_list = weather_info.get("wind", [])
                if wind_list and len(wind_list) > 0:
                    wind_data = wind_list[0]  # 今日の風速データ
        except Exception as e:
            logger.error(f"Error fetching wind data from Redis: {e}")
        
        # レスポンス作成
        today_data = _add_date_info(today_weather, 0)
        if wind_data:
            today_data["wind"] = wind_data
        
        return JSONResponse(
            {
                "status": "ok",
                "coordinates": {"lat": lat, "lng": lng},
                "area_code": area_code,
                "today": today_data,
            }
        )
    except Exception as e:  # pragma: no cover
        logger.error(f"Error in current_weather: {e}")
        return JSONResponse(
            {"status": "error", "message": "現在の天気情報の取得に失敗しました"},
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
