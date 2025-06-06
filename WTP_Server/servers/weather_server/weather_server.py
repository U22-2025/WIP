"""
天気サーバー - プロキシサーバー実装（改良版：専用パケットクラス使用）
他のサーバーへリクエストを転送し、レスポンスを返す
"""

import time
import sys
import os
import threading
from datetime import datetime
from pathlib import Path

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    # 共通ライブラリのパスも追加
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


# モジュールとして使用される場合
from ..base_server import BaseServer
from common.packet import (
    WeatherRequest, WeatherResponse, 
    LocationRequest, LocationResponse,
    QueryRequest, QueryResponse,
    BitFieldError
)
from common.clients.location_client import LocationClient
from common.clients.query_client import QueryClient
from common.utils.config_loader import ConfigLoader


class WeatherServer(BaseServer):
    """天気サーバーのメインクラス（プロキシサーバー・専用パケットクラス使用）"""
    
    def __init__(self, host=None, port=None, debug=None, max_workers=None):
        """
        初期化
        
        Args:
            host: サーバーホスト（Noneの場合は設定ファイルから取得）
            port: サーバーポート（Noneの場合は設定ファイルから取得）
            debug: デバッグモードフラグ（Noneの場合は設定ファイルから取得）
            max_workers: スレッドプールのワーカー数（Noneの場合は設定ファイルから取得）
        """
        # 設定ファイルを読み込む
        config_path = Path(__file__).parent / 'config.ini'
        self.config = ConfigLoader(config_path)
        
        # サーバー設定を取得（引数優先、なければ設定ファイル、なければデフォルト）
        if host is None:
            host = self.config.get('server', 'host', '0.0.0.0')
        if port is None:
            port = self.config.getint('server', 'port', 4110)
        if debug is None:
            debug_str = self.config.get('server', 'debug', 'false')
            debug = debug_str.lower() == 'true'
        if max_workers is None:
            max_workers = self.config.getint('server', 'max_workers', None)
        
        # 基底クラスの初期化
        super().__init__(host, port, debug, max_workers)
        
        # サーバー名を設定
        self.server_name = "WeatherServer (Enhanced)"
        
        # プロトコルバージョンを設定から取得
        self.version = self.config.getint('system', 'protocol_version', 1)
        
        # 他のサーバーへの接続設定を読み込む
        self.location_resolver_host = self.config.get('connections', 'location_server_host', 'localhost')
        self.location_resolver_port = self.config.getint('connections', 'location_server_port', 4109)
        self.query_generator_host = self.config.get('connections', 'query_server_host', 'localhost')
        self.query_generator_port = self.config.getint('connections', 'query_server_port', 4111)
        
        # ネットワーク設定
        self.udp_buffer_size = self.config.getint('network', 'udp_buffer_size', 4096)
        
        if self.debug:
            print(f"\n[天気サーバー] 設定:")
            print(f"  Server: {host}:{port}")
            print(f"  Location Resolver: {self.location_resolver_host}:{self.location_resolver_port}")
            print(f"  Query Generator: {self.query_generator_host}:{self.query_generator_port}")
            print(f"  Protocol Version: {self.version}")
            print(f"  専用パケットクラスを使用して処理を改善しています")
        
        # クライアントの初期化（改良版）
        self.location_client = LocationClient(
            host=self.location_resolver_host,
            port=self.location_resolver_port,
            debug=self.debug
        )
        self.query_client = QueryClient(
            host=self.query_generator_host,
            port=self.query_generator_port,
            debug=self.debug
        )
        
    def handle_request(self, data, addr):
        """
        リクエストを処理（プロキシとして転送・改良版）
        
        Args:
            data: 受信したバイナリデータ
            addr: 送信元アドレス
        """
        timing_info = {}
        start_time = time.time()
        
        if self.debug:
            print(f"\n[天気サーバー] {addr} から {len(data)} バイトを受信しました")
            print(f"生データ（最初の20バイト）: {' '.join(f'{b:02x}' for b in data[:min(20, len(data))])}")
        
        try:
            # リクエストカウントを増加（スレッドセーフ）
            with self.lock:
                self.request_count += 1
            
            # リクエストをパース（専用パケットクラス使用）
            try:
                request, parse_time = self._measure_time(self.parse_request, data)
                timing_info['parse'] = parse_time
                if self.debug:
                    print(f"[天気サーバー] リクエストのパースに成功しました。タイプ: {request.type}")
                    if hasattr(request, 'get_request_summary'):
                        summary = request.get_request_summary()
                        print(f"[天気サーバー] リクエスト概要: {summary}")
            except Exception as e:
                print(f"[天気サーバー] リクエストのパース中にエラーが発生しました: {e}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
                return
            
            # デバッグ出力（改良版）
            self._debug_print_request(data, request)
            
            # リクエストの妥当性をチェック
            is_valid, error_msg = self.validate_request(request)
            if not is_valid:
                # type0でclientに返す
                self._handle_bad_response(request, addr)
                with self.lock:
                    self.error_count += 1
                if self.debug:
                    print(f"[{threading.current_thread().name}] {addr} からの不正なリクエスト: {error_msg}")
                return
            
            # パケットタイプによる分岐処理（専用クラス対応）
            if self.debug:
                print(f"[天気サーバー] パケットタイプ {request.type} を処理中")
                
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
                    print(f"不明なパケットタイプ: {request.type}")
                    
            # タイミング情報を出力
            timing_info['total'] = time.time() - start_time
            if self.debug:
                self._print_timing_info(addr, timing_info)
                
        except Exception as e:
            with self.lock:
                self.error_count += 1
            print(f"[{threading.current_thread().name}] {addr} からのリクエスト処理中にエラーが発生しました: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    def _handle_location_request(self, request, addr):
        """座標解決リクエストの処理（Type 0・改良版）"""
        try:
            source_info = f"{addr[0]}:{addr[1]}"
            
            if self.debug:
                print(f"\n[天気サーバー] タイプ0: 位置情報リクエストを処理中")
                print(f"  Source: {source_info}")
                print(f"  Target: {self.location_resolver_host}:{self.location_resolver_port}")
                if hasattr(request, 'get_coordinates'):
                    coords = request.get_coordinates()
                    print(f"  Coordinates: {coords}")
            
            # 専用クラスを使用してLocationRequestに変換
            if isinstance(request, WeatherRequest):
                # WeatherRequestからLocationRequestに変換
                location_request = LocationRequest.from_weather_request(
                    request, 
                    source=source_info
                )
            else:
                # 既にLocationRequestの場合は、source情報を追加
                location_request = request
                location_request.ex_field.set('source', source_info)
            
            if self.debug:
                print(f"  LocationRequest に変換しました")
                if hasattr(location_request, 'get_source_info'):
                    print(f"  送信元を追加しました: {location_request.get_source_info()}")
            
            # Location Resolverに転送
            packet_data = location_request.to_bytes()
            if self.debug:
                print(f"  パケットサイズ: {len(packet_data)} バイト")
                
            # メインソケットを使用して送信
            bytes_sent = self.send_udp_packet(packet_data, self.location_resolver_host, self.location_resolver_port)
            
        except Exception as e:
            print(f"[天気サーバー] 位置情報リクエストの処理中にエラーが発生しました: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    def _handle_location_response(self, data, addr):
        """座標解決レスポンスの処理（Type 1・改良版）"""
        try:
            # 専用クラスでレスポンスをパース
            response = LocationResponse.from_bytes(data)
            
            if self.debug:
                print(f"\n[天気サーバー] タイプ1: 位置情報レスポンスを天気リクエストに変換中")
                print(f"  Area code: {response.get_area_code()}")
                print(f"  Source: {response.get_source_info()}")
                print(f"  Valid: {response.is_valid()}")
            
            # 専用クラスの変換メソッドを使用
            weather_request = response.to_weather_request()
            
            if self.debug:
                print(f"  WeatherRequest (タイプ2) に変換しました")
                print(f"  Target: {self.query_generator_host}:{self.query_generator_port}")
            
            # Query Generatorに送信
            packet_data = weather_request.to_bytes()
            if self.debug:
                print(f"  パケットサイズ: {len(packet_data)} バイト")
                
            # メインソケットを使用して送信
            bytes_sent = self.send_udp_packet(packet_data, self.query_generator_host, self.query_generator_port)
            
        except Exception as e:
            print(f"[天気サーバー] 位置情報レスポンスの処理中にエラーが発生しました: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    def _handle_weather_request(self, request, addr):
        """気象データリクエストの処理（Type 2・改良版）"""
        try:
            source_info = f"{addr[0]}:{addr[1]}"
            
            if self.debug:
                print(f"\n[天気サーバー] タイプ2: 天気リクエストを処理中")
                print(f"  Source: {source_info}")
                print(f"  Target: {self.query_generator_host}:{self.query_generator_port}")
                print(f"  Area code: {request.area_code}")
                if hasattr(request, 'get_requested_data_types'):
                    data_types = request.get_requested_data_types()
                    print(f"  Requested data: {data_types}")
            
            # 専用クラスを使用してQueryRequestに変換
            if isinstance(request, WeatherRequest):
                # WeatherRequestからQueryRequestに変換
                query_request = QueryRequest.from_weather_request(
                    request,
                    source=source_info
                )
            else:
                # 既にQueryRequestの場合は、source情報を追加
                query_request = request
                query_request.ex_field.set('source', source_info)
            
            if self.debug:
                print(f"  QueryRequest に変換しました")
                if hasattr(query_request, 'get_source_info'):
                    print(f"  送信元を追加しました: {query_request.get_source_info()}")
            
            # Query Generatorに転送
            packet_data = query_request.to_bytes()
            if self.debug:
                print(f"  パケットサイズ: {len(packet_data)} バイト")
                
            # メインソケットを使用して送信
            bytes_sent = self.send_udp_packet(packet_data, self.query_generator_host, self.query_generator_port)
            
        except Exception as e:
            print(f"[天気サーバー] 天気リクエストの処理中にエラーが発生しました: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    
    def _handle_weather_response(self, data, addr):
        """気象データレスポンスの処理（Type 3・改良版）"""
        try:
            # 専用クラスでレスポンスをパース
            response = QueryResponse.from_bytes(data)
            
            if self.debug:
                print(f"\n[天気サーバー] タイプ3: 天気レスポンスを処理中")
                print(f"  Success: {response.is_success()}")
                if hasattr(response, 'get_response_summary'):
                    summary = response.get_response_summary()
                    print(f"  Summary: {summary}")
            
            # 専用クラスのメソッドでsource情報を取得
            source_info = response.get_source_info()
            if source_info:
                host, port = source_info.split(':')
                dest_addr = (host, int(port))
                
                if self.debug:
                    print(f"  {dest_addr} へ天気レスポンスを転送中")
                    print(f"  Weather data: {response.get_weather_data()}")
                    print(f"  パケットサイズ: {len(data)} バイト")
                    print(f"  送信元情報が保存されました: {source_info}")
                
                # source情報を変数に格納したので拡張フィールドから削除
                if hasattr(response, 'ex_field') and response.ex_field:
                    if self.debug:
                        print(f"  拡張フィールドから送信元を削除中")
                        print(f"  拡張フィールド（変更前）: {response.ex_field.to_dict()}")
                    
                    # sourceフィールドを削除
                    response.ex_field.remove('source')
                    
                    # 拡張フィールドが空になった場合はフラグを0にする
                    if response.ex_field.is_empty():
                        if self.debug:
                            print(f"  拡張フィールドが空になりました。フラグを0に設定します")
                        response.ex_field.flag = 0
                    
                    if self.debug:
                        print(f"  拡張フィールド（変更後）: {response.ex_field.to_dict()}")
                        print(f"  拡張フィールドフラグ: {response.ex_field.flag}")
                
                # WeatherResponseに変換
                weather_response = WeatherResponse.from_query_response(response)
                final_data = weather_response.to_bytes()
                
                # 元のクライアントに送信
                bytes_sent = self.sock.sendto(final_data, dest_addr)
                
                if self.debug:
                    print(f"  クライアントに {bytes_sent} バイトを送信しました")
            else:
                print("[天気サーバー] エラー: 天気レスポンスに送信元情報がありません")
                if self.debug and hasattr(response, 'ex_field'):
                    print(f"  ex_field の内容: {response.ex_field.to_dict()}")
                
        except Exception as e:
            print(f"[天気サーバー] 天気レスポンスの処理中にエラーが発生しました: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    def _handle_bad_response(self, data, addr,):
        """エラーレスポンスの処理（Type ？）"""
        return
        # try:
        #     # 専用クラスでレスポンスをパース
        #     response = QueryResponse.from_bytes(data)
            
        #     if self.debug:
        #         print(f"\n[Weather Server Enhanced] Type 3: Processing weather response")
        #         print(f"  Success: {response.is_success()}")
        #         if hasattr(response, 'get_response_summary'):
        #             summary = response.get_response_summary()
        #             print(f"  Summary: {summary}")
            
        #     # 専用クラスのメソッドでsource情報を取得
        #     source_info = response.get_source_info()
        #     if source_info:
        #         host, port = source_info.split(':')
        #         dest_addr = (host, int(port))
                
        #         if self.debug:
        #             print(f"  Forwarding weather response to {dest_addr}")
        #             print(f"  Weather data: {response.get_weather_data()}")
        #             print(f"  Packet size: {len(data)} bytes")
        #             print(f"  Source info stored: {source_info}")
                
        #         # source情報を変数に格納したので拡張フィールドから削除
        #         if hasattr(response, 'ex_field') and response.ex_field:
        #             if self.debug:
        #                 print(f"  Removing source from extended field")
        #                 print(f"  Extended field before: {response.ex_field.to_dict()}")
                    
        #             # sourceフィールドを削除
        #             response.ex_field.remove('source')
                    
        #             # 拡張フィールドが空になった場合はフラグを0にする
        #             if response.ex_field.is_empty():
        #                 if self.debug:
        #                     print(f"  Extended field is now empty, setting flag to 0")
        #                 response.ex_field.flag = 0
                    
        #             if self.debug:
        #                 print(f"  Extended field after: {response.ex_field.to_dict()}")
        #                 print(f"  Extended field flag: {response.ex_field.flag}")
                
        #         # WeatherResponseに変換
        #         weather_response = WeatherResponse.from_query_response(response)
        #         final_data = weather_response.to_bytes()
                
        #         # 元のクライアントに送信
        #         bytes_sent = self.sock.sendto(final_data, dest_addr)
                
        #         if self.debug:
        #             print(f"  Sent {bytes_sent} bytes to client")
        #     else:
        #         print("[Weather Server Enhanced] Error: No source information in weather response")
        #         if self.debug and hasattr(response, 'ex_field'):
        #             print(f"  ex_field content: {response.ex_field.to_dict()}")
                
        # except Exception as e:
        #     print(f"[Weather Server Enhanced] Error handling weather response: {e}")
        #     if self.debug:
        #         import traceback
        #         traceback.print_exc()
    
    
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
        リクエストデータをパース（専用パケットクラス使用）
        
        Args:
            data: 受信したバイナリデータ
            
        Returns:
            専用パケットクラスのインスタンス
        """
        # まず基本的なパケットを解析してタイプを確認
        from common.packet import Request
        temp_request = Request.from_bytes(data)
        packet_type = temp_request.type
        
        # タイプに応じて適切な専用クラスでパース
        if packet_type == 0:
            # 座標解決リクエスト
            return WeatherRequest.from_bytes(data)
        elif packet_type == 1:
            # 座標解決レスポンス
            return LocationResponse.from_bytes(data)
        elif packet_type == 2:
            # 気象データリクエスト
            return WeatherRequest.from_bytes(data)
        elif packet_type == 3:
            # 気象データレスポンス
            return QueryResponse.from_bytes(data)
        else:
            # 不明なタイプの場合は基本クラスを返す
            return temp_request
    
    def validate_request(self, request):
        """
        リクエストの妥当性をチェック（改良版）
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if request.version != self.version:
            return False, f"バージョンが不正です (expected: {self.version}, got: {request.version})"
        
        # タイプのチェック（0-3が有効）
        if request.type not in [0, 1, 2, 3]:
            return False, f"不正なパケットタイプ: {request.type}"
        
        # エリアコードのチェック
        if not request.area_code or request.area_code == "000000": 
            return False, "エリアコードが未設定"

        # 専用クラスのバリデーションメソッドを使用
        if hasattr(request, 'is_valid') and callable(getattr(request, 'is_valid')):
            if not request.is_valid():
                return False, "専用クラスのバリデーションに失敗"
        
        return True, None
    
    def _debug_print_request(self, data, parsed):
        """リクエストのデバッグ情報を出力（改良版・専用クラス対応）"""
        if not self.debug:
            return
            
        print("\n=== 受信パケット (拡張版) ===")
        print(f"Total Length: {len(data)} bytes")
        print(f"Packet Class: {type(parsed).__name__}")
        
        # 専用クラスのサマリー情報を使用
        if hasattr(parsed, 'get_request_summary'):
            summary = parsed.get_request_summary()
            print(f"Request Summary: {summary}")
        elif hasattr(parsed, 'get_response_summary'):
            summary = parsed.get_response_summary()
            print(f"Response Summary: {summary}")
        
        print("\nHeader:")
        print(f"Version: {parsed.version}")
        print(f"Type: {parsed.type}")
        print(f"Area Code: {parsed.area_code}")
        print(f"Packet ID: {parsed.packet_id}")
        print(f"Timestamp: {time.ctime(parsed.timestamp)}")
        
        # 専用クラスのメソッドを使用
        if hasattr(parsed, 'get_coordinates'):
            coords = parsed.get_coordinates()
            if coords:
                print(f"Coordinates: {coords}")
                
        if hasattr(parsed, 'get_source_info'):
            source = parsed.get_source_info()
            if source:
                print(f"Source: {source}")
                
        if hasattr(parsed, 'get_requested_data_types'):
            data_types = parsed.get_requested_data_types()
            if data_types:
                print(f"Requested Data: {data_types}")
                
        if hasattr(parsed, 'get_weather_data'):
            weather_data = parsed.get_weather_data()
            if weather_data:
                print(f"Weather Data: {weather_data}")
            
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("===========================\n")
    
    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理（オーバーライド）"""
        # クライアントのクリーンアップ
        if hasattr(self, 'location_client'):
            self.location_client.close()
        if hasattr(self, 'query_client'):
            self.query_client.close()


if __name__ == "__main__":
    # 設定ファイルから読み込んで起動
    server = WeatherServer()
    server.run()
