"""
Location Client - 改良版（専用パケットクラス使用）
Location Serverとの通信を行うクライアント（サーバー間通信用）
"""

import socket
import struct
import ipaddress
import time
import random
from datetime import datetime
from dotenv import load_dotenv
import os
from ..packet import LocationRequest, LocationResponse
from .utils.packet_id_generator import PacketIDGenerator12Bit

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
        self.VERSION = 1

    def _hex_dump(self, data):
        """バイナリデータのhexダンプを作成"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"

    def _debug_print_request(self, request):
        """リクエストのデバッグ情報を出力（改良版）"""
        if not self.debug:
            return

        print("\n=== SENDING LOCATION REQUEST PACKET ===")
        print(f"Total Length: {len(request.to_bytes())} bytes")
        
        # 専用クラスのメソッドを使用
        coordinates = request.get_coordinates()
        source_info = request.get_source_info()
        
        print(f"\nRequest Details:")
        print(f"Type: {request.type}")
        print(f"Packet ID: {request.packet_id}")
        print(f"Coordinates: {coordinates}")
        print(f"Source: {source_info}")
        
        print("\nRaw Packet:")
        print(self._hex_dump(request.to_bytes()))
        print("===========================\n")

    def _debug_print_response(self, response):
        """レスポンスのデバッグ情報を出力（改良版）"""
        if not self.debug:
            return

        print("\n=== RECEIVED LOCATION RESPONSE PACKET ===")
        print(f"Total Length: {len(response.to_bytes())} bytes")
        
        # 専用クラスのメソッドを使用
        if hasattr(response, 'get_response_summary'):
            summary = response.get_response_summary()
            print(f"\nResponse Summary: {summary}")
        
        print(f"\nResponse Details:")
        print(f"Type: {response.type}")
        print(f"Area Code: {response.get_area_code()}")
        print(f"Valid: {response.is_valid()}")
        print(f"Source: {response.get_source_info()}")
        
        print("\nRaw Packet:")
        print(self._hex_dump(response.to_bytes()))
        print("============================\n")

    def get_location_info(self, latitude, longitude, source=None, preserve_flags=None):
        """
        座標から位置情報を取得（改良版）
        
        Args:
            latitude: 緯度
            longitude: 経度
            source: 送信元情報（プロキシルーティング用）
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
            if self.debug:
                print(f"Sent request to {self.server_host}:{self.server_port}")

            data, addr = self.sock.recvfrom(1024)
            network_time = time.time() - network_start
            if self.debug:
                print(f"Received response from {addr}")

            # 専用クラスでレスポンス解析
            parse_start = time.time()
            response = LocationResponse.from_bytes(data)
            parse_time = time.time() - parse_start
            
            self._debug_print_response(response)

            total_time = time.time() - start_time

            if self.debug:
                print("\n=== TIMING INFORMATION ===")
                print(f"Request creation time: {request_time*1000:.2f}ms")
                print(f"Request send time: {(network_start - request_start)*1000:.2f}ms")
                print(f"Network round-trip time: {network_time*1000:.2f}ms")
                print(f"Response parsing time: {parse_time*1000:.2f}ms")
                print(f"Total processing time: {total_time*1000:.2f}ms")
                print("========================\n")

            return response, total_time

        except Exception as e:
            print(f"Error communicating with location resolver: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None, 0

    def get_area_code_from_coordinates(self, latitude, longitude, source=None):
        """
        座標からエリアコードのみを取得する簡便メソッド
        
        Args:
            latitude: 緯度
            longitude: 経度
            source: 送信元情報
            
        Returns:
            str: エリアコード（失敗時はNone）
        """
        response, _ = self.get_location_info(latitude, longitude, source)
        if response and response.is_valid():
            return response.get_area_code()
        return None

    def close(self):
        """ソケットを閉じる"""
        self.sock.close()


def main():
    """メイン関数 - 使用例（専用パケットクラス版）"""
    print("Location Client Example (Enhanced with Specialized Packet Classes)")
    print("=" * 70)
    
    # 東京の座標を使用
    latitude = 35.6895
    longitude = 139.6917
    
    client = LocationClient(debug=True)
    try:
        print(f"\nTesting location resolution for coordinates:")
        print(f"Latitude: {latitude}, Longitude: {longitude}")
        print("-" * 50)
        
        # 改良版のメソッドを使用
        response, total_time = client.get_location_info(
            latitude=latitude, 
            longitude=longitude,
            source="location_client_test"
        )
        
        if response and response.is_valid():
            print(f"\n✓ Location request completed in {total_time*1000:.2f}ms")
            print(f"Area Code: {response.get_area_code()}")
            print(f"Response Summary: {response.get_response_summary()}")
            
            # 簡便メソッドのテスト
            print(f"\n--- Testing convenience method ---")
            area_code = client.get_area_code_from_coordinates(latitude, longitude)
            print(f"Area Code (convenience method): {area_code}")
            
        else:
            print("\n✗ Location request failed")
            if response:
                print(f"Response valid: {response.is_valid()}")
                
    finally:
        client.close()
        
    print("\n" + "="*70)
    print("Enhanced Location Client Example completed")
    print("✓ Using specialized packet classes for improved usability")


if __name__ == "__main__":
    main()
