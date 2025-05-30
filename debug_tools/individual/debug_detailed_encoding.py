#!/usr/bin/env python3
"""
拡張フィールドの詳細なエンコード/デコードデバッグ
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'wtp'))

from wtp.packet import Format
from wtp.packet.extended_field_mixin import ExtendedFieldType
from wtp.packet.bit_utils import extract_bits

def debug_encoding_process():
    """エンコード処理の詳細デバッグ"""
    print("=== エンコード処理デバッグ ===")
    
    # テストデータ
    test_data = {
        'latitude': 35.6895,
        'longitude': 139.6917,
        'source_ip': '192.168.1.1'
    }
    
    for field_name, field_value in test_data.items():
        print(f"\n--- {field_name} = {field_value} ---")
        
        try:
            packet = Format(
                version=1,
                packet_id=1,
                ex_flag=1,
                timestamp=1234567890,
                ex_field={field_name: field_value}
            )
            
            # キー情報
            key_int = packet._get_extended_field_key_from_str(field_name)
            print(f"キー整数値: {key_int}")
            print(f"キーが6ビット範囲内: {0 <= key_int <= 63}")
            
            # エンコード処理をトレース
            ex_field_bits = packet._dict_to_ex_field_bits(packet.ex_field)
            print(f"拡張フィールドビット: {bin(ex_field_bits)}")
            print(f"拡張フィールドビット長: {ex_field_bits.bit_length()}")
            
            # バイト列変換
            data = packet.to_bytes()
            print(f"総バイト数: {len(data)}")
            
            # 復元プロセス
            print("\n復元プロセス:")
            restored = Format.from_bytes(data)
            print(f"復元結果: {restored.ex_field}")
            
        except Exception as e:
            print(f"エラー: {e}")
            import traceback
            traceback.print_exc()

def debug_bit_extraction():
    """ビット抽出のデバッグ"""
    print("\n=== ビット抽出デバッグ ===")
    
    # 手動でヘッダーを作成してテスト
    key = 33  # latitude
    bytes_length = 4
    
    # ヘッダー作成（バイト長を上位、キーを下位）
    header = ((bytes_length & 0x3FF) << 6) | (key & 0x3F)
    print(f"作成したヘッダー: {bin(header)} ({header})")
    
    # ヘッダーから値を抽出
    extracted_bytes_length = (header >> 6) & 0x3FF
    extracted_key = header & 0x3F
    print(f"抽出したバイト長: {extracted_bytes_length}")
    print(f"抽出したキー: {extracted_key}")
    
    # キーマッピング確認
    packet = Format(version=1, packet_id=1, ex_flag=0, timestamp=1234567890)
    field_name = packet._get_extended_field_key(extracted_key)
    print(f"キーから復元したフィールド名: {field_name}")

if __name__ == "__main__":
    debug_encoding_process()
    debug_bit_extraction()
