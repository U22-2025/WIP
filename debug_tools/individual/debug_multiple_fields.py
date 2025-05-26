#!/usr/bin/env python3
"""
複数フィールドのデバッグスクリプト
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'wtp'))

from wtp.packet import Format

def debug_multiple_fields():
    """複数フィールドのデバッグ"""
    print("=== 複数フィールドデバッグ ===")
    
    # latitude + longitude の組み合わせをデバッグ
    print("\n1. latitude + longitude 組み合わせデバッグ")
    try:
        packet = Format(
            version=1,
            packet_id=1,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={
                'latitude': 35.6895,
                'longitude': 139.6917
            }
        )
        
        print(f"  入力: {packet.ex_field}")
        
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
        print(f"  拡張フィールドビット長: {ex_field_bits.bit_length()}")
        
        # 手動でデコードを試す
        from wtp.packet.bit_utils import extract_bits
        
        current_pos = 0
        record_count = 0
        
        while current_pos < ex_field_bits.bit_length() and ex_field_bits != 0:
            record_count += 1
            print(f"\n  === レコード {record_count} ===")
            
            if ex_field_bits.bit_length() - current_pos < 16:
                print(f"  残りビット不足: {ex_field_bits.bit_length() - current_pos}")
                break
                
            header = extract_bits(ex_field_bits, current_pos, 16)
            print(f"  ヘッダー: {bin(header)} ({header})")
            
            bytes_length = (header >> 6) & ((1 << 10) - 1)
            key = header & ((1 << 6) - 1)
            print(f"  解析結果: key={key}, bytes_length={bytes_length}")
            
            # キー名を取得
            key_mapping = {1: 'alert', 2: 'disaster', 3: 'latitude', 4: 'longitude', 5: 'source_ip'}
            key_name = key_mapping.get(key, f'unknown({key})')
            print(f"  キー名: {key_name}")
            
            if bytes_length > 0:
                value_start = current_pos + 16
                value_bits = extract_bits(ex_field_bits, value_start, bytes_length * 8)
                print(f"  値ビット: {bin(value_bits)} ({value_bits})")
                
                try:
                    value_bytes = value_bits.to_bytes(bytes_length, byteorder='big')
                    print(f"  値バイト: {value_bytes.hex()}")
                    
                    if key in [3, 4] and bytes_length == 4:  # latitude, longitude
                        int_value = int.from_bytes(value_bytes, byteorder='big', signed=True)
                        float_value = int_value / 1_000_000
                        print(f"  座標復元: {int_value} -> {float_value}")
                    else:
                        str_value = value_bytes.decode('utf-8', errors='ignore')
                        print(f"  文字列復元: '{str_value}'")
                except Exception as e:
                    print(f"  復元エラー: {e}")
            
            current_pos += 16 + (bytes_length * 8)
            print(f"  次の位置: {current_pos}")
            
            if current_pos >= ex_field_bits.bit_length():
                break
        
        # 実際の復元結果
        restored = Format.from_bytes(data)
        print(f"\n  実際の復元結果: {restored.ex_field}")
        
    except Exception as e:
        print(f"  エラー: {e}")
        import traceback
        traceback.print_exc()

def debug_source_ip():
    """source_ip フィールドのデバッグ"""
    print("\n=== source_ip フィールドデバッグ ===")
    
    try:
        packet = Format(
            version=1,
            packet_id=1,
            ex_flag=1,
            timestamp=1234567890,
            ex_field={'source_ip': '192.168.1.1'}
        )
        
        print(f"  入力: {packet.ex_field}")
        
        # バイト列に変換
        data = packet.to_bytes()
        print(f"  バイト列: {data.hex()}")
        
        # 復元
        restored = Format.from_bytes(data)
        print(f"  復元結果: {restored.ex_field}")
        
    except Exception as e:
        print(f"  エラー: {e}")
        import traceback
        traceback.print_exc()

def debug_all_fields():
    """全フィールドのデバッグ"""
    print("\n=== 全フィールドデバッグ ===")
    
    try:
        packet = Format(
            version=1,
            packet_id=1,
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
        
        print(f"  入力: {packet.ex_field}")
        
        # バイト列に変換
        data = packet.to_bytes()
        print(f"  バイト列長: {len(data)} バイト")
        
        # 復元
        restored = Format.from_bytes(data)
        print(f"  復元結果: {restored.ex_field}")
        
        # 各フィールドの比較
        for key in packet.ex_field:
            input_val = packet.ex_field[key]
            restored_val = restored.ex_field.get(key, None)
            
            if key in ['latitude', 'longitude']:
                if restored_val is not None:
                    error = abs(input_val - restored_val)
                    status = "✅" if error < 0.000001 else "❌"
                    print(f"  {key}: {input_val} -> {restored_val} (誤差: {error:.9f}) {status}")
                else:
                    print(f"  {key}: {input_val} -> None ❌")
            else:
                status = "✅" if input_val == restored_val else "❌"
                print(f"  {key}: {input_val} -> {restored_val} {status}")
        
    except Exception as e:
        print(f"  エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("複数フィールドデバッグ開始")
    print("=" * 50)
    
    debug_multiple_fields()
    debug_source_ip()
    debug_all_fields()
    
    print("\n" + "=" * 50)
    print("デバッグ完了")
