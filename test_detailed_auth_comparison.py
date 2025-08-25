#!/usr/bin/env python3
"""
Python版とRust版の認証ハッシュ計算の詳細比較
同一のパラメータで計算して違いを特定
"""

import sys
import os
import hashlib
import hmac

# WIPCommonPyをインポートできるようにパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from WIPCommonPy.utils.auth import WIPAuth

def test_with_specific_values():
    """Rust版のテストと同じ具体的な値でテスト"""
    print("=== 同一パラメータでの詳細比較 ===")
    
    # Rust版のテストと同じ値を使用
    test_cases = [
        {
            "name": "テストケース1（固定値）",
            "packet_id": 1,
            "timestamp": 1634567890,
            "passphrase": "wip"
        },
        {
            "name": "テストケース2（Rust版debug_auth_details相当）",
            "packet_id": 123,
            "timestamp": 1755828175,  # 大体の値
            "passphrase": "wip"
        }
    ]
    
    for case in test_cases:
        print(f"\n{case['name']}:")
        packet_id = case['packet_id']
        timestamp = case['timestamp']
        passphrase = case['passphrase']
        
        print(f"  packet_id: {packet_id} (型: {type(packet_id)})")
        print(f"  timestamp: {timestamp} (型: {type(timestamp)})")
        print(f"  passphrase: '{passphrase}' (型: {type(passphrase)})")
        
        # 認証データの構築
        auth_data_str = f"{packet_id}:{timestamp}:{passphrase}"
        print(f"  auth_data文字列: '{auth_data_str}'")
        print(f"  auth_data長: {len(auth_data_str)} 文字")
        
        # バイト列への変換
        auth_data_bytes = auth_data_str.encode('utf-8')
        passphrase_bytes = passphrase.encode('utf-8')
        
        print(f"  auth_data_bytes: {auth_data_bytes}")
        print(f"  auth_data_bytes長: {len(auth_data_bytes)} バイト")
        print(f"  passphrase_bytes: {passphrase_bytes}")
        print(f"  passphrase_bytes長: {len(passphrase_bytes)} バイト")
        
        # WIPAuth.calculate_auth_hash()を使用
        hash_result = WIPAuth.calculate_auth_hash(packet_id, timestamp, passphrase)
        print(f"  WIPAuth結果: {hash_result.hex()}")
        print(f"  WIPAuth結果長: {len(hash_result)} バイト")
        
        # 手動HMAC計算
        manual_hmac = hmac.new(passphrase_bytes, auth_data_bytes, hashlib.sha256).digest()
        print(f"  手動HMAC結果: {manual_hmac.hex()}")
        print(f"  手動HMAC結果長: {len(manual_hmac)} バイト")
        
        # 一致確認
        print(f"  一致: {hash_result.hex() == manual_hmac.hex()}")
        
        # バイト単位での比較
        if hash_result != manual_hmac:
            print("  【不一致詳細】")
            for i, (a, b) in enumerate(zip(hash_result, manual_hmac)):
                if a != b:
                    print(f"    バイト{i}: WIPAuth={a:02x}, 手動={b:02x}")

def test_data_type_variations():
    """データ型による違いをテスト"""
    print("\n=== データ型による影響テスト ===")
    
    # 異なるデータ型でテスト
    packet_id_int = 123
    packet_id_str = "123"
    timestamp_int = 1755828175
    timestamp_str = "1755828175"
    passphrase = "wip"
    
    variations = [
        ("int:int", packet_id_int, timestamp_int),
        ("str:int", packet_id_str, timestamp_int),
        ("int:str", packet_id_int, timestamp_str),
        ("str:str", packet_id_str, timestamp_str),
    ]
    
    for name, pid, ts in variations:
        print(f"\n{name} - packet_id:{type(pid)}, timestamp:{type(ts)}")
        auth_data = f"{pid}:{ts}:{passphrase}"
        print(f"  auth_data: '{auth_data}'")
        
        try:
            # WIPAuthは型変換を行うかもしれない
            hash_result = WIPAuth.calculate_auth_hash(pid, ts, passphrase)
            print(f"  結果: {hash_result.hex()}")
        except Exception as e:
            print(f"  エラー: {e}")

def test_string_encoding():
    """文字列エンコーディングの詳細テスト"""
    print("\n=== 文字列エンコーディング詳細テスト ===")
    
    packet_id = 123
    timestamp = 1755828175
    passphrase = "wip"
    
    # 様々なエンコーディング方法でテスト
    auth_data_str = f"{packet_id}:{timestamp}:{passphrase}"
    
    encodings = ['utf-8', 'ascii', 'latin-1']
    for encoding in encodings:
        try:
            auth_bytes = auth_data_str.encode(encoding)
            pass_bytes = passphrase.encode(encoding)
            hash_result = hmac.new(pass_bytes, auth_bytes, hashlib.sha256).digest()
            print(f"  {encoding}: {hash_result.hex()}")
        except Exception as e:
            print(f"  {encoding}: エラー - {e}")

if __name__ == "__main__":
    test_with_specific_values()
    test_data_type_variations()
    test_string_encoding()