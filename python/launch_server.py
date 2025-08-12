import os
import sys
import time
import threading
import argparse
import subprocess
from typing import List, Tuple

from WIPServerPy import QueryServer, LocationServer, WeatherServer, ReportServer


def _start_process(name: str, cmd: List[str]) -> subprocess.Popen:
    print(f"{name} を起動しています...\n  cmd: {' '.join(cmd)}")
    # ルートディレクトリ（このファイルの2階層上が WIP 直下）を起点に実行
    cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = os.environ.copy()
    # Windows でも Python 実行パスを明示
    return subprocess.Popen([sys.executable] + cmd, cwd=cwd, env=env)


def main():
    parser = argparse.ArgumentParser(description="WIPサーバー起動スクリプト")
    parser.add_argument(
        "--server",
        choices=["query", "location", "weather", "report"],
        help="起動するサーバーを指定 (query, location, weather, report)",
    )
    parser.add_argument("--query", action="store_true", help="Queryサーバーを起動")
    parser.add_argument(
        "--location", action="store_true", help="Locationサーバーを起動"
    )
    parser.add_argument("--weather", action="store_true", help="Weatherサーバーを起動")
    parser.add_argument("--report", action="store_true", help="Reportサーバーを起動")
    # 追加: アプリ系（Map/外部Weather API）
    parser.add_argument("--map", action="store_true", help="Map FastAPI を起動")
    parser.add_argument("--api", action="store_true", help="外部Weather API を起動")
    parser.add_argument(
        "--apps",
        action="store_true",
        help="Map と 外部Weather API を一括起動",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="すべて起動（Weather/Query/Location/Report + Map + API）",
    )
    parser.add_argument("--debug", action="store_true", help="デバッグモードで起動")
    parser.add_argument(
        "--noupdate",
        action="store_true",
        help="Queryサーバーの起動時自動更新をスキップ",
    )

    args = parser.parse_args()

    # 起動するサーバーを決定
    servers_to_start: List[str] = []

    # アプリ起動フラグ
    start_map = False
    start_api = False

    if args.server:
        # --server オプションが指定された場合
        if args.server == "query":
            servers_to_start.append("query")
        elif args.server == "location":
            servers_to_start.append("location")
        elif args.server == "weather":
            servers_to_start.append("weather")
        elif args.server == "report":
            servers_to_start.append("report")
    else:
        # 個別のフラグをチェック
        if args.query:
            servers_to_start.append("query")
        if args.location:
            servers_to_start.append("location")
        if args.weather:
            servers_to_start.append("weather")
        if args.report:
            servers_to_start.append("report")
        if args.apps:
            start_map = True
            start_api = True
        if args.map:
            start_map = True
        if args.api:
            start_api = True

    # --all の場合は全て起動
    if args.all:
        servers_to_start = ["query", "location", "weather", "report"]
        start_map = True
        start_api = True

    # 何も指定されていない場合はコアサーバーのみを起動（従来仕様踏襲）
    if not servers_to_start and not (start_map or start_api):
        servers_to_start = ["query", "location", "weather", "report"]
        print("引数が指定されていないため、コアサーバーを起動します。")

    label = ", ".join(servers_to_start) if servers_to_start else "(なし)"
    apps_label = ", ".join([n for n, f in (("map", start_map), ("api", start_api)) if f]) or "(なし)"
    print(f"起動するサーバー: {label}")
    print(f"起動するアプリ: {apps_label}")

    # サーバーインスタンスとスレッドを格納するリスト
    servers = {}
    threads = []
    processes: List[Tuple[str, subprocess.Popen]] = []

    # デバッグモードの表示
    if args.debug:
        print("デバッグモードが有効です。")

    # 選択されたサーバーを起動
    if "query" in servers_to_start:
        debug_msg = " (デバッグモード)" if args.debug else ""
        print(f"Query Serverを起動しています...{debug_msg}")
        if args.noupdate:
            print("  ※起動時自動更新をスキップします")
        servers["query"] = QueryServer(debug=args.debug, noupdate=args.noupdate)
        query_thread = threading.Thread(target=servers["query"].run, name="QueryServer")
        threads.append(query_thread)
        query_thread.start()

    if "location" in servers_to_start:
        debug_msg = " (デバッグモード)" if args.debug else ""
        print(f"Location Serverを起動しています...{debug_msg}")
        servers["location"] = LocationServer(debug=args.debug)
        location_thread = threading.Thread(
            target=servers["location"].run, name="LocationServer"
        )
        threads.append(location_thread)
        location_thread.start()

    if "weather" in servers_to_start:
        debug_msg = " (デバッグモード)" if args.debug else ""
        print(f"Weather Serverを起動しています...{debug_msg}")
        servers["weather"] = WeatherServer(debug=args.debug)
        weather_thread = threading.Thread(
            target=servers["weather"].run, name="WeatherServer"
        )
        threads.append(weather_thread)
        weather_thread.start()

    if "report" in servers_to_start:
        debug_msg = " (デバッグモード)" if args.debug else ""
        print(f"Report Serverを起動しています...{debug_msg}")
        servers["report"] = ReportServer(debug=args.debug)
        report_thread = threading.Thread(
            target=servers["report"].run, name="ReportServer"
        )
        threads.append(report_thread)
        report_thread.start()

    # 追加: Map / External Weather API をサブプロセスで起動
    if start_map:
        proc = _start_process(
            "Map FastAPI Server",
            ["python/application/map/start_fastapi_server.py"],
        )
        processes.append(("map", proc))

    if start_api:
        proc = _start_process(
            "External Weather API",
            ["python/application/weather_api/start_fastapi_server.py"],
        )
        processes.append(("api", proc))

    print(f"{len(threads)}個のサーバー、{len(processes)}個のアプリを起動しました。")
    if start_map:
        print("  Map:     http://localhost:5000")
    if start_api:
        port = os.getenv("WEATHER_API_PORT", "8001")
        print(f"  Weather API: http://localhost:{port}")
    print("サーバー/アプリを停止するには Ctrl+C を押してください。")

    # 全てのスレッドが終了するまで待機
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\nサーバー/アプリを停止しています...")
    finally:
        # サブプロセスを終了
        for name, proc in processes:
            if proc.poll() is None:
                try:
                    print(f"{name} を終了しています...")
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
