#!/usr/bin/env python3
"""
fetch_ex_field メソッドの詳細デバッグ
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'wtp'))

from wtp.packet import Format
from wtp.packet.extended_field_mixin import ExtendedFieldType
from wtp.packet.bit_utils import extract_bits, extract_rest_bits

def debug_fetch_ex_field_manually():
    """fetch_ex_fieldの処理を手動で再現してデバッグ"""
    print("=== fetch_ex_field 手動デバッグ ===")
    
    # テストデータ
    packet = Format(
        version=1,
        packet_id=1,
        ex_flag=1,
        timestamp=1234567890,
        ex_field={'latitude': 35.6895}
    )
    
    # バイト列に変換
    data = packet.to_bytes()
    bitstr = int.from_bytes(data, byteorder='big')
    
    # 拡張フィールドビットを抽出
    max_pos = max(pos + size for field, (pos, size) in packet._BIT_FIELDS.items())
    ex_field_bits = extract_rest_bits(bitstr, max_pos)
    
    print(f"拡張フィールドビット: {bin(ex_field_bits)}")
    print(f"拡張フィールドビット長: {ex_field_bits.bit_length()}")
    
    # fetch_ex_fieldの処理を手動で再現
    result = []
    current_pos = 0
    total_bits = ex_field_bits.bit_length()
    
    print(f"total_bits: {total_bits}")
    print(f"EXTENDED_HEADER_TOTAL: {packet.EXTENDED_HEADER_TOTAL}")
    
    iteration = 0
    while current_pos < total_bits:
        iteration += 1
        print(f"\n--- 反復 {iteration} ---")
        print(f"current_pos: {current_pos}")
        print(f"残りビット: {total_bits - current_pos}")
        
        if total_bits - current_pos < packet.EXTENDED_HEADER_TOTAL:
            print("ヘッダー分のビットが不足、ループ終了")
            break
            
        header = extract_bits(ex_field_bits, current_pos, packet.EXTENDED_HEADER_TOTAL)
        print(f"ヘッダー: {bin(header)} ({header})")
        
        # ビット配置を統一（バイト長を上位、キーを下位）
        bytes_length = (header >> packet.EXTENDED_HEADER_KEY) & packet.MAX_EXTENDED_LENGTH
        key = header & packet.MAX_EXTENDED_KEY
        bits_length = bytes_length * 8
        
        print(f"抽出したバイト長: {bytes_length}")
        print(f"抽出したキー: {key}")
        print(f"必要ビット長: {bits_length}")
        
        # ヘッダーが0の場合（無効なレコード）はスキップ
        if header == 0 or bytes_length == 0:
            print("無効なレコード、スキップ")
            current_pos += packet.EXTENDED_HEADER_TOTAL
            continue
        
        required_bits = packet.EXTENDED_HEADER_TOTAL + bits_length
        print(f"必要な総ビット数: {required_bits}")
        
        if current_pos + required_bits > total_bits:
            print("必要なビット数が不足、ループ終了")
            break
        
        value_bits = extract_bits(ex_field_bits, current_pos + packet.EXTENDED_HEADER_TOTAL, bits_length)
        print(f"値ビット: {bin(value_bits)}")
        
        try:
            value_bytes = value_bits.to_bytes(bytes_length, byteorder='big')
            print(f"値バイト列: {value_bytes}")
            
            if key in ExtendedFieldType.STRING_LIST_FIELDS or key == ExtendedFieldType.SOURCE_IP:
                # 文字列の末尾の余分な文字を削除
                value = value_bytes.decode('utf-8').rstrip('\x00#')
                print(f"文字列値: '{value}'")
            elif key in ExtendedFieldType.COORDINATE_FIELDS:
                # 修正：4バイト符号付き整数として復元し、10^6で割って浮動小数点数に戻す
                if bytes_length == 4:
                    int_value = int.from_bytes(value_bytes, byteorder='big', signed=True)
                    value = int_value / ExtendedFieldType.COORDINATE_SCALE
                    print(f"座標値: {value} (整数値: {int_value})")
                else:
                    # 互換性のため、従来の文字列形式もサポート
                    try:
                        decoded_str = value_bytes.decode('utf-8').rstrip('\x00#')
                        value = float(decoded_str)
                        print(f"文字列から座標値: {value}")
                    except (UnicodeDecodeError, ValueError):
                        value = int.from_bytes(value_bytes, byteorder='big')
                        print(f"整数値: {value}")
            else:
                value = value_bits
                print(f"その他の値: {value}")
        except UnicodeDecodeError:
            value = value_bits
            print(f"デコードエラー、ビット値: {value}")
        
        field_key = packet._get_extended_field_key(key)
        print(f"フィールドキー: {field_key}")
        
        if field_key:
            result.append({field_key: value})
            print(f"結果に追加: {field_key} = {value}")
        else:
            print("フィールドキーが見つからない")
        
        current_pos += required_bits
        print(f"次のcurrent_pos: {current_pos}")
        
        if iteration > 5:  # 無限ループ防止
            print("反復回数制限に達しました")
            break
    
    print(f"\n最終結果: {result}")
    
    # _extended_field_to_dictを呼び出し
    try:
        final_dict = packet._extended_field_to_dict(result)
        print(f"辞書変換結果: {final_dict}")
    except Exception as e:
        print(f"辞書変換エラー: {e}")

if __name__ == "__main__":
    debug_fetch_ex_field_manually()
