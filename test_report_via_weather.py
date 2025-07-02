#!/usr/bin/env python3
"""
Report Client経由でweather_server→report_serverの転送をテストする
"""

import sys
import os
import time
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent))

from common.packet.report_client import ReportClient

def test_report_via_weather_server():
    """weather_server経由でreport_serverにデータ送信をテスト"""
    print("=" * 60)
    print("Report Client → Weather Server → Report Server テスト")
    print("=" * 60)
    
    # Weather Server経由でテスト（port 4110）
    print(f"接続先: localhost:4110 (Weather Server)")
    client = ReportClient(host='localhost', port=4110, debug=True)
    
    try:
        # テストデータを設定
        client.set_sensor_data(
            area_code="130000",  # 東京
            weather_code=100,    # 晴れ
            temperature=25.0,    # 25℃
            precipitation_prob=30,  # 30%
            source=("localhost", 12345)  # テスト用source
        )
        
        print(f"\n送信データ:")
        print(f"  エリアコード: {client.area_code}")
        print(f"  天気コード: {client.weather_code}")
        print(f"  気温: {client.temperature}℃")
        print(f"  降水確率: {client.precipitation_prob}%")
        print(f"  送信元: {client.source}")
        
        # レポート送信
        print(f"\nWeather Server (4110) 経由でReport Server (4112) にレポート送信中...")
        result = client.send_report()
        
        if result:
            print(f"\n✓ レポート送信成功!")
            print(f"Response: {result}")
            print(f"\nフロー: Report Client → Weather Server → Report Server → Weather Server → Report Client")
        else:
            print(f"\n✗ レポート送信失敗")
            
    except Exception as e:
        print(f"\nエラー: {e}")
        
    finally:
        client.close()

if __name__ == "__main__":
    test_report_via_weather_server()