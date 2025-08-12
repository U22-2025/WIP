#!/usr/bin/env python3
"""
Scheduled Weather Reporter - 定期実行用天気データレポーター

このスクリプトはweather_api_reporter.pyを定期実行し、
継続的に天気データをレポートサーバーに送信します。
"""

import schedule
import time
import logging
import os
import sys
import signal
from datetime import datetime

# 同じディレクトリのweather_api_reporterをインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from weather_api_reporter import WeatherAPIReporter


class ScheduledWeatherReporter:
    """定期実行天気レポーター"""
    
    def __init__(self, 
                 api_key: str = None,
                 report_server_host: str = "localhost", 
                 report_server_port: int = 9999,
                 debug: bool = False):
        """
        初期化
        
        Args:
            api_key: 天気APIのキー
            report_server_host: レポートサーバーのホスト
            report_server_port: レポートサーバーのポート 
            debug: デバッグモード
        """
        self.running = True
        self.debug = debug
        
        # ログ設定
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # WeatherAPIReporterインスタンス
        self.reporter = WeatherAPIReporter(
            api_key=api_key,
            report_server_host=report_server_host,
            report_server_port=report_server_port,
            debug=debug
        )
        
        # 対象都市（設定可能）
        self.target_cities = [
            "Tokyo", "Osaka", "Kyoto", "Sapporo", 
            "Fukuoka", "Sendai", "Hiroshima", "Nagoya"
        ]
        
        # シグナルハンドラー設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """シグナルハンドラー（Ctrl+C等での終了）"""
        self.logger.info(f"シグナル {signum} を受信しました。終了処理中...")
        self.running = False
    
    def update_all_cities(self):
        """全都市の天気データを更新"""
        try:
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"定期更新開始: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.logger.info('='*70)
            
            results = self.reporter.process_multiple_cities(self.target_cities)
            
            # 統計情報
            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)
            success_rate = (success_count / total_count * 100) if total_count > 0 else 0
            
            self.logger.info(f"\n更新完了: 成功率 {success_rate:.1f}% ({success_count}/{total_count})")
            
            # 失敗した都市があれば警告
            failed_cities = [city for city, success in results.items() if not success]
            if failed_cities:
                self.logger.warning(f"失敗した都市: {', '.join(failed_cities)}")
                
        except Exception as e:
            self.logger.error(f"定期更新中にエラーが発生: {e}")
            if self.debug:
                self.logger.exception("エラー詳細:")
    
    def update_priority_cities(self):
        """優先都市のみ更新（頻繁な更新用）"""
        priority_cities = ["Tokyo", "Osaka", "Sapporo"]
        
        try:
            self.logger.info(f"優先都市更新: {', '.join(priority_cities)}")
            results = self.reporter.process_multiple_cities(priority_cities)
            
            success_count = sum(1 for success in results.values() if success)
            self.logger.info(f"優先都市更新完了: {success_count}/{len(priority_cities)}")
            
        except Exception as e:
            self.logger.error(f"優先都市更新エラー: {e}")
    
    def setup_schedule(self):
        """スケジュール設定"""
        # 全都市の更新（1日3回）
        schedule.every().day.at("06:00").do(self.update_all_cities)
        schedule.every().day.at("12:00").do(self.update_all_cities) 
        schedule.every().day.at("18:00").do(self.update_all_cities)
        
        # 優先都市の更新（2時間おき）
        schedule.every(2).hours.do(self.update_priority_cities)
        
        self.logger.info("スケジュール設定完了:")
        self.logger.info("  - 全都市更新: 06:00, 12:00, 18:00")
        self.logger.info("  - 優先都市更新: 2時間おき")
    
    def run_scheduler(self):
        """スケジューラー実行"""
        self.setup_schedule()
        self.logger.info("天気データ定期レポーター開始")
        
        # 初回実行（起動時）
        self.logger.info("初回更新を実行...")
        self.update_all_cities()
        
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
        
        self.logger.info("天気データ定期レポーター終了")
    
    def run_once(self):
        """一回だけ実行"""
        self.logger.info("一回限りの天気データ更新を実行")
        self.update_all_cities()
    
    def add_city(self, city: str):
        """対象都市を追加"""
        if city not in self.target_cities:
            self.target_cities.append(city)
            self.logger.info(f"都市 {city} を対象に追加しました")
    
    def remove_city(self, city: str):
        """対象都市を削除"""
        if city in self.target_cities:
            self.target_cities.remove(city)
            self.logger.info(f"都市 {city} を対象から削除しました")
    
    def get_status(self):
        """現在の状態を取得"""
        return {
            "running": self.running,
            "target_cities": self.target_cities,
            "next_run": schedule.next_run() if schedule.jobs else None,
            "total_jobs": len(schedule.jobs)
        }


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="天気データ定期レポーター")
    parser.add_argument("--mode", choices=["schedule", "once"], default="schedule",
                       help="実行モード: schedule(定期実行) または once(一回限り)")
    parser.add_argument("--host", default="localhost", 
                       help="レポートサーバーホスト")
    parser.add_argument("--port", type=int, default=9999,
                       help="レポートサーバーポート") 
    parser.add_argument("--debug", action="store_true",
                       help="デバッグモード")
    parser.add_argument("--api-key", 
                       help="天気APIキー（環境変数WEATHER_API_KEYでも可）")
    
    args = parser.parse_args()
    
    # 環境変数からも設定を取得
    api_key = args.api_key or os.getenv("WEATHER_API_KEY")
    
    # ScheduledWeatherReporterを初期化
    scheduler = ScheduledWeatherReporter(
        api_key=api_key,
        report_server_host=args.host,
        report_server_port=args.port,
        debug=args.debug
    )
    
    print("Scheduled Weather Reporter")
    print("="*50)
    print(f"モード: {args.mode}")
    print(f"レポートサーバー: {args.host}:{args.port}")
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