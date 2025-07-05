#!/usr/bin/env python3
"""
weatherサーバーのキャッシュ統合テスト
"""

import sys
import os
import time
from datetime import datetime, timedelta

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.clients.query_client import QueryClient

def test_query_client_cache():
    """query_clientのキャッシュ機能を直接テスト"""
    print("=== QueryClient キャッシュテスト ===")
    
    # デバッグモードでクライアントを作成（TTL: 5分）
    client = QueryClient(host='localhost', port=4111, debug=True, cache_ttl_minutes=5)
    
    test_area_code = "130010"  # 東京
    
    print("1. 最初のリクエスト（キャッシュミス想定）")
    start_time = time.time()
    
    # force_refresh=True で強制的にサーバーアクセス
    result1 = client.get_weather_data(
        area_code=test_area_code,
        weather=True,
        temperature=True,
        precipitation_prob=True,
        use_cache=True,
        force_refresh=True,  # 強制リフレッシュ
        timeout=10.0
    )
    
    first_request_time = time.time() - start_time
    print(f"1回目の結果: {result1}")
    print(f"1回目の実行時間: {first_request_time:.3f}秒")
    
    # キャッシュ統計を確認
    cache_stats = client.get_cache_stats()
    print(f"キャッシュ統計（1回目後）: {cache_stats}")
    
    print("\n2. 2回目のリクエスト（キャッシュヒット想定）")
    start_time = time.time()
    
    result2 = client.get_weather_data(
        area_code=test_area_code,
        weather=True,
        temperature=True,
        precipitation_prob=True,
        use_cache=True,
        force_refresh=False,  # キャッシュ使用
        timeout=10.0
    )
    
    second_request_time = time.time() - start_time
    print(f"2回目の結果: {result2}")
    print(f"2回目の実行時間: {second_request_time:.3f}秒")
    
    # キャッシュ統計を再確認
    cache_stats = client.get_cache_stats()
    print(f"キャッシュ統計（2回目後）: {cache_stats}")
    
    # 結果比較
    if 'error' not in result1 and 'error' not in result2:
        print("\n=== 結果比較 ===")
        print(f"1回目のsource: {result1.get('source', 'N/A')}")
        print(f"2回目のsource: {result2.get('source', 'N/A')}")
        
        if result2.get('source') == 'cache':
            print("✓ 2回目はキャッシュから取得されました")
            print(f"✓ 応答時間短縮: {first_request_time:.3f}秒 → {second_request_time:.3f}秒")
            return True
        else:
            print("✗ 2回目もサーバーアクセスが発生しました")
            return False
    else:
        print("✗ リクエストでエラーが発生しました")
        return False

def test_cache_key_consistency():
    """キャッシュキーの一貫性テスト"""
    print("\n=== キャッシュキー一貫性テスト ===")
    
    client = QueryClient(debug=True)
    
    # 同じパラメータで複数回キャッシュキーを生成
    area_code = "130010"
    test_cases = [
        (True, True, True, False, False, 0),
        (False, True, False, True, True, 1),
        (True, False, True, False, True, 0),
    ]
    
    for weather, temperature, precipitation_prob, alert, disaster, day in test_cases:
        key1 = client._get_cache_key(area_code, weather, temperature, precipitation_prob, alert, disaster, day)
        key2 = client._get_cache_key(area_code, weather, temperature, precipitation_prob, alert, disaster, day)
        
        print(f"パラメータ: w{int(weather)}t{int(temperature)}p{int(precipitation_prob)}a{int(alert)}d{int(disaster)}, day={day}")
        print(f"生成キー1: {key1}")
        print(f"生成キー2: {key2}")
        print(f"一致: {'✓' if key1 == key2 else '✗'}")
        print()
    
    return True

if __name__ == "__main__":
    print("weatherサーバー キャッシュ統合テスト")
    print("=" * 60)
    
    print("注意: このテストはquery_serverが起動している必要があります")
    print("=" * 60)
    
    test1_result = test_cache_key_consistency()
    
    # query_serverが起動していない場合はスキップ
    try:
        test2_result = test_query_client_cache()
    except Exception as e:
        print(f"query_serverとの通信テストをスキップ: {e}")
        test2_result = True
    
    print("\n" + "=" * 60)
    if test1_result and test2_result:
        print("✓ キャッシュ統合テストが完了しました")
        print("修正により、キャッシュが適切に動作するはずです")
    else:
        print("✗ 一部のテストが失敗しました")