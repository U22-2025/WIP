#!/usr/bin/env python3
"""
Weather API Reporter - APIから気象データを取得してレポートサーバーに送信

このスクリプトは外部APIから気象情報を取得し、
既存のreport_client.pyを使用してレポートサーバーに送信します。
report_client.pyには一切変更を加えません。
"""

import requests
import json
import time
import logging
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

# WIPCommonPyをインポートするためのパス設定
sys.path.insert(0, '/mnt/c/Users/ポッポ焼き/Desktop/WIP/src')

from WIPCommonPy.clients.report_client import ReportClient


class WeatherAPIReporter:
    """外部APIから気象データを取得してレポートサーバーに送信するクラス"""
    
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
        self.api_key = api_key or os.getenv("WEATHER_API_KEY")
        self.report_server_host = report_server_host
        self.report_server_port = report_server_port
        self.debug = debug
        
        # ログ設定
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # エリアコードマッピング（例）
        self.area_mapping = {
            "Tokyo": "130000",
            "Osaka": "270000", 
            "Kyoto": "260000",
            "Sapporo": "011000",
            "Fukuoka": "400000",
            "Sendai": "040000",
            "Hiroshima": "340000",
            "Nagoya": "230000"
        }
        
        # 天気コードマッピング（API固有の値をWIPの値に変換）
        self.weather_code_mapping = {
            "clear": 100,      # 晴れ
            "cloudy": 200,     # 曇り
            "rain": 300,       # 雨
            "snow": 400,       # 雪
            "partly_cloudy": 101,  # 晴れ時々曇り
            "heavy_rain": 301,     # 大雨
            "storm": 302,          # 嵐
        }
    
    def get_weather_from_api(self, city: str) -> Optional[Dict[str, Any]]:
        """
        外部APIから天気データを取得（ダミー実装）
        実際のAPIに合わせて変更してください
        
        Args:
            city: 都市名
            
        Returns:
            天気データ辞書
        """
        # ダミーデータ（実際のAPI呼び出しに置き換えてください）
        dummy_data = {
            "Tokyo": {
                "weather": "partly_cloudy",
                "temperature": 22.5,
                "precipitation_prob": 30,
                "alerts": [],
                "disasters": []
            },
            "Osaka": {
                "weather": "rain", 
                "temperature": 19.8,
                "precipitation_prob": 80,
                "alerts": ["大雨注意報"],
                "disasters": []
            },
            "Sapporo": {
                "weather": "snow",
                "temperature": -2.1, 
                "precipitation_prob": 90,
                "alerts": [],
                "disasters": ["大雪警報"]
            }
        }
        
        if city in dummy_data:
            self.logger.info(f"APIから{city}の天気データを取得しました")
            return dummy_data[city]
        else:
            self.logger.warning(f"都市 {city} のデータが見つかりません")
            return None
    
    def convert_weather_data(self, api_data: Dict[str, Any], city: str) -> Dict[str, Any]:
        """
        APIデータをWIP形式に変換
        
        Args:
            api_data: APIから取得した生データ
            city: 都市名
            
        Returns:
            WIP形式のデータ
        """
        area_code = self.area_mapping.get(city)
        if not area_code:
            self.logger.error(f"都市 {city} のエリアコードが見つかりません")
            return None
        
        converted = {
            "area_code": area_code,
            "weather_code": self.weather_code_mapping.get(api_data.get("weather")),
            "temperature": api_data.get("temperature"),
            "precipitation_prob": api_data.get("precipitation_prob"),
            "alert": api_data.get("alerts", []),
            "disaster": api_data.get("disasters", [])
        }
        
        self.logger.debug(f"変換済みデータ: {converted}")
        return converted
    
    def send_weather_report(self, weather_data: Dict[str, Any]) -> bool:
        """
        変換済み天気データをレポートサーバーに送信
        
        Args:
            weather_data: WIP形式の天気データ
            
        Returns:
            送信成功フラグ
        """
        # ReportClientを使用（既存実装を変更せず）
        client = ReportClient(
            host=self.report_server_host,
            port=self.report_server_port,
            debug=self.debug
        )
        
        try:
            # センサーデータを設定
            client.set_sensor_data(
                area_code=weather_data["area_code"],
                weather_code=weather_data.get("weather_code"),
                temperature=weather_data.get("temperature"),
                precipitation_prob=weather_data.get("precipitation_prob"),
                alert=weather_data.get("alert"),
                disaster=weather_data.get("disaster")
            )
            
            # レポート送信
            result = client.send_report_data()
            
            if result and result.get("success"):
                self.logger.info(f"✓ レポート送信成功: エリア {weather_data['area_code']}")
                self.logger.debug(f"レスポンス: {result}")
                return True
            else:
                self.logger.error(f"✗ レポート送信失敗: エリア {weather_data['area_code']}")
                return False
                
        except Exception as e:
            self.logger.error(f"レポート送信エラー: {e}")
            return False
        finally:
            client.close()
    
    def process_single_city(self, city: str) -> bool:
        """
        単一都市の天気データを処理
        
        Args:
            city: 都市名
            
        Returns:
            処理成功フラグ
        """
        self.logger.info(f"都市 {city} の天気データを処理中...")
        
        # APIからデータ取得
        api_data = self.get_weather_from_api(city)
        if not api_data:
            return False
        
        # WIP形式に変換
        weather_data = self.convert_weather_data(api_data, city)
        if not weather_data:
            return False
        
        # レポートサーバーに送信
        return self.send_weather_report(weather_data)
    
    def process_multiple_cities(self, cities: List[str]) -> Dict[str, bool]:
        """
        複数都市の天気データを処理
        
        Args:
            cities: 都市名リスト
            
        Returns:
            都市別処理結果
        """
        results = {}
        
        for city in cities:
            self.logger.info(f"\n{'='*50}")
            self.logger.info(f"処理中: {city}")
            self.logger.info('='*50)
            
            results[city] = self.process_single_city(city)
            
            # 連続API呼び出しを避けるため少し待機
            time.sleep(1)
        
        return results
    
    def run_scheduled_update(self, cities: List[str] = None):
        """
        定期実行用メソッド
        
        Args:
            cities: 処理する都市のリスト（Noneの場合は全都市）
        """
        if cities is None:
            cities = list(self.area_mapping.keys())
        
        self.logger.info(f"定期更新開始: {datetime.now()}")
        self.logger.info(f"対象都市: {cities}")
        
        results = self.process_multiple_cities(cities)
        
        # 結果サマリー
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info("更新結果サマリー")
        self.logger.info('='*60)
        self.logger.info(f"成功: {success_count}/{total_count}")
        
        for city, success in results.items():
            status = "✓" if success else "✗"
            self.logger.info(f"  {status} {city}")
        
        self.logger.info(f"定期更新完了: {datetime.now()}")


def main():
    """メイン関数"""
    # 環境変数から設定を取得
    api_key = os.getenv("WEATHER_API_KEY")
    report_host = os.getenv("REPORT_SERVER_HOST", "localhost")
    report_port = int(os.getenv("REPORT_SERVER_PORT", "9999"))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    # WeatherAPIReporterを初期化
    reporter = WeatherAPIReporter(
        api_key=api_key,
        report_server_host=report_host,
        report_server_port=report_port,
        debug=debug
    )
    
    # 使用例
    print("Weather API Reporter - 天気データをレポートサーバーに送信")
    print("="*60)
    
    # 単一都市のテスト
    print("\n1. 単一都市テスト (Tokyo)")
    success = reporter.process_single_city("Tokyo")
    print(f"結果: {'成功' if success else '失敗'}")
    
    # 複数都市のテスト
    print("\n2. 複数都市テスト")
    test_cities = ["Tokyo", "Osaka", "Sapporo"]
    results = reporter.process_multiple_cities(test_cities)
    
    print(f"\n結果サマリー:")
    for city, success in results.items():
        print(f"  {city}: {'成功' if success else '失敗'}")


if __name__ == "__main__":
    main()