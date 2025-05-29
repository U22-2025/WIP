"""
天気サーバー - プロキシサーバー実装
他のサーバーへリクエストを転送し、レスポンスを返す
"""

import socket
import time
import sys
import os
import threading
from datetime import datetime
from dotenv import load_dotenv

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # モジュールとして使用される場合
    from .base_server import BaseServer
    from .packet import Request, Response, BitFieldError
    from .location_resolver_client import LocationResolverClient
    from .query_generator_client import QueryGeneratorClient
except ImportError:
    # 直接実行される場合
    from base_server import BaseServer
    from packet import Request, Response, BitFieldError
    from location_resolver_client import LocationResolverClient
    from query_generator_client import QueryGeneratorClient


class WeatherServer(BaseServer):
    """天気サーバーのメインクラス（プロキシサーバー）"""
    
    def __init__(self, host='localhost', port=None, debug=False, max_workers=None):
        """
        初期化
        
        Args:
            host: サーバーホスト
            port: サーバーポート（Noneの場合は環境変数から取得）
            debug: デバッグモードフラグ
            max_workers: スレッドプールのワーカー数（Noneの場合はCPU数*2）
        """
        # 環境変数を読み込む
        load_dotenv()
        
        # ポートを環境変数から取得
        if port is None:
            port = int(os.getenv('WEATHER_SERVER_PORT', 4110))
        
        # 基底クラスの初期化（max_workersも渡す）
        super().__init__(host, port, debug, max_workers)
        
        # サーバー名を設定
        self.server_name = "WeatherServer"
        
        # 他のサーバーへの接続設定
        self.location_resolver_host = os.getenv('LOCATION_RESOLVER_HOST', 'localhost')
        self.location_resolver_port = int(os.getenv('LOCATION_RESOLVER_PORT', 4109))
        self.query_generator_host = os.getenv('QUERY_GENERATOR_HOST', 'localhost')
        self.query_generator_port = int(os.getenv('QUERY_GENERATOR_PORT', 4111))
        
        if self.debug:
            print(f"\n[Weather Server] Configuration:")
            print(f"  Location Resolver: {self.location_resolver_host}:{self.location_resolver_port}")
            print(f"  Query Generator: {self.query_generator_host}:{self.query_generator_port}")
        
        # クライアントの初期化
        self.location_client = LocationResolverClient(
            host=self.location_resolver_host,
            port=self.location_resolver_port,
            debug=self.debug
        )
        self.query_client = QueryGeneratorClient(
            host=self.query_generator_host,
            port=self.query_generator_port,
            debug=self.debug
        )
        
    def handle_request(self, data, addr):
        """
        リクエストを処理（プロキシとして転送）
        
        Args:
            data: 受信したバイナリデータ
            addr: 送信元アドレス
        """
        timing_info = {}
        start_time = time.time()
        
        if self.debug:
            print(f"\n[Weather Server] Received {len(data)} bytes from {addr}")
            print(f"Raw data (first 20 bytes): {' '.join(f'{b:02x}' for b in data[:min(20, len(data))])}")
        
        try:
            # リクエストカウントを増加（スレッドセーフ）
            with self.lock:
                self.request_count += 1
            
            # リクエストをパース
            try:
                request, parse_time = self._measure_time(self.parse_request, data)
                timing_info['parse'] = parse_time
                if self.debug:
                    print(f"[Weather Server] Successfully parsed request. Type: {request.type}")
            except Exception as e:
                print(f"[Weather Server] ERROR parsing request: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
                return
            
            # デバッグ出力
            self._debug_print_request(data, request)
            
            # リクエストの妥当性をチェック
            is_valid, error_msg = self.validate_request(request)
            if not is_valid:
                with self.lock:
                    self.error_count += 1
                if self.debug:
                    print(f"[{threading.current_thread().name}] Invalid request from {addr}: {error_msg}")
                return
            
            # パケットタイプによる分岐処理
            if self.debug:
                print(f"[Weather Server] Processing packet type {request.type}")
                
            if request.type == 0:
                # Type 0: 座標解決リクエスト
                self._handle_location_request(request, addr)
            elif request.type == 1:
                # Type 1: 座標解決レスポンス
                self._handle_location_response(data, addr)
            elif request.type == 2:
                # Type 2: 気象データリクエスト
                self._handle_weather_request(request, addr)
            elif request.type == 3:
                # Type 3: 気象データレスポンス
                self._handle_weather_response(data, addr)
            else:
                if self.debug:
                    print(f"Unknown packet type: {request.type}")
                    
            # タイミング情報を出力
            timing_info['total'] = time.time() - start_time
            if self.debug:
                self._print_timing_info(addr, timing_info)
                
        except Exception as e:
            with self.lock:
                self.error_count += 1
            print(f"[{threading.current_thread().name}] Error processing request from {addr}: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    def _handle_location_request(self, request, addr):
        """座標解決リクエストの処理（Type 0）"""
        try:
            # source情報をex_fieldに追加
            source_info = f"{addr[0]}:{addr[1]}"
            if not hasattr(request, 'ex_field') or request.ex_field is None:
                request.ex_field = {}
            request.ex_field['source'] = source_info
            request.ex_flag = 1
            
            if self.debug:
                print(f"\n[Weather Server] Type 0: Forwarding location request to Location Resolver")
                print(f"  Added source: {source_info}")
                print(f"  Target: {self.location_resolver_host}:{self.location_resolver_port}")
                print(f"  ex_field: {request.ex_field}")
            
            # Location Resolverに転送
            packet_data = request.to_bytes()
            if self.debug:
                print(f"  Packet size: {len(packet_data)} bytes")
                
            # メインソケットを使用して送信
            bytes_sent = self.send_udp_packet(packet_data, self.location_resolver_host, self.location_resolver_port)
            
        except Exception as e:
            print(f"[Weather Server] Error handling location request: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    def _handle_location_response(self, data, addr):
        """座標解決レスポンスの処理（Type 1）"""
        try:
            # レスポンスをパース
            response = Response.from_bytes(data)
            
            if self.debug:
                print(f"\n[Weather Server] Type 1: Converting location response to weather request")
                print(f"  Area code: {response.area_code}")
                print(f"  ex_field: {response.ex_field if hasattr(response, 'ex_field') else 'None'}")
            
            # Type 2のリクエストパケットに変換
            request = Request(
                version=response.version,
                packet_id=response.packet_id,
                type=2,  # タイプを2に変更
                weather_flag=response.weather_flag,
                temperature_flag=response.temperature_flag,
                pops_flag=response.pops_flag,
                alert_flag=response.alert_flag,
                disaster_flag=response.disaster_flag,
                ex_flag=1,  # ex_flagを1に設定
                day=response.day,
                timestamp=int(datetime.now().timestamp()),  # タイムスタンプを更新
                area_code=response.area_code,
                ex_field=response.ex_field if hasattr(response, 'ex_field') else {}  # ex_fieldを引き継ぎ
            )
            
            if self.debug:
                print(f"  Target: {self.query_generator_host}:{self.query_generator_port}")
            
            # Query Generatorに送信
            packet_data = request.to_bytes()
            if self.debug:
                print(f"  Packet size: {len(packet_data)} bytes")
                
            # メインソケットを使用して送信
            bytes_sent = self.send_udp_packet(packet_data, self.query_generator_host, self.query_generator_port)
            
        except Exception as e:
            print(f"[Weather Server] Error handling location response: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    def _handle_weather_request(self, request, addr):
        """気象データリクエストの処理（Type 2）"""
        try:
            # source情報をex_fieldに追加
            source_info = f"{addr[0]}:{addr[1]}"
            if not hasattr(request, 'ex_field') or request.ex_field is None:
                request.ex_field = {}
            request.ex_field['source'] = source_info
            request.ex_flag = 1
            
            if self.debug:
                print(f"\n[Weather Server] Type 2: Forwarding weather request to Query Generator")
                print(f"  Added source: {source_info}")
                print(f"  Target: {self.query_generator_host}:{self.query_generator_port}")
                print(f"  Area code: {request.area_code}")
            
            # Query Generatorに転送
            packet_data = request.to_bytes()
            if self.debug:
                print(f"  Packet size: {len(packet_data)} bytes")
                
            # メインソケットを使用して送信
            bytes_sent = self.send_udp_packet(packet_data, self.query_generator_host, self.query_generator_port)
            
        except Exception as e:
            print(f"[Weather Server] Error handling weather request: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    def _handle_weather_response(self, data, addr):
        """気象データレスポンスの処理（Type 3）"""
        try:
            # レスポンスをパース
            response = Response.from_bytes(data)
            
            if self.debug:
                print(f"\n[Weather Server] Type 3: Processing weather response")
                print(f"  ex_field: {response.ex_field if hasattr(response, 'ex_field') else 'None'}")
            
            # ex_field.sourceから送信先を取得
            if hasattr(response, 'ex_field') and response.ex_field and 'source' in response.ex_field:
                source_info = response.ex_field['source']
                host, port = source_info.split(':')
                dest_addr = (host, int(port))
                
                if self.debug:
                    print(f"  Forwarding weather response to {dest_addr}")
                    print(f"  Packet size: {len(data)} bytes")
                
                # 元のクライアントに送信
                bytes_sent = self.sock.sendto(data, dest_addr)
                
                if self.debug:
                    print(f"  Sent {bytes_sent} bytes to client")
            else:
                print("[Weather Server] Error: No source information in weather response")
                if self.debug:
                    print(f"  ex_field content: {response.ex_field if hasattr(response, 'ex_field') else 'No ex_field attribute'}")
                
        except Exception as e:
            print(f"[Weather Server] Error handling weather response: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    def create_response(self, request):
        """
        レスポンスを作成（プロキシサーバーなので基本的に使用しない）
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            レスポンスのバイナリデータ
        """
        # エラーレスポンスなどが必要な場合に実装
        return b''
    
    def parse_request(self, data):
        """
        リクエストデータをパース
        
        Args:
            data: 受信したバイナリデータ
            
        Returns:
            Request or Response: パースされたオブジェクト
        """
        # まずRequestとしてパースを試みる
        try:
            return Request.from_bytes(data)
        except:
            # 失敗したらResponseとしてパース（Type 1, 3の場合）
            return Response.from_bytes(data)
    
    def validate_request(self, request):
        """
        リクエストの妥当性をチェック
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if request.version != self.version:
            return False, "バージョンが不正です"
        
        # タイプのチェック（0-3が有効）
        if request.type not in [0, 1, 2, 3]:
            return False, f"不正なパケットタイプ: {request.type}"
        
        return True, None
    
    def _debug_print_request(self, data, parsed):
        """リクエストのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print("\n=== RECEIVED PACKET ===")
        print(f"Total Length: {len(data)} bytes")
        print("\nHeader:")
        print(f"Version: {parsed.version}")
        print(f"Type: {parsed.type}")
        print(f"Area Code: {parsed.area_code}")
        print(f"Packet ID: {parsed.packet_id}")
        print(f"Timestamp: {time.ctime(parsed.timestamp)}")
        
        if parsed.type in [0, 2]:  # リクエストタイプ
            print("\nFlags:")
            print(f"Weather: {parsed.weather_flag}")
            print(f"Temperature: {parsed.temperature_flag}")
            print(f"PoPs: {parsed.pops_flag}")
            print(f"Alert: {parsed.alert_flag}")
            print(f"Disaster: {parsed.disaster_flag}")
            print(f"Extended Field: {parsed.ex_flag}")
            
        if hasattr(parsed, 'ex_field') and parsed.ex_field:
            print(f"\nExtended Field: {parsed.ex_field}")
            
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("=====================\n")
    
    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理（オーバーライド）"""
        # クライアントのクリーンアップ
        if hasattr(self, 'location_client'):
            self.location_client.close()
        if hasattr(self, 'query_client'):
            self.query_client.close()


if __name__ == "__main__":
    server = WeatherServer(host="0.0.0.0", port=4110, debug=True)
    server.run()
