import os
import threading
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from WIPServerPy.data.alert_processor import AlertDataProcessor
from WIPServerPy.data.controllers.unified_data_processor import UnifiedDataProcessor


app = FastAPI(title="External Weather API", version="0.1.0")

# data directory
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
WEATHER_FILE = DATA_DIR / "weather_store.json"
HAZARD_FILE = DATA_DIR / "hazard_store.json"


class UpdateResponse(BaseModel):
    ok: bool
    detail: str


def _filter_weather_payload(
    payload: Optional[dict],
    *,
    weather_flag: bool,
    temperature_flag: bool,
    pop_flag: bool,
    alert_flag: bool,
    disaster_flag: bool,
    day: int,
) -> dict:
    if not payload:
        return {}

    result = {}
    # weather
    if weather_flag and "weather" in payload:
        wc = payload["weather"]
        result["weather"] = wc[day] if isinstance(wc, list) and len(wc) > day else wc
    # temperature
    if temperature_flag and "temperature" in payload:
        t = payload["temperature"]
        result["temperature"] = t[day] if isinstance(t, list) and len(t) > day else t
    # precipitation probability
    if pop_flag and "precipitation_prob" in payload:
        p = payload["precipitation_prob"]
        result["precipitation_prob"] = p[day] if isinstance(p, list) and len(p) > day else p
    # alerts
    if alert_flag and "warnings" in payload:
        result["warnings"] = payload.get("warnings", [])
    # disaster
    if disaster_flag and ("disaster" in payload or "disaster_info" in payload):
        result["disaster"] = payload.get("disaster") or payload.get("disaster_info") or []
    return result


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    tmp.replace(path)


def _select_midday_indices(time_defines: List[str]) -> List[int]:
    # JMA timeseries has many time points; choose one per day near 12:00
    date_to_indices: Dict[str, List[int]] = {}
    for idx, t in enumerate(time_defines):
        date = t[:10]
        date_to_indices.setdefault(date, []).append(idx)
    selected: List[int] = []
    removed: List[int] = []
    for _, indices in date_to_indices.items():
        if len(indices) == 1:
            selected.append(indices[0])
        else:
            min_diff = 999
            sel = indices[0]
            for i in indices:
                hour = int(time_defines[i][11:13])
                diff = abs(hour - 12)
                if diff < min_diff:
                    min_diff = diff
                    sel = i
            selected.append(sel)
            removed.extend([i for i in indices if i != sel])
    return selected, removed


