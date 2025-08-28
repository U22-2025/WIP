#!/usr/bin/env python3
"""
Scheduled Weather Reporter - 定期実行用天気/災害データレポーター

要件（プレビュー用特別仕様）:
- 全エリアコードの全気象情報を、毎日 05:00 / 11:00 / 17:00 にレポートサーバへ送信
- 全ての災害情報・注意報/警報を、10分間隔でAPIに問い合わせ、レポートサーバへ送信
- 全エリアコードは docs/area_codes.json を参照

実装方針:
- API から各エリアのデータを取得し、ReportClient で Type4 を送信
- 気象データ送信と災害/警報データ送信を別ジョブとしてスケジュール
"""

import json
import schedule
import time
import logging
import os
import sys
import signal
from pathlib import Path
from datetime import datetime

# 近傍ユーティリティを利用
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# src を import path に追加（リポジトリ相対）
try:
    repo_root = Path(__file__).resolve().parents[3]
    src_path = repo_root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
except Exception:
    pass

from push_api_to_report import fetch_api_weather  # API GET /weather 用
from WIPCommonPy.clients.report_client import ReportClient


class ScheduledWeatherReporter:
    """定期実行天気レポーター"""
    
    def __init__(self,
                 api_base_url: str = None,
                 report_server_host: str = "localhost",
                 report_server_port: int = 9999,
                 debug: bool = False,
                 area_codes_path: str = None):
        """
        初期化
        
        Args:
            api_base_url: 天気APIのベースURL（例: http://localhost:8001）
            report_server_host: レポートサーバーのホスト
            report_server_port: レポートサーバーのポート
            debug: デバッグモード
            area_codes_path: エリアコード定義JSONのパス（docs/area_codes.json を既定）
        """
        self.running = True
        self.debug = debug
        
        # ログ設定
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # API設定
        self.api_base_url = (api_base_url or os.getenv("WEATHER_API_BASE_URL")
                             or "http://localhost:8001").rstrip("/")

        # Report Server 宛先
        self.report_host = report_server_host
        self.report_port = report_server_port
        
        # エリアコード一覧（docs/area_codes.json を参照）
        self.area_codes = self._load_all_area_codes(area_codes_path)
        
        # シグナルハンドラー設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """シグナルハンドラー（Ctrl+C等での終了）"""
        self.logger.info(f"シグナル {signum} を受信しました。終了処理中...")
        self.running = False
    
    def _load_all_area_codes(self, area_codes_path: str | None) -> list[str]:
        """docs/area_codes.json から全てのエリアコード（トップレベルキー）を取得"""
        try:
            if area_codes_path:
                json_path = Path(area_codes_path)
            else:
                # ワークスペース基準の docs/area_codes.json
                # 本ファイルから二階層上へ辿って docs を解決
                repo_root = Path(__file__).resolve().parents[3]
                json_path = repo_root / "docs" / "area_codes.json"

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                codes = sorted(list(data.keys()))
                if not codes:
                    self.logger.warning("area_codes.json にエリアコードがありません")
                else:
                    self.logger.info(f"エリアコード読込: {len(codes)} 件")
                return codes
            else:
                self.logger.error("area_codes.json の形式が不正です（辞書を期待）")
                return []
        except Exception as e:
            self.logger.error(f"エリアコード読込エラー: {e}")
            return []

    def send_weather_all_areas(self):
        """全エリアの気象情報（天気/気温/降水/警報/災害）を送信"""
        try:
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"全エリア気象送信開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info('='*70)
            success = 0
            total = 0

            for area_code in self.area_codes:
                total += 1
                data = fetch_api_weather(self.api_base_url, area_code, day=0)
                if not data:
                    continue

                # ReportClient で送信（全フィールド）
                rc = ReportClient(host=self.report_host, port=self.report_port, debug=self.debug)
                try:
                    # 値の正規化（push_api_to_report と整合）
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
                    if res and res.get("success"):
                        success += 1
                finally:
                    rc.close()

                time.sleep(0.1)  # API/サーバー負荷を緩和

            rate = (success / max(total, 1)) * 100.0
            self.logger.info(f"全エリア気象送信完了: 成功 {success}/{total} ({rate:.1f}%)")

        except Exception as e:
            self.logger.error(f"全エリア気象送信中にエラー: {e}")
            if self.debug:
                self.logger.exception("エラー詳細:")

    def send_hazards_all_areas(self):
        """全エリアの災害/注意報・警報のみを10分間隔で送信"""
        try:
            self.logger.info(f"災害/警報送信(全エリア) 開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            sent = 0
            total = 0
            for area_code in self.area_codes:
                total += 1
                data = fetch_api_weather(self.api_base_url, area_code, day=0)
                if not data:
                    continue

                alerts = data.get("warnings") or []
                disasters = data.get("disaster") or []

                # 警報/災害のみセット（他は None）
                rc = ReportClient(host=self.report_host, port=self.report_port, debug=self.debug)
                try:
                    rc.set_sensor_data(
                        area_code=area_code,
                        weather_code=None,
                        temperature=None,
                        precipitation_prob=None,
                        alert=alerts,
                        disaster=disasters,
                    )
                    res = rc.send_report_data()
                    if res and res.get("success"):
                        sent += 1
                finally:
                    rc.close()

                time.sleep(0.1)

            self.logger.info(f"災害/警報送信完了: 成功 {sent}/{total}")
        except Exception as e:
            self.logger.error(f"災害/警報送信エラー: {e}")
    
    def setup_schedule(self):
        """スケジュール設定"""
        # 全エリア気象情報（1日3回: 05:00, 11:00, 17:00）
        schedule.every().day.at("05:00").do(self.send_weather_all_areas)
        schedule.every().day.at("11:00").do(self.send_weather_all_areas)
        schedule.every().day.at("17:00").do(self.send_weather_all_areas)

        # 災害/注意報・警報（10分間隔）
        schedule.every(10).minutes.do(self.send_hazards_all_areas)

        self.logger.info("スケジュール設定完了:")
        self.logger.info("  - 全エリア気象情報送信: 05:00, 11:00, 17:00")
        self.logger.info("  - 災害/警報送信: 10分間隔")
    
    def run_scheduler(self):
        """スケジューラー実行"""
        self.setup_schedule()
        self.logger.info("天気/災害データ定期レポーター開始")
        
        # 初回実行（起動時）
        self.logger.info("初回: 全エリア気象送信を実行...")
        self.send_weather_all_areas()
        
        # メインループ
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # 1分おきにチェック
            except KeyboardInterrupt:
                self.logger.info("キーボード割り込みを受信")
                break
            except Exception as e:
                self.logger.error(f"スケジューラーエラー: {e}")
                time.sleep(10)  # エラー時は10秒待機
        
        self.logger.info("天気/災害データ定期レポーター終了")
    
    def run_once(self):
        """一回だけ実行"""
        self.logger.info("一回限り: 全エリア気象送信を実行")
        self.send_weather_all_areas()
    
    def get_status(self):
        """現在の状態を取得"""
        return {
            "running": self.running,
            "area_count": len(self.area_codes),
            "next_run": schedule.next_run() if schedule.jobs else None,
            "total_jobs": len(schedule.jobs)
        }


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="天気/災害データ定期レポーター")
    parser.add_argument("--mode", choices=["schedule", "once"], default="schedule",
                       help="実行モード: schedule(定期実行) または once(一回限り)")
    parser.add_argument("--host", default="localhost", 
                       help="レポートサーバーホスト")
    parser.add_argument("--port", type=int, default=9999,
                       help="レポートサーバーポート") 
    parser.add_argument("--debug", action="store_true",
                       help="デバッグモード")
    parser.add_argument("--api-base-url", default=os.getenv("WEATHER_API_BASE_URL", "http://localhost:8001"),
                       help="天気APIベースURL（例: http://localhost:8001）")
    parser.add_argument("--area-codes-json", default=None,
                       help="エリアコード定義JSONのパス（既定: docs/area_codes.json）")
    
    args = parser.parse_args()
    
    # ScheduledWeatherReporterを初期化
    scheduler = ScheduledWeatherReporter(
        api_base_url=args.api_base_url,
        report_server_host=args.host,
        report_server_port=args.port,
        debug=args.debug,
        area_codes_path=args.area_codes_json,
    )
    
    print("Scheduled Weather/Disaster Reporter")
    print("="*50)
    print(f"モード: {args.mode}")
    print(f"レポートサーバー: {args.host}:{args.port}")
    print(f"API: {args.api_base_url}")
    print(f"デバッグ: {args.debug}")
    print("="*50)
    
    if args.mode == "once":
        # 一回限り実行
        scheduler.run_once()
    else:
        # 定期実行
        try:
            scheduler.run_scheduler()
        except KeyboardInterrupt:
            print("\n定期実行を停止しました")


if __name__ == "__main__":
    main()
