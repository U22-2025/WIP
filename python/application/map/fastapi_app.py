import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
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
from WIP_Client import ClientAsync

# ドキュメントエンドポイントを有効化
app = FastAPI()
script_dir = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(script_dir / "static")), name="static")
templates = Jinja2Templates(directory=str(script_dir / "templates"))

WEATHER_SERVER_HOST = os.getenv("WEATHER_SERVER_HOST", "localhost")
WEATHER_SERVER_PORT = int(os.getenv("WEATHER_SERVER_PORT", 4110))

logger = logging.getLogger("fastapi_app")
logging.basicConfig(level=logging.INFO)


class ConnectionManager:
    def __init__(self) -> None:
        self.active: List[WebSocket] = []
        self.logs: List[str] = []

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
        for ws in list(self.active):
            try:
                await ws.send_text(message)
            except WebSocketDisconnect:
                self.disconnect(ws)


manager = ConnectionManager()


class Coordinates(BaseModel):
    """リクエストボディ用の座標モデル"""

    lat: float
    lng: float


async def log_event(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    logger.info(msg)
    await manager.broadcast(msg)


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

async def get_client() -> ClientAsync:
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
        today_weather = await client.get_weather(day=0)
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
                weather_data = await client.get_weather_by_area_code(
                    area_code=area_code, day=day
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
