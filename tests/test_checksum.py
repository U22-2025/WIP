import unittest
import timeit
import os
import time
from common.packet.format_base import FormatBase
from common.packet.exceptions import BitFieldError

class TestChecksum(unittest.TestCase):
    """チェックサム機能のテストクラス"""
    
    def test_basic_calculation(self):
        """基本チェックサム計算テスト"""
        test_cases = [
            # (input_data, expected_checksum)
            (b'\x01\x02\x03\x04', 0xFF5),  # 0x01 + 0x02 + 0x03 + 0x04 = 0x0A → ~0x0A & 0xFFF = 0xFF5
            (b'\xFF\xFF\xFF\xFF', 0x000),  # 最大値テスト
            (b'\x00\x00\x00\x00', 0xFFF),  # 0xFFFは0として扱われる
            (b'\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 0xFEF),  # 16バイト境界テスト
            (b'\x01\x23\x45\x67\x89\xAB\xCD\xEF', 0x1A9),  # 実データに近いパターン
        ]
        
        for data, expected in test_cases:
            with self.subTest(data=data.hex()):
                self.assertEqual(FormatBase().calc_checksum12(data), expected)
    
    def test_performance(self):
        """パフォーマンス測定テスト"""
        large_data = os.urandom(1024*1024)  # 1MBテストデータ
        elapsed = timeit.timeit(
            lambda: FormatBase().calc_checksum12(large_data),
            number=100
        )
        self.assertLess(elapsed, 2.5)  # 100回の計算が2.5秒未満 (閾値を緩和)
        
    def test_error_handling(self):
        """エラーハンドリングテスト"""
        test_cases = [
            # (input_data, invalid_checksum, expected_error_msg)
            (b'\x00'*16, 0xFFF, "不正なチェックサム値 (0xFFF)"),
            (b'\x01\x02\x03\x04', 0x123, "チェックサム不一致"),
            (b'', 0x000, "バイト列の長さが最小パケットサイズ"),
        ]
        
        for data, invalid_checksum, err_msg in test_cases:
            with self.subTest(data=data.hex() if data else "empty"):
                with self.assertRaises(BitFieldError) as cm:
                    FormatBase().validate_checksum(data, invalid_checksum)
                self.assertIn(err_msg, str(cm.exception))
            
    def test_load_performance(self):
        """高負荷時のパフォーマンステスト"""
        start = time.perf_counter()
        for _ in range(1000):
            FormatBase().calc_checksum12(os.urandom(1024))
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, 1.5)  # 1000回の計算が1.5秒未満

    def test_endian_performance(self):
        """エンディアン変換のパフォーマンス比較テスト"""
        data = os.urandom(1024)  # 1KBテストデータ
        iterations = 1000
        
        # エンディアン変換なし
        base = FormatBase()
        start = time.perf_counter()
        for _ in range(iterations):
            base.calc_checksum12(data)
        no_endian_time = time.perf_counter() - start
        
        # エンディアン変換あり
        converter = FormatBase(needs_endian_conversion=True)
        start = time.perf_counter()
        for _ in range(iterations):
            converter.calc_checksum12(data)
        endian_time = time.perf_counter() - start
        
        # 結果を出力 (assertはしないが、時間差を確認できる)
        print(f"\nエンディアン変換なし: {no_endian_time:.4f}s")
        print(f"エンディアン変換あり: {endian_time:.4f}s")
        print(f"オーバーヘッド: {(endian_time/no_endian_time - 1)*100:.1f}%")

class MockServer:
    """テスト用のモックサーバークラス"""
    
    def __init__(self):
        self.packet_handler = FormatBase()
        
    def validate_packet(self, data: bytes) -> bool:
        """
        パケットのチェックサムを検証する
        
        Args:
            data: 検証対象のパケットデータ
            
        Returns:
            チェックサムが有効な場合はTrue
        """
        if len(data) < 16:  # 最小パケットサイズ
            return False
            
        # 最後の12ビットがチェックサム
        checksum = int.from_bytes(data[-2:], byteorder='little') & 0xFFF
        packet_data = data[:-2] + b'\x00\x00'  # チェックサム部分をゼロクリア
        
        return self.packet_handler.validate_checksum(packet_data, checksum)

