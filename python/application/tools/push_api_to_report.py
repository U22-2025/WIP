import os
import sys
import time
from typing import List, Optional

import requests

from WIPCommonPy.clients.report_client import ReportClient


def fetch_api_weather(base_url: str, area_code: str, day: int = 0) -> Optional[dict]:
    try:
        url = base_url.rstrip("/") + "/weather"
        params = dict(
            area_code=area_code,
            day=day,
            weather_flag=1,
            temperature_flag=1,
            pop_flag=1,
            alert_flag=1,
            disaster_flag=1,
        )
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"API fetch failed for {area_code}: {e}")
        return None


def send_to_report(report_host: str, report_port: int, area_code: str, data: dict, debug: bool=False) -> None:
    rc = ReportClient(host=report_host, port=report_port, debug=debug)

    # normalize fields
    def pick(v):
        if v is None:
            return None
        if isinstance(v, list):
            return v[0] if v else None
        return v

    weather_code = pick(data.get("weather"))
    # temperature may be string; convert if numeric
    t = pick(data.get("temperature"))
    try:
        temperature = int(t) if t not in (None, "") else None
    except Exception:
        temperature = None
    pop = pick(data.get("precipitation_prob"))
    try:
        precipitation_prob = int(pop) if pop not in (None, "") else None
    except Exception:
        precipitation_prob = None
    alerts = data.get("warnings") or []
    disasters = data.get("disaster") or []

    rc.set_sensor_data(
        area_code=area_code,
        weather_code=weather_code,
        temperature=temperature,
        precipitation_prob=precipitation_prob,
        alert=alerts,
        disaster=disasters,
    )
    res = rc.send_report_data()
    if not res or not res.get("success"):
        print(f"Report send failed for {area_code}: {res}")


def main() -> None:
    base_url = os.getenv("WEATHER_API_BASE_URL", "http://localhost:8001")
    # 全エリアコードをAPIから取得
    try:
        r = requests.get(base_url.rstrip('/') + "/areas", timeout=10)
        r.raise_for_status()
        area_codes: List[str] = r.json() or []
    except Exception as e:
        print(f"Failed to fetch areas: {e}")
        return

    report_host = os.getenv("REPORT_SERVER_HOST", "localhost")
    report_port = int(os.getenv("REPORT_SERVER_PORT", "4112"))
    debug = os.getenv("WIP_DEBUG", "false").lower() == "true"

    for ac in area_codes:
        data = fetch_api_weather(base_url, ac, day=0)
        if data is None:
            continue
        send_to_report(report_host, report_port, ac, data, debug)
        time.sleep(0.1)


if __name__ == "__main__":
    main()
