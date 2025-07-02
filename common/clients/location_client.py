"""
Location Client - 改良版（専用パケットクラス使用）
Location Serverとの通信を行うクライアント（サーバー間通信用）
"""

import json
import socket
import struct
import time
from datetime import datetime
from dotenv import load_dotenv
import os
import logging
from ..packet import LocationRequest, LocationResponse
from ..utils.packet_id_generator import PacketIDGenerator12Bit
import traceback

PIDG = PacketIDGenerator12Bit()
load_dotenv()

class LocationClient:
    """Location Serverと通信するクライアント（専用パケットクラス使用）"""
    
    def __init__(self, host=os.getenv('LOCATION_RESOLVER_HOST'), port=int(os.getenv('LOCATION_RESOLVER_PORT')), debug=False):
        """
        初期化
        
        Args:
            host: Location Serverのホスト
            port: Location Serverのポート
            debug: デバッグモード
        """
        self.server_host = host
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.debug = debug
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.VERSION = 1

    def _hex_dump(self, data):
        """バイナリデータのhexダンプを作成"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"

    def _debug_print_request(self, request):
        """リクエストのデバッグ情報を出力（改良版）"""
        self.logger.debug("\n=== SENDING LOCATION REQUEST PACKET ===")
        self.logger.debug(f"Total Length: {len(request.to_bytes())} bytes")
        
        # 専用クラスのメソッドを使用
        coordinates = request.get_coordinates()
        source_info = request.get_source_info()
        
        self.logger.debug("\nRequest Details:")
        self.logger.debug(f"Type: {request.type}")
        self.logger.debug(f"Packet ID: {request.packet_id}")
        self.logger.debug(f"Coordinates: {coordinates}")
        self.logger.debug(f"Source: {source_info}")
        
        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(request.to_bytes()))
        self.logger.debug("===========================\n")

    def _debug_print_response(self, response):
        """レスポンスのデバッグ情報を出力（改良版）"""

        self.logger.debug("\n=== RECEIVED LOCATION RESPONSE PACKET ===")
        self.logger.debug(f"Total Length: {len(response.to_bytes())} bytes")
        
        # 専用クラスのメソッドを使用
        if hasattr(response, 'get_response_summary'):
            summary = response.get_response_summary()
            # summaryが辞書の場合、json.dumpsで安全に表示
            if isinstance(summary, dict):
                self.logger.debug(f"\nResponse Summary: {json.dumps(summary, ensure_ascii=False, indent=2)}")
            else:
                self.logger.debug(f"\nResponse Summary: {summary}")
        
        self.logger.debug("\nResponse Details:")
        self.logger.debug(f"Type: {response.type}")
        self.logger.debug(f"Area Code: {response.get_area_code()}")
        self.logger.debug(f"Valid: {response.is_valid()}")
        self.logger.debug(f"Source: {response.get_source_info()}")
        
        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(response.to_bytes()))
        self.logger.debug("============================\n")

    def get_location_info(self, latitude, longitude, source=None, preserve_flags=None):
        """
        座標から位置情報を取得（改良版）
        
        Args:
            latitude: 緯度
            longitude: 経度
            source: 送信元情報 (ip, port) のタプル
            preserve_flags: 保持するフラグ情報
            
        Returns:
            tuple: (LocationResponse, 処理時間)
        """
        try:
            start_time = time.time()

            # 専用クラスでリクエスト作成（大幅に簡潔になった）
            request_start = time.time()
            request = LocationRequest.create_coordinate_lookup(
                latitude=latitude,
                longitude=longitude,
                packet_id=PIDG.next_id(),
                source=source,
                preserve_flags=preserve_flags,
                version=self.VERSION
            )
            request_time = time.time() - request_start
            
            self._debug_print_request(request)

            # リクエスト送信とレスポンス受信
            network_start = time.time()
            self.sock.sendto(request.to_bytes(), (self.server_host, self.server_port))
            self.logger.debug(f"Sent request to {self.server_host}:{self.server_port}")

            data, addr = self.sock.recvfrom(1024)
            network_time = time.time() - network_start
            self.logger.debug(f"Received response from {addr}")

            # 専用クラスでレスポンス解析
            parse_start = time.time()
            response = LocationResponse.from_bytes(data)
            parse_time = time.time() - parse_start
            
            self._debug_print_response(response)

            total_time = time.time() - start_time

            if self.debug:
                self.logger.debug("\n=== TIMING INFORMATION ===")
                self.logger.debug(f"Request creation time: {request_time*1000:.2f}ms")
                self.logger.debug(f"Request send time: {(network_start - request_start)*1000:.2f}ms")
                self.logger.debug(f"Network round-trip time: {network_time*1000:.2f}ms")
                self.logger.debug(f"Response parsing time: {parse_time*1000:.2f}ms")
                self.logger.debug(f"Total processing time: {total_time*1000:.2f}ms")
                self.logger.debug("========================\n")

            return response, total_time

        except socket.timeout:
            self.logger.error("411: クライアントエラー: 座標解決サーバ接続タイムアウト")
            if self.debug:
                self.logger.exception("Traceback:")
            return None, 0
        except (ValueError, struct.error) as e:
            self.logger.error(f"400: クライアントエラー: 不正なパケット: {e}")
            if self.debug:
                self.logger.exception("Traceback:")
            return None, 0
        except Exception as e:
            self.logger.error(f"410: クライアントエラー: 座標解決サーバが見つからない: {e}")
            if self.debug:
                self.logger.exception("Traceback:")
            return None, 0

    def get_area_code_from_coordinates(self, latitude, longitude, source=None):
        """
        座標からエリアコードのみを取得する簡便メソッド
        
        Args:
            latitude: 緯度
            longitude: 経度
            source: 送信元情報 (ip, port) のタプル
            
        Returns:
            str: エリアコード（失敗時はNone）
        """
        response, _ = self.get_location_info(latitude, longitude, source)
        if response and response.is_valid():
            return response.get_area_code()
        self.logger.error("400: クライアントエラー: 不正なパケット")
        return None

    def close(self):
        """ソケットを閉じる"""
        self.sock.close()


def main():
    """メイン関数 - 使用例（専用パケットクラス版）"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Location Client Example (Enhanced with Specialized Packet Classes)")
    logger.info("=" * 70)
    
    # 東京の座標を使用
    latitude = 35.6895
    longitude = 139.6917
    
    client = LocationClient(debug=True)
    try:
        logger.info("\nTesting location resolution for coordinates:")
        logger.info(f"Latitude: {latitude}, Longitude: {longitude}")
        logger.info("-" * 50)
        
        # 改良版のメソッドを使用
        response, total_time = client.get_location_info(
            latitude=latitude,
            longitude=longitude,
            source=("127.0.0.1", 9999)
        )
        
        if response and response.is_valid():
            logger.info(f"\nLocation request completed in {total_time*1000:.2f}ms")
            logger.info(f"Area Code: {response.get_area_code()}")
            logger.info(f"Response Summary: {response.get_response_summary()}")
            
            # 簡便メソッドのテスト
            logger.info(f"\n--- Testing convenience method ---")
            area_code = client.get_area_code_from_coordinates(latitude, longitude)
            logger.info(f"Area Code (convenience method): {area_code}")
            
        else:
            logger.error("400: クライアントエラー: 不正なパケット")
            if response:
                logger.error(f"Response valid: {response.is_valid()}")
                
    finally:
        client.close()
        
    logger.info("\n" + "="*70)
    logger.info("Enhanced Location Client Example completed")
    logger.info("Using specialized packet classes for improved usability")


if __name__ == "__main__":
    main()
