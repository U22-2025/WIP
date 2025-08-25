#!/usr/bin/env python3
"""
Python版認証ハッシュ計算のデバッグ出力
Rust版と同じパラメータで計算して比較
"""

import sys
import os
import hashlib
import hmac

# WIPCommonPyをインポートできるようにパスを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from WIPCommonPy.utils.auth import WIPAuth

def test_with_rust_parameters():
    """Rust版のデバッグ出力と同じパラメータでテスト"""
    print("[DEBUG] Python版認証ハッシュ計算:")
    
    # Rust版の出力と同じ値を使用
    packet_id = 123
    timestamp = 1755838020  # Rust版のデバッグ出力から
    passphrase = "wip"
    
    print(f"  packet_id: {packet_id}")
    print(f"  timestamp: {timestamp}")
    print(f"  passphrase: '{passphrase}'")
    
    # 認証データを構築
    auth_data_str = f"{packet_id}:{timestamp}:{passphrase}"
    print(f"  auth_data文字列: '{auth_data_str}'")
    
    # バイト列への変換
    auth_data_bytes = auth_data_str.encode('utf-8')
    passphrase_bytes = passphrase.encode('utf-8')
    
    print(f"  auth_data bytes: {list(auth_data_bytes)}")
    print(f"  passphrase bytes: {list(passphrase_bytes)}")
    
    # WIPAuth.calculate_auth_hash()を使用
    hash_result = WIPAuth.calculate_auth_hash(packet_id, timestamp, passphrase)
    print(f"  計算されたハッシュ: {hash_result.hex()}")
    
    # 手動HMAC計算での確認
    manual_hmac = hmac.new(passphrase_bytes, auth_data_bytes, hashlib.sha256).digest()
    print(f"  手動HMAC結果: {manual_hmac.hex()}")
    
    # 一致確認
    print(f"  WIPAuth vs 手動HMAC一致: {hash_result.hex() == manual_hmac.hex()}")
    
    # Rust版の出力と比較
    rust_hash = "07b7ad87d9ffaac0cfdc1cc96f1b53215a0bed9bd0d0e7b8b135008b4f481484"
    print(f"  Rust版ハッシュ: {rust_hash}")
    print(f"  Python版 vs Rust版一致: {hash_result.hex() == rust_hash}")
    
    # バイト単位の詳細比較
    if hash_result.hex() != rust_hash:
        print("  【不一致詳細】")
        python_bytes = hash_result
        rust_bytes = bytes.fromhex(rust_hash)
        for i, (p, r) in enumerate(zip(python_bytes, rust_bytes)):
            if p != r:
                print(f"    バイト{i}: Python={p:02x}, Rust={r:02x}")

if __name__ == "__main__":
    test_with_rust_parameters()