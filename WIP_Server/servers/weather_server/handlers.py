"""Weather server request handler mixin."""

import time
import threading
import traceback
from datetime import datetime

from common.packet import (
    LocationRequest, LocationResponse,
    QueryRequest, QueryResponse,
    ReportRequest, ReportResponse,
    ErrorResponse, ExtendedField,
)


class WeatherRequestHandlers:
    """Mixin providing handler implementations for WeatherServer."""
    def _handle_location_request(self, request, addr):
        """座標解決リクエストの処理（Type 0・改良版）"""
        source_info = (addr[0], addr[1])  # タプル形式で保持
        try:
            # location_clientのキャッシュを使用してエリアコード取得を試行（ネットワークリクエストなし）
            coords = request.get_coordinates() if hasattr(request, 'get_coordinates') and callable(request.get_coordinates) else None
            if coords:
                lat, long = coords
                if self.debug:
                    print(f"[{self.server_name}] 座標取得成功: {lat}, {long}")
                    print(f"[{self.server_name}] location_clientのキャッシュを確認中...")
                
                # キャッシュのみをチェック（ネットワークリクエストは送信しない）
                cached_area_code = self.location_client.get_cached_area_code(lat, long)
                
                if cached_area_code:
                    if self.debug:
                        print(f"[{self.server_name}] エリアキャッシュヒット: {cached_area_code}")
                        print(f"[{self.server_name}] weather_requestを作成します")
                    
                    try:
                        weather_request = QueryRequest.create_query_request(
                            area_code=cached_area_code,
                            packet_id=request.packet_id,
                            day=request.day,
                            weather=bool(request.weather_flag),
                            temperature=bool(request.temperature_flag),
                            precipitation_prob=bool(request.pop_flag),
                            alert=bool(request.alert_flag),
                            disaster=bool(request.disaster_flag),
                            source=source_info,
                            version=self.version
                        )
                        
                        # 座標情報を拡張フィールドに追加
                        if not hasattr(weather_request, 'ex_field') or weather_request.ex_field is None:
                            weather_request.ex_field = ExtendedField()
                        weather_request.ex_field.latitude = lat
                        weather_request.ex_field.longitude = long
                        weather_request.ex_flag = 1
                        
                        # _handle_weather_requestに処理を移譲
                        return self._handle_weather_request(weather_request, addr)
                        
                    except Exception as e:
                        print(f"キャッシュデータの処理中にエラーが発生しました: {e}")
                        if self.debug:
                            traceback.print_exc()
                        # エラーが発生した場合は通常処理を続行
                else:
                    if self.debug:
                        print(f"[{self.server_name}] エリアキャッシュミス - location_serverに転送")
            else:
                # 拡張フィールドから直接座標を取得
                lat = request.ex_field.get('latitude') if hasattr(request, 'ex_field') and request.ex_field else None
                long = request.ex_field.get('longitude') if hasattr(request, 'ex_field') and request.ex_field else None
                
                if lat is None or long is None:
                    if self.debug:
                        print(f"[{self.server_name}] ❌ 座標情報が取得できません - location_serverに転送")
            
            # 既存のLocationRequestをそのまま使用し、必要に応じて拡張フィールドのみ更新
            location_request = request
            
            # 座標情報を取得
            coords = request.get_coordinates() if hasattr(request, 'get_coordinates') and callable(request.get_coordinates) else None
            if coords:
                lat, long = coords
            else:
                # 拡張フィールドから直接座標を取得
                lat = request.ex_field.get('latitude') if hasattr(request, 'ex_field') and request.ex_field else None
                long = request.ex_field.get('longitude') if hasattr(request, 'ex_field') and request.ex_field else None
            
            # 拡張フィールドを確実に初期化（既存のものがあっても新規作成）
            location_request.ex_field = ExtendedField()
            
            # 座標情報を拡張フィールドに追加
            if lat is not None and long is not None:
                location_request.ex_field.latitude = lat
                location_request.ex_field.longitude = long
                if self.debug:
                    print(f"  座標を拡張フィールドに追加: {lat}, {long}")
            else:
                if self.debug:
                    print(f"  警告: 座標情報が取得できませんでした")
            
            # source情報を追加
            location_request.ex_field.source = source_info
            location_request.ex_flag = 1
            
            if self.debug:
                print(f"  LocationRequestタイプ: {location_request.type} (Type 0であることを確認)")
                print(f"  パケットID: {location_request.packet_id} (元のIDを保持)")
                print(f"  ex_flag: {location_request.ex_flag}")
                print(f"  source情報: {location_request.ex_field.source}")
                print(f"  拡張フィールド内容: {location_request.ex_field.to_dict() if hasattr(location_request.ex_field, 'to_dict') else 'N/A'}")
                print(f"  送信先: {self.location_resolver_host}:{self.location_resolver_port}")
            
            # 認証が有効な場合は認証ハッシュを追加
            if self.auth_enabled:
                try:
                    from common.utils.auth import WIPAuth
                    passphrase = self.passphrases['location_server']
                    auth_hash = WIPAuth.calculate_auth_hash(
                        location_request.packet_id,
                        location_request.timestamp,
                        passphrase
                    )
                    # 拡張フィールドに認証ハッシュを追加（hex文字列に変換）
                    location_request.ex_field.auth_hash = auth_hash.hex()
                    if self.debug:
                        print(f"  認証ハッシュを追加しました (location_server)")
                        print(f"  パスフレーズキー: location_server")
                        print(f"  認証ハッシュサイズ: {len(auth_hash)} バイト")
                except Exception as auth_e:
                    if self.debug:
                        print(f"  認証ハッシュ追加エラー: {auth_e}")
                    # 認証ハッシュ追加に失敗した場合はエラーレスポンスを返す
                    error_response = ErrorResponse(
                        version=self.version,
                        packet_id=request.packet_id,
                        error_code=401,  # 認証エラー
                        timestamp=int(datetime.now().timestamp())
                    )
                    if hasattr(request, 'ex_field') and request.ex_field and request.ex_field.contains('source'):
                        dest = request.ex_field.source
                        if isinstance(dest, tuple) and len(dest) == 2:
                            error_response.ex_field.source = dest
                            self.sock.sendto(error_response.to_bytes(), dest)
                    return
            
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
            print(f"530: [{self.server_name}] 位置情報リクエストの処理中にエラーが発生しました: {e}")
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
    
    
    def _handle_location_response(self, data, addr):
        """座標解決レスポンスの処理（Type 1・改良版）"""
        try:
            if self.debug:
                print(f"\n[{self.server_name}] タイプ1: 位置情報レスポンス処理開始")
                print(f"  受信データサイズ: {len(data)}バイト")
                print(f"  受信アドレス: {addr}")
            
            # 専用クラスでレスポンスをパース
            response = LocationResponse.from_bytes(data)
    
            lat, long = response.get_coordinates()
            
            # location_serverからのレスポンスでlocation_clientのキャッシュを手動更新
            if response.is_valid():
                area_code = response.get_area_code()
                if area_code and lat is not None and long is not None:
                    # location_clientのキャッシュを適切なpublicメソッドで更新
                    self.location_client.set_cached_area_code(lat, long, area_code)
                    if self.debug:
                        print(f"[{self.server_name}] location_clientキャッシュを手動更新: {lat}, {long} -> {area_code}")
    
            if self.debug:
                print(f"\n[{self.server_name}] タイプ1: 位置情報レスポンスを天気リクエストに変換中")
                print(f"  Area code: {response.get_area_code()}")
                print(f"  Source: {response.get_source_info()}")
                print(f"  Valid: {response.is_valid()}")
                print(f"  パケットID: {response.packet_id}")
                print(f"  バージョン: {response.version}")
                print(f"  タイプ: {response.type}")
                print(f"  タイムスタンプ: {response.timestamp}")
            
            # query_clientのキャッシュを使用してクエリを実行
            try:
                weather_data = self.query_client.get_weather_data(
                    area_code=response.area_code,
                    weather=bool(response.weather_flag),
                    temperature=bool(response.temperature_flag),
                    precipitation_prob=bool(response.pop_flag),
                    alert=bool(response.alert_flag),
                    disaster=bool(response.disaster_flag),
                    day=response.day,
                    use_cache=True,
                    timeout=10.0
                )
                
                if weather_data and 'error' not in weather_data:
                    # query_clientから直接データを取得できた場合
                    if self.debug:
                        print(f"  query_clientキャッシュヒット/成功: {response.area_code}")
                        print(f"  Weather data: {weather_data}")
                    
                    # 拡張フィールドの準備
                    ex_field_data = {}
                    if lat and long:
                        ex_field_data['latitude'] = lat
                        ex_field_data['longitude'] = long
                    
                    # alertとdisasterのデータをキャッシュから取得して拡張フィールドに追加
                    if response.alert_flag and 'alert' in weather_data:
                        ex_field_data['alert'] = weather_data['alert']
                    if response.disaster_flag and 'disaster' in weather_data:
                        ex_field_data['disaster'] = weather_data['disaster']
                    
                    # QueryResponseを作成
                    query_response = QueryResponse(
                        version=self.version,
                        packet_id=response.packet_id,
                        type=3,  # 気象データレスポンス
                        weather_flag=response.weather_flag,
                        temperature_flag=response.temperature_flag,
                        pop_flag=response.pop_flag,
                        alert_flag=response.alert_flag,
                        disaster_flag=response.disaster_flag,
                        ex_flag=1 if ex_field_data else 0,
                        day=response.day,
                        timestamp=int(datetime.now().timestamp()),
                        area_code=response.area_code,
                        weather_code=weather_data.get('weather_code', '0000'),
                        temperature=weather_data.get('temperature', 0) + 100,  # パケット形式に変換（+100）
                        pop=weather_data.get('precipitation_prob', 0),
                        ex_field=ex_field_data if ex_field_data else None
                    )
                    
                    # レスポンスを送信
                    response_data = query_response.to_bytes()
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
                            print(f"  query_clientキャッシュレスポンスを送信: {len(response_data)}バイト")
                            print(f"  送信先アドレス: {source_addr}")
    
                        bytes_sent = self.sock.sendto(response_data, source_addr)
                        if bytes_sent != len(response_data):
                            raise RuntimeError(f"送信バイト数不一致: {bytes_sent}/{len(response_data)}")
    
                        if self.debug:
                            print(f"  送信成功: {bytes_sent}バイト")
                            print(f"  query_clientから生成したレスポンスを {addr} へ送信しました")
    
                        return  # query_clientキャッシュヒット/成功時はここで終了
                    raise RuntimeError("source情報が見つかりません")
                else:
                    if self.debug:
                        print(f"  query_clientキャッシュミス/エラー - 通常のクエリサーバ転送を実行")
            except Exception as e:
                if self.debug:
                    print(f'query_clientでの処理中にエラーが発生: {str(e)}')
                    print('通常のクエリサーバ転送にフォールバック')
    
            query_request = QueryRequest.from_location_response(response)
    
            if self.debug:
                print(f"  WeatherRequest (タイプ2) に変換しました")
                print(f"  Target: {self.query_generator_host}:{self.query_generator_port}")
            
            # 認証が有効な場合は認証ハッシュを追加
            if self.auth_enabled:
                try:
                    from common.utils.auth import WIPAuth
                    passphrase = self.passphrases['query_server']
                    auth_hash = WIPAuth.calculate_auth_hash(
                        query_request.packet_id,
                        query_request.timestamp,
                        passphrase
                    )
                    # 拡張フィールドに認証ハッシュを追加（hex文字列に変換）
                    if not hasattr(query_request, 'ex_field') or query_request.ex_field is None:
                        query_request.ex_field = ExtendedField()
                    query_request.ex_field.auth_hash = auth_hash.hex()
                    query_request.ex_flag = 1
                    if self.debug:
                        print(f"  認証ハッシュを追加しました (query_server)")
                        print(f"  パスフレーズキー: query_server")
                        print(f"  認証ハッシュサイズ: {len(auth_hash)} バイト")
                except Exception as auth_e:
                    if self.debug:
                        print(f"  認証ハッシュ追加エラー: {auth_e}")
                    # 認証ハッシュ追加に失敗した場合はエラーレスポンスを返す
                    error_response = ErrorResponse(
                        version=self.version,
                        packet_id=response.packet_id,
                        error_code=401,  # 認証エラー
                        timestamp=int(datetime.now().timestamp())
                    )
                    source_info = response.get_source_info()
                    if source_info and isinstance(source_info, tuple) and len(source_info) == 2:
                        error_response.ex_field.source = source_info
                        self.sock.sendto(error_response.to_bytes(), source_info)
                    return
            
            # Query Generatorに送信
            packet_data = query_request.to_bytes()
            # パケットサイズのデバッグ出力を削除
                
            # メインソケットを使用して送信
            bytes_sent = self.send_udp_packet(packet_data, self.query_generator_host, self.query_generator_port)
            if bytes_sent != len(packet_data):
                raise RuntimeError(f"404: 不正なパケット長: (expected: {len(packet_data)}, sent: {bytes_sent})")
            
        except Exception as e:
            print(f"107: [{self.server_name}] 位置情報レスポンスの処理中にエラーが発生しました: {e}")
            if self.debug:
                traceback.print_exc()
            source_ip,source_port = data.get_source_info()
            if not (source_ip and source_port):
                print("sourceが不正なためエラーパケットを送信できません")
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
                print(f"\n[{self.server_name}] タイプ2: 天気リクエストを処理中")
                print(f"  Source: {source_info}")
                print(f"  Target: {self.query_generator_host}:{self.query_generator_port}")
                print(f"  Area code: {request.area_code}")
                if hasattr(request, 'get_requested_data_types'):
                    data_types = request.get_requested_data_types()
                    print(f"  Requested data: {data_types}")
            
            # query_clientのキャッシュを使用してクエリを実行
            try:
                weather_data = self.query_client.get_weather_data(
                    area_code=request.area_code,
                    weather=bool(request.weather_flag),
                    temperature=bool(request.temperature_flag),
                    precipitation_prob=bool(request.pop_flag),
                    alert=bool(request.alert_flag),
                    disaster=bool(request.disaster_flag),
                    day=request.day,
                    use_cache=True,
                    timeout=10.0
                )
                
                if weather_data and 'error' not in weather_data:
                    # query_clientから直接データを取得できた場合
                    if self.debug:
                        print(f"  query_clientキャッシュヒット/成功: {request.area_code}")
                        print(f"  Weather data: {weather_data}")
                    
                    # requestから座標情報を取得
                    coords = request.get_coordinates() if hasattr(request, 'get_coordinates') else (None, None)
                    req_lat, req_long = coords if coords else (None, None)
                    
                    # 拡張フィールドの準備
                    ex_field_data = {}
                    if req_lat and req_long:
                        ex_field_data['latitude'] = req_lat
                        ex_field_data['longitude'] = req_long
                    
                    # alertとdisasterのデータをキャッシュから取得して拡張フィールドに追加
                    if request.alert_flag and 'alert' in weather_data:
                        ex_field_data['alert'] = weather_data['alert']
                    if request.disaster_flag and 'disaster' in weather_data:
                        ex_field_data['disaster'] = weather_data['disaster']
                    
                    # QueryResponseを作成
                    query_response = QueryResponse(
                        version=self.version,
                        packet_id=request.packet_id,
                        type=3,  # 気象データレスポンス
                        weather_flag=request.weather_flag,
                        temperature_flag=request.temperature_flag,
                        pop_flag=request.pop_flag,
                        alert_flag=request.alert_flag,
                        disaster_flag=request.disaster_flag,
                        ex_flag=1 if ex_field_data else 0,
                        day=request.day,
                        timestamp=int(datetime.now().timestamp()),
                        area_code=request.area_code,
                        weather_code=weather_data.get('weather_code', '0000'),
                        temperature=weather_data.get('temperature', 0) + 100,  # パケット形式に変換（+100）
                        pop=weather_data.get('precipitation_prob', 0),
                        ex_field=ex_field_data if ex_field_data else None
                    )
    
                    response_data = query_response.to_bytes()
                    self.sock.sendto(response_data, addr)
    
                    if self.debug:
                        print(f"  query_clientから生成したレスポンスを {addr} へ送信しました")
                        print(f"  パケットサイズ: {len(response_data)} バイト")
    
                    return  # query_clientキャッシュヒット/成功時はここで終了
                else:
                    if self.debug:
                        print(f"  query_clientキャッシュミス/エラー - 通常のクエリサーバ転送を実行")
            except Exception as e:
                if self.debug:
                    print(f'query_clientでの処理中にエラーが発生: {str(e)}')
                    print('通常のクエリサーバ転送にフォールバック')
    
            if self.debug:
                print(f"  バックエンドサーバーにリクエストを転送します")
    
            # 既にQueryRequestの場合は、source情報を追加
            query_request = request
            
            # 拡張フィールドが存在しない場合は作成
            if not hasattr(query_request, 'ex_field') or query_request.ex_field is None:
                query_request.ex_field = ExtendedField()
            
            # source情報をセット
            query_request.ex_field.source = source_info
            query_request.ex_flag = 1  # 拡張フィールドを使用するのでフラグを1に
            
            if self.debug:
                if hasattr(query_request, 'get_source_info'):
                    print(f"  送信元を追加しました: {query_request.get_source_info()}")
            
            # 認証が有効な場合は認証ハッシュを追加
            if self.auth_enabled:
                try:
                    from common.utils.auth import WIPAuth
                    passphrase = self.passphrases['query_server']
                    auth_hash = WIPAuth.calculate_auth_hash(
                        query_request.packet_id,
                        query_request.timestamp,
                        passphrase
                    )
                    # 拡張フィールドに認証ハッシュを追加（hex文字列に変換）
                    query_request.ex_field.auth_hash = auth_hash.hex()
                    if self.debug:
                        print(f"  認証ハッシュを追加しました (query_server)")
                        print(f"  パスフレーズキー: query_server")
                        print(f"  認証ハッシュサイズ: {len(auth_hash)} バイト")
                except Exception as auth_e:
                    if self.debug:
                        print(f"  認証ハッシュ追加エラー: {auth_e}")
                    # 認証ハッシュ追加に失敗した場合はエラーレスポンスを返す
                    error_response = ErrorResponse(
                        version=self.version,
                        packet_id=request.packet_id,
                        error_code=401,  # 認証エラー
                        timestamp=int(datetime.now().timestamp())
                    )
                    if hasattr(request, 'ex_field') and request.ex_field and request.ex_field.contains('source'):
                        dest = request.ex_field.source
                        if isinstance(dest, tuple) and len(dest) == 2:
                            error_response.ex_field.source = dest
                            self.sock.sendto(error_response.to_bytes(), dest)
                    return
            
            # Query Generatorに転送
            packet_data = query_request.to_bytes()
                
            # メインソケットを使用して送信
            try:
                bytes_sent = self.send_udp_packet(packet_data, self.query_generator_host, self.query_generator_port)
                if bytes_sent != len(packet_data):
                    raise RuntimeError(f"404: 不正なパケット長: (expected: {len(packet_data)}, sent: {bytes_sent})")
            except Exception as e:
                print(f"クエリリクエストの転送に失敗しました: {self.query_generator_host}:{self.query_generator_port} - {str(e)}")
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
    
    def _handle_query_response(self, data, addr):
        """気象データレスポンスの処理（Type 3・改良版）"""
        try:
            # 専用クラスでレスポンスをパース
            response = QueryResponse.from_bytes(data)
            
            if self.debug:
                print(f"\n[{self.server_name}] タイプ3: 天気レスポンスを処理中")
                print(f"  Success: {response.is_success()}")
                if hasattr(response, 'get_response_summary'):
                    summary = response.get_response_summary()
                    print(f"  Summary: {summary}")
            
            # キャッシュ処理はquery_clientで統一管理されるため、
            # weather_serverでの重複キャッシュ保存は削除
            if self.debug and response.is_success():
                print(f"  成功レスポンスを受信 - キャッシュはquery_clientで管理済み")
            
            # 専用クラスのメソッドでsource情報を取得
            source_info = response.get_source_info()
            if not source_info:
                print(f"530: [{self.server_name}] 処理エラー: 天気レスポンスに送信元情報がありません")
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
                    print(f"[{self.server_name}] 不正なポート番号: {port}")
                    return
            else:
                print(f"[{self.server_name}] 不正なsource_info形式: {source_info}")
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
                response.version = self.version  # バージョンを正規化
                final_data = response.to_bytes()
                
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
            print(f"530: [{self.server_name}] 基本エラー: リクエスト処理失敗: {e}")
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
                print(f"\n[{self.server_name}] タイプ7: エラーパケットを処理中")
                print(f"  エラーコード: {request.error_code}")
                print(f"  送信元アドレス: {addr}")
            
            # 拡張フィールドからsourceを取得
            if request.ex_field and request.ex_field.contains('source'):
                source = request.ex_field.source
                if self.debug:
                    print(f"  ソースを取得: {source}")
                
                # エラーパケットを送信
                # インスタンス化済みエラーパケットのsourceは常にタプル形式であるべき
                if isinstance(source, tuple) and len(source) == 2:
                    host, port = source
                    try:
                        port = int(port)  # ポート番号のバリデーション
                        if not (0 < port <= 65535):
                            raise ValueError("Invalid port number")
                        dest_addr = (host, port)
                        self.sock.sendto(request.to_bytes(), dest_addr)
                        if self.debug:
                            print(f"  エラーパケットを {dest_addr} に送信しました")
                    except (ValueError, TypeError) as e:
                        print(f"[{self.server_name}] 不正なポート番号: {port} - {e}")
                        if self.debug:
                            print(f"  source内容: {source} (type: {type(source)})")
                else:
                    print(f"[{self.server_name}] 不正なsource形式: {source} (type: {type(source)})")
                    if self.debug:
                        print(f"  期待値: タプル (ip, port)")
                        print(f"  実際の値: {source}")
                        print(f"  拡張フィールド全体: {request.ex_field.to_dict() if request.ex_field else 'なし'}")
                        # デシリアライゼーション問題の可能性を調査
                        if isinstance(source, str):
                            print(f"  ⚠️  文字列形式のsourceが検出されました。デシリアライゼーション問題の可能性があります。")
                    return
            else:
                print(f"[{self.server_name}] エラー: エラーパケットにsourceが含まれていません")
                if self.debug:
                    print(f"  拡張フィールド: {request.ex_field.to_dict() if request.ex_field else 'なし'}")
                    
        except Exception as e:
            print(f"[{self.server_name}] エラーパケット処理中にエラーが発生しました: {e}")
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
    
    def _handle_report_request(self, request, addr):
        """データレポートリクエストの処理（Type 4）"""
        try:
            source_info = (addr[0], addr[1])  # タプル形式で保持
            
            if self.debug:
                print(f"\n[{self.server_name}] タイプ4: データレポートリクエストを処理中")
                print(f"  Source: {source_info}")
                print(f"  Target: {self.report_server_host}:{self.report_server_port}")
                print(f"  Area code: {request.area_code}")
            
            # ReportRequestにsource情報を追加（強化版）
            if self.debug:
                print(f"  拡張フィールドフラグ: {getattr(request, 'ex_flag', 'N/A')}")
                print(f"  拡張フィールド存在: {hasattr(request, 'ex_field') and request.ex_field is not None}")
            
            try:
                # 拡張フィールドフラグが0でも強制的にsource情報を追加
                
                # 既存の拡張フィールドデータを保持
                existing_data = {}
                if hasattr(request, 'ex_field') and request.ex_field:
                    try:
                        if hasattr(request.ex_field, 'to_dict'):
                            existing_data = request.ex_field.to_dict()
                        elif hasattr(request.ex_field, '__dict__'):
                            existing_data = {k: v for k, v in request.ex_field.__dict__.items()
                                           if not k.startswith('_')}
                    except Exception as preserve_e:
                        if self.debug:
                            print(f"  既存データ保持エラー: {preserve_e}")
                
                # 新しい拡張フィールドを作成
                request.ex_field = ExtendedField()
                
                # 既存データを復元
                for key, value in existing_data.items():
                    if key != 'source':  # sourceは新しく設定するので除外
                        try:
                            setattr(request.ex_field, key, value)
                        except Exception as restore_e:
                            if self.debug:
                                print(f"  データ復元エラー ({key}): {restore_e}")
                
                # source情報を追加
                request.ex_field.source = source_info
                
                # 拡張フィールドフラグを強制的に1に設定
                request.ex_flag = 1
                
                if self.debug:
                    print(f"  ✓ ReportRequest に送信元情報を強制追加: {source_info}")
                    print(f"  ✓ 拡張フィールドフラグを1に設定")
                    if hasattr(request.ex_field, 'to_dict'):
                        print(f"  ✓ 拡張フィールド内容: {request.ex_field.to_dict()}")
            
            except Exception as ex_e:
                print(f"❌ 拡張フィールドへのsource追加に失敗: {ex_e}")
                if self.debug:
                    traceback.print_exc()
                
                # 最終手段：エラーレスポンスを送信
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=request.packet_id,
                    error_code=530,
                    timestamp=int(datetime.now().timestamp())
                )
                try:
                    self.sock.sendto(error_response.to_bytes(), source_info)
                    if self.debug:
                        print(f"  エラーレスポンスを送信: {source_info}")
                except Exception as send_e:
                    print(f"エラーレスポンス送信も失敗: {send_e}")
                return
            
            # 認証が有効な場合は認証ハッシュを追加
            if self.auth_enabled:
                try:
                    from common.utils.auth import WIPAuth
                    passphrase = self.passphrases['report_server']
                    auth_hash = WIPAuth.calculate_auth_hash(
                        request.packet_id,
                        request.timestamp,
                        passphrase
                    )
                    # 拡張フィールドに認証ハッシュを追加（hex文字列に変換）
                    request.ex_field.auth_hash = auth_hash.hex()
                    if self.debug:
                        print(f"  認証ハッシュを追加しました (report_server)")
                        print(f"  パスフレーズキー: report_server")
                        print(f"  認証ハッシュサイズ: {len(auth_hash)} バイト")
                except Exception as auth_e:
                    if self.debug:
                        print(f"  認証ハッシュ追加エラー: {auth_e}")
                    # 認証ハッシュ追加に失敗した場合はエラーレスポンスを返す
                    error_response = ErrorResponse(
                        version=self.version,
                        packet_id=request.packet_id,
                        error_code=401,  # 認証エラー
                        timestamp=int(datetime.now().timestamp())
                    )
                    if hasattr(request, 'ex_field') and request.ex_field and request.ex_field.contains('source'):
                        dest = request.ex_field.source
                        if isinstance(dest, tuple) and len(dest) == 2:
                            error_response.ex_field.source = dest
                            self.sock.sendto(error_response.to_bytes(), dest)
                    return
            
            # レポートサーバーに転送
            packet_data = request.to_bytes()
            
            try:
                bytes_sent = self.send_udp_packet(packet_data, self.report_server_host, self.report_server_port)
                if bytes_sent != len(packet_data):
                    raise RuntimeError(f"404: 不正なパケット長: (expected: {len(packet_data)}, sent: {bytes_sent})")
                    
                if self.debug:
                    print(f"  レポートサーバーに転送しました: {bytes_sent}バイト")
                    
            except Exception as e:
                print( f"レポートリクエストの転送に失敗しました: {self.report_server_host}:{self.report_server_port} - {str(e)}")
                if self.debug:
                    traceback.print_exc()
                # ErrorResponseを作成して返す
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=request.packet_id,
                    error_code=420,
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
            print(f"530: [{self.server_name}] レポートリクエストの処理中にエラーが発生しました: {e}")
            if self.debug:
                traceback.print_exc()
            # ErrorResponseを作成して返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code=530,
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
    
    def _handle_report_response(self, data, addr):
        """データレポートレスポンスの処理（Type 5）"""
        try:
            # 専用クラスでレスポンスをパース
            response = ReportResponse.from_bytes(data)
            
            if self.debug:
                print(f"\n[{self.server_name}] タイプ5: データレポートレスポンスを処理中")
                print(f"  Success: {response.is_success()}")
                print(f"  Area code: {response.area_code}")
                print(f"  Packet ID: {response.packet_id}")
            
            # 専用クラスのメソッドでsource情報を取得
            source_info = response.get_source_info()
            if not source_info:
                print(f"530: [{self.server_name}] 処理エラー: レポートレスポンスに送信元情報がありません")
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
                    print(f"[{self.server_name}] 不正なポート番号: {port}")
                    return
            else:
                print(f"[{self.server_name}] 不正なsource_info形式: {source_info}")
                return
            
            if self.debug:
                status = "成功" if response.is_success() else "失敗"
                print(f"  {dest_addr} へレポートレスポンス({status})を転送中")
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
                # レスポンスのバージョンを現在のサーバーバージョンで設定
                response.version = self.version  # バージョンを正規化
                final_data = response.to_bytes()
                
                # 元のクライアントに送信
                try:
                    bytes_sent = self.sock.sendto(final_data, dest_addr)
                    if bytes_sent != len(final_data):
                        raise RuntimeError(f"パケット長エラー: (expected: {len(final_data)}, sent: {bytes_sent})")
                        
                    if self.debug:
                        print(f"  クライアントに {bytes_sent} バイトを送信しました")
                        
                except Exception as e:
                    if self.debug:
                        traceback.print_exc()
                    # ErrorResponseを作成して返す
                    error_response = ErrorResponse(
                        version=self.version,
                        packet_id=response.packet_id,
                        error_code=530,
                        timestamp=int(datetime.now().timestamp())
                    )
                    self.sock.sendto(error_response.to_bytes(), dest_addr)
                    raise RuntimeError(f"天気サーバーでの処理エラー: クライアントへの転送に失敗 {str(e)}")
                    
            except Exception as conv_e:
                print(f"530: [{self.server_name}] 処理エラー: {conv_e}")
                if self.debug:
                    traceback.print_exc()
                # ErrorResponseを作成して返す
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=response.packet_id,
                    error_code=530,
                    timestamp=int(datetime.now().timestamp())
                )
                error_response.ex_field.source = dest_addr
                self.sock.sendto(error_response.to_bytes(), dest_addr)
                return
                
        except Exception as e:
            print(f"530: [{self.server_name}] レポートレスポンス処理中にエラーが発生しました: {e}")
            if self.debug:
                traceback.print_exc()
            # ErrorResponseを作成して返す（responseが未定義の場合の処理を追加）
            packet_id = getattr(response, 'packet_id', 0) if 'response' in locals() else 0
            error_response = ErrorResponse(
                version=self.version,
                packet_id=packet_id,
                error_code=530,
                timestamp=int(datetime.now().timestamp())
            )
            # dest_addrが未定義の場合はaddrを使用
            dest_addr = locals().get('dest_addr', addr)
            self.sock.sendto(error_response.to_bytes(), dest_addr)
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
            return LocationRequest.from_bytes(data)
        elif packet_type == 1:
            # 座標解決レスポンス
            return LocationResponse.from_bytes(data)
        elif packet_type == 2:
            # 気象データリクエスト
            return QueryRequest.from_bytes(data)
        elif packet_type == 3:
            # 気象データレスポンス
            return QueryResponse.from_bytes(data)
        elif packet_type == 4:
            # データレポートリクエスト
            return ReportRequest.from_bytes(data)
        elif packet_type == 5:
            # データレポートレスポンス
            return ReportResponse.from_bytes(data)
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
            return False, "403", f"バージョンが不正です (expected: {self.version}, got: {request.version})"
        
        # タイプのチェック（0-3,4,5,7が有効）
        if request.type not in [0, 1, 2, 3, 4, 5, 7]:
            return False, "400", f"不正なパケットタイプ: {request.type}"
    
        # エリアコードのチェック (タイプ0と7は除外)
        if request.type not in [0, 7] and (not request.area_code or request.area_code == "000000"):
            return False, "402", "エリアコードが未設定"
    
        # 専用クラスのバリデーションメソッドを使用
        if hasattr(request, 'is_valid') and callable(getattr(request, 'is_valid')):
            if not request.is_valid():
                return False, "400", "専用クラスのバリデーションに失敗"
        
        return True, None, None
    
    def _debug_print_request(self, data, parsed):
        """リクエストのデバッグ情報を出力（改良版・専用クラス対応）"""
        if not self.debug:
            return
            
        print(f"\n[{self.server_name}] === 受信パケット (拡張版) ===")
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

