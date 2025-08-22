#!/usr/bin/env python3
"""
Python版認証ハッシュ計算のテスト
Rust版と同じパラメータで計算して結果を比較
"""

import sys
import os
import hashlib
import hmac

# WIPCommonPyをインポートできるようにパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from WIPCommonPy.utils.auth import WIPAuth

def main():
    print("=== Python版認証ハッシュ計算テスト ===")
    
    # テストケース1: Rust版と同じ基本パラメータ
    packet_id1 = 1
    timestamp1 = 1634567890
    passphrase1 = "test_passphrase"
    
    hash1 = WIPAuth.calculate_auth_hash(packet_id1, timestamp1, passphrase1)
    print("テストケース1:")
    print(f"  packet_id: {packet_id1}")
    print(f"  timestamp: {timestamp1}")
    print(f"  passphrase: {passphrase1}")
    print(f"  auth_data: {packet_id1}:{timestamp1}:{passphrase1}")
    print(f"  Python計算結果: {hash1.hex()}")
    print()
    
    # 手動計算で詳細を確認
    auth_data = f"{packet_id1}:{timestamp1}:{passphrase1}"
    print("=== 手動計算詳細 ===")
    print(f"auth_data文字列: '{auth_data}'")
    print(f"auth_data bytes: {auth_data.encode('utf-8')}")
    print(f"passphrase bytes: {passphrase1.encode('utf-8')}")
    
    # 手動でHMAC計算
    auth_data_bytes = auth_data.encode('utf-8')
    passphrase_bytes = passphrase1.encode('utf-8')
    manual_hash = hmac.new(passphrase_bytes, auth_data_bytes, hashlib.sha256).digest()
    
    print(f"手動HMAC計算結果: {manual_hash.hex()}")
    print(f"ライブラリ計算結果: {hash1.hex()}")
    print(f"一致: {manual_hash.hex() == hash1.hex()}")
    print()
    
    # データ型の確認
    print("=== データ型と値の確認 ===")
    print(f"packet_id型: {type(packet_id1)}, 値: {packet_id1}")
    print(f"timestamp型: {type(timestamp1)}, 値: {timestamp1}")
    print(f"passphrase型: {type(passphrase1)}, 値: '{passphrase1}'")
    
    # フォーマット後の文字列の確認
    formatted_data = f"{packet_id1}:{timestamp1}:{passphrase1}"
    print(f"フォーマット後: '{formatted_data}'")
    print(f"文字数: {len(formatted_data)}")
    print(f"バイト数: {len(formatted_data.encode('utf-8'))}")
    
    # 各部分のバイト表現
    parts = [str(packet_id1), str(timestamp1), passphrase1]
    for i, part in enumerate(parts):
        print(f"部分{i+1} '{part}': {part.encode('utf-8')}")
    
    # 区切り文字の確認
    separator = ":"
    print(f"区切り文字 '{separator}': {separator.encode('utf-8')}")

if __name__ == "__main__":
    main()