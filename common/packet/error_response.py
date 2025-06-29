import json
from pathlib import Path
from typing import Dict

from .format_base import FormatBase
from .extended_field import ExtendedField
from .exceptions import InvalidErrorCodeException, ErrorPacketSerializationException

class ErrorResponse(FormatBase):
    _error_codes: Dict[str, str] = {}
    
    def __init__(self, *, error_code: int = None, version: int = 1, type: int = 7, **kwargs):
        super().__init__(version=version, type=type, **kwargs)
        # チェックサム自動計算を有効化
        self._auto_checksum = True
        # エンディアン変換フラグを明示的に設定
        self._needs_endian_conversion = False
        print(f"[DEBUG] ErrorResponse initialized - auto_checksum: {self._auto_checksum}, needs_endian: {self._needs_endian_conversion}")
        
        self._weather_code = 0  # エラーコード格納用 (16ビット)
        self.ex_field = ExtendedField()  # ソースIP格納用
        
        # error_codeが指定されていれば設定
        if error_code is not None:
            self.error_code = error_code
            
        # 初回のみエラーコードを読み込む
        if not self._error_codes:
            self.load_error_codes()
    
    @classmethod
    def load_error_codes(cls, json_path: str = None) -> None:
        """エラーコードJSONを読み込む
        
        Args:
            json_path (str, optional): JSONファイルパス. Defaults to None (common/packet/error_code.json).
        """
        default_path = str(Path(__file__).parent / "error_code.json")
        path = json_path or default_path
        
        if not Path(path).exists():
            raise InvalidErrorCodeException(
                f"Error code file not found: {path}\n"
                "Please ensure error_code.json exists in common/packet directory"
            )
            
        try:
            with open(path, "r", encoding="utf-8") as f:
                cls._error_codes = json.load(f)
        except json.JSONDecodeError as e:
            raise InvalidErrorCodeException(
                f"Invalid JSON format in error code file: {path}\n"
                f"Error details: {str(e)}"
            )
        except Exception as e:
            raise InvalidErrorCodeException(
                f"Failed to load error codes from {path}\n"
                f"Error details: {str(e)}"
            )

    @property
    def error_code(self) -> int:
        """エラーコードを取得 (16ビット符号なし整数)"""
        return self._weather_code

    def _validate_error_code_range(self, code: int, server_type: str = None) -> bool:
        """エラーコードが適切な範囲内にあるか検証
        
        Args:
            code: 検証するエラーコード
            server_type: サーバータイプ('weather','location','query')
        
        Returns:
            bool: コードが有効な範囲内ならTrue
        """
        if server_type:
            if server_type == 'weather' and 256 <= code <= 511:
                return True
            elif server_type == 'location' and 512 <= code <= 767:
                return True
            elif server_type == 'query' and 768 <= code <= 1023:
                return True
        else:
            if 0 <= code <= 255:  # 共通エラー
                return True
            elif 256 <= code <= 1023:  # 全サーバー固有エラー
                return True
        return False

    @error_code.setter
    def error_code(self, value: int) -> None:
        """エラーコードを設定 (16ビット符号なし整数)
        
        Args:
            value: 0-65535の範囲の整数
            
        Raises:
            ValueError: 範囲外の値が指定された場合
        """
        if not 0 <= value <= 0xFFFF:
            raise ValueError(f"Error code must be 16-bit unsigned (0-65535), got {value}")
        if not self._validate_error_code_range(value):
            raise ValueError(f"Error code {value} is outside allowed ranges (0-255 or 256-1023)")
        self._weather_code = value

    def set_source_ip(self, ip: str, port: int) -> None:
        """ソースIPアドレスを設定
        
        Args:
            ip: IPアドレス文字列 (IPv4形式, 例: "192.168.1.1")
            port: ポート番号 (0-65535)
            
        Raises:
            ValueError: 無効なIPまたはポートの場合
            
        Examples:
            >>> pkt.set_source_ip("192.168.1.1", 8080)  # 正常
            >>> pkt.set_source_ip("invalid", 99999)      # ValueError
        """
        # IPアドレスの簡易検証
        if not isinstance(ip, str) or not ip:
            raise ValueError("IPアドレスは空でない文字列である必要があります")
        if ip.count('.') != 3 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in ip.split('.')):
            raise ValueError(f"無効なIPv4アドレス形式: {ip}")
            
        # ポート番号の検証
        if not isinstance(port, int) or not (0 <= port <= 65535):
            raise ValueError(f"ポート番号は0-65535の整数である必要があります: {port}")
            
        self.ex_field.source = (ip, port)

    def get_error_message(self, code: str = None) -> str:
        """エラーコードからメッセージを取得
        
        Args:
            code (str, optional): エラーコード. Defaults to None (インスタンスのerror_codeを使用).
            
        Returns:
            str: エラーメッセージ。不明なコードの場合は汎用メッセージを返す
            
        Raises:
            InvalidErrorCodeException: コード形式が不正な場合
        """
        target_code = code if code is not None else f"{self.error_code:03d}"
        
        # コード形式の検証
        if not isinstance(target_code, str):
            raise InvalidErrorCodeException(f"Error code must be string, got {type(target_code)}")
        if len(target_code) != 3 or not target_code.isdigit():
            raise InvalidErrorCodeException(f"Error code must be 3-digit string, got '{target_code}'")
            
        # コードが存在しない場合は汎用メッセージを返す
        if target_code not in self._error_codes:
            return f"Unknown error (code: {target_code})"
            
        return self._error_codes[target_code]
        
    def serialize(self) -> bytes:
        """パケットをバイト列にシリアライズ

        Returns:
            bytes: シリアライズされたバイト列
            
        Raises:
            ErrorPacketSerializationException: シリアライズに失敗した場合
        """
        try:
            # エラーコードを3桁文字列に変換して検証
            error_code_str = f"{self.error_code:03d}"
            
            # エラーコードが存在しない場合のフォールバック処理
            if error_code_str not in self._error_codes:
                # 不明なエラーコード用のデフォルトバイト列を返す
                self._weather_code = 0  # 不明エラー用コード
                error_code_str = "000"  # デフォルトエラーコード
            
            # 基本フィールドをビット列に変換
            bitstr = self.to_bits()
            # ex_fieldをビット列に変換
            ex_bits = self.ex_field.to_bits()
            
            # 結合してバイト列に変換
            combined = (ex_bits << 128) | bitstr  # 基本フィールドは128ビット
            required_bytes = max((combined.bit_length() + 7) // 8, 16)  # 最小16バイト確保
            data = combined.to_bytes(required_bytes, byteorder='little')
            
            # 全データ(基本+拡張)に対してチェックサム計算
            print(f"[DEBUG] Checksum input data: {data.hex()}")
            self._checksum = self.calc_checksum12(data)
            print(f"[DEBUG] Calculated checksum: {self._checksum:04x}")
            return data
        except InvalidErrorCodeException as e:
            raise
        except Exception as e:
            raise ErrorPacketSerializationException(
                f"ErrorResponse serialization failed: {str(e)}"
            )
        
    def __str__(self) -> str:
        """人間が読める形式の文字列表現"""
        return (
            f"ErrorResponse("
            f"version={self.version}, "
            f"packet_id={self.packet_id}, "
            f"type={self.type}, "
            f"error_code={self.error_code}, "
            f"source={self.ex_field.source}"
            f")"
        )

    def deserialize(self, data: bytes) -> int:
        """バイト列からパケットをデシリアライズ
        
        Args:
            data: デシリアライズするバイト列
            
        Returns:
            int: 処理したバイト数
            
        Raises:
            ErrorPacketSerializationException: デシリアライズに失敗した場合
        """
        try:
            # 基本フィールド (128ビット = 16バイト)
            if len(data) < 16:
                raise ErrorPacketSerializationException("Data too short for base fields")
                
            base_bits = int.from_bytes(data[:16], byteorder='little')
            self.from_bits(base_bits)
            
            # チェックサム検証 (全データで検証)
            print(f"[DEBUG] Verify checksum input: {data.hex()}")
            if not self.verify_checksum12(data):  # 全データで検証
                raise ErrorPacketSerializationException(
                    "チェックサム検証に失敗しました。パケットが破損しているか、改ざんされています。"
                )
            
            # ex_field (残りのデータ)
            if len(data) > 16:
                ex_bits = int.from_bytes(data[16:], byteorder='little')
                self.ex_field = ExtendedField.from_bits(ex_bits)
            
            return len(data)
        except Exception as e:
            raise ErrorPacketSerializationException(
                f"ErrorResponse deserialization failed: {str(e)}"
            ) from e

if __name__ == "__main__":
    """テストスクリプト
    
    実行例:
        $ python -m common.packet.error_response
        
    テストケース:
        1. 正常なエラーコード読み込み
        2. ソースIP設定
        3. シリアライズ/デシリアライズ
        4. エラーメッセージ取得
        5. 不明なエラーコード処理
    """
    import os
    import tempfile
    import json
    
    # テスト用エラーコードJSONを作成
    TEST_JSON = {
        "001": "Invalid request",
        "002": "Authentication failed",
        "005": "Server busy"
    }
    
    try:
        # 一時ファイルにテストデータを書き込み
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(TEST_JSON, f)
            temp_path = f.name
            
        # テスト実行
        print("=== ErrorResponse Test ===")
        
        # 1. エラーコード読み込みテスト
        ErrorResponse.load_error_codes(temp_path)
        print("✓ Error codes loaded successfully")
        
        # 2. パケット作成テスト
        test_cases = [
            (1, "192.168.1.1", 8080),  # 正常ケース
            (2, "10.0.0.1", 12345),    # 別のIP/ポート
            (999, "127.0.0.1", 80),    # 不明なエラーコード
            (0, "invalid_ip", 99999),  # 不正なIP/ポート
        ]
        
        # 拡張テストケース
        test_cases_extended = [
            # (error_code, ip, port, expected_result)
            (1, "192.168.1.1", 8080, "Valid"),  # 正常ケース
            (2, "10.0.0.1", 12345, "Valid"),     # 別のIP/ポート
            (999, "127.0.0.1", 80, "Unknown code"),  # 不明なエラーコード
            (0, "invalid_ip", 99999, "Invalid IP"),  # 不正なIP
            (5, "192.168.1.256", 80, "Invalid IP"),  # IP範囲外
            (5, "192.168.1", 80, "Invalid IP"),      # IP形式不正
            (5, "", 80, "Invalid IP"),              # 空のIP
            (5, "192.168.1.1", -1, "Invalid port"),  # ポート範囲外
            (5, "192.168.1.1", 65536, "Invalid port"),  # ポート範囲外
            (5, "192.168.1.1", "8080", "Invalid port"),  # 文字列ポート
        ]

        for code, ip, port, expected in test_cases_extended:
            print(f"\nTest case: code={code}, ip={ip}, port={port} (Expected: {expected})")
            try:
                pkt = ErrorResponse()
                pkt.packet_id = 100 + code
                pkt.error_code = code
                
                # ソースIP設定テスト
                try:
                    pkt.set_source_ip(ip, port)
                    print(f"✓ Source IP set: {ip}:{port}")
                    
                    # シリアライズ/デシリアライズテスト
                    try:
                        data = pkt.serialize()
                        decoded = ErrorResponse.from_bytes(data)
                        
                        print(f"Original: {pkt}")
                        print(f"Decoded: {decoded}")
                        
                        # エラーメッセージ取得テスト
                        msg = decoded.get_error_message()
                        print(f"Error message: {msg}")
                        
                        # 期待結果と比較
                        if expected == "Unknown code":
                            assert "Unknown error" in msg
                        elif expected == "Valid":
                            assert msg == TEST_JSON.get(f"{code:03d}", f"Unknown error (code: {code:03d})")
                            
                    except ErrorPacketSerializationException as e:
                        print(f"! Serialization failed: {e}")
                        
                except ValueError as e:
                    print(f"! Invalid source: {e}")
                    # 期待されるエラーか確認
                    if expected not in str(e):
                        print(f"!! Unexpected error: {e}")
                    continue
                    
            except Exception as e:
                print(f"!! Unexpected error: {type(e).__name__}: {e}")
                
    finally:
        # 一時ファイルを削除
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)