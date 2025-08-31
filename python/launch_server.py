import os
import sys
import time
import threading
import argparse
import subprocess
from typing import List, Tuple
from pathlib import Path

from WIPServerPy import QueryServer, LocationServer, WeatherServer, ReportServer


def _start_jma_auto_update(debug: bool = False):
    """JMAからの自動データ更新プロセスを起動"""
    try:
        # 起動時に一度実行
        print("JMA初回データ更新を実行しています...")
        _run_jma_update_once(debug)
        
        # 定期実行用のデーモンスレッドを開始
        update_thread = threading.Thread(
            target=_jma_update_scheduler,
            args=(debug,),
            daemon=True,
            name="JMA-Auto-Updater"
        )
        update_thread.start()
        print("JMA自動データ更新スケジューラを開始しました")
        
    except Exception as e:
        print(f"JMA自動更新の開始に失敗しました: {e}")


def _run_jma_update_once(debug: bool = False):
    """JMAデータの一回限り更新を実行"""
    try:
        # ワーキングディレクトリをプロジェクトルートに設定
        cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        env = os.environ.copy()
        env["PYTHONPATH"] = cwd + os.pathsep + env.get("PYTHONPATH", "")
        
        # 気象データ更新
        print("  気象データを更新中...")
        result = subprocess.run(
            [sys.executable, "-c", 
             "import sys; sys.path.insert(0, 'src'); from WIPServerPy.scripts.update_weather_data import update_redis_weather_data; from WIPServerPy.data.get_codes import get_all_area_codes; codes = get_all_area_codes(); update_redis_weather_data(debug=False, area_codes=codes)"],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5分でタイムアウト
        )
        
        if result.returncode == 0:
            print("  気象データ更新完了")
        else:
            print(f"  気象データ更新エラー: {result.stderr}")
        
        # 災害・警報データ更新
        print("  災害・警報データを更新中...")
        result = subprocess.run(
            [sys.executable, "-c", 
             "import sys; sys.path.insert(0, 'src'); from WIPServerPy.scripts.update_alert_disaster_data import main; main()"],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5分でタイムアウト
        )
        
        if result.returncode == 0:
            print("  災害・警報データ更新完了")
        else:
            print(f"  災害・警報データ更新エラー: {result.stderr}")
            
        print("JMAデータ更新が完了しました")
        
    except subprocess.TimeoutExpired:
        print("JMAデータ更新がタイムアウトしました")
    except Exception as e:
        print(f"JMAデータ更新エラー: {e}")


def _jma_update_scheduler(debug: bool = False):
    """JMAデータの定期更新スケジューラ"""
    import schedule
    
    # 気象データ更新: 1日3回（5:00, 11:00, 17:00）
    schedule.every().day.at("05:00").do(_run_jma_update_once, debug)
    schedule.every().day.at("11:00").do(_run_jma_update_once, debug)
    schedule.every().day.at("17:00").do(_run_jma_update_once, debug)
    
    # 災害・警報データ更新: 10分間隔
    def update_disaster_only():
        try:
            cwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            env = os.environ.copy()
            env["PYTHONPATH"] = cwd + os.pathsep + env.get("PYTHONPATH", "")
            
            result = subprocess.run(
                [sys.executable, "-c", 
                 "import sys; sys.path.insert(0, 'src'); from WIPServerPy.scripts.update_alert_disaster_data import main; main()"],
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if debug and result.returncode != 0:
                print(f"災害データ更新エラー: {result.stderr}")
                
        except Exception as e:
            if debug:
                print(f"災害データ更新エラー: {e}")
    
    schedule.every(10).minutes.do(update_disaster_only)
    
    print("JMAデータ更新スケジュール設定完了:")
    print("  - 気象データ: 05:00, 11:00, 17:00")
    print("  - 災害・警報データ: 10分間隔")
    
    # メインループ
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 1分間隔でチェック
        except Exception as e:
            if debug:
                print(f"JMAスケジューラーエラー: {e}")
            time.sleep(60)


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
        help="JMA自動データ更新、Queryサーバーの起動時自動更新とScheduled Weather Reporterをスキップ",
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

    # 何も指定されていない場合はすべて（コア＋アプリ）を起動
    if not servers_to_start and not (start_map or start_api):
        servers_to_start = ["query", "location", "weather", "report"]
        start_map = True
        start_api = True
        print("引数が指定されていないため、全てのサーバーとアプリを起動します。")

    label = ", ".join(servers_to_start) if servers_to_start else "(なし)"
    apps_label = ", ".join([n for n, f in (("map", start_map), ("api", start_api)) if f]) or "(なし)"
    print(f"起動するサーバー: {label}")
    print(f"起動するアプリ: {apps_label}")

    # サーバーインスタンスとスレッドを格納するリスト
    servers = {}
    threads = []
    processes: List[Tuple[str, subprocess.Popen]] = []
    processes_lock = threading.Lock()  # processes リストの同期用

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

    # Map 側で /api に Weather API をマウントしているため、
    # 両方要求された場合は API の単独起動はスキップして競合を防止
    if start_api and not start_map:
        # 公式起動スクリプトを使用（デフォルトでポート8001）
        proc = _start_process(
            "External Weather API",
            ["python/application/weather_api/start_server.py"],
        )
        processes.append(("api", proc))

    # JMA自動更新プロセスを起動（--noupdateが指定されていない場合のみ）
    if not args.noupdate and ("query" in servers_to_start or "report" in servers_to_start or args.all):
        _start_jma_auto_update(args.debug)
        
        # Scheduled Weather Reporterを起動（APIサーバの起動を待つため遅延起動）
        if start_api or start_map:
            # APIサーバが起動するまで3秒待機
            def delayed_reporter_start():
                time.sleep(3)
                print("Weather APIの起動完了を待って、Scheduled Weather Reporterを開始します...")
                proc = _start_process(
                    "Scheduled Weather Reporter",
                    ["python/application/tools/scheduled_weather_reporter.py", "--mode", "schedule"],
                )
                with processes_lock:
                    processes.append(("scheduled_reporter", proc))
            
            reporter_thread = threading.Thread(target=delayed_reporter_start, daemon=True)
            reporter_thread.start()
        else:
            # APIサーバを起動しない場合は通常通り起動
            proc = _start_process(
                "Scheduled Weather Reporter",
                ["python/application/tools/scheduled_weather_reporter.py", "--mode", "schedule"],
            )
            processes.append(("scheduled_reporter", proc))

    total_processes = len(processes)
    print(f"{len(threads)}個のサーバー、{total_processes}個のアプリを起動しました。")
    if start_map:
        print("  Map:           http://localhost")
        print("  Weather API:   http://localhost/api")
    elif start_api:
        port = os.getenv("WEATHER_API_PORT", "80")
        print(f"  Weather API:   http://localhost:{port}/api (エイリアス: /weather)")
    print("サーバー/アプリを停止するには Ctrl+C を押してください。")

    # 停止処理と待機
    try:
        if threads:
            # サーバースレッドがある場合はそれらを待機
            for thread in threads:
                thread.join()
        elif processes:
            # サーバーが無くアプリのみ起動の場合、プロセスが終了するまで待機
            while True:
                with processes_lock:
                    alive = any(proc.poll() is None for _, proc in processes)
                if not alive:
                    break
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nサーバー/アプリを停止しています...")
    finally:
        # サブプロセスを終了
        with processes_lock:
            processes_copy = list(processes)
        for name, proc in processes_copy:
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
