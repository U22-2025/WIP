#!/usr/bin/env python3
"""
エンコード処理をステップバイステップでデバッグ
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'wtp'))

from wtp.packet import Format
from wtp.packet.extended_field_mixin import ExtendedFieldType

def debug_encoding_manually():
    """エンコード処理を手動で再現してデバッグ"""
    print("=== エンコード処理手動デバッグ ===")
    
    # テストデータ
    ex_field_dict = {'latitude': 35.6895}
    
    print(f"入力: {ex_field_dict}")
    
    # 手動でエンコード処理を再現
    result_bits = 0
    current_pos = 0
    
    for key, value in ex_field_dict.items():
        print(f"\n--- {key} = {value} の処理 ---")
        
        # キーを整数に変換
        packet = Format(version=1, packet_id=1, ex_flag=0, timestamp=1234567890)
        key_int = packet._get_extended_field_key_from_str(key)
        print(f"キー整数値: {key_int}")
        
        # 座標値の変換
        coord_value = float(value)
        int_value = int(coord_value * ExtendedFieldType.COORDINATE_SCALE)
        value_bytes = int_value.to_bytes(4, byteorder='big', signed=True)
        
        print(f"座標値: {coord_value}")
        print(f"整数値: {int_value}")
        print(f"バイト列: {value_bytes}")
        print(f"バイト列長: {len(value_bytes)}")
        
        # ヘッダー作成
        bytes_needed = len(value_bytes)
        header = ((bytes_needed & packet.MAX_EXTENDED_LENGTH) << packet.EXTENDED_HEADER_KEY) | (key_int & packet.MAX_EXTENDED_KEY)
        value_bits = int.from_bytes(value_bytes, byteorder='big')
        
        print(f"バイト数: {bytes_needed}")
        print(f"ヘッダー: {bin(header)} ({header})")
        print(f"値ビット: {bin(value_bits)} ({value_bits})")
        print(f"値ビット長: {value_bits.bit_length()}")
        
        # レコードビット作成
        record_bits = (value_bits << packet.EXTENDED_HEADER_TOTAL) | header
        print(f"レコードビット: {bin(record_bits)}")
        print(f"レコードビット長: {record_bits.bit_length()}")
        
        # 結果に追加
        result_bits |= (record_bits << current_pos)
        print(f"current_pos: {current_pos}")
        print(f"結果ビット: {bin(result_bits)}")
        print(f"結果ビット長: {result_bits.bit_length()}")
        
        current_pos += packet.EXTENDED_HEADER_TOTAL + (bytes_needed * 8)
        print(f"次のcurrent_pos: {current_pos}")
    
    print(f"\n最終結果ビット: {bin(result_bits)}")
    print(f"最終結果ビット長: {result_bits.bit_length()}")
    
    # 実際のメソッドと比較
    print(f"\n--- 実際のメソッドとの比較 ---")
    actual_bits = packet._dict_to_ex_field_bits(ex_field_dict)
    print(f"実際のメソッド結果: {bin(actual_bits)}")
    print(f"実際のメソッド結果長: {actual_bits.bit_length()}")
    print(f"一致: {result_bits == actual_bits}")

if __name__ == "__main__":
    debug_encoding_manually()
