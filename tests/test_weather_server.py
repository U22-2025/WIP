import unittest
import socket
import threading
from time import sleep
from WIP_Server.servers.weather_server import WeatherServer
from common.packet.weather_packet import WeatherRequest, WeatherResponse

class TestWeatherServer(unittest.TestCase):
    """WeatherServerのエンドツーエンドテスト"""

    def setUp(self):
        """テストサーバーを起動"""
        self.server = WeatherServer('localhost', 0)
        self.server_thread = threading.Thread(target=self.server.start)
        self.server_thread.start()
        sleep(0.1)  # サーバー起動待機

    def tearDown(self):
        """テストサーバーを停止"""
        self.server.stop()
        self.server_thread.join()

    def test_endian_conversion(self):
        """エンディアン変換を含む正常なリクエストテスト"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # 正しいエンディアン変換ありリクエスト
            req = WeatherRequest.create(latitude=35.68, longitude=139.76, days=3)
            sock.sendto(req.to_bytes(), ('localhost', self.server.port))
            
            data, _ = sock.recvfrom(1024)
            response = WeatherResponse.from_bytes(data)
            self.assertTrue(response.is_valid())

    def test_endian_mismatch(self):
        """エンディアン変換不一致テスト"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            # 意図的にエンディアン変換なしで送信
            req = WeatherRequest.create(latitude=35.68, longitude=139.76, days=3)
            invalid_data = req.to_bytes(needs_endian_conversion=False)
            sock.sendto(invalid_data, ('localhost', self.server.port))
            
            data, _ = sock.recvfrom(1024)
            # エラーレスポンスが返ることを確認
            self.assertEqual(data[0], 0x01)  # エラーコード

if __name__ == '__main__':
    unittest.main()