class TestEndianConversion(unittest.TestCase):
    """エンディアン変換機能のテストクラス"""
    
    def test_endian_conversion(self):
        """エンディアン変換ありのチェックサム計算テスト"""
        data = b'\x01\x02\x03\x04'
        
        # 通常のチェックサム計算
        normal_checksum = FormatBase().calc_checksum12(data)
        
        # エンディアン変換ありのチェックサム計算
        converter = FormatBase(needs_endian_conversion=True)
        converted_checksum = converter.calc_checksum12(data)
        
        # 結果が異なることを確認
        self.assertNotEqual(normal_checksum, converted_checksum)
        
        # エンディアン変換後の期待値 (データを反転して計算)
        expected = FormatBase().calc_checksum12(data[::-1])
        self.assertEqual(converted_checksum, expected)
    
    def test_mixed_endian(self):
        """ヘッダーとデータ部で異なるエンディアンを設定したテスト"""
        # ヘッダーはビッグエンディアン、データ部はリトルエンディアン
        packet = FormatBase(
            header_endian='big',
            data_endian='little',
            needs_endian_conversion=True
        )
        
        # テストデータ生成 (ヘッダー26バイト + データ10バイト)
        test_data = bytes(range(36))
        converted = packet._convert_header_endian(test_data)
        converted = packet._convert_data_endian(converted)
        
        # 変換前後でデータ長が変わらないことを確認
        self.assertEqual(len(test_data), len(converted))
        
        # ヘッダー部(最初の26バイト)がビッグエンディアンで変換されていることを確認
        header_original = test_data[:26]
        header_converted = converted[:26]
        self.assertNotEqual(header_original, header_converted)
        self.assertEqual(
            int.from_bytes(header_original, 'little'),
            int.from_bytes(header_converted, 'big')
        )
        
        # データ部(27バイト以降)がリトルエンディアンのままであることを確認
        data_original = test_data[26:]
        data_converted = converted[26:]
        self.assertEqual(data_original, data_converted)

    def test_boundary_bytes(self):
        """26/27バイト目の境界値テスト"""
        # 26バイト目と27バイト目に異なる値を設定
        test_data = bytes([i % 256 for i in range(26)] + [0xFF, 0x00] + [i % 256 for i in range(28, 36)])
        
        packet = FormatBase(
            header_endian='big',
            data_endian='little',
            needs_endian_conversion=True
        )
        
        converted = packet._convert_header_endian(test_data)
        converted = packet._convert_data_endian(converted)
        
        # 26バイト目(ヘッダー最終バイト)が変換されていることを確認
        self.assertNotEqual(test_data[25], converted[25])
        
        # 27バイト目(データ先頭バイト)が変換されていないことを確認
        self.assertEqual(test_data[26], converted[26])

    def test_validation_with_endian(self):
        """エンディアン変換ありのチェックサム検証テスト"""
        data = b'\x01\x02\x03\x04'
        
        # エンディアン変換ありでチェックサム計算
        converter = FormatBase(needs_endian_conversion=True)
        checksum = converter.calc_checksum12(data)
        
        # 検証 (エンディアン変換ありで正しく検証できること)
        self.assertTrue(converter.validate_checksum(data, checksum))
        
        # エンディアン変換なしで検証すると失敗すること
        normal_validator = FormatBase()
        self.assertFalse(normal_validator.validate_checksum(data, checksum))

    def test_real_packet_data(self):
        """実際のパケットデータを使用したテスト"""
        # 実際のパケットデータ例 (16バイト)
        real_packet = bytes.fromhex('0102030405060708090A0B0C0D0E0F10')
        checksum = FormatBase().calc_checksum12(real_packet)
        
        # チェックサム検証
        self.assertTrue(FormatBase().validate_checksum(real_packet, checksum))
        
        # 不正なデータで検証失敗を確認
        corrupted_packet = bytes.fromhex('0102030405060708090A0B0C0D0E0F11')
        self.assertFalse(FormatBase().validate_checksum(corrupted_packet, checksum))

    def test_bit_position_accuracy(self):
        """ビット位置指定の正確性テスト"""
        # 12ビットチェックサムの各ビットを個別にテスト
        for bit in range(12):
            # 特定のビットだけが立っているデータ
            test_value = 1 << bit
            data = test_value.to_bytes(2, byteorder='little')
            
            # チェックサム計算
            checksum = FormatBase().calc_checksum12(data)
            
            # 期待値: 1の補数
            expected = (~test_value) & 0xFFF
            self.assertEqual(checksum, expected,
                           f"Bit {bit} failed: got 0x{checksum:03x}, expected 0x{expected:03x}")

if __name__ == '__main__':
    unittest.main()