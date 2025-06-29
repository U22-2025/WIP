import unittest
from unittest.mock import patch
from WIP_Server.servers.base_server import MockServer
from common.packet.exceptions import BitFieldError
from common.packet.weather_packet import WeatherRequest

class TestServerChecksum(unittest.TestCase):
    """サーバーサイドチェックサム検証テスト"""

    @patch('WIP_Server.servers.base_server.MockServer._handle_error')
    def test_invalid_checksum(self, mock_handle):
        """無効なチェックサムが検出されるかテスト"""
        server = MockServer()
        invalid_packet = b'\x00'*128  # 不正なチェックサムを含むパケット
        
        with patch.object(server, 'validate_request') as mock_validate:
            mock_validate.return_value = (False, "Invalid checksum")
            server.handle_request(invalid_packet, ('127.0.0.1', 12345))
            
            mock_handle.assert_called_once()
            args, _ = mock_handle.call_args
            self.assertEqual(args[0], 0x0001)  # エラーコード0x0001が設定されているか

    def test_valid_checksum(self):
        """有効なチェックサムの処理テスト"""
        server = MockServer()
        valid_packet = b'\x01\x02\x03\x04' + b'\x00'*124  # 有効なチェックサムを想定
        
        with patch.object(server, 'create_response') as mock_create:
            mock_create.return_value = b'\x01\x02\x03\x04' + b'\x00'*124
            server.handle_request(valid_packet, ('127.0.0.1', 12345))
            mock_create.assert_called_once()

    def test_endian_conversion_checksum(self):
        """エンディアン変換が必要なパケットのチェックサム検証テスト"""
        server = MockServer()
        # 天気リクエストパケットはエンディアン変換が必要
        packet = WeatherRequest.create(1, 2, 3)
        
        with patch.object(server, 'create_response') as mock_create:
            mock_create.return_value = packet.to_bytes()
            server.handle_request(packet.to_bytes(), ('127.0.0.1', 12345))
            mock_create.assert_called_once()

    @patch('WIP_Server.servers.base_server.MockServer._handle_error')
    def test_endian_mismatch_checksum(self, mock_handle):
        """エンディアン変換不一致によるチェックサムエラーテスト"""
        server = MockServer()
        packet = WeatherRequest.create(1, 2, 3)
        # エンディアン変換を無効化した不正なパケット
        invalid_bytes = packet.to_bytes(needs_endian_conversion=False)
        
        server.handle_request(invalid_bytes, ('127.0.0.1', 12345))
        mock_handle.assert_called_once()
        args, _ = mock_handle.call_args
        self.assertEqual(args[0], 0x0001)  # チェックサムエラーコード

if __name__ == '__main__':
    unittest.main()