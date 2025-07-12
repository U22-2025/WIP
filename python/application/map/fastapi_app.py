import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from geopy.geocoders import Nominatim

# 直接実行時のパス調整
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from WIP_Client import Client

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

client = Client(host="localhost", port=4110, debug=True)
geolocator = Nominatim(user_agent="wip_map_app")

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


async def log_event(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] {message}"
    logger.info(msg)
    await manager.broadcast(msg)


# ----------------------------------------------------------------------
# Utility functions
# ----------------------------------------------------------------------

def get_address_from_coordinates(lat: float, lng: float) -> Optional[dict]:
    try:
        location = geolocator.reverse(f"{lat}, {lng}", timeout=10, language="ja")
        if location:
            address = location.address
            comps = location.raw.get("address", {})
            city = comps.get("city") or comps.get("town") or comps.get("village")
            return {
                "full_address": address,
                "prefecture": comps.get("state", ""),
                "city": city or "",
                "suburb": comps.get("suburb", ""),
                "neighbourhood": comps.get("neighbourhood", ""),
                "country": comps.get("country", ""),
                "postcode": comps.get("postcode", ""),
                "raw_components": comps,
            }
    except Exception as e:  # pragma: no cover - geopy errors
        logger.error(f"Error getting address: {e}")
    return None


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
# Routes
# ----------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    await log_event("GET /")
    return templates.TemplateResponse("map.html", {"request": request})


@app.post("/click")
async def click(request: Request):
    data = await request.json()
    lat = data.get("lat")
    lng = data.get("lng")
    await log_event(f"POST /click lat={lat} lng={lng}")

    client.set_coordinates(lat, lng)
    weather_result = client.get_weather()

    if not weather_result:
        return JSONResponse({"status": "error", "message": "天気情報の取得に失敗しました"}, status_code=500)

    if isinstance(weather_result, dict) and "error_code" in weather_result:
        return JSONResponse({"status": "error", "error_code": weather_result["error_code"], "message": "エラーパケットを受信しました"}, status_code=500)

    return JSONResponse({
        "status": "ok",
        "coordinates": {"lat": lat, "lng": lng},
        "weather": weather_result,
    })


@app.post("/get_address")
async def get_address(request: Request):
    data = await request.json()
    lat = data.get("lat")
    lng = data.get("lng")
    await log_event(f"POST /get_address lat={lat} lng={lng}")

    if lat is None or lng is None:
        return JSONResponse({"status": "error", "message": "緯度と経度が必要です"}, status_code=400)

    address_info = get_address_from_coordinates(lat, lng)
    if address_info:
        return JSONResponse({
            "status": "ok",
            "coordinates": {"lat": lat, "lng": lng},
            "address": address_info,
        })
    else:
        return JSONResponse({
            "status": "error",
            "message": "住所の取得に失敗しました",
            "coordinates": {"lat": lat, "lng": lng},
        }, status_code=404)


@app.post("/weekly_forecast")
async def weekly_forecast(request: Request):
    data = await request.json()
    lat = data.get("lat")
    lng = data.get("lng")
    await log_event(f"POST /weekly_forecast lat={lat} lng={lng}")

    if lat is None or lng is None:
        return JSONResponse({"status": "error", "message": "緯度と経度が必要です"}, status_code=400)

    try:
        client.set_coordinates(lat, lng)
        today_weather = client.get_weather(day=0)
        if not today_weather or (isinstance(today_weather, dict) and "error_code" in today_weather):
            return JSONResponse({"status": "error", "message": "今日の天気データの取得に失敗しました"}, status_code=500)

        area_code = today_weather.get("area_code")
        if not area_code:
            return JSONResponse({"status": "error", "message": "エリアコードが見つかりませんでした"}, status_code=500)

        weekly_forecast_list = []
        for day in range(7):
            try:
                base_date = datetime.now()
                target_date = base_date + timedelta(days=day)
                date_str = target_date.strftime("%Y-%m-%d")
                day_of_week = target_date.strftime("%A")

                if day == 0:
                    weather_data = today_weather.copy()
                else:
                    weather_data = client.get_weather_by_area_code(area_code=area_code, day=day)
                    if not weather_data or (isinstance(weather_data, dict) and "error_code" in weather_data):
                        weather_data = {
                            "weather_code": "100",
                            "temperature": "--",
                            "precipitation_prob": "--",
                            "area_code": area_code,
                        }

                weather_data["date"] = date_str
                weather_data["day_of_week"] = day_of_week
                weather_data["day"] = day
                weekly_forecast_list.append(weather_data)
            except Exception as e:  # pragma: no cover
                logger.error(f"Error getting weather for day {day}: {e}")
                target_date = datetime.now() + timedelta(days=day)
                dummy = {
                    "date": target_date.strftime("%Y-%m-%d"),
                    "day_of_week": target_date.strftime("%A"),
                    "weather_code": "100",
                    "temperature": "--",
                    "precipitation_prob": "--",
                    "area_code": area_code,
                    "day": day,
                }
                weekly_forecast_list.append(dummy)

        weekly_forecast_list.sort(key=lambda x: x["day"])
        return JSONResponse({
            "status": "ok",
            "coordinates": {"lat": lat, "lng": lng},
            "area_code": area_code,
            "weekly_forecast": weekly_forecast_list,
        })
    except Exception as e:  # pragma: no cover
        logger.error(f"Error in weekly_forecast: {e}")
        return JSONResponse({"status": "error", "message": "週間予報の取得に失敗しました"}, status_code=500)


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
