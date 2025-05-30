#!/usr/bin/env python3
"""
拡張フィールドのエンコード/デコードをデバッグするスクリプト
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'wtp'))

from wtp.packet import Format
from wtp.packet.extended_field_mixin import ExtendedFieldType

def debug_single_field(field_name, field_value, packet_id):
    """単一フィールドのエンコード/デコードをデバッグ"""
    print(f"\n=== {field_name} フィールドデバッグ ===")
    print(f"入力値: {field_value}")
    
    try:
        # パケット作成
        packet = Format(
            version=1,
            packet_id=packet_id,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={field_name: field_value}
        )
        
        print(f"作成されたex_field: {packet.ex_field}")
        
        # キーマッピング確認
        key_int = packet._get_extended_field_key_from_str(field_name)
        print(f"キー整数値: {key_int}")
        
        # バイト列に変換
        data = packet.to_bytes()
        print(f"バイト列長: {len(data)} bytes")
        
        # 復元
        restored = Format.from_bytes(data)
        print(f"復元されたex_field: {restored.ex_field}")
        
        # 比較
        if field_name in restored.ex_field:
            if isinstance(field_value, float):
                error = abs(field_value - restored.ex_field[field_name])
                print(f"誤差: {error}")
                success = error < 0.000001
            else:
                success = field_value == restored.ex_field[field_name]
            print(f"結果: {'✅ 成功' if success else '❌ 失敗'}")
        else:
            print(f"結果: ❌ 失敗 - フィールドが見つかりません")
            
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

def debug_field_constants():
    """フィールド定数の確認"""
    print("=== フィールド定数確認 ===")
    print(f"ALERT = {ExtendedFieldType.ALERT}")
    print(f"DISASTER = {ExtendedFieldType.DISASTER}")
    print(f"LATITUDE = {ExtendedFieldType.LATITUDE}")
    print(f"LONGITUDE = {ExtendedFieldType.LONGITUDE}")
    print(f"SOURCE_IP = {ExtendedFieldType.SOURCE_IP}")
    
    print(f"\nSTRING_LIST_FIELDS = {ExtendedFieldType.STRING_LIST_FIELDS}")
    print(f"COORDINATE_FIELDS = {ExtendedFieldType.COORDINATE_FIELDS}")
    print(f"STRING_FIELDS = {ExtendedFieldType.STRING_FIELDS}")

if __name__ == "__main__":
    debug_field_constants()
    
    # 各フィールドを個別にテスト
    debug_single_field('latitude', 35.6895, 1)
    debug_single_field('longitude', 139.6917, 2)
    debug_single_field('source_ip', '192.168.1.1', 3)
