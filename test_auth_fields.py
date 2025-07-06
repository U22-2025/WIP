#!/usr/bin/env python3
"""
認証フィールドのテストスクリプト
新しく実装したrequest_authとresponse_authフィールドをテストします
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.packet import Request, Response
from common.packet.extended_field import ExtendedField
from datetime import datetime

def test_auth_fields():
    """認証フィールドの基本テスト"""
    print("=== 認証フィールド基本テスト ===")
    
    # 1. リクエストパケットでの認証フラグテスト
    print("\n1. リクエストパケットの認証フラグテスト")
    
    request = Request(
        version=1,
        packet_id=1234,  # 12ビットの有効範囲内（0-4095）
        type=2,  # 気象データリクエスト
        area_code="123456",
        timestamp=int(datetime.now().timestamp())
    )
    
    print(f"認証フラグ設定前:")
    print(f"  request_auth: {request.request_auth}")
    print(f"  response_auth: {request.response_auth}")
    print(f"  reserved: {request.reserved}")
    
    # 認証フラグを設定
    request.set_auth_flags(
        server_request_auth_enabled=True,
        response_auth_enabled=True
    )
    
    print(f"認証フラグ設定後:")
    print(f"  request_auth: {request.request_auth}")
    print(f"  response_auth: {request.response_auth}")
    print(f"  reserved: {request.reserved}")
    
    # パケットをバイト列に変換して復元
    packet_bytes = request.to_bytes()
    restored_request = Request.from_bytes(packet_bytes)
    
    print(f"パケット復元後:")
    print(f"  request_auth: {restored_request.request_auth}")
    print(f"  response_auth: {restored_request.response_auth}")
    print(f"  reserved: {restored_request.reserved}")
    
    # 2. レスポンスパケットでの認証処理テスト
    print("\n2. レスポンスパケットの認証処理テスト")
    
    response = Response(
        version=1,
        packet_id=1234,  # 12ビットの有効範囲内（0-4095）
        type=3,  # 気象データレスポンス
        area_code="123456",
        timestamp=int(datetime.now().timestamp()),
        weather_code=1000,
        temperature=125,  # 25℃ (+100)
        pop=30
    )
    
    print(f"レスポンス認証処理前:")
    print(f"  認証有効: {response.is_auth_enabled()}")
    print(f"  拡張フラグ: {response.ex_flag}")
    
    # リクエストのレスポンス認証フラグをチェックして処理
    server_passphrase = "test_server_password"
    response.process_request_auth_flags(restored_request, server_passphrase)
    
    print(f"レスポンス認証処理後:")
    print(f"  認証有効: {response.is_auth_enabled()}")
    print(f"  拡張フラグ: {response.ex_flag}")
    
    if response.is_auth_enabled():
        auth_hash = response.calculate_auth_hash()
        print(f"  認証ハッシュ: {auth_hash.hex() if auth_hash else 'None'}")
    
    # レスポンスパケットをバイト列に変換して復元
    response_bytes = response.to_bytes()
    restored_response = Response.from_bytes(response_bytes)
    
    print(f"レスポンスパケット復元後:")
    print(f"  認証有効: {restored_response.is_auth_enabled()}")
    print(f"  拡張フラグ: {restored_response.ex_flag}")
    
    # 3. 認証検証テスト
    print("\n3. 認証検証テスト")
    
    if restored_response.is_auth_enabled():
        # 正しいパスフレーズで検証
        restored_response.enable_auth(server_passphrase)
        is_valid = restored_response.verify_auth_from_extended_field()
        print(f"  正しいパスフレーズでの検証: {is_valid}")
        
        # 間違ったパスフレーズで検証
        restored_response.enable_auth("wrong_password")
        is_valid_wrong = restored_response.verify_auth_from_extended_field()
        print(f"  間違ったパスフレーズでの検証: {is_valid_wrong}")

def test_bit_field_integrity():
    """ビットフィールドの整合性テスト"""
    print("\n=== ビットフィールド整合性テスト ===")
    
    request = Request(
        version=15,  # 最大値
        packet_id=4095,  # 最大値（12ビット）
        type=7,  # 最大値（3ビット）
        weather_flag=1,
        temperature_flag=1,
        pop_flag=1,
        alert_flag=1,
        disaster_flag=1,
        ex_flag=1,
        day=7,  # 最大値（3ビット）
        request_auth=1,  # 新フィールド
        response_auth=1,  # 新フィールド
        reserved=3,  # 最大値（2ビット）
        timestamp=int(datetime.now().timestamp()),
        area_code="999999"
    )
    
    print(f"設定値:")
    print(f"  version: {request.version}")
    print(f"  packet_id: {request.packet_id}")
    print(f"  type: {request.type}")
    print(f"  weather_flag: {request.weather_flag}")
    print(f"  temperature_flag: {request.temperature_flag}")
    print(f"  pop_flag: {request.pop_flag}")
    print(f"  alert_flag: {request.alert_flag}")
    print(f"  disaster_flag: {request.disaster_flag}")
    print(f"  ex_flag: {request.ex_flag}")
    print(f"  day: {request.day}")
    print(f"  request_auth: {request.request_auth}")
    print(f"  response_auth: {request.response_auth}")
    print(f"  reserved: {request.reserved}")
    print(f"  area_code: {request.area_code}")
    
    # パケットをバイト列に変換して復元
    packet_bytes = request.to_bytes()
    restored = Request.from_bytes(packet_bytes)
    
    print(f"\n復元後:")
    print(f"  version: {restored.version}")
    print(f"  packet_id: {restored.packet_id}")
    print(f"  type: {restored.type}")
    print(f"  weather_flag: {restored.weather_flag}")
    print(f"  temperature_flag: {restored.temperature_flag}")
    print(f"  pop_flag: {restored.pop_flag}")
    print(f"  alert_flag: {restored.alert_flag}")
    print(f"  disaster_flag: {restored.disaster_flag}")
    print(f"  ex_flag: {restored.ex_flag}")
    print(f"  day: {restored.day}")
    print(f"  request_auth: {restored.request_auth}")
    print(f"  response_auth: {restored.response_auth}")
    print(f"  reserved: {restored.reserved}")
    print(f"  area_code: {restored.area_code}")
    
    # 値が保持されているかチェック
    fields_match = (
        request.version == restored.version and
        request.packet_id == restored.packet_id and
        request.type == restored.type and
        request.weather_flag == restored.weather_flag and
        request.temperature_flag == restored.temperature_flag and
        request.pop_flag == restored.pop_flag and
        request.alert_flag == restored.alert_flag and
        request.disaster_flag == restored.disaster_flag and
        request.ex_flag == restored.ex_flag and
        request.day == restored.day and
        request.request_auth == restored.request_auth and
        request.response_auth == restored.response_auth and
        request.reserved == restored.reserved and
        request.area_code == restored.area_code
    )
    
    print(f"\nビットフィールド整合性: {'✓ 成功' if fields_match else '✗ 失敗'}")

if __name__ == "__main__":
    test_auth_fields()
    test_bit_field_integrity()
    print("\n=== テスト完了 ===")