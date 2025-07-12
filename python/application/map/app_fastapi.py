from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import json
import sys
import os

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from WIP_Client import Client

app = FastAPI()
client = Client(host="localhost", port=4110, debug=True)

base_dir = Path(__file__).parent
templates = Jinja2Templates(directory=str(base_dir / "templates"))
app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")
JSON_DIR = Path(__file__).resolve().parents[2] / "wip" / "json"

geolocator = Nominatim(user_agent="wip_map_app")


def get_address_from_coordinates(lat: float, lng: float):
    try:
        location = geolocator.reverse(f"{lat}, {lng}", timeout=10, language="ja")
        if location:
            address_components = location.raw.get("address", {})
            prefecture = address_components.get("state", "")
            city = address_components.get("city", "") or address_components.get("town", "") or address_components.get("village", "")
            suburb = address_components.get("suburb", "")
            country = address_components.get("country", "")
            return {
                "full_address": location.address,
                "prefecture": prefecture,
                "city": city,
                "suburb": suburb,
                "country": country,
            }
        return None
    except (GeocoderTimedOut, GeocoderServiceError):
        return None
    except Exception:
        return None


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("map.html", {"request": request})


@app.get("/weather_code.json")
async def weather_code():
    try:
        with open(JSON_DIR / "weather_code.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(data.get("codes", {}))
    except Exception:
        return JSONResponse({
            "100": "晴れ",
            "200": "くもり",
            "300": "雨",
            "400": "雪",
        })


@app.get("/error_code.json")
async def error_code_json():
    return FileResponse(JSON_DIR / "error_code.json")


@app.post("/click")
async def click(request: Request):
    data = await request.json()
    lat = data.get("lat")
    lng = data.get("lng")
    client.set_coordinates(lat, lng)
    weather_result = client.get_weather()
    if not weather_result:
        raise HTTPException(status_code=500, detail="天気情報の取得に失敗しました")
    if isinstance(weather_result, dict) and "error_code" in weather_result:
        raise HTTPException(status_code=500, detail="エラーパケットを受信しました")
    return {
        "status": "ok",
        "coordinates": {"lat": lat, "lng": lng},
        "weather": weather_result,
    }


@app.post("/get_address")
async def get_address(request: Request):
    data = await request.json()
    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="緯度と経度が必要です")
    address_info = get_address_from_coordinates(lat, lng)
    if address_info:
        return {
            "status": "ok",
            "coordinates": {"lat": lat, "lng": lng},
            "address": address_info,
        }
    raise HTTPException(status_code=404, detail="住所の取得に失敗しました")


def _add_date_info(weather_data, day_offset=0):
    base_date = datetime.now()
    target_date = base_date + timedelta(days=day_offset)
    weekday_en = target_date.strftime("%A")
    weather_data["date"] = target_date.strftime("%Y-%m-%d")
    weather_data["day_of_week"] = weekday_en
    weather_data["day"] = day_offset
    return weather_data


def _create_fallback_weather_data(area_code, days_offset=0):
    date = datetime.now() + timedelta(days=days_offset)
    return {
        "date": date.strftime("%Y-%m-%d"),
        "day_of_week": date.strftime("%A"),
        "weather_code": "100",
        "temperature": "--",
        "precipitation_prob": "--",
        "area_code": area_code,
    }


@app.post("/weekly_forecast")
async def weekly_forecast(request: Request):
    data = await request.json()
    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        raise HTTPException(status_code=400, detail="緯度と経度が必要です")
    try:
        client.set_coordinates(lat, lng)
        today_weather = client.get_weather(day=0)
        if not today_weather or (isinstance(today_weather, dict) and "error_code" in today_weather):
            raise RuntimeError("今日の天気データの取得に失敗しました")
        if "area_code" not in today_weather:
            raise RuntimeError("エリアコードが見つかりませんでした")
        area_code = today_weather["area_code"]
        weekly_forecast_list = []
        for day in range(7):
            try:
                base_date = datetime.now()
                target_date = base_date + timedelta(days=day)
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
                weather_data["date"] = target_date.strftime("%Y-%m-%d")
                weather_data["day_of_week"] = target_date.strftime("%A")
                weather_data["day"] = day
                weekly_forecast_list.append(weather_data)
            except Exception:
                weekly_forecast_list.append(_create_fallback_weather_data(area_code, day))
        weekly_forecast_list.sort(key=lambda x: x["day"])
        return {
            "status": "ok",
            "coordinates": {"lat": lat, "lng": lng},
            "area_code": area_code,
            "weekly_forecast": weekly_forecast_list,
        }
    except Exception:
        raise HTTPException(status_code=500, detail="週間予報の取得に失敗しました")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app_fastapi:app", host="0.0.0.0", port=5000, reload=True)
