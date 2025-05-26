"""
パケットテスト用のカスタムアサーション

パケットの比較や検証に特化したアサーション関数を提供します。
"""

import sys
from typing import Any, Dict, List, Optional, Union
from wtp.packet import Format, Request, Response, BitFieldError


class PacketAssertions:
    """パケット専用のアサーション関数群"""
    
    @staticmethod
    def assert_packet_fields_equal(packet1: Any, packet2: Any, ignore_fields: Optional[List[str]] = None) -> None:
        """
        パケットのフィールドが等しいことを確認
        
        Args:
            packet1: 比較対象パケット1
            packet2: 比較対象パケット2
            ignore_fields: 比較から除外するフィールドのリスト
        """
        ignore_fields = ignore_fields or []
        
        dict1 = packet1.as_dict()
        dict2 = packet2.as_dict()
        
        # 除外フィールドを削除
        for field in ignore_fields:
            dict1.pop(field, None)
            dict2.pop(field, None)
        
        # フィールドごとに比較
        all_fields = set(dict1.keys()) | set(dict2.keys())
        
        for field in all_fields:
            if field not in dict1:
                raise AssertionError(f"フィールド '{field}' がpacket1に存在しません")
            if field not in dict2:
                raise AssertionError(f"フィールド '{field}' がpacket2に存在しません")
            
            value1 = dict1[field]
            value2 = dict2[field]
            
            if value1 != value2:
                raise AssertionError(
                    f"フィールド '{field}' の値が一致しません:\n"
                    f"  packet1: {value1} (type: {type(value1)})\n"
                    f"  packet2: {value2} (type: {type(value2)})"
                )
    
    @staticmethod
    def assert_roundtrip_conversion(packet: Any) -> Any:
        """
        往復変換（パケット→バイト列→パケット）の整合性を確認

        Args:
            packet: テスト対象のパケット

        Returns:
            復元されたパケット
        """
        try:
            # パケット → バイト列
            bytes_data = packet.to_bytes()

            # バイト列 → パケット
            restored_packet = packet.__class__.from_bytes(bytes_data)

            # 元のパケットと復元されたパケットを比較（チェックサムは除外）
            PacketAssertions.assert_packet_fields_equal(packet, restored_packet, ignore_fields=['checksum'])

            return restored_packet

        except Exception as e:
            raise AssertionError(f"往復変換に失敗しました: {e}")
    
    @staticmethod
    def assert_bit_conversion(packet: Any) -> int:
        """
        ビット列変換の整合性を確認
        
        Args:
            packet: テスト対象のパケット
            
        Returns:
            生成されたビット列
        """
        try:
            # パケット → ビット列
            bitstr = packet.to_bits()
            
            # ビット列 → パケット
            restored_packet = packet.__class__(bitstr=bitstr)
            
            # 元のパケットと復元されたパケットを比較
            PacketAssertions.assert_packet_fields_equal(packet, restored_packet)
            
            return bitstr
            
        except Exception as e:
            raise AssertionError(f"ビット列変換に失敗しました: {e}")
    
    @staticmethod
    def assert_extended_field_integrity(packet: Any, expected_ex_field: Dict[str, Any]) -> None:
        """
        拡張フィールドの整合性を確認
        
        Args:
            packet: テスト対象のパケット
            expected_ex_field: 期待される拡張フィールド
        """
        if not hasattr(packet, 'ex_field'):
            raise AssertionError("パケットに拡張フィールドが存在しません")
        
        actual_ex_field = packet.ex_field
        
        # キーの比較
        expected_keys = set(expected_ex_field.keys())
        actual_keys = set(actual_ex_field.keys())
        
        if expected_keys != actual_keys:
            raise AssertionError(
                f"拡張フィールドのキーが一致しません:\n"
                f"  期待値: {expected_keys}\n"
                f"  実際値: {actual_keys}"
            )
        
        # 値の比較
        for key in expected_keys:
            expected_value = expected_ex_field[key]
            actual_value = actual_ex_field[key]
            
            if isinstance(expected_value, list) and isinstance(actual_value, list):
                # リストの場合は順序も含めて比較
                if expected_value != actual_value:
                    raise AssertionError(
                        f"拡張フィールド '{key}' のリスト値が一致しません:\n"
                        f"  期待値: {expected_value}\n"
                        f"  実際値: {actual_value}"
                    )
            elif isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
                # 数値の場合は型変換を考慮
                if abs(float(expected_value) - float(actual_value)) > 1e-10:
                    raise AssertionError(
                        f"拡張フィールド '{key}' の数値が一致しません:\n"
                        f"  期待値: {expected_value}\n"
                        f"  実際値: {actual_value}"
                    )
            else:
                # その他の場合は直接比較
                if expected_value != actual_value:
                    raise AssertionError(
                        f"拡張フィールド '{key}' の値が一致しません:\n"
                        f"  期待値: {expected_value} (type: {type(expected_value)})\n"
                        f"  実際値: {actual_value} (type: {type(actual_value)})"
                    )
    
    @staticmethod
    def assert_checksum_valid(packet: Any) -> None:
        """
        チェックサムが正しく計算されていることを確認
        
        Args:
            packet: テスト対象のパケット
        """
        try:
            # パケットをバイト列に変換
            bytes_data = packet.to_bytes()
            
            # チェックサムを検証
            is_valid = packet.verify_checksum12(bytes_data)
            
            if not is_valid:
                raise AssertionError(
                    f"チェックサムが無効です:\n"
                    f"  計算されたチェックサム: {packet.checksum}\n"
                    f"  パケットデータ: {bytes_data.hex()}"
                )
                
        except Exception as e:
            raise AssertionError(f"チェックサム検証に失敗しました: {e}")
    
    @staticmethod
    def assert_field_in_range(packet: Any, field_name: str, min_value: int, max_value: int) -> None:
        """
        フィールドの値が指定された範囲内にあることを確認
        
        Args:
            packet: テスト対象のパケット
            field_name: フィールド名
            min_value: 最小値
            max_value: 最大値
        """
        if not hasattr(packet, field_name):
            raise AssertionError(f"フィールド '{field_name}' が存在しません")
        
        value = getattr(packet, field_name)
        
        if not (min_value <= value <= max_value):
            raise AssertionError(
                f"フィールド '{field_name}' の値 {value} が範囲 [{min_value}, {max_value}] 外です"
            )
    
    @staticmethod
    def assert_raises_bit_field_error(func, *args, **kwargs) -> BitFieldError:
        """
        BitFieldErrorが発生することを確認
        
        Args:
            func: 実行する関数
            *args: 関数の引数
            **kwargs: 関数のキーワード引数
            
        Returns:
            発生したBitFieldError
        """
        try:
            func(*args, **kwargs)
            raise AssertionError("BitFieldErrorが発生しませんでした")
        except BitFieldError as e:
            return e
        except Exception as e:
            raise AssertionError(f"BitFieldError以外の例外が発生しました: {type(e).__name__}: {e}")
    
    @staticmethod
    def assert_bytes_equal(bytes1: bytes, bytes2: bytes, message: str = "") -> None:
        """
        バイト列が等しいことを確認（詳細な差分表示付き）
        
        Args:
            bytes1: 比較対象バイト列1
            bytes2: 比較対象バイト列2
            message: エラーメッセージの追加情報
        """
        if bytes1 == bytes2:
            return
        
        # 詳細な差分情報を生成
        len1, len2 = len(bytes1), len(bytes2)
        max_len = max(len1, len2)
        
        diff_info = []
        diff_info.append(f"バイト列が一致しません {message}")
        diff_info.append(f"長さ: {len1} vs {len2}")
        
        if len1 != len2:
            diff_info.append(f"長さが異なります")
        
        # 最初の10個の差分を表示
        diff_count = 0
        for i in range(min(max_len, 50)):  # 最大50バイトまで比較
            b1 = bytes1[i] if i < len1 else None
            b2 = bytes2[i] if i < len2 else None
            
            if b1 != b2:
                diff_count += 1
                if diff_count <= 10:
                    diff_info.append(
                        f"  位置 {i}: 0x{b1:02x} vs 0x{b2:02x}" if b1 is not None and b2 is not None
                        else f"  位置 {i}: {b1} vs {b2}"
                    )
        
        if diff_count > 10:
            diff_info.append(f"  ... 他 {diff_count - 10} 箇所で差分")
        
        # 16進ダンプ（最初の32バイト）
        diff_info.append("\n16進ダンプ（最初の32バイト）:")
        diff_info.append(f"bytes1: {bytes1[:32].hex()}")
        diff_info.append(f"bytes2: {bytes2[:32].hex()}")
        
        raise AssertionError("\n".join(diff_info))
    
    @staticmethod
    def assert_bit_pattern(value: int, expected_pattern: str, bit_length: int = None) -> None:
        """
        ビットパターンが期待値と一致することを確認
        
        Args:
            value: 検証する値
            expected_pattern: 期待されるビットパターン（例: "1010"）
            bit_length: ビット長（Noneの場合は自動計算）
        """
        if bit_length is None:
            bit_length = len(expected_pattern)
        
        actual_pattern = format(value, f'0{bit_length}b')
        
        if actual_pattern != expected_pattern:
            raise AssertionError(
                f"ビットパターンが一致しません:\n"
                f"  期待値: {expected_pattern}\n"
                f"  実際値: {actual_pattern}\n"
                f"  値: {value} (0x{value:x})"
            )
