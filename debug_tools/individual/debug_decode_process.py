#!/usr/bin/env python3
"""
拡張フィールドのデコード処理を詳細にデバッグ
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'wtp'))

from wtp.packet import Format
from wtp.packet.extended_field_mixin import ExtendedFieldType
from wtp.packet.bit_utils import extract_bits, extract_rest_bits

def debug_decode_step_by_step():
    """デコード処理をステップバイステップでデバッグ"""
    print("=== デコード処理詳細デバッグ ===")
    
    # テストデータ
    packet = Format(
        version=1,
        packet_id=1,
        ex_flag=1,
        timestamp=1234567890,
        ex_field={'latitude': 35.6895}
    )
    
    print(f"元のex_field: {packet.ex_field}")
    
    # バイト列に変換
    data = packet.to_bytes()
    print(f"バイト列長: {len(data)} bytes")
    
    # ビット列に戻す
    bitstr = int.from_bytes(data, byteorder='big')
    print(f"ビット列: {bin(bitstr)}")
    print(f"ビット列長: {bitstr.bit_length()}")
    
    # 基本フィールドの終了位置を計算
    max_pos = max(pos + size for field, (pos, size) in packet._BIT_FIELDS.items())
    print(f"基本フィールド終了位置: {max_pos}")
    
    # 拡張フィールドビットを抽出
    ex_field_bits = extract_rest_bits(bitstr, max_pos)
    print(f"拡張フィールドビット: {bin(ex_field_bits)}")
    print(f"拡張フィールドビット長: {ex_field_bits.bit_length()}")
    
    # 手動でヘッダーを解析
    if ex_field_bits.bit_length() >= 16:  # 最低限のヘッダー長
        header = extract_bits(ex_field_bits, 0, 16)
        bytes_length = (header >> 6) & 0x3FF
        key = header & 0x3F
        
        print(f"ヘッダー: {bin(header)} ({header})")
        print(f"抽出したバイト長: {bytes_length}")
        print(f"抽出したキー: {key}")
        
        # キーマッピング確認
        field_name = packet._get_extended_field_key(key)
        print(f"キーから復元したフィールド名: {field_name}")
        
        # 値ビットを抽出
        if ex_field_bits.bit_length() >= 16 + (bytes_length * 8):
            value_bits = extract_bits(ex_field_bits, 16, bytes_length * 8)
            print(f"値ビット: {bin(value_bits)}")
            
            # 値をバイト列に変換
            try:
                value_bytes = value_bits.to_bytes(bytes_length, byteorder='big')
                print(f"値バイト列: {value_bytes}")
                
                # 座標として復元
                if key in ExtendedFieldType.COORDINATE_FIELDS:
                    int_value = int.from_bytes(value_bytes, byteorder='big', signed=True)
                    coord_value = int_value / ExtendedFieldType.COORDINATE_SCALE
                    print(f"復元した座標値: {coord_value}")
                    
            except Exception as e:
                print(f"値の復元でエラー: {e}")
    
    # 実際のfetch_ex_fieldを呼び出し
    print("\n--- 実際のfetch_ex_field呼び出し ---")
    try:
        test_packet = Format(version=1, packet_id=1, ex_flag=0, timestamp=1234567890)
        test_packet.fetch_ex_field(ex_field_bits)
        print(f"fetch_ex_field結果: {test_packet.ex_field}")
    except Exception as e:
        print(f"fetch_ex_fieldでエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_decode_step_by_step()
