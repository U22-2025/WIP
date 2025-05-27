#!/usr/bin/env python3
"""
拡張フィールド修正のテストスクリプト
レポートで問題となった各フィールドの動作を検証します
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'wtp'))

from wtp.packet import Format

def test_individual_fields():
    """個別フィールドのテスト"""
    print("=== 個別フィールドテスト ===")
    
    # 1. alert フィールド（正常動作確認）
    print("\n1. alert フィールドテスト")
    try:
        packet = Format(
            version=1,
            packet_id=1,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={'alert': ['津波警報']}
        )
        data = packet.to_bytes()
        restored = Format.from_bytes(data)
        print(f"  入力: {packet.ex_field}")
        print(f"  復元: {restored.ex_field}")
        print(f"  結果: {'✅ 成功' if packet.ex_field == restored.ex_field else '❌ 失敗'}")
    except Exception as e:
        print(f"  結果: ❌ エラー - {e}")
    
    # 2. disaster フィールド（正常動作確認）
    print("\n2. disaster フィールドテスト")
    try:
        packet = Format(
            version=1,
            packet_id=2,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={'disaster': ['土砂崩れ']}
        )
        data = packet.to_bytes()
        restored = Format.from_bytes(data)
        print(f"  入力: {packet.ex_field}")
        print(f"  復元: {restored.ex_field}")
        print(f"  結果: {'✅ 成功' if packet.ex_field == restored.ex_field else '❌ 失敗'}")
    except Exception as e:
        print(f"  結果: ❌ エラー - {e}")
    
    # 3. latitude フィールド（修正対象）
    print("\n3. latitude フィールドテスト")
    try:
        packet = Format(
            version=1,
            packet_id=3,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={'latitude': 35.6895}
        )
        data = packet.to_bytes()
        restored = Format.from_bytes(data)
        print(f"  入力: {packet.ex_field}")
        print(f"  復元: {restored.ex_field}")
        
        # 浮動小数点数の比較（誤差を考慮）
        input_lat = packet.ex_field['latitude']
        restored_lat = restored.ex_field.get('latitude', None)
        success = (restored_lat is not None and 
                  abs(input_lat - restored_lat) < 0.000001)
        print(f"  結果: {'✅ 成功' if success else '❌ 失敗'}")
    except Exception as e:
        print(f"  結果: ❌ エラー - {e}")
    
    # 4. longitude フィールド（修正対象）
    print("\n4. longitude フィールドテスト")
    try:
        packet = Format(
            version=1,
            packet_id=4,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={'longitude': 139.6917}
        )
        data = packet.to_bytes()
        restored = Format.from_bytes(data)
        print(f"  入力: {packet.ex_field}")
        print(f"  復元: {restored.ex_field}")
        
        # 浮動小数点数の比較（誤差を考慮）
        input_lng = packet.ex_field['longitude']
        restored_lng = restored.ex_field.get('longitude', None)
        success = (restored_lng is not None and 
                  abs(input_lng - restored_lng) < 0.000001)
        print(f"  結果: {'✅ 成功' if success else '❌ 失敗'}")
    except Exception as e:
        print(f"  結果: ❌ エラー - {e}")
    
    # 5. source_ip フィールド（修正対象）
    print("\n5. source_ip フィールドテスト")
    try:
        packet = Format(
            version=1,
            packet_id=5,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={'source_ip': '192.168.1.1'}
        )
        data = packet.to_bytes()
        restored = Format.from_bytes(data)
        print(f"  入力: {packet.ex_field}")
        print(f"  復元: {restored.ex_field}")
        print(f"  結果: {'✅ 成功' if packet.ex_field == restored.ex_field else '❌ 失敗'}")
    except Exception as e:
        print(f"  結果: ❌ エラー - {e}")

def test_field_combinations():
    """フィールド組み合わせのテスト"""
    print("\n=== フィールド組み合わせテスト ===")
    
    # 1. alert + disaster（正常動作確認）
    print("\n1. alert + disaster 組み合わせテスト")
    try:
        packet = Format(
            version=1,
            packet_id=10,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={
                'alert': ['津波警報', '大雨警報'],
                'disaster': ['洪水']
            }
        )
        data = packet.to_bytes()
        restored = Format.from_bytes(data)
        print(f"  入力: {packet.ex_field}")
        print(f"  復元: {restored.ex_field}")
        print(f"  結果: {'✅ 成功' if packet.ex_field == restored.ex_field else '❌ 失敗'}")
    except Exception as e:
        print(f"  結果: ❌ エラー - {e}")
    
    # 2. latitude + longitude（修正対象）
    print("\n2. latitude + longitude 組み合わせテスト")
    try:
        packet = Format(
            version=1,
            packet_id=11,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={
                'latitude': 35.6895,
                'longitude': 139.6917
            }
        )
        data = packet.to_bytes()
        restored = Format.from_bytes(data)
        print(f"  入力: {packet.ex_field}")
        print(f"  復元: {restored.ex_field}")
        
        # 座標の比較（誤差を考慮）
        input_lat = packet.ex_field['latitude']
        input_lng = packet.ex_field['longitude']
        restored_lat = restored.ex_field.get('latitude', None)
        restored_lng = restored.ex_field.get('longitude', None)
        
        success = (restored_lat is not None and restored_lng is not None and
                  abs(input_lat - restored_lat) < 0.000001 and
                  abs(input_lng - restored_lng) < 0.000001)
        print(f"  結果: {'✅ 成功' if success else '❌ 失敗'}")
    except Exception as e:
        print(f"  結果: ❌ エラー - {e}")
    
    # 3. alert + source_ip（修正対象）
    print("\n3. alert + source_ip 組み合わせテスト")
    try:
        packet = Format(
            version=1,
            packet_id=12,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={
                'alert': ['津波警報'],
                'source_ip': '192.168.1.1'
            }
        )
        data = packet.to_bytes()
        restored = Format.from_bytes(data)
        print(f"  入力: {packet.ex_field}")
        print(f"  復元: {restored.ex_field}")
        print(f"  結果: {'✅ 成功' if packet.ex_field == restored.ex_field else '❌ 失敗'}")
    except Exception as e:
        print(f"  結果: ❌ エラー - {e}")
    
    # 4. 全フィールド組み合わせ（修正対象）
    print("\n4. 全フィールド組み合わせテスト")
    try:
        packet = Format(
            version=1,
            packet_id=13,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={
                'alert': ['津波警報'],
                'disaster': ['土砂崩れ'],
                'latitude': 35.6895,
                'longitude': 139.6917,
                'source_ip': '192.168.1.1'
            }
        )
        data = packet.to_bytes()
        restored = Format.from_bytes(data)
        print(f"  入力: {packet.ex_field}")
        print(f"  復元: {restored.ex_field}")
        
        # 各フィールドの比較
        success = True
        
        # alert/disaster の比較
        if (packet.ex_field.get('alert') != restored.ex_field.get('alert') or
            packet.ex_field.get('disaster') != restored.ex_field.get('disaster') or
            packet.ex_field.get('source_ip') != restored.ex_field.get('source_ip')):
            success = False
        
        # 座標の比較（誤差を考慮）
        input_lat = packet.ex_field['latitude']
        input_lng = packet.ex_field['longitude']
        restored_lat = restored.ex_field.get('latitude', None)
        restored_lng = restored.ex_field.get('longitude', None)
        
        if (restored_lat is None or restored_lng is None or
            abs(input_lat - restored_lat) >= 0.000001 or
            abs(input_lng - restored_lng) >= 0.000001):
            success = False
        
        print(f"  結果: {'✅ 成功' if success else '❌ 失敗'}")
    except Exception as e:
        print(f"  結果: ❌ エラー - {e}")

def test_coordinate_precision():
    """座標精度のテスト"""
    print("\n=== 座標精度テスト ===")
    
    test_coordinates = [
        (35.6895, 139.6917),    # 東京
        (-33.8688, 151.2093),   # シドニー
        (40.7128, -74.0060),    # ニューヨーク
        (0.0, 0.0),             # 赤道・本初子午線
        (90.0, 180.0),          # 極値
        (-90.0, -180.0),        # 極値
    ]
    
    for i, (lat, lng) in enumerate(test_coordinates, 1):
        print(f"\n{i}. 座標テスト ({lat}, {lng})")
        try:
            packet = Format(
                version=1,
                packet_id=20 + i,
                ex_flag=1,
                timestamp=1234567890,
                ex_field={
                    'latitude': lat,
                    'longitude': lng
                }
            )
            data = packet.to_bytes()
            restored = Format.from_bytes(data)
            
            restored_lat = restored.ex_field.get('latitude', None)
            restored_lng = restored.ex_field.get('longitude', None)
            
            lat_error = abs(lat - restored_lat) if restored_lat is not None else float('inf')
            lng_error = abs(lng - restored_lng) if restored_lng is not None else float('inf')
            
            print(f"  入力: lat={lat}, lng={lng}")
            print(f"  復元: lat={restored_lat}, lng={restored_lng}")
            print(f"  誤差: lat={lat_error:.9f}, lng={lng_error:.9f}")
            
            success = (restored_lat is not None and restored_lng is not None and
                      lat_error < 0.000001 and lng_error < 0.000001)
            print(f"  結果: {'✅ 成功' if success else '❌ 失敗'}")
        except Exception as e:
            print(f"  結果: ❌ エラー - {e}")

if __name__ == "__main__":
    print("拡張フィールド修正テスト開始")
    print("=" * 50)
    
    test_individual_fields()
    test_field_combinations()
    test_coordinate_precision()
    
    print("\n" + "=" * 50)
    print("テスト完了")
