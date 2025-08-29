import os
import sys
import time
import argparse
from typing import List, Optional

from dotenv import load_dotenv
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

    w = pick(data.get("weather"))
    try:
        weather_code = int(w) if w not in (None, "") else None
    except Exception:
        weather_code = None
    
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
    # .env を読込（存在しなければ無視）
    try:
        load_dotenv()  # override=False 既定
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="Push External Weather API data to ReportServer")
    parser.add_argument("--base-url", dest="base_url", default=os.getenv("WEATHER_API_BASE_URL", "http://localhost/api"), help="External Weather API base URL (default: env WEATHER_API_BASE_URL or http://localhost/api)")
    parser.add_argument("--host", dest="report_host", default=os.getenv("REPORT_SERVER_HOST", "localhost"), help="ReportServer host (default: env REPORT_SERVER_HOST or localhost)")
    parser.add_argument("--port", dest="report_port", type=int, default=int(os.getenv("REPORT_SERVER_PORT", "4112")), help="ReportServer port (default: env REPORT_SERVER_PORT or 4112)")
    parser.add_argument("--delay", dest="delay", type=float, default=float(os.getenv("PUSH_DELAY_SEC", "0.1")), help="Delay seconds between sends (default: 0.1)")
    parser.add_argument("--limit", dest="limit", type=int, default=0, help="Limit number of area codes to send (0=all)")
    parser.add_argument("--day", dest="day", type=int, default=0, help="Forecast day index (0-6), default 0")
    parser.add_argument("--debug", dest="debug", action="store_true", help="Enable debug logs (also respects WIP_DEBUG=true)")

    args = parser.parse_args()

    # debug フラグ決定
    debug = args.debug or (os.getenv("WIP_DEBUG", "false").lower() == "true")

    base_url = args.base_url
    report_host = args.report_host
    report_port = args.report_port
    delay = args.delay
    day = max(0, min(args.day, 6))

    print("Push settings:")
    print(f"  WEATHER_API_BASE_URL = {base_url}")
    print(f"  REPORT_SERVER_HOST   = {report_host}")
    print(f"  REPORT_SERVER_PORT   = {report_port}")
    print(f"  DAY                  = {day}")
    print(f"  DELAY_SEC            = {delay}")
    print(f"  DEBUG                = {debug}")

    # 全エリアコードをAPIから取得
    try:
        r = requests.get(base_url.rstrip('/') + "/areas", timeout=10)
        r.raise_for_status()
        area_codes: List[str] = r.json() or []
    except Exception as e:
        print(f"Failed to fetch areas from {base_url}/areas: {e}")
        return

    if args.limit and args.limit > 0:
        area_codes = area_codes[: args.limit]

    print(f"Areas to send: {len(area_codes)}")
    if area_codes:
        preview = ", ".join(area_codes[:5])
        print(f"  First areas: {preview}{' ...' if len(area_codes) > 5 else ''}")

    for ac in area_codes:
        data = fetch_api_weather(base_url, ac, day=day)
        if data is None:
            continue
        send_to_report(report_host, report_port, ac, data, debug)
        if delay > 0:
            time.sleep(delay)


if __name__ == "__main__":
    main()
