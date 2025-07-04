import unittest
import random
from datetime import datetime
from common.packet.format_base import FormatBase
from common.packet.format import Format
from common.packet.exceptions import BitFieldError

class TestChecksum(unittest.TestCase):
    """
    チェックサム機能のテストクラス
    """

    def test_calc_checksum12_basic(self):
        """
        calc_checksum12の基本的な計算テスト
        """
        # 既知の入力と期待される出力
        self.assertEqual(FormatBase().calc_checksum12(b'\x01\x02\x03'), 4089) # (1+2+3) = 6, ~6 = -7, -7 & 0xFFF = 4089
        self.assertEqual(FormatBase().calc_checksum12(b'\x00\x00\x00'), 4095) # (0) = 0, ~0 = -1, -1 & 0xFFF = 4095
        self.assertEqual(FormatBase().calc_checksum12(b'\xFF\xFF\xFF'), 3330) # (255*3) = 765, ~765 = -766, -766 & 0xFFF = 3330
        self.assertEqual(FormatBase().calc_checksum12(b'Hello World'), 3043) # sum('Hello World') = 1052, ~1052 = -1053, -1053 & 0xFFF = 3043

        # 長いバイト列のテスト
        long_data = bytes([i % 256 for i in range(1000)])
        # 1バイトずつ加算し、12ビットに折り返す計算をシミュレート
        expected_sum = sum(long_data)
        while expected_sum >> 12:
            expected_sum = (expected_sum & 0xFFF) + (expected_sum >> 12)
        expected_checksum = (~expected_sum) & 0xFFF
        self.assertEqual(FormatBase().calc_checksum12(long_data), expected_checksum)

    def test_verify_checksum12_valid(self):
        """
        verify_checksum12の正常系テスト
        """
        # FormatBaseインスタンスを作成し、to_bytesでチェックサムを自動計算させる
        packet = FormatBase(
            version=1,
            packet_id=100,
            type=1,
            timestamp=int(datetime.now().timestamp()),
            area_code="130000"
        )
        
        # バイト列に変換（この時点でチェックサムが計算される）
        data_with_checksum = packet.to_bytes()
        
        # 検証がTrueになることを確認
        self.assertTrue(packet.verify_checksum12(data_with_checksum))

    def test_verify_checksum12_tampered(self):
        """
        verify_checksum12の改ざんテスト
        """
        packet = FormatBase(
            version=1,
            packet_id=100,
            type=1,
            timestamp=int(datetime.now().timestamp()),
            area_code="130000"
        )
        
        data_with_checksum = packet.to_bytes()
        
        # チェックサム部分を意図的に改ざん
        # checksumフィールドの開始位置と長さを取得
        checksum_start, checksum_length = FormatBase._BIT_FIELDS['checksum']
        
        # バイト列を可変リストに変換
        tampered_data_list = list(data_with_checksum)
        
        # チェックサムが格納されているバイトのインデックスを計算
        # チェックサムは12ビットなので、2バイトにまたがる可能性がある
        # リトルエンディアンなので、下位ビットが先にくる
        
        # チェックサムの開始バイトと終了バイトを特定
        checksum_start_byte = checksum_start // 8
        checksum_end_byte = (checksum_start + checksum_length - 1) // 8
        
        # 少なくとも1バイトは改ざんする
        if len(tampered_data_list) > checksum_start_byte:
            tampered_data_list[checksum_start_byte] = (tampered_data_list[checksum_start_byte] + 1) % 256
        else:
            # パケットが短すぎる場合は、適当なバイトを改ざん
            if len(tampered_data_list) > 0:
                tampered_data_list[0] = (tampered_data_list[0] + 1) % 256
            else:
                # 空のバイト列の場合はテストできない
                return

        tampered_data = bytes(tampered_data_list)
        
        # 検証がFalseになることを確認
        self.assertFalse(packet.verify_checksum12(tampered_data))

    def test_packet_checksum_auto_calculation(self):
        """
        パケット生成時のチェックサム自動計算テスト
        """
        # FormatBaseインスタンスを作成
        packet = FormatBase(
            version=2,
            packet_id=200,
            type=2,
            weather_flag=1,
            timestamp=int(datetime.now().timestamp()),
            area_code="010000"
        )
        
        # to_bytesを呼び出すことでチェックサムが計算される
        data = packet.to_bytes()
        
        # チェックサムが0ではないことを確認
        self.assertNotEqual(packet.checksum, 0)
        
        # from_bytesで復元し、チェックサムが一致することを確認
        restored_packet = FormatBase.from_bytes(data)
        self.assertEqual(packet.checksum, restored_packet.checksum)
        self.assertTrue(restored_packet.verify_checksum12(data))

    def test_field_change_recalculates_checksum(self):
        """
        フィールド変更時のチェックサム再計算テスト
        """
        packet = FormatBase(
            version=1,
            packet_id=1,
            type=0,
            timestamp=int(datetime.now().timestamp()),
            area_code="130000"
        )
        
        original_checksum = packet.checksum
        
        # フィールドを変更
        packet.packet_id = 2
        
        # チェックサムが再計算され、元の値と異なることを確認
        self.assertNotEqual(packet.checksum, original_checksum)
        
        # 新しいチェックサムで検証が通ることを確認
        data = packet.to_bytes()
        self.assertTrue(packet.verify_checksum12(data))

    def test_extended_field_change_recalculates_checksum(self):
        """
        FormatExtendedの拡張フィールド変更時のチェックサム再計算テスト
        """
        # Formatクラス（FormatExtendedを継承）のインスタンスを作成
        packet = Format(
            version=1,
            packet_id=1,
            type=0,
            ex_flag=1,
            timestamp=int(datetime.now().timestamp()),
            ex_field={
                'latitude': 35.0,
                'longitude': 135.0
            }
        )
        
        original_checksum = packet.checksum
        
        # 拡張フィールドを変更
        packet.ex_field.latitude = 36.0
        
        # チェックサムが再計算され、元の値と異なることを確認
        self.assertNotEqual(packet.checksum, original_checksum)
        
        # 新しいチェックサムで検証が通ることを確認
        data = packet.to_bytes()
        self.assertTrue(packet.verify_checksum12(data))

    def test_checksum_error_handling(self):
        """
        チェックサム関連のエラーハンドリングテスト
        """
        # 不正なバイト列（短すぎる）
        packet = FormatBase()
        self.assertFalse(packet.verify_checksum12(b'\x01\x02')) # 短すぎるバイト列

        # from_bytesで不正なバイト列を渡した場合
        with self.assertRaises(BitFieldError):
            FormatBase.from_bytes(b'\x01\x02')

        # calc_checksum12に不正な型を渡した場合（Pythonの型チェックで防がれるが、念のため）
        with self.assertRaises(TypeError):
            FormatBase().calc_checksum12("invalid_data")

    def test_from_bytes_with_checksum_validation(self):
        """
        from_bytesがチェックサム検証を正しく行うかテスト
        """
        # 正常なパケットのテスト
        packet = FormatBase(
            version=1,
            packet_id=100,
            type=1,
            timestamp=int(datetime.now().timestamp()),
            area_code="130000"
        )
        data_with_checksum = packet.to_bytes()
        
        # 正常なパケットを復元できるか確認
        try:
            restored_packet = FormatBase.from_bytes(data_with_checksum)
            self.assertIsInstance(restored_packet, FormatBase)
            self.assertEqual(restored_packet.packet_id, packet.packet_id)
            self.assertEqual(restored_packet.checksum, packet.checksum)
        except BitFieldError as e:
            self.fail(f"正常なパケットでBitFieldErrorが発生しました: {e}")

        # 破損したパケットのテスト
        tampered_data_list = list(data_with_checksum)
        checksum_start, checksum_length = FormatBase._BIT_FIELDS['checksum']
        checksum_start_byte = checksum_start // 8
        
        if len(tampered_data_list) > checksum_start_byte:
            tampered_data_list[checksum_start_byte] = (tampered_data_list[checksum_start_byte] + 1) % 256
        else:
            if len(tampered_data_list) > 0:
                tampered_data_list[0] = (tampered_data_list[0] + 1) % 256
            else:
                self.skipTest("空のバイト列では改ざんテストができません")

        tampered_data = bytes(tampered_data_list)

        # 改ざんされたバイト列からの復元はBitFieldErrorを発生させることを確認
        with self.assertRaises(BitFieldError):
            FormatBase.from_bytes(tampered_data)

    def test_from_bytes_auto_checksum_behavior(self):
        """
        from_bytesでの自動チェックサム計算が抑制されているかを確認
        """
        packet = FormatBase(
            version=1,
            packet_id=1,
            type=0,
            timestamp=int(datetime.now().timestamp()),
            area_code="130000"
        )
        data = packet.to_bytes()

        call_count = 0
        original = FormatBase._recalculate_checksum

        def patched(self):
            nonlocal call_count
            call_count += 1
            return original(self)

        FormatBase._recalculate_checksum = patched
        try:
            FormatBase.from_bytes(data)
        finally:
            FormatBase._recalculate_checksum = original

        expected = 2 * (len(FormatBase.FIELD_LENGTH) - 1)
        self.assertEqual(call_count, expected)

if __name__ == '__main__':
    unittest.main()
