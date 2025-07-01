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
import traceback

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
from common.packet import ErrorResponse
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
        try:
            self.config = ConfigLoader(config_path)
        except Exception as e:
            error_msg = f"設定ファイルの読み込みに失敗しました: {config_path} - {str(e)}"
            if self.debug:
                traceback.print_exc()
            raise RuntimeError(f"設定ファイル読み込みエラー: {str(e)}")
        
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
        
        # キャッシュストレージの初期化（設定ファイルからTTLを取得）
        self.cache_ttl_weather = self.config.getint('cache', 'expiration_time_weather', 600)
        self.cache_ttl_area = self.config.getint('cache', 'expiration_time_area', 604800)
        self.cache_weather = Cache(default_ttl=timedelta(seconds=self.cache_ttl_weather))
        self.cache_area = Cache(default_ttl=timedelta(seconds=self.cache_ttl_area))
        
        
        # サーバー設定情報のデバッグ出力を削除
        
        # クライアントの初期化（改良版）
        try:
            self.location_client = LocationClient(
                host=self.location_resolver_host,
                port=self.location_resolver_port,
                debug=self.debug
            )
        except Exception as e:
            error_msg = f"ロケーションクライアントの初期化に失敗しました: {self.location_resolver_host}:{self.location_resolver_port} - {str(e)}"
            if self.debug:
                traceback.print_exc()
            raise RuntimeError(f"ロケーションクライアント初期化エラー: {str(e)}")

        try:
            self.query_client = QueryClient(
                host=self.query_generator_host,
                port=self.query_generator_port,
                debug=self.debug
            )
        except Exception as e:
            error_msg = f"クエリクライアントの初期化に失敗しました: {self.query_generator_host}:{self.query_generator_port} - {str(e)}"
            if self.debug:
                traceback.print_exc()
            raise RuntimeError(f"クエリクライアント初期化エラー: {str(e)}")
        
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
                print(f"\n[天気サーバー] {addr} から {len(data)} バイトを受信しました")
                print(f"生データ（最初の20バイト）: {' '.join(f'{b:02x}' for b in data[:min(20, len(data))])}")
        try:
            # リクエストカウントを増加（スレッドセーフ）
            try:
                with self.lock:
                    self.request_count += 1
            except Exception as e:
                error_msg = f"リクエストカウントの更新に失敗しました - {str(e)}"
                if self.debug:
                    traceback.print_exc()
                raise RuntimeError(f"755: レート制限超過: {str(e)}")
            
            # リクエストをパース（専用パケットクラス使用）
            try:
                request, parse_time = self._measure_time(self.parse_request, data)
                timing_info['parse'] = parse_time
                # リクエストパース成功のデバッグ出力を削除
            except Exception as e:
                print(f"530: [天気サーバー] リクエストのパース中にエラーが発生しました: {e}")
                if self.debug:
                    traceback.print_exc()
                # ErrorResponseを作成して返す（パースエラー時はpacket_id=0とする）
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=0,  # パースエラー時はpacket_id=0
                    error_code=530,
                    timestamp=int(datetime.now().timestamp())
                )
                # パースエラー時は送信先が不明なため転送できない
                if self.debug:
                    print(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
                return
            
            # デバッグ出力（改良版）
            self._debug_print_request(data, request)
            
            # リクエストの妥当性をチェック
            is_valid, error_code, error_msg = self.validate_request(request)
            if not is_valid:
                # ErrorResponseを作成して返す
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=request.packet_id,
                    error_code=error_code,
                    timestamp=int(datetime.now().timestamp())
                )
                dest = None
                if (
                    hasattr(request, "ex_field")
                    and request.ex_field
                    and request.ex_field.contains("source")
                ):
                    candidate = request.ex_field.source
                    if isinstance(candidate, tuple) and len(candidate) == 2:
                        dest = candidate

                if dest:
                    error_response.ex_field.source = dest
                    self.sock.sendto(error_response.to_bytes(), dest)
                if self.debug:
                    if dest:
                        print(f"[{threading.current_thread().name}] Error response sent to {dest}")
                    else:
                        print(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
                    print(f"{error_code}: [{threading.current_thread().name}] {addr} からの不正なリクエスト: {error_msg}")
                with self.lock:
                    self.error_count += 1
                return
            
            # パケットタイプによる分岐処理（専用クラス対応）
            # パケットタイプ処理中のデバッグ出力を削除
                
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
                    print(f"405: 不正なパケットタイプ: {request.type}")
                    # ErrorResponseを作成して返す
                    error_response = ErrorResponse(
                        version=self.version,
                        packet_id=request.packet_id,
                        error_code= 405,
                        timestamp=int(datetime.now().timestamp())
                    )
                    dest = None
                    if (
                        hasattr(request, "ex_field")
                        and request.ex_field
                        and request.ex_field.contains('source')
                    ):
                        candidate = request.ex_field.source
                        if isinstance(candidate, tuple) and len(candidate) == 2:
                            dest = candidate

                    if dest:
                        error_response.ex_field.source = dest
                        self.sock.sendto(error_response.to_bytes(), dest)
                        if self.debug:
                            print(f"[{threading.current_thread().name}] Error response sent to {dest}")
                    else:
                        if self.debug:
                            print(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
                    return
                    
            # タイミング情報を出力
            timing_info['total'] = time.time() - start_time
            # タイミング情報のデバッグ出力を削除
                
        except Exception as e:
            with self.lock:
                self.error_count += 1
            print(f"530: [{threading.current_thread().name}] {addr} からのリクエスト処理中にエラーが発生しました: {e}")
            if self.debug:
                traceback.print_exc()
            # ErrorResponseを作成して返す（requestが未定義の場合の処理を追加）
            packet_id = getattr(request, 'packet_id', 0)  # requestが未定義の場合は0
            error_response = ErrorResponse(
                version=self.version,
                packet_id=packet_id,
                error_code=530,
                timestamp=int(datetime.now().timestamp())
            )

            dest = None
            if (
                'request' in locals()
                and hasattr(request, 'ex_field')
                and request.ex_field
                and request.ex_field.contains('source')
            ):
                candidate = request.ex_field.source
                if isinstance(candidate, tuple) and len(candidate) == 2:
                    dest = candidate

            if dest:
                error_response.ex_field.source = dest
                self.sock.sendto(error_response.to_bytes(), dest)
                if self.debug:
                    print(f"[{threading.current_thread().name}] Error response sent to {dest}")
            else:
                if self.debug:
                    print(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
            return
    
    def _handle_location_request(self, request, addr):
        """座標解決リクエストの処理（Type 0・改良版）"""
        source_info = (addr[0], addr[1])  # タプル形式で保持
        try:
            # 気象キャッシュ処理
            lat, long = request.get_coordinates()
            cache_key = f"{lat}_{long}"
            cached_data = self.cache_area.get(cache_key)

            # キャッシュの有効期限チェック
            cache_expiration_for_area = timedelta(seconds=self.cache_ttl_area)

            if cached_data and cached_data.get("area_code") == "000000":
                # 無効なキャッシュは削除
                self.cache_area.delete(cache_key)
                cached_data = None

            area_code_valid = (
                cached_data
                and cached_data.get("area_code")
                and cached_data.get("area_code") != "000000"
            )

            if (
                area_code_valid
                and (datetime.now() - cached_data["timestamp"]) < cache_expiration_for_area
            ):
                print("キャッシュヒット！\nweather_requestを作成します。")
                try:
                    # キャッシュからWeatherRequestを生成 (source_infoがある場合のみsourceを含め、常に座標を含める)
                    ex_field_content = {}
                    if source_info:
                        ex_field_content['source'] = source_info
                    # 座標を拡張フィールドに追加
                    ex_field_content['latitude'] = lat
                    ex_field_content['longitude'] = long
                    ex_flag_val = 1  # 座標を含むので常に1
                    
                    # キャッシュされたエリアコードを使用
                    cached_area_code = cached_data.get("area_code") if isinstance(cached_data, dict) else None
                    weather_request = WeatherRequest(
                        version=self.version,
                        packet_id=request.packet_id,
                        type=2,  # WeatherRequest
                        area_code=cached_area_code if cached_area_code else request.area_code,
                        day=request.day,  # 当日
                        timestamp=int(datetime.now().timestamp()),
                        weather_flag=request.weather_flag,
                        temperature_flag=request.temperature_flag,
                        pop_flag=request.pop_flag,
                        alert_flag=request.alert_flag,
                        disaster_flag=request.disaster_flag,
                        ex_flag=ex_flag_val,
                        ex_field=ex_field_content
                    )
                    
                    # _handle_weather_requestに処理を移譲
                    return self._handle_weather_request(weather_request, addr)
                    
                except Exception as e:
                    print(f"キャッシュデータの処理中にエラーが発生しました: {e}")
                    if self.debug:
                        traceback.print_exc()
                    # エラーが発生した場合はキャッシュを削除して通常処理を続行
                    self.cache_area.delete(cache_key)
            
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
                location_request.ex_field.source = source_info
            
            # LocationRequest変換のデバッグ出力を削除
            
            # Location Resolverに転送
            packet_data = location_request.to_bytes()
            if self.debug:
                print(f"  パケットサイズ: {len(packet_data)} バイト")
                
            # メインソケットを使用して送信
            try:
                bytes_sent = self.send_udp_packet(packet_data, self.location_resolver_host, self.location_resolver_port)
                if bytes_sent != len(packet_data):
                    raise RuntimeError(f"404: 不正なパケット長 (expected: {len(packet_data)}, sent: {bytes_sent})")
            except Exception as e:
                if self.debug:
                    traceback.print_exc()
                # ErrorResponseを作成して返す
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=request.packet_id,
                    error_code= 410,
                    timestamp=int(datetime.now().timestamp())
                )
                dest = None
                if (
                    hasattr(request, 'ex_field')
                    and request.ex_field
                    and request.ex_field.contains('source')
                ):
                    cand = request.ex_field.source
                    if isinstance(cand, tuple) and len(cand) == 2:
                        dest = cand

                if dest:
                    error_response.ex_field.source = dest
                    self.sock.sendto(error_response.to_bytes(), dest)
                    if self.debug:
                        print(f"[{threading.current_thread().name}] Error response sent to {dest}")
                else:
                    if self.debug:
                        print(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
                return
            
        except Exception as e:
            print(f"530: [天気サーバー] 位置情報リクエストの処理中にエラーが発生しました: {e}")
            if self.debug:
                traceback.print_exc()
            # ErrorResponseを作成して返す
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=request.packet_id,
                    error_code= 530,
                    timestamp=int(datetime.now().timestamp())
                )
                dest = None
                if (
                    hasattr(request, 'ex_field')
                    and request.ex_field
                    and request.ex_field.contains('source')
                ):
                    cand = request.ex_field.source
                    if isinstance(cand, tuple) and len(cand) == 2:
                        dest = cand

                if dest:
                    error_response.ex_field.source = dest
                    self.sock.sendto(error_response.to_bytes(), dest)
                    if self.debug:
                        print(f"[{threading.current_thread().name}] Error response sent to {dest}")
                else:
                    if self.debug:
                        print(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
                return
    
    def _validate_cache_data(self, cached_data, flags):
        """キャッシュデータのバリデーションを行う"""
        if not cached_data:
            return False

        if flags.get('weather') and "weather_code" not in cached_data:
            raise ValueError("キャッシュにweather_codeがありません")
        if flags.get('temperature') and "temperature" not in cached_data:
            raise ValueError("キャッシュにtemperatureがありません")
        if flags.get('pop') and "pop" not in cached_data:
            raise ValueError("キャッシュにpopがありません")
        if flags.get('alert') and ("ex_field" not in cached_data or "alert" not in cached_data["ex_field"]):
            raise ValueError("キャッシュにalertデータがありません")
        if flags.get('disaster') and ("ex_field" not in cached_data or "disaster" not in cached_data["ex_field"]):
            return False  # キャッシュ検証失敗
        
        return True

    def _create_response_from_cache(self, cached_data, packet_id, area_code, day, flags, lat=None, long=None):
        """キャッシュデータからWeatherResponseを生成"""

        weather_response = WeatherResponse(
            version=self.version,
            packet_id=packet_id,
            type=3,
            area_code=area_code,
            day=day,
            timestamp=int(datetime.now().timestamp()),
            weather_flag=flags.get('weather', False),
            temperature_flag=flags.get('temperature', False),
            pop_flag=flags.get('pop', False),
            alert_flag=flags.get('alert', False),
            disaster_flag=flags.get('disaster', False),
            ex_flag=0
        )

        if weather_response.weather_flag:
            weather_response.weather_code = cached_data["weather_code"]
        if weather_response.temperature_flag:
            weather_response.temperature = int(cached_data["temperature"]) + 100
        if weather_response.pop_flag:
            weather_response.pop = cached_data["pop"]
        if weather_response.disaster_flag or weather_response.alert_flag:
            weather_response.ex_flag = 1
            # alertとdisasterのデータを分離して設定
            if cached_data.get("ex_field"):
                ex_data = cached_data["ex_field"]
                filtered_ex_field = {}
                if weather_response.alert_flag:
                    alert_val = ex_data.get("alert")
                    if alert_val:
                        filtered_ex_field["alert"] = alert_val
                if weather_response.disaster_flag:
                    disaster_val = ex_data.get("disaster")
                    if disaster_val:
                        filtered_ex_field["disaster"] = disaster_val
                if lat is not None:
                    filtered_ex_field['latitude'] = lat
                if long is not None:
                    filtered_ex_field['longitude'] = long
                weather_response.ex_field = filtered_ex_field

        return weather_response

    def _handle_location_response(self, data, addr):
        """座標解決レスポンスの処理（Type 1・改良版）"""
        try:
            if self.debug:
                print(f"\n[天気サーバー] タイプ1: 位置情報レスポンス処理開始")
                print(f"  受信データサイズ: {len(data)}バイト")
                print(f"  受信アドレス: {addr}")
            
            # 専用クラスでレスポンスをパース
            response = LocationResponse.from_bytes(data)

            lat, long = response.get_coordinates()
            
            # エリアキャッシュ処理
            # キャッシュキーの生成: 緯度_経度
            cache_key = f"{lat}_{long}"
            
            # キャッシュが存在しないか有効期限切れの場合に更新
            # TTLは地域キャッシュ設定(expiration_time_area)を参照
            cached_data = self.cache_area.get(cache_key)
            cache_expiration = timedelta(seconds=self.config.getint('cache', 'expiration_time_area', 604800))
            
            if not cached_data or (datetime.now() - cached_data["timestamp"]) > cache_expiration:
                # キャッシュデータの作成
                cache_data = {
                    "timestamp": datetime.now(),
                    "area_code": response.area_code
                }

                # "000000" は無効とみなし、キャッシュしない
                if response.area_code != "000000":
                    # キャッシュに保存（デフォルトTTLを使用）
                    self.cache_area.set(cache_key, cache_data)

            if self.debug:
                print(f"\n[天気サーバー] タイプ1: 位置情報レスポンスを天気リクエストに変換中")
                print(f"  Area code: {response.get_area_code()}")
                print(f"  Source: {response.get_source_info()}")
                print(f"  Valid: {response.is_valid()}")
                print(f"  パケットID: {response.packet_id}")
                print(f"  バージョン: {response.version}")
                print(f"  タイプ: {response.type}")
                print(f"  タイムスタンプ: {response.timestamp}")
            
            # 気象キャッシュ処理
            cache_key = f"{response.area_code}_{response.day}"
            cached_data = self.cache_weather.get(cache_key)

            if cached_data:
                try:
                    flags = {
                        'weather': response.weather_flag,
                        'temperature': response.temperature_flag,
                        'pop': response.pop_flag,
                        'alert': response.alert_flag,
                        'disaster': response.disaster_flag,
                    }
                    is_valid = self._validate_cache_data(cached_data, flags)
                    if is_valid:
                        weather_response = self._create_response_from_cache(
                            cached_data,
                            response.packet_id,
                            response.area_code,
                            response.day,
                            flags,
                            lat,
                            long
                        )

                        if self.debug:
                            print(f"  WeatherResponse生成完了")
                            print(f"  生成されたオブジェクト: {weather_response}")
                            print(f"  座標情報: {weather_response.get_coordinates()}")
                            if hasattr(weather_response, 'ex_field'):
                                print(f"  ex_field内容: {weather_response.ex_field.to_dict()}")

                        print (weather_response.get_coordinates())
                        # レスポンスを送信
                        response_data = weather_response.to_bytes()
                        source_info = response.get_source_info()

                        if source_info:
                            # source_infoがタプルの場合と文字列の場合を処理
                            if isinstance(source_info, tuple):
                                host, port_str = source_info[0], str(source_info[1])
                            else:
                                host, port_str = source_info.split(':')
                            port = int(port_str)
                            source_addr = (host, port)

                            if self.debug:
                                print(f"  キャッシュレスポンスを送信: {len(response_data)}バイト")
                                print(f"  送信先アドレス: {source_addr}")

                            bytes_sent = self.sock.sendto(response_data, source_addr)
                            if bytes_sent != len(response_data):
                                raise RuntimeError(f"送信バイト数不一致: {bytes_sent}/{len(response_data)}")

                            if self.debug:
                                print(f"  送信成功: {bytes_sent}バイト")
                                print(f"  送信先ソケット: {source_addr}")
                                print(f"  送信データサイズ: {len(response_data)}バイト")
                                print(f"  キャッシュから生成したレスポンスを {addr} へ送信しました")
                                print(f"  レスポンス成功フラグ: True")

                            return  # キャッシュヒット時はここで終了
                        raise RuntimeError("source情報が見つかりません")
                    else:
                        if self.debug:
                            print('  キャッシュデータのバリデーションに失敗しました')
                        self.cache_weather.delete(cache_key)
                        # 以降の処理でキャッシュミスとして扱う
                        
                except Exception as e:
                    if self.debug:
                        print(f'キャッシュデータの処理中にエラーが発生しました: {str(e)}')
                        print('キャッシュデータを削除して新しいリクエストを処理します')
                    self.cache_weather.delete(cache_key)
                    print(f"[WARNING] キャッシュデータが不完全です: {str(e)}")  # loggerが使えない場合の代替
                    # キャッシュが不完全でもクエリサーバーへリクエストを継続
                    return self._send_weather_request(response)

            # 専用クラスの変換メソッドを使用
            weather_request = response.to_weather_request()
            print(f"\n\n=====================これがweather_requestです。===================\n{weather_request}")
            
            if self.debug:
                print(f"  WeatherRequest (タイプ2) に変換しました")
                print(f"  Target: {self.query_generator_host}:{self.query_generator_port}")
            
            # Query Generatorに送信
            packet_data = weather_request.to_bytes()
            # パケットサイズのデバッグ出力を削除
                
            # メインソケットを使用して送信
            bytes_sent = self.send_udp_packet(packet_data, self.query_generator_host, self.query_generator_port)
            if bytes_sent != len(packet_data):
                raise RuntimeError(f"404: 不正なパケット長: (expected: {len(packet_data)}, sent: {bytes_sent})")
            
        except Exception as e:
            print(f"107: [天気サーバー] 位置情報レスポンスの処理中にエラーが発生しました: {e}")
            if self.debug:
                traceback.print_exc()
            source_ip,source_port = data.get_source_info()
            if not source_ip or not source_port:
                print("error")
                return
            # ErrorResponseを作成して返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=response.packet_id,
                error_code=107,
                timestamp=int(datetime.now().timestamp())
            )
            error_response.ex_field.source = (source_ip, source_port)
            self.sock.sendto(error_response.to_bytes(), (source_ip, source_port))
            return
    
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
            
            # キャッシュ処理
            cache_key = f"{request.area_code}_{request.day}"
            cached_data = self.cache_weather.get(cache_key)
            
            if cached_data:
                try:
                    flags = {
                        'weather': request.weather_flag,
                        'temperature': request.temperature_flag,
                        'pop': request.pop_flag,
                        'alert': request.alert_flag,
                        'disaster': request.disaster_flag
                    }
                    
                    if self.debug:
                        print(f"  キャッシュヒット: {cache_key}")
                        print(f"  キャッシュデータをクライアントに返します")
                    
                    is_valid = self._validate_cache_data(cached_data, flags)
                    if is_valid:
                        weather_response = self._create_response_from_cache(
                            cached_data,
                            request.packet_id,
                            request.area_code,
                            request.day,
                            flags
                        )

                        response_data = weather_response.to_bytes()
                        self.sock.sendto(response_data, addr)

                        if self.debug:
                            print(f"  キャッシュから生成したレスポンスを {addr} へ送信しました")
                            print(f"  パケットサイズ: {len(response_data)} バイト")
                            print(f"  レスポンス成功フラグ: True")

                        return  # キャッシュヒット時はここで終了
                    else:
                        if self.debug:
                            print('  キャッシュデータのバリデーションに失敗しました')
                        self.cache_weather.delete(cache_key)
                        # キャッシュミスとして処理継続
                    
                except Exception as e:
                    if self.debug:
                        print(f'キャッシュデータの処理中にエラーが発生しました: {str(e)}')
                        print('キャッシュデータを削除して新しいリクエストを処理します')
                    self.cache_weather.delete(cache_key)
            
            if self.debug:
                if not cached_data:
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
                query_request.ex_field.source = source_info
            
            if self.debug:
                print(f"  QueryRequest に変換しました")
                if hasattr(query_request, 'get_source_info'):
                    print(f"  送信元を追加しました: {query_request.get_source_info()}")
            
            # Query Generatorに転送
            packet_data = query_request.to_bytes()
            # パケットサイズのデバッグ出力を削除
                
            # メインソケットを使用して送信
            try:
                bytes_sent = self.send_udp_packet(packet_data, self.query_generator_host, self.query_generator_port)
                if bytes_sent != len(packet_data):
                    raise RuntimeError(f"404: 不正なパケット長: (expected: {len(packet_data)}, sent: {bytes_sent})")
            except Exception as e:
                error_msg = f"クエリリクエストの転送に失敗しました: {self.query_generator_host}:{self.query_generator_port} - {str(e)}"
                if self.debug:
                    traceback.print_exc()
                # ErrorResponseを作成して返す
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=request.packet_id,
                    error_code= 420,
                    timestamp=int(datetime.now().timestamp())
                )
                dest = None
                if (
                    hasattr(request, 'ex_field')
                    and request.ex_field
                    and request.ex_field.contains('source')
                ):
                    cand = request.ex_field.source
                    if isinstance(cand, tuple) and len(cand) == 2:
                        dest = cand

                if dest:
                    error_response.ex_field.source = dest
                    self.sock.sendto(error_response.to_bytes(), dest)
                    if self.debug:
                        print(f"[{threading.current_thread().name}] Error response sent to {dest}")
                else:
                    if self.debug:
                        print(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
                return
            
        except Exception as e:
            print(f"420: クエリサーバが見つからない: {e}")
            if self.debug:
                traceback.print_exc()
            # ErrorResponseを作成して返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code= 420,
                timestamp=int(datetime.now().timestamp())
            )
            dest = None
            if (
                hasattr(request, 'ex_field')
                and request.ex_field
                and request.ex_field.contains('source')
            ):
                cand = request.ex_field.source
                if isinstance(cand, tuple) and len(cand) == 2:
                    dest = cand

            if dest:
                error_response.ex_field.source = dest
                self.sock.sendto(error_response.to_bytes(), dest)
                if self.debug:
                    print(f"[{threading.current_thread().name}] Error response sent to {dest}")
            else:
                if self.debug:
                    print(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
            return

    def _send_weather_request(self, location_response):
        """LocationResponseからWeatherRequestを生成して処理する補助メソッド"""
        try:
            weather_request = location_response.to_weather_request()
            source = location_response.get_source_info()
            if source is None:
                # source情報が無い場合は空タプルを渡す
                source = ("", 0)
            return self._handle_weather_request(weather_request, source)
        except Exception:
            if self.debug:
                traceback.print_exc()
            raise

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
                cached_data = self.cache_weather.get(cache_key)
                cache_expiration = timedelta(seconds=self.config.getint('cache', 'expiration_time_weather', 1800))
                
                if not cached_data or (datetime.now() - cached_data["timestamp"]) > cache_expiration:
                    # キャッシュデータの作成
                    ex_data = response.ex_field.to_dict() if response.ex_field else {}
                    cache_data = {
                        "timestamp": datetime.now(),
                        "area_code": response.area_code,
                        "weather_code": response.get_weather_code(),
                        "temperature": response.get_temperature_celsius(),
                        "pop": response.get_precipitation(),  # precipitation_prob -> pop に変更
                        "ex_field": {
                            "alert": ex_data.get("alert", ""),
                            "disaster": ex_data.get("disaster", "")
                        }
                    }
                    
                    # キャッシュに保存（デフォルトTTLを使用）
                    try:
                        self.cache_weather.set(cache_key, cache_data)
                    except Exception as e:
                        error_msg = f"キャッシュへのデータ保存に失敗しました: {cache_key} - {str(e)}"
                        if self.debug:
                            traceback.print_exc()
                        raise RuntimeError(error_msg)
                    
                    if self.debug:
                        print(f"  キャッシュを更新しました: {cache_key}")
                        print(f"  キャッシュ内容: {cache_data}")
                        print(f"  キャッシュエントリ数: {self.cache_weather.size()}")
                else:
                    if self.debug:
                        print(f"  キャッシュが既に存在するため更新をスキップ: {cache_key}")
            
            # 専用クラスのメソッドでsource情報を取得
            source_info = response.get_source_info()
            if not source_info:
                print("530: 気象サーバでの処理エラー: 天気レスポンスに送信元情報がありません")
                if self.debug and hasattr(response, 'ex_field'):
                    print(f"  ex_field の内容: {response.ex_field.to_dict()}")
                return

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
                    print(f"  エラーコード: {response.get_weather_code()}")
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
                try:
                    bytes_sent = self.sock.sendto(final_data, dest_addr)
                    if bytes_sent != len(final_data):
                        raise RuntimeError(f"パケット長エラー: (expected: {len(final_data)}, sent: {bytes_sent})")
                except Exception as e:
                    if self.debug:
                        traceback.print_exc()
                    # ErrorResponseを作成して返す
                    error_response = ErrorResponse(
                        version=self.version,
                        packet_id=response.packet_id,
                        error_code= 530,
                        timestamp=int(datetime.now().timestamp())
                    )
                    self.sock.sendto(error_response.to_bytes(), dest_addr)
                    raise RuntimeError(f"気象サーバでの処理エラー: クライアントへの転送に失敗 {str(e)}")
                
                if self.debug:
                    print(f"  クライアントに {bytes_sent} バイトを送信しました")
                    print (final_data)
            except Exception as conv_e:
                print(f"530: 気象サーバでの処理エラー: {conv_e}")
                if self.debug:
                    traceback.print_exc()
                # ErrorResponseを作成して返す
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=response.packet_id,
                    error_code= 530,
                    timestamp=int(datetime.now().timestamp())
                )
                error_response.ex_field.source = dest_addr
                self.sock.sendto(error_response.to_bytes(), dest_addr)
                return
                
        except Exception as e:
            print(f"530: [天気サーバー] 基本エラー: リクエスト処理失敗: {e}")
            if self.debug:
                traceback.print_exc()
            # ErrorResponseを作成して返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=response.packet_id,
                error_code= 530,
                timestamp=int(datetime.now().timestamp())
            )
            self.sock.sendto(error_response.to_bytes(), dest_addr)
            return

    def _handle_error_packet(self, request, addr):
        """エラーパケットの処理（Type 7）"""
        try:
            if self.debug:
                print(f"\n[天気サーバー] タイプ7: エラーパケットを処理中")
                print(f"  エラーコード: {request.error_code}")
                print(f"  送信元アドレス: {addr}")
            
            # 拡張フィールドからsourceを取得
            if request.ex_field and request.ex_field.contains('source'):
                source = request.ex_field.source
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
                        if self.debug:
                            print(f"  エラーパケットを {source} に送信しました")
                    except (ValueError, TypeError) as e:
                        print(f"[天気サーバー] 不正なポート番号: {port}")
                else:
                    print(f"[天気サーバー] 不正なsource形式: {source}")
            else:
                print(f"[天気サーバー] エラー: エラーパケットにsourceが含まれていません")
                if self.debug:
                    print(f"  拡張フィールド: {request.ex_field.to_dict() if request.ex_field else 'なし'}")
                    
        except Exception as e:
            print(f"[天気サーバー] エラーパケット処理中にエラーが発生しました: {e}")
            if self.debug:
                traceback.print_exc()
            # ErrorResponseを作成して返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code= 530,
                timestamp=int(datetime.now().timestamp())
            )
            dest = None
            if (
                hasattr(request, 'ex_field')
                and request.ex_field
                and request.ex_field.contains('source')
            ):
                cand = request.ex_field.source
                if isinstance(cand, tuple) and len(cand) == 2:
                    dest = cand

            if dest:
                error_response.ex_field.source = dest
                self.sock.sendto(error_response.to_bytes(), dest)
                if self.debug:
                    print(f"[{threading.current_thread().name}] Error response sent to {dest}")
            else:
                if self.debug:
                    print(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
            return
    
    
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
            print("1")
            return False, "403", f"バージョンが不正です (expected: {self.version}, got: {request.version})"
        
        # タイプのチェック（0-3,7が有効）
        if request.type not in [0, 1, 2, 3, 7]:
            print(f"2: {request.type}")
            return False, "400", f"不正なパケットタイプ: {request.type}"

        # エリアコードのチェック (タイプ0と7は除外)
        if request.type not in [0, 7] and (not request.area_code or request.area_code == "000000"):
            print("3")
            return False, "402", "エリアコードが未設定"

        # 専用クラスのバリデーションメソッドを使用
        if hasattr(request, 'is_valid') and callable(getattr(request, 'is_valid')):
            print("4")
            if not request.is_valid():
                print("5")
                return False, "400", "専用クラスのバリデーションに失敗"
        
        return True, None, None
    
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
