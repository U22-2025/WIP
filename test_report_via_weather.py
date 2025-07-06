#!/usr/bin/env python3
"""
Report Client経由でweather_server→report_serverの転送をテストする
"""

import sys
import os
from pathlib import Path

# プロジェクトルートを追加
sys.path.insert(0, str(Path(__file__).parent))
# テスト実行用のデフォルト環境変数を設定
os.environ.setdefault('LOCATION_RESOLVER_HOST', 'localhost')
os.environ.setdefault('LOCATION_RESOLVER_PORT', '4111')

from common.clients.report_client import ReportClient

def test_report_via_weather_server():
    """weather_server経由でreport_serverにデータ送信をテスト"""

    # Weather Server経由でテスト（port 4110）
    client = ReportClient(host='localhost', port=4110, debug=True)
    
    try:
        # テストデータを設定
        client.set_sensor_data(
            area_code="130000",  # 東京
            weather_code=100,    # 晴れ
            temperature=25.0,    # 25℃
            precipitation_prob=30   # 30%
        )
        
        # レポート送信
        result = client.send_report()

        # 成功時は結果が辞書で返る想定
        assert result is None or isinstance(result, dict)
            
    except Exception as e:
        raise AssertionError(f"エラー: {e}")
        
    finally:
        client.close()

if __name__ == "__main__":
    test_report_via_weather_server()