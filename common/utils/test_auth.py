"""
WIP認証機能のテスト

認証ハッシュの計算と検証機能のテストを行います。
"""

import time
import unittest
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.utils.auth import WIPAuth, AuthConfig, AuthErrorCode, AuthenticationError


class TestWIPAuth(unittest.TestCase):
    """WIP認証機能のテストクラス"""
    
    def setUp(self):
        """テスト前の準備"""
        self.packet_id = 0x123  # 291 (12bit範囲内)
        self.timestamp = int(time.time())  # 現在時刻
        self.passphrase = "test_passphrase_2025"
    
    def test_calculate_auth_hash_basic(self):
        """基本的な認証ハッシュ計算のテスト"""
        hash_value = WIPAuth.calculate_auth_hash(
            self.packet_id, 
            self.timestamp, 
            self.passphrase
        )
        
        self.assertIsInstance(hash_value, bytes)
    
    def test_calculate_auth_hash_reproducible(self):
        """同じ入力で同じハッシュが生成されることを確認"""
        hash1 = WIPAuth.calculate_auth_hash(
            self.packet_id, 
            self.timestamp, 
            self.passphrase
        )
        hash2 = WIPAuth.calculate_auth_hash(
            self.packet_id, 
            self.timestamp, 
            self.passphrase
        )
        
        self.assertEqual(hash1, hash2)
    
    def test_calculate_auth_hash_different_inputs(self):
        """異なる入力で異なるハッシュが生成されることを確認"""
        hash1 = WIPAuth.calculate_auth_hash(
            self.packet_id, 
            self.timestamp, 
            self.passphrase
        )
        hash2 = WIPAuth.calculate_auth_hash(
            self.packet_id + 1, 
            self.timestamp, 
            self.passphrase
        )
        hash3 = WIPAuth.calculate_auth_hash(
            self.packet_id, 
            self.timestamp + 1, 
            self.passphrase
        )
        hash4 = WIPAuth.calculate_auth_hash(
            self.packet_id, 
            self.timestamp, 
            self.passphrase + "_different"
        )
        
        # すべて異なるハッシュであることを確認
        self.assertNotEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)
        self.assertNotEqual(hash1, hash4)
        self.assertNotEqual(hash2, hash3)
        self.assertNotEqual(hash2, hash4)
        self.assertNotEqual(hash3, hash4)
    
    def test_verify_auth_hash_success(self):
        """認証ハッシュ検証の成功ケース"""
        hash_value = WIPAuth.calculate_auth_hash(
            self.packet_id, 
            self.timestamp, 
            self.passphrase
        )
        
        result = WIPAuth.verify_auth_hash(
            self.packet_id, 
            self.timestamp, 
            self.passphrase, 
            hash_value
        )
        
        self.assertTrue(result)
    
    def test_verify_auth_hash_failure(self):
        """認証ハッシュ検証の失敗ケース"""
        hash_value = WIPAuth.calculate_auth_hash(
            self.packet_id, 
            self.timestamp, 
            self.passphrase
        )
        
        # 間違ったパスフレーズで検証
        result = WIPAuth.verify_auth_hash(
            self.packet_id, 
            self.timestamp, 
            "wrong_passphrase", 
            hash_value
        )
        self.assertFalse(result)
        
        # 間違ったパケットIDで検証
        result = WIPAuth.verify_auth_hash(
            self.packet_id + 1, 
            self.timestamp, 
            self.passphrase, 
            hash_value
        )
        self.assertFalse(result)
        
        # 間違ったタイムスタンプで検証
        result = WIPAuth.verify_auth_hash(
            self.packet_id, 
            self.timestamp + 1, 
            self.passphrase, 
            hash_value
        )
        self.assertFalse(result)
    
    def test_invalid_packet_id(self):
        """不正なパケットIDのテスト"""
        # パケットIDが範囲外 (12bit = 0-4095)
        with self.assertRaises(ValueError):
            WIPAuth.calculate_auth_hash(4096, self.timestamp, self.passphrase)
        
        with self.assertRaises(ValueError):
            WIPAuth.calculate_auth_hash(-1, self.timestamp, self.passphrase)
    
    def test_invalid_timestamp(self):
        """不正なタイムスタンプのテスト"""
        # タイムスタンプが負の値
        with self.assertRaises(ValueError):
            WIPAuth.calculate_auth_hash(self.packet_id, -1, self.passphrase)
    
    def test_invalid_passphrase(self):
        """不正なパスフレーズのテスト"""
        # 空の文字列
        with self.assertRaises(ValueError):
            WIPAuth.calculate_auth_hash(self.packet_id, self.timestamp, "")
        
        # None
        with self.assertRaises(ValueError):
            WIPAuth.calculate_auth_hash(self.packet_id, self.timestamp, None)
    
    def test_verify_with_invalid_hash(self):
        """不正なハッシュでの検証テスト"""
        # 長さが不正
        result = WIPAuth.verify_auth_hash(
            self.packet_id, 
            self.timestamp, 
            self.passphrase, 
            b"short"
        )
        self.assertFalse(result)
        
        # 型が不正
        result = WIPAuth.verify_auth_hash(
            self.packet_id, 
            self.timestamp, 
            self.passphrase, 
            "not_bytes"
        )
        self.assertFalse(result)


class TestAuthConfig(unittest.TestCase):
    """認証設定のテストクラス"""
    
    def test_auth_config_default(self):
        """デフォルト設定のテスト"""
        config = AuthConfig()
        
        self.assertFalse(config.enabled)
        self.assertIsNone(config.passphrase)
        self.assertEqual(config.target_packet_types, {4, 5})
    
    def test_auth_config_custom(self):
        """カスタム設定のテスト"""
        config = AuthConfig(
            enabled=True,
            passphrase="test123",
            target_packet_types={2, 3, 4}
        )
        
        self.assertTrue(config.enabled)
        self.assertEqual(config.passphrase, "test123")
        self.assertEqual(config.target_packet_types, {2, 3, 4})
    
    def test_is_auth_required(self):
        """認証要否の判定テスト"""
        # 無効な設定
        config = AuthConfig(enabled=False)
        self.assertFalse(config.is_auth_required(4))
        self.assertFalse(config.is_auth_required(5))
        
        # 有効な設定
        config = AuthConfig(enabled=True, target_packet_types={4, 5})
        self.assertTrue(config.is_auth_required(4))
        self.assertTrue(config.is_auth_required(5))
        self.assertFalse(config.is_auth_required(2))
        self.assertFalse(config.is_auth_required(3))
    
    def test_validate_success(self):
        """設定検証の成功ケース"""
        # 無効な設定（パスフレーズ不要）
        config = AuthConfig(enabled=False)
        config.validate()  # エラーが発生しないことを確認
        
        # 有効な設定（パスフレーズあり）
        config = AuthConfig(enabled=True, passphrase="test123")
        config.validate()  # エラーが発生しないことを確認
    
    def test_validate_failure(self):
        """設定検証の失敗ケース"""
        # 有効だがパスフレーズなし
        config = AuthConfig(enabled=True)
        with self.assertRaises(ValueError):
            config.validate()
        
        # パスフレーズが文字列でない
        config = AuthConfig(enabled=True, passphrase=123)
        with self.assertRaises(ValueError):
            config.validate()
        
        # 対象パケットタイプがsetでない
        config = AuthConfig(enabled=True, passphrase="test", target_packet_types=[4, 5])
        with self.assertRaises(ValueError):
            config.validate()


def run_tests():
    """テストを実行"""
    unittest.main()


if __name__ == "__main__":
    run_tests()