def update_weather_json(area_codes: List[str]) -> None:
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=50, max_retries=3)
    session.mount("https://", adapter)
    timeout = 5.0

    store: Dict[str, Any] = {"weather_reportdatetime": {}}

    for area_code in area_codes:
        url = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        weather_areas = data[0]["timeSeries"][0]["areas"]
        pop_areas = data[0]["timeSeries"][1]["areas"]
        reporttime = data[0]["reportDatetime"]

        time_defines = data[0]["timeSeries"][0]["timeDefines"]
        selected, removed = _select_midday_indices(time_defines)

        parent_code = area_code
        for area in weather_areas:
            area_name = area["area"].get("name", "")
            code = area["area"].get("code")
            weather_codes = [c for i, c in enumerate(area.get("weatherCodes", [])) if i not in removed]

            # pick pops for same sub area code
            pop = []
            for p in pop_areas:
                if p.get("area", {}).get("code") == code:
                    pop = [v for i, v in enumerate(p.get("pops", [])) if i not in removed]
                    break

            # temps
            temps_max = []
            temp_avg = None
            if len(data) > 1:
                temp_avg_areas = data[1].get("tempAverage", {}).get("areas", [])
                for avg_area in temp_avg_areas:
                    try:
                        min_val_str = avg_area.get("min", "")
                        max_val_str = avg_area.get("max", "")
                        if min_val_str != "" and max_val_str != "":
                            min_val = int(float(min_val_str))
                            max_val = int(float(max_val_str))
                            temp_avg = int((min_val + max_val) / 2)
                        else:
                            temp_avg = ""
                    except Exception:
                        temp_avg = ""
                    break
                if "timeSeries" in data[1] and len(data[1]["timeSeries"]) > 1:
                    temps_max_areas = data[1]["timeSeries"][1].get("areas", [])
                    for tmax_area in temps_max_areas:
                        temps_max = tmax_area.get("tempsMax", [])
                        break

            temps: List[str] = []
            temps.append(str(temp_avg) if (temp_avg is not None and temp_avg != "") else "")
            temps += temps_max[-6:] if temps_max else [""] * 6
            temps = temps[:7]

            # fallback fill from broader area if insufficient
            week_days = 7
            if len(weather_codes) < week_days or len(pop) < week_days:
                if len(data) > 1 and "timeSeries" in data[1]:
                    ts = data[1]["timeSeries"]
                    for sub_area in ts[0]["areas"]:
                        if sub_area["area"]["code"][:2] == code[:2]:
                            if len(weather_codes) < week_days:
                                add_codes = sub_area.get("weatherCodes", [])
                                weather_codes += add_codes[len(weather_codes):week_days]
                            if len(pop) < week_days:
                                add_pop = sub_area.get("pops", [])
                                pop += add_pop[len(pop):week_days]
                            break

            store[code] = {
                "parent_code": parent_code,
                "area_name": area_name,
                "weather": weather_codes,
                "temperature": temps,
                "precipitation_prob": pop,
            }

        store["weather_reportdatetime"][area_code] = reporttime

    _save_json(WEATHER_FILE, store)


def update_hazard_json() -> None:
    # Alerts
    alert_proc = AlertDataProcessor()
    alert_urls = alert_proc.xml_processor.get_alert_xml_list()
    alert_result = alert_proc.get_alert_info(alert_urls)

    # Disasters/Earthquakes
    unified = UnifiedDataProcessor()
    url_list = unified.get_xml_list()
    disaster_json, earthquake_json = unified.process_unified_data(url_list)

    # convert to area codes and merge
    script_dir = Path(__file__).resolve().parent.parent  # python/application
    # area codes data: use JMA area.json via create_area_codes_json logic on the fly
    try:
        area_json = requests.get("https://www.jma.go.jp/bosai/common/const/area.json", timeout=5).json()
    except Exception:
        area_json = {"offices": {}, "class10s": {}, "class15s": {}}

    # unify keys
    try:
        disaster_dict = json.loads(disaster_json) if isinstance(disaster_json, str) else disaster_json
    except Exception:
        disaster_dict = {}
    try:
        earthquake_dict = json.loads(earthquake_json) if isinstance(earthquake_json, str) else earthquake_json
    except Exception:
        earthquake_dict = {}

    disaster_converted, disaster_report_times = unified.convert_disaster_keys_to_area_codes(
        disaster_dict, area_json
    )
    earthquake_converted, earthquake_report_times = unified.convert_earthquake_keys_to_area_codes(
        earthquake_dict, area_json
    )

    disaster_final = unified.format_to_alert_style(
        disaster_converted, disaster_report_times, area_json, "disaster"
    ) if disaster_converted else {}
    earthquake_final = unified.format_to_alert_style(
        earthquake_converted, earthquake_report_times, area_json, "earthquake"
    ) if earthquake_converted else {}

    merged_disaster = unified.merge_earthquake_into_disaster(disaster_final, earthquake_final)

    # hazard store: combine alerts and disaster by area_code
    store: Dict[str, Any] = {}
    if isinstance(alert_result, dict):
        for k, v in alert_result.items():
            store.setdefault(k, {})
            if k == "alert_pulldatetime":
                store[k] = v
            else:
                store[k]["warnings"] = v.get("alert_info", [])
    for k, v in merged_disaster.items():
        if k == "disaster_pulldatetime":
            store[k] = v
        else:
            store.setdefault(k, {})
            store[k]["disaster"] = v.get("disaster", [])

    _save_json(HAZARD_FILE, store)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/areas")
