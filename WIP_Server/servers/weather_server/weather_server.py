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
from common.utils.cache import Cache
from datetime import timedelta


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
        
        # プロトコルバージョンを設定から取得（4ビット値に制限）
        version = self.config.getint('system', 'protocol_version', 1)
        self.version = version & 0x0F  # 4ビットにマスク
        
        # 他のサーバーへの接続設定を読み込む
        self.location_resolver_host = self.config.get('connections', 'location_server_host', 'localhost')
        self.location_resolver_port = self.config.getint('connections', 'location_server_port', 4109)
        self.query_generator_host = self.config.get('connections', 'query_server_host', 'localhost')
        self.query_generator_port = self.config.getint('connections', 'query_server_port', 4111)
        
        # ネットワーク設定
        self.udp_buffer_size = self.config.getint('network', 'udp_buffer_size', 4096)
        
        # キャッシュストレージの初期化（30分TTL付き）
        self.cache_ttl = self.config.getint('cache', 'expiration_time', 600)
        self.cache = Cache(default_ttl=self.cache_ttl)
        
        
        if self.debug:
            print(f"\n[天気サーバー] 設定:")
            print(f"  Server: {host}:{port}")
            print(f"  Location Resolver: {self.location_resolver_host}:{self.location_resolver_port}")
            print(f"  Query Generator: {self.query_generator_host}:{self.query_generator_port}")
            print(f"  Protocol Version: {self.version}")
            print(f"  専用パケットクラスを使用して処理を改善しています")
            print(f"  キャッシュ機能が有効化されました")
        
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
            elif request.type == 7:  # エラーパケット処理を追加
                self._handle_error_packet(request, addr)
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
            source_info = (addr[0], addr[1])  # タプル形式で保持
            
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
            source_info = (addr[0], addr[1])  # タプル形式で保持
            
            if self.debug:
                print(f"\n[天気サーバー] タイプ2: 天気リクエストを処理中")
                print(f"  Source: {source_info}")
                print(f"  Target: {self.query_generator_host}:{self.query_generator_port}")
                print(f"  Area code: {request.area_code}")
                if hasattr(request, 'get_requested_data_types'):
                    data_types = request.get_requested_data_types()
                    print(f"  Requested data: {data_types}")
            
            # キャッシュキーの生成: 地域コード + リクエストの日付
            cache_key = f"{request.area_code}_{request.day}"
            
            # キャッシュチェック
            cached_data = self.cache.get(cache_key)
            if cached_data:
                # キャッシュの有効期限を確認
                cache_expiration = timedelta(seconds=self.cache_ttl)
                cache_age = datetime.now() - cached_data["timestamp"]
                
                if cache_age > cache_expiration:
                    if self.debug:
                        print(f"  キャッシュ有効期限切れ: {cache_key} (age: {cache_age}, expiration: {cache_expiration})")
                    # 古いキャッシュを削除
                    self.cache.delete(cache_key)
                    cached_data = None
                else:
                    try:
                        if self.debug:
                            print(f"  キャッシュヒット: {cache_key}")
                            print(f"  キャッシュデータをクライアントに返します")

                        weather_response = WeatherResponse(
                            version=self.version,  # 正規化されたバージョン
                            packet_id=request.packet_id,
                            type = 3,
                            area_code=cached_data["area_code"],
                            day=request.day,
                            timestamp=int(datetime.now().timestamp()),
                            weather_flag=request.weather_flag,
                            temperature_flag=request.temperature_flag,
                            pop_flag=request.pop_flag,
                            alert_flag=request.alert_flag,
                            disaster_flag=request.disaster_flag,
                            ex_flag=0
                        )

                        if weather_response.weather_flag:
                            weather_response.weather_code=cached_data["weather_code"]
                        if weather_response.temperature_flag:
                            weather_response.temperature=int(cached_data["temperature"])+100
                        if weather_response.pop_flag:
                            weather_response.pop=cached_data["pop"]
                        if weather_response.disaster_flag or weather_response.alert_flag:
                            weather_response.ex_flag =1
                            weather_response.ex_field=cached_data.get("ex_field")
                        
                        # レスポンスを送信
                        response_data = weather_response.to_bytes()
                        self.sock.sendto(response_data, addr)
                        
                        if self.debug:
                            print(f"  キャッシュから生成したレスポンスを {addr} へ送信しました")
                            print(f"  パケットサイズ: {len(response_data)} バイト")
                            print(f"  レスポンス成功フラグ: True")
                        
                        return  # キャッシュヒット時はここで終了
                    except:
                        weather_response = None
                        if self.debug:
                            print('キャッシュには要求されたデータが存在しませんでした')
            
            if self.debug:
                print(f"  キャッシュミス: {cache_key}")
                print(f"  バックエンドサーバーにリクエストを転送します")
            
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
            
            # 成功レスポンスでキャッシュミスの場合のみキャッシュに保存
            if response.is_success():
                # キャッシュキーの生成: 地域コード + 日付
                cache_key = f"{response.area_code}_{response.day}"
                
                # キャッシュが存在しないか有効期限切れの場合に更新
                cached_data = self.cache.get(cache_key)
                cache_expiration = timedelta(seconds=self.config.getint('cache', 'expiration_time', 1800))
                
                if not cached_data or (datetime.now() - cached_data["timestamp"]) > cache_expiration:
                    # キャッシュデータの作成
                    cache_data = {
                        "timestamp": datetime.now(),
                        "area_code": response.area_code,
                        "weather_code": response.get_weather_code(),
                        "temperature": response.get_temperature_celsius(),
                        "pop": response.get_precipitation(),  # precipitation_prob -> pop に変更
                        "ex_field": response.ex_field.to_dict()  # 元のex_fieldデータ
                    }
                    
                    # キャッシュに保存（TTLはデフォルトの30分）
                    self.cache.set(cache_key, cache_data, timedelta(seconds=self.cache_ttl))
                    
                    if self.debug:
                        print(f"  キャッシュを更新しました: {cache_key}")
                        print(f"  キャッシュ内容: {cache_data}")
                        print(f"  キャッシュエントリ数: {self.cache.size()}")
                else:
                    if self.debug:
                        print(f"  キャッシュが既に存在するため更新をスキップ: {cache_key}")
            
            # 専用クラスのメソッドでsource情報を取得
            source_info = response.get_source_info()
            if source_info:
                # 既にタプル形式なのでそのまま使用
                if isinstance(source_info, tuple) and len(source_info) == 2:
                    host, port = source_info
                    try:
                        port = int(port)  # ポート番号のバリデーション
                        if not (0 < port <= 65535):
                            raise ValueError("Invalid port number")
                        dest_addr = (host, port)
                    except (ValueError, TypeError) as e:
                        print(f"[天気サーバー] 不正なポート番号: {port}")
                        return
                else:
                    print(f"[天気サーバー] 不正なsource_info形式: {source_info}")
                    return
                
                if self.debug:
                    status = "成功" if response.is_success() else "失敗"
                    print(f"  {dest_addr} へ天気レスポンス({status})を転送中")
                    if response.is_success():
                        print(f"  Weather data: {response.get_weather_data()}")
                    else:
                        print(f"  エラーコード: {response.get_error_code()}")
                    print(f"  パケットサイズ: {len(data)} バイト")
                    print(f"  送信元情報: {source_info}")
                
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
                
                try:
                    # WeatherResponseに変換（バージョンを現在のサーバーバージョンで設定）
                    weather_response = WeatherResponse.from_query_response(response)
                    weather_response.version = self.version  # バージョンを正規化
                    final_data = weather_response.to_bytes()
                    
                    # 元のクライアントに送信
                    bytes_sent = self.sock.sendto(final_data, dest_addr)
                    
                    if self.debug:
                        print(f"  クライアントに {bytes_sent} バイトを送信しました")
                except Exception as conv_e:
                    print(f"[天気サーバー] レスポンス変換エラー: {conv_e}")
                    if self.debug:
                        import traceback
                        traceback.print_exc()
            else:
                print("[天気サーバー] エラー: 天気レスポンスに送信元情報がありません")
                if self.debug and hasattr(response, 'ex_field'):
                    print(f"  ex_field の内容: {response.ex_field.to_dict()}")
                
        except Exception as e:
            print(f"[天気サーバー] 天気レスポンスの処理中にエラーが発生しました: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
    def _handle_error_packet(self, request, addr):
        """エラーパケットの処理（Type 7）"""
        try:
            if self.debug:
                print(f"\n[天気サーバー] タイプ7: エラーパケットを処理中")
                print(f"  エラーコード: {request.error_code}")
                print(f"  送信元アドレス: {addr}")
            
            # 拡張フィールドからsourceを取得
            if request.ex_field and 'source' in request.ex_field:
                source = request.ex_field['source']
                if self.debug:
                    print(f"  ソースを取得: {source}")
                
                # エラーパケットを送信
                if isinstance(source, tuple) and len(source) == 2:
                    host, port = source
                    try:
                        port = int(port)  # ポート番号のバリデーション
                        if not (0 < port <= 65535):
                            raise ValueError("Invalid port number")
                        self.sock.sendto(request.to_bytes(), (host, port))
                    except (ValueError, TypeError) as e:
                        print(f"[天気サーバー] 不正なポート番号: {port}")
                else:
                    print(f"[天気サーバー] 不正なsource形式: {source}")
                
                if self.debug:
                    print(f"  エラーパケットを {source} に送信しました")
            else:
                print(f"[天気サーバー] エラー: エラーパケットにsourceが含まれていません")
                if self.debug:
                    print(f"  拡張フィールド: {request.ex_field.to_dict() if request.ex_field else 'なし'}")
                    
        except Exception as e:
            print(f"[天気サーバー] エラーパケット処理中にエラーが発生しました: {e}")
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
        elif packet_type == 7:  # エラーパケット
            from common.packet.error_response import ErrorResponse
            return ErrorResponse.from_bytes(data)
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
        if request.type != 0 and (not request.area_code or request.area_code == "000000"): 
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
