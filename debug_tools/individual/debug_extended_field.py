#!/usr/bin/env python3
"""
拡張フィールドのデバッグスクリプト
ビット構造を詳細に分析します
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'wtp'))

from wtp.packet import Format

def debug_bit_structure():
    """ビット構造のデバッグ"""
    print("=== ビット構造デバッグ ===")
    
    # 1. latitude フィールドのビット構造を詳細に分析
    print("\n1. latitude フィールドのビット構造分析")
    try:
        packet = Format(
            version=1,
            packet_id=1,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={'latitude': 35.6895}
        )
        
        # ビット列を取得
        bitstr = packet.to_bits()
        print(f"  全体ビット列: {bin(bitstr)}")
        print(f"  全体ビット長: {bitstr.bit_length()}")
        
        # 拡張フィールド部分を抽出
        ex_field_start = 128  # 基本フィールドの後
        ex_field_bits = bitstr >> ex_field_start
        print(f"  拡張フィールドビット列: {bin(ex_field_bits)}")
        print(f"  拡張フィールドビット長: {ex_field_bits.bit_length()}")
        
        # ヘッダー部分を解析
        if ex_field_bits:
            header = ex_field_bits & ((1 << 16) - 1)  # 下位16ビット
            print(f"  ヘッダー: {bin(header)} ({header})")
            
            # 現在の解析方法
            bytes_length = (header >> 6) & ((1 << 10) - 1)
            key = header & ((1 << 6) - 1)
            print(f"  解析結果: key={key}, bytes_length={bytes_length}")
            
            # 期待される値
            expected_key = 65  # latitude
            expected_bytes = 4  # 4バイト
            print(f"  期待値: key={expected_key}, bytes_length={expected_bytes}")
            
    except Exception as e:
        print(f"  エラー: {e}")
        import traceback
        traceback.print_exc()

def debug_encoding_process():
    """エンコード過程のデバッグ"""
    print("\n=== エンコード過程デバッグ ===")
    
    # ExtendedFieldMixinのメソッドを直接呼び出してデバッグ
    from wtp.packet.extended_field_mixin import ExtendedFieldMixin
    
    class DebugMixin(ExtendedFieldMixin):
        def debug_dict_to_bits(self, ex_field_dict):
            print(f"  入力辞書: {ex_field_dict}")
            
            result_bits = 0
            current_pos = 0
            
            for key, value in ex_field_dict.items():
                print(f"\n  処理中のキー: {key}, 値: {value}")
                
                # キーを整数に変換
                key_int = self._get_extended_field_key_from_str(key)
                print(f"  キー整数: {key_int}")
                
                # 値の処理
                if key in ['latitude', 'longitude']:
                    int_value = int(float(value) * 1_000_000)
                    value_bytes = int_value.to_bytes(4, byteorder='big', signed=True)
                    print(f"  座標変換: {value} -> {int_value} -> {value_bytes.hex()}")
                else:
                    value_bytes = str(value).encode('utf-8')
                    print(f"  文字列変換: {value} -> {value_bytes}")
                
                bytes_needed = len(value_bytes)
                print(f"  必要バイト数: {bytes_needed}")
                
                # ヘッダー作成
                header = ((bytes_needed & self.MAX_EXTENDED_LENGTH) << self.EXTENDED_HEADER_KEY) | (key_int & self.MAX_EXTENDED_KEY)
                print(f"  ヘッダー: {bin(header)} ({header})")
                print(f"    バイト長部分: {bin((bytes_needed & self.MAX_EXTENDED_LENGTH) << self.EXTENDED_HEADER_KEY)}")
                print(f"    キー部分: {bin(key_int & self.MAX_EXTENDED_KEY)}")
                
                value_bits = int.from_bytes(value_bytes, byteorder='big')
                print(f"  値ビット: {bin(value_bits)} ({value_bits})")
                
                record_bits = header | (value_bits << self.EXTENDED_HEADER_TOTAL)
                print(f"  レコードビット: {bin(record_bits)}")
                
                result_bits |= (record_bits << current_pos)
                current_pos += self.EXTENDED_HEADER_TOTAL + (bytes_needed * 8)
                print(f"  現在位置: {current_pos}")
            
            print(f"\n  最終結果ビット: {bin(result_bits)}")
            return result_bits
    
    debug_mixin = DebugMixin()
    
    print("\n1. latitude フィールドのエンコード")
    debug_mixin.debug_dict_to_bits({'latitude': 35.6895})

def debug_decoding_process():
    """デコード過程のデバッグ"""
    print("\n=== デコード過程デバッグ ===")
    
    # まずエンコードしてからデコードを試す
    packet = Format(
        version=1,
        packet_id=1,
        ex_flag=1,
        timestamp=1234567890,
        ex_field={'latitude': 35.6895}
    )
    
    # バイト列に変換
    data = packet.to_bytes()
    print(f"  バイト列: {data.hex()}")
    
    # ビット列に戻す
    bitstr = int.from_bytes(data, byteorder='big')
    print(f"  ビット列: {bin(bitstr)}")
    
    # 拡張フィールド部分を抽出
    ex_field_start = 128
    ex_field_bits = bitstr >> ex_field_start
    print(f"  拡張フィールドビット: {bin(ex_field_bits)}")
    
    # 手動でデコードを試す
    if ex_field_bits:
        from wtp.packet.bit_utils import extract_bits
        
        current_pos = 0
        header = extract_bits(ex_field_bits, current_pos, 16)
        print(f"  ヘッダー: {bin(header)} ({header})")
        
        # 現在の解析方法
        bytes_length = (header >> 6) & ((1 << 10) - 1)
        key = header & ((1 << 6) - 1)
        print(f"  解析結果: key={key}, bytes_length={bytes_length}")
        
        # 値部分を抽出
        if bytes_length > 0:
            value_bits = extract_bits(ex_field_bits, current_pos + 16, bytes_length * 8)
            print(f"  値ビット: {bin(value_bits)} ({value_bits})")
            
            try:
                value_bytes = value_bits.to_bytes(bytes_length, byteorder='big')
                print(f"  値バイト: {value_bytes.hex()}")
                
                if key in [65, 66] and bytes_length == 4:
                    int_value = int.from_bytes(value_bytes, byteorder='big', signed=True)
                    float_value = int_value / 1_000_000
                    print(f"  座標復元: {int_value} -> {float_value}")
                else:
                    str_value = value_bytes.decode('utf-8', errors='ignore')
                    print(f"  文字列復元: {str_value}")
            except Exception as e:
                print(f"  復元エラー: {e}")

if __name__ == "__main__":
    print("拡張フィールドデバッグ開始")
    print("=" * 50)
    
    debug_bit_structure()
    debug_encoding_process()
    debug_decoding_process()
    
    print("\n" + "=" * 50)
    print("デバッグ完了")