def list_areas() -> list[str]:
    """保存済みの全エリアコード一覧を返す。"""
    weather_store = _load_json(WEATHER_FILE)
    hazard_store = _load_json(HAZARD_FILE)
    keys = set()
    for k in list(weather_store.keys()) + list(hazard_store.keys()):
        if not k:
            continue
        if k.endswith("_pulldatetime") or k.endswith("_reportdatetime"):
            continue
        if k.isdigit() and len(k) == 6:
            keys.add(k)
    return sorted(keys)


@app.get("/weather")
def get_weather(
    area_code: str,
    day: int = 0,
    weather_flag: int = 1,
    temperature_flag: int = 1,
    pop_flag: int = 1,
    alert_flag: int = 1,
    disaster_flag: int = 1,
) -> dict:
    if not area_code or len(area_code) < 1:
        raise HTTPException(status_code=400, detail="area_code is required")

    try:
        weather_store = _load_json(WEATHER_FILE)
        hazard_store = _load_json(HAZARD_FILE)
        payload = weather_store.get(area_code, {})
        # merge hazards
        hazards = hazard_store.get(area_code, {}) if (alert_flag or disaster_flag) else {}
        if hazards:
            if alert_flag and "warnings" in hazards:
                payload["warnings"] = hazards["warnings"]
            if disaster_flag and "disaster" in hazards:
                payload["disaster"] = hazards["disaster"]
        return _filter_weather_payload(
            payload,
            weather_flag=bool(weather_flag),
            temperature_flag=bool(temperature_flag),
            pop_flag=bool(pop_flag),
            alert_flag=bool(alert_flag),
            disaster_flag=bool(disaster_flag),
            day=max(0, min(day, 6)),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"fetch error: {e}")


@app.post("/update/weather", response_model=UpdateResponse)
def update_weather() -> UpdateResponse:
    try:
        # 監視対象のオフィスコード一覧（例: 130000=東京地方）を環境変数で指定
        offices = os.getenv("WEATHER_API_TARGET_OFFICES", "130000").split(",")
        offices = [s.strip() for s in offices if s.strip()]
        update_weather_json(offices)
        return UpdateResponse(ok=True, detail=f"updated weather for {len(offices)} offices")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/update/disaster", response_model=UpdateResponse)
def update_disaster() -> UpdateResponse:
    try:
        update_hazard_json()
        return UpdateResponse(ok=True, detail="disaster/alert updated")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _scheduler_loop() -> None:
    # 簡易スケジューラ: 指定間隔で更新実行（デフォルト:10分）
    weather_interval = int(os.getenv("WEATHER_API_WEATHER_INTERVAL_MIN", "180"))
    disaster_interval = int(os.getenv("WEATHER_API_DISASTER_INTERVAL_MIN", "10"))
    w_next = time.time()
    d_next = time.time()
    while True:
        now = time.time()
        try:
            if now >= w_next:
                try:
                    offices = os.getenv("WEATHER_API_TARGET_OFFICES", "130000").split(",")
                    offices = [s.strip() for s in offices if s.strip()]
                    update_weather_json(offices)
                except Exception:
                    pass
                w_next = now + weather_interval * 60
            if now >= d_next:
                try:
                    update_hazard_json()
                except Exception:
                    pass
                d_next = now + disaster_interval * 60
        finally:
            time.sleep(10)


@app.on_event("startup")
def on_startup() -> None:
    if os.getenv("WEATHER_API_SCHEDULE_ENABLED", "true").lower() == "true":
        t = threading.Thread(target=_scheduler_loop, daemon=True)
        t.start()
    # 初回更新（非同期）
    def _initial_update():
        try:
            offices = os.getenv("WEATHER_API_TARGET_OFFICES", "130000").split(",")
            offices = [s.strip() for s in offices if s.strip()]
            update_weather_json(offices)
        except Exception:
            pass
        try:
            update_hazard_json()
        except Exception:
            pass
    threading.Thread(target=_initial_update, daemon=True).start()
