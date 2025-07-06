"""
認証機能と拡張フィールドの統合テスト

認証ハッシュが拡張フィールドで正しく処理されることを確認します。
"""

import time
import unittest
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from common.packet.extended_field import ExtendedField, ExtendedFieldType
from common.utils.auth import WIPAuth


class TestAuthIntegration(unittest.TestCase):
    """認証機能と拡張フィールドの統合テスト"""
    
    def setUp(self):
        """テスト前の準備"""
        self.packet_id = 0x123  # 291
        self.timestamp = int(time.time())
        self.passphrase = "test_passphrase_2025"
        
        # 認証ハッシュを計算
        self.auth_hash = WIPAuth.calculate_auth_hash(
            self.packet_id, 
            self.timestamp, 
            self.passphrase
        )
    
    def test_extended_field_auth_hash_basic(self):
        """拡張フィールドでの認証ハッシュ基本操作"""
        # ExtendedFieldに認証ハッシュを設定
        ext_field = ExtendedField()
        ext_field.auth_hash = self.auth_hash
        
        # 取得して確認
        retrieved_hash = ext_field.auth_hash
        self.assertEqual(retrieved_hash, self.auth_hash)
        self.assertEqual(len(retrieved_hash), 16)
        self.assertIsInstance(retrieved_hash, bytes)
    
    def test_extended_field_auth_hash_validation(self):
        """拡張フィールドでの認証ハッシュバリデーション"""
        ext_field = ExtendedField()
        
        # 正常なケース
        ext_field.auth_hash = self.auth_hash
        self.assertEqual(ext_field.auth_hash, self.auth_hash)
        
        # 不正な長さ（15バイト）
        with self.assertRaises(ValueError):
            ext_field.auth_hash = b'x' * 15
        
        # 不正な長さ（17バイト）
        with self.assertRaises(ValueError):
            ext_field.auth_hash = b'x' * 17
        
        # 不正な型
        with self.assertRaises(ValueError):
            ext_field.auth_hash = "not_bytes"
    
    def test_extended_field_serialization_with_auth(self):
        """認証ハッシュを含む拡張フィールドのシリアライゼーション"""
        # 複数のフィールドを持つ拡張フィールドを作成
        ext_field = ExtendedField()
        ext_field.auth_hash = self.auth_hash
        ext_field.alert = ["津波警報", "地震情報"]
        ext_field.latitude = 35.6895
        ext_field.longitude = 139.6917
        
        # ビット列に変換
        bits = ext_field.to_bits()
        self.assertIsInstance(bits, int)
        self.assertGreater(bits, 0)
        
        # ビット列から復元
        restored_field = ExtendedField.from_bits(bits)
        
        # 認証ハッシュが正しく復元されることを確認
        self.assertEqual(restored_field.auth_hash, self.auth_hash)
        self.assertEqual(len(restored_field.auth_hash), 16)
        
        # 他のフィールドも正しく復元されることを確認
        self.assertIsNotNone(restored_field.alert)
        self.assertAlmostEqual(restored_field.latitude, 35.6895, places=5)
        self.assertAlmostEqual(restored_field.longitude, 139.6917, places=5)
    
    def test_extended_field_auth_only(self):
        """認証ハッシュのみを持つ拡張フィールド"""
        ext_field = ExtendedField()
        ext_field.auth_hash = self.auth_hash
        
        # 他のフィールドが空であることを確認
        self.assertIsNone(ext_field.alert)
        self.assertIsNone(ext_field.disaster)
        self.assertIsNone(ext_field.latitude)
        self.assertIsNone(ext_field.longitude)
        self.assertIsNone(ext_field.source)
        
        # 認証ハッシュのみが設定されていることを確認
        self.assertEqual(ext_field.auth_hash, self.auth_hash)
        
        # シリアライゼーション・デシリアライゼーション
        bits = ext_field.to_bits()
        restored_field = ExtendedField.from_bits(bits)
        self.assertEqual(restored_field.auth_hash, self.auth_hash)
    
    def test_extended_field_dict_conversion_with_auth(self):
        """認証ハッシュを含む辞書変換"""
        ext_field = ExtendedField()
        ext_field.auth_hash = self.auth_hash
        ext_field.alert = ["地震情報"]
        
        # 辞書に変換
        field_dict = ext_field.to_dict()
        
        self.assertIn('auth_hash', field_dict)
        self.assertEqual(field_dict['auth_hash'], self.auth_hash)
        self.assertIn('alert', field_dict)
    
    def test_extended_field_initialization_with_auth(self):
        """初期化時に認証ハッシュを含むデータを渡す"""
        data = {
            'auth_hash': self.auth_hash,
            'alert': ['津波警報'],
            'latitude': 35.6895
        }
        
        ext_field = ExtendedField(data)
        
        self.assertEqual(ext_field.auth_hash, self.auth_hash)
        self.assertIsNotNone(ext_field.alert)
        self.assertAlmostEqual(ext_field.latitude, 35.6895, places=5)
    
    def test_auth_verification_with_extended_field(self):
        """拡張フィールドから取得した認証ハッシュでの検証"""
        # 拡張フィールドに認証ハッシュを設定
        ext_field = ExtendedField()
        ext_field.auth_hash = self.auth_hash
        
        # シリアライゼーション・デシリアライゼーション
        bits = ext_field.to_bits()
        restored_field = ExtendedField.from_bits(bits)
        
        # 復元された認証ハッシュで検証
        result = WIPAuth.verify_auth_hash(
            self.packet_id,
            self.timestamp,
            self.passphrase,
            restored_field.auth_hash
        )
        
        self.assertTrue(result)
    
    def test_multiple_auth_hashes_different_params(self):
        """異なるパラメータで複数の認証ハッシュを処理"""
        # パケット1
        packet_id_1 = 0x100
        timestamp_1 = self.timestamp
        auth_hash_1 = WIPAuth.calculate_auth_hash(packet_id_1, timestamp_1, self.passphrase)
        
        # パケット2
        packet_id_2 = 0x200
        timestamp_2 = self.timestamp + 1
        auth_hash_2 = WIPAuth.calculate_auth_hash(packet_id_2, timestamp_2, self.passphrase)
        
        # 異なるハッシュであることを確認
        self.assertNotEqual(auth_hash_1, auth_hash_2)
        
        # 両方とも拡張フィールドで処理可能
        ext_field_1 = ExtendedField()
        ext_field_1.auth_hash = auth_hash_1
        
        ext_field_2 = ExtendedField()
        ext_field_2.auth_hash = auth_hash_2
        
        # それぞれ正しく検証される
        self.assertTrue(WIPAuth.verify_auth_hash(packet_id_1, timestamp_1, self.passphrase, ext_field_1.auth_hash))
        self.assertTrue(WIPAuth.verify_auth_hash(packet_id_2, timestamp_2, self.passphrase, ext_field_2.auth_hash))
        
        # 間違った組み合わせでは検証失敗
        self.assertFalse(WIPAuth.verify_auth_hash(packet_id_1, timestamp_1, self.passphrase, ext_field_2.auth_hash))
        self.assertFalse(WIPAuth.verify_auth_hash(packet_id_2, timestamp_2, self.passphrase, ext_field_1.auth_hash))


def run_integration_tests():
    """統合テストを実行"""
    unittest.main()


if __name__ == "__main__":
    run_integration_tests()