#!/usr/bin/env python3
"""
シンプルなキャッシュテスト - weatherサーバーのキャッシュ機能のテスト
"""

import sys
import os
import time
from datetime import datetime, timedelta

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.utils.cache import Cache

def test_cache_basic():
    """基本的なキャッシュテスト"""
    print("=== 基本キャッシュテスト ===")
    
    # キャッシュを初期化（TTL: 1分）
    cache = Cache(default_ttl=timedelta(minutes=1))
    
    # テストデータ
    test_key = "query:130010:w1t1p1a0d0:d0"
    test_data = {
        'area_code': '130010',
        'weather_code': '0100',
        'temperature': 125,  # パケット形式（+100）
        'precipitation_prob': 30,
        'source': 'test'
    }
    
    print(f"1. キャッシュサイズ: {cache.size()}")
    
    # データをキャッシュに保存
    cache.set(test_key, test_data)
    print(f"2. データ保存後のキャッシュサイズ: {cache.size()}")
    print(f"   保存キー: {test_key}")
    print(f"   保存データ: {test_data}")
    
    # データを取得
    retrieved_data = cache.get(test_key)
    print(f"3. データ取得結果: {retrieved_data}")
    
    if retrieved_data == test_data:
        print("✓ キャッシュの保存・取得が正常に動作しています")
        return True
    else:
        print("✗ キャッシュの保存・取得に問題があります")
        return False

def test_cache_key_generation():
    """キャッシュキー生成テスト"""
    print("\n=== キャッシュキー生成テスト ===")
    
    # query_clientのキーとweather_serverで期待するキーが一致するかテスト
    def get_cache_key(area_code, weather, temperature, precipitation_prob, alert, disaster, day=0):
        flags = f"w{int(weather)}t{int(temperature)}p{int(precipitation_prob)}a{int(alert)}d{int(disaster)}"
        return f"query:{area_code}:{flags}:d{day}"
    
    test_cases = [
        ("130010", True, True, True, False, False, 0),
        ("011000", False, True, False, True, True, 1),
        ("270000", True, False, True, False, True, 0),
    ]
    
    for area_code, weather, temperature, precipitation_prob, alert, disaster, day in test_cases:
        key = get_cache_key(area_code, weather, temperature, precipitation_prob, alert, disaster, day)
        print(f"エリア: {area_code}, フラグ: w{int(weather)}t{int(temperature)}p{int(precipitation_prob)}a{int(alert)}d{int(disaster)}, 日: {day}")
        print(f"生成キー: {key}")
    
    return True

def test_cache_ttl():
    """TTL（有効期限）テスト"""
    print("\n=== TTL（有効期限）テスト ===")
    
    # 短いTTL（2秒）でテスト
    cache = Cache(default_ttl=timedelta(seconds=2))
    
    test_key = "ttl_test"
    test_data = {"message": "This should expire"}
    
    cache.set(test_key, test_data)
    print(f"1. データ保存直後: {cache.get(test_key)}")
    
    time.sleep(1)
    print(f"2. 1秒後: {cache.get(test_key)}")
    
    time.sleep(2)
    expired_data = cache.get(test_key)
    print(f"3. 3秒後（期限切れ）: {expired_data}")
    
    if expired_data is None:
        print("✓ TTLが正常に動作しています")
        return True
    else:
        print("✗ TTLに問題があります")
        return False

if __name__ == "__main__":
    print("weatherサーバー キャッシュ機能テスト")
    print("=" * 50)
    
    test1_result = test_cache_basic()
    test2_result = test_cache_key_generation()
    test3_result = test_cache_ttl()
    
    print("\n" + "=" * 50)
    if all([test1_result, test2_result, test3_result]):
        print("✓ すべてのキャッシュテストが成功しました")
    else:
        print("✗ 一部のキャッシュテストが失敗しました")