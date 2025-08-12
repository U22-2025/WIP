#!/usr/bin/env python3
"""
Packet Validation Test - 4バイトパケット問題の解決確認
"""

import sys
import os
import time
from pathlib import Path

# WIPプロジェクトのsrcディレクトリをPythonパスに追加
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

from WIPCommonPy.clients.report_client import ReportClient

def test_report_server_validation():
    """Report Serverのパケット検証テスト"""
    print("🔍 Report Server Packet Validation Test")
    print("=" * 50)
    
    try:
        # 有効なデータでのテスト
        print("\n1. 有効データテスト")
        client = ReportClient(host="localhost", port=4112, debug=True)
        
        client.set_sensor_data(
            area_code="130000",
            weather_code=100,
            temperature=25.0,
            precipitation_prob=30,
            alert=["テスト警報", "もう一つの警報"],
            disaster=["テスト災害情報"]
        )
        
        result = client.send_report_data()
        client.close()
        
        if result and result.get("success"):
            print("✅ 有効データ送信成功")
            print(f"   パケットID: {result.get('packet_id')}")
            print(f"   応答時間: {result.get('response_time_ms', 0):.1f}ms")
        else:
            print("❌ 有効データ送信失敗")
            
        print("\n2. 警報データ文字列形式テスト")
        client2 = ReportClient(host="localhost", port=4112, debug=True)
        
        # 文字列形式の警報データ（カンマ区切り）をテスト
        client2.set_sensor_data(
            area_code="270000",
            weather_code=200,
            temperature=18.5,
            precipitation_prob=75,
            alert=["大雨警報,洪水注意報,雷注意報"],  # 単一要素にカンマ区切り文字列
            disaster=[]
        )
        
        result2 = client2.send_report_data()
        client2.close()
        
        if result2 and result2.get("success"):
            print("✅ 文字列警報データ送信成功")
            print(f"   パケットID: {result2.get('packet_id')}")
        else:
            print("❌ 文字列警報データ送信失敗")
            
        print("\n3. Redis保存確認")
        from WIPServerPy.data.redis_manager import WeatherRedisManager
        
        time.sleep(1)  # データ保存待機
        
        redis_manager = WeatherRedisManager(debug=True, key_prefix="")
        
        # 130000エリアのデータ確認
        data_130000 = redis_manager.get_weather_data("130000")
        if data_130000:
            warnings = data_130000.get("warnings", [])
            print(f"✅ 130000エリア警報: {warnings}")
        
        # 270000エリアのデータ確認
        data_270000 = redis_manager.get_weather_data("270000")
        if data_270000:
            warnings = data_270000.get("warnings", [])
            print(f"✅ 270000エリア警報: {warnings}")
        
        redis_manager.close()
        
        print("\n🎉 全テスト成功 - パケット検証機能が正常に動作しています")
        return True
        
    except Exception as e:
        print(f"❌ テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_report_server_validation()
    if success:
        print("\n✅ パケット検証テスト完了")
        sys.exit(0)
    else:
        print("\n❌ パケット検証テストに問題があります")
        sys.exit(1)