"""
Weather Client - 改良版（専用パケットクラス使用）
Weather Serverプロキシと通信するクライアント
"""

import socket
import time
import logging
import sys
import os
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from WIPCommonPy.packet import (
    LocationRequest,
    LocationResponse,
    QueryRequest,
    QueryResponse,
    ErrorResponse,
)
from WIPCommonPy.packet.debug import create_debug_logger
from WIPCommonPy.clients.utils.packet_id_generator import PacketIDGenerator12Bit
from WIPCommonPy.clients.utils import (
    receive_with_id,
    receive_with_id_async,
    safe_sock_sendto,
)
from WIPCommonPy.utils.network import resolve_ipv4

PIDG = PacketIDGenerator12Bit()


class WeatherClient:
    """Weather Serverと通信するクライアント（専用パケットクラス使用）"""

    def __init__(self, host=None, port=None, debug=False):
        if host is None:
            host = os.getenv("WEATHER_SERVER_HOST", "wip.ncc.onl")
        if port is None:
            port = int(os.getenv("WEATHER_SERVER_PORT", "4110"))
        """
        初期化
        
        Args:
            host: Weather Serverのホスト
            port: Weather Serverのポート
            debug: デバッグモード
        """
        self.host = resolve_ipv4(host)
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(10.0)
        self.debug = debug
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.debug_logger = create_debug_logger(__name__, debug)
        self.VERSION = 1
        self.PIDG = PacketIDGenerator12Bit()

        # 認証設定を初期化
        self._init_auth_config()

    def _init_auth_config(self):
        """認証設定を環境変数から読み込み"""
        # WeatherServer向けのリクエスト認証設定
        auth_enabled = (
            os.getenv("WEATHER_SERVER_REQUEST_AUTH_ENABLED", "false").lower() == "true"
        )
        auth_passphrase = os.getenv("WEATHER_SERVER_PASSPHRASE", "")

        self.auth_enabled = auth_enabled
        self.auth_passphrase = auth_passphrase

    def _get_response_auth_config(self):
        """レスポンス認証設定を取得"""
        return (
            os.getenv("WEATHER_SERVER_RESPONSE_AUTH_ENABLED", "false").lower() == "true"
        )
    
    def _verify_response_auth(self, response):
        """
        レスポンス認証を検証
        
        Args:
            response: Response オブジェクト
            
        Returns:
            bool: 認証が成功した場合True、失敗またはスキップした場合False
        """
        # レスポンス認証が無効な場合は常にTrue
        if not self._get_response_auth_config():
            return True
            
        # レスポンスのresponse_authフラグをチェック
        # フラグが0の場合は認証検証をスキップ
        if not hasattr(response, 'response_auth') or response.response_auth != 1:
            self.logger.debug("Response authentication skipped - response_auth flag not set")
            return True
            
        # パスフレーズが設定されていない場合は失敗
        if not self.auth_passphrase:
            self.logger.warning("Response authentication enabled but passphrase not set")
            return False
            
        # レスポンスパケットのタイムスタンプとパケットIDを使って再計算
        from WIPCommonPy.utils.auth import WIPAuth
        
        try:
            # レスポンスパケットの認証ハッシュを拡張フィールドから取得
            if not hasattr(response, "ex_field") or not response.ex_field:
                self.logger.warning("Response authentication required but no extended field found")
                return False
                
            if not response.ex_field.contains("auth_hash"):
                self.logger.warning("Response authentication required but no auth_hash found")
                return False
                
            auth_hash_str = response.ex_field.auth_hash
            if not auth_hash_str:
                self.logger.warning("Response authentication required but no auth_hash found")
                return False
                
            # hex文字列をバイト列に変換
            received_hash = bytes.fromhex(auth_hash_str)
            
            # レスポンスパケットのタイムスタンプとパケットIDで認証ハッシュを再計算
            is_valid = WIPAuth.verify_auth_hash(
                packet_id=response.packet_id,
                timestamp=response.timestamp,
                passphrase=self.auth_passphrase,
                received_hash=received_hash
            )
            
            if not is_valid:
                self.logger.error("Response authentication verification failed")
                return False
                
            self.logger.debug("Response authentication verification successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during response authentication verification: {e}")
            return False

    def get_weather_data(
        self,
        area_code,
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=False,
        disaster=False,
        landmarks=False,
        landmarks_offset=None,
        landmarks_limit=None,
        day=0,
    ):
        """
        エリアコードから天気情報を取得（統一命名規則版）

        Args:
            area_code: エリアコード（文字列または数値、例: "011000" または 11000）
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation_prob: 降水確率データを取得するか
            alert: 警報データを取得するか
            disaster: 災害情報データを取得するか
            landmarks: ランドマークデータを取得するか
            landmarks_offset: ランドマークデータの開始オフセット
            landmarks_limit: ランドマークデータの取得件数制限
            day: 予報日（0: 今日, 1: 明日, ...）

        Returns:
            dict: 気象データ（ランドマークデータを含む）
        """
        # QueryRequestインスタンスを作成
        request = QueryRequest.create_query_request(
            area_code=area_code,
            packet_id=self.PIDG.next_id(),
            weather=weather,
            temperature=temperature,
            precipitation_prob=precipitation_prob,
            alert=alert,
            disaster=disaster,
            landmarks=landmarks,
            landmarks_offset=landmarks_offset,
            landmarks_limit=landmarks_limit,
            day=day,
            version=self.VERSION,
        )

        # 認証設定を適用（認証が有効な場合）
        if self.auth_enabled and self.auth_passphrase:
            request.enable_auth(self.auth_passphrase)
            request.set_auth_flags()

        # レスポンス認証フラグの設定
        if self._get_response_auth_config():
            request.response_auth = 1

        # QueryRequestインスタンスを使用して実行
        return self._execute_query_request(request)

    def _execute_query_request(self, request: QueryRequest):
        """
        QueryRequestを実行する共通処理

        Args:
            request: 実行するQueryRequestインスタンス

        Returns:
            dict: 気象データ
        """
        try:
            start_time = time.time()

            self.debug_logger.log_request(request, "WEATHER DATA REQUEST")

            # リクエスト送信
            self.sock.sendto(request.to_bytes(), (self.host, self.port))

            # レスポンスを受信
            response_data, addr = receive_with_id(self.sock, request.packet_id, 10.0)
            self.logger.debug(response_data)

            # パケットタイプに基づいて適切なレスポンスクラスを選択
            response_type = (
                int.from_bytes(response_data[2:3], byteorder="little") & 0x07
            )

            if response_type == 3:  # 天気レスポンス
                response = QueryResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "WEATHER DATA RESPONSE")

                # レスポンス認証検証
                if response and not self._verify_response_auth(response):
                    self.logger.error("Response authentication verification failed")
                    return None

                if response.is_success():
                    result = response.get_weather_data()

                    # 統一フォーマットでの成功ログ出力
                    if result:
                        execution_time = time.time() - start_time
                        self.debug_logger.log_unified_packet_received(
                            "Direct request", execution_time, result
                        )

                    return result
                else:
                    if self.debug:
                        self.logger.error(
                            "420: クライアントエラー: クエリサーバが見つからない"
                        )
                    return None

            elif response_type == 7:  # エラーレスポンス
                response = ErrorResponse.from_bytes(response_data)
                if self.debug:
                    self.logger.error("\n=== ERROR RESPONSE ===")
                    self.logger.error(f"Error Code: {response.error_code}")
                    self.logger.error("=====================\n")

                return {
                    "type": "error",
                    "error_code": response.error_code,
                }
            else:
                if self.debug:
                    self.logger.error(f"不明なパケットタイプ: {response_type}")
                return None

        except socket.timeout:
            self.logger.error("421: クライアントエラー:  クエリサーバ接続タイムアウト")
            return None
        except Exception as e:
            self.logger.error(
                f"420: クライアントエラー: クエリサーバが見つからない - {e}"
            )
            if self.debug:
                self.logger.exception("Traceback:")
            return None

    async def _execute_query_request_async(
        self, request: QueryRequest, *, raw_packet: bool = False
    ):
        """
        非同期版 _execute_query_request

        Args:
            request: 送信するQueryRequest
            raw_packet: Trueの場合はパースせずにQueryResponse/ErrorResponseをそのまま返す
        """
        try:
            start_time = time.time()

            self.debug_logger.log_request(request, "WEATHER DATA REQUEST")

            loop = asyncio.get_running_loop()
            self.sock.setblocking(False)
            await safe_sock_sendto(
                loop, self.sock, request.to_bytes(), (self.host, self.port)
            )

            response_data, addr = await receive_with_id_async(
                self.sock, request.packet_id, 10.0
            )
            self.logger.debug(response_data)

            response_type = (
                int.from_bytes(response_data[2:3], byteorder="little") & 0x07
            )

            if response_type == 3:
                response = QueryResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "WEATHER DATA RESPONSE")

                # レスポンス認証検証（非同期版）
                if response and not self._verify_response_auth(response):
                    self.logger.error("Response authentication verification failed")
                    return None

                if raw_packet:
                    return response

                if response.is_success():
                    result = response.get_weather_data()

                    if result:
                        execution_time = time.time() - start_time
                        self.debug_logger.log_unified_packet_received(
                            "Direct request", execution_time, result
                        )

                    return result
                else:
                    if self.debug:
                        self.logger.error(
                            "420: クライアントエラー: クエリサーバが見つからない"
                        )
                    return None

            elif response_type == 7:
                response = ErrorResponse.from_bytes(response_data)
                if self.debug:
                    self.logger.error("\n=== ERROR RESPONSE ===")
                    self.logger.error(f"Error Code: {response.error_code}")
                    self.logger.error("=====================\n")

                return response if raw_packet else {"type": "error", "error_code": response.error_code}
            else:
                if self.debug:
                    self.logger.error(f"不明なパケットタイプ: {response_type}")
                return None

        except asyncio.TimeoutError:
            self.logger.error("421: クライアントエラー:  クエリサーバ接続タイムアウト")
            return None
        except Exception as e:
            self.logger.error(
                f"420: クライアントエラー: クエリサーバが見つからない - {e}"
            )
            if self.debug:
                self.logger.exception("Traceback:")
            return None

    def _execute_location_request(self, request: LocationRequest):
        """
        LocationRequestを実行する共通処理

        Args:
            request: 実行するLocationRequestインスタンス

        Returns:
            dict: 気象データ
        """
        try:
            start_time = time.time()

            self.debug_logger.log_request(request, "LOCATION REQUEST")

            # リクエスト送信
            self.sock.sendto(request.to_bytes(), (self.host, self.port))

            # レスポンスを受信
            response_data, addr = self.sock.recvfrom(1024)

            # パケットタイプに基づいて適切なレスポンスクラスを選択
            response_type = (
                int.from_bytes(response_data[2:3], byteorder="little") & 0x07
            )
            self.logger.debug(response_data)

            if response_type == 1:  # Location レスポンス
                response = LocationResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "LOCATION RESPONSE")

                # レスポンス認証検証
                if response and not self._verify_response_auth(response):
                    self.logger.error("Location response authentication verification failed")
                    return None

                if self.debug:
                    self.logger.debug(
                        "LocationResponseを受信しました。weather_serverからの追加処理を待機します。"
                    )

                # weather_serverが座標解決後、直接query_serverにリクエストを送信し、
                # その結果をクライアントに返すため、ここでは追加のリクエストは送信しません。
                # 次のレスポンス（Type 3）を待機します。
                try:
                    # 次のレスポンス（天気データ）を受信
                    response_data, addr = self.sock.recvfrom(1024)
                    response_type = (
                        int.from_bytes(response_data[2:3], byteorder="little") & 0x07
                    )

                    if response_type == 3:  # 天気レスポンス
                        query_response = QueryResponse.from_bytes(response_data)
                        self.debug_logger.log_response(
                            query_response, "WEATHER RESPONSE"
                        )

                        # レスポンス認証検証
                        if query_response and not self._verify_response_auth(query_response):
                            self.logger.error("Weather response authentication verification failed")
                            return None

                        if query_response.is_success():
                            result = query_response.get_weather_data()

                            # 統一フォーマットでの成功ログ出力
                            if result:
                                execution_time = time.time() - start_time
                                self.debug_logger.log_unified_packet_received(
                                    "Direct request", execution_time, result
                                )

                            return result
                        else:
                            if self.debug:
                                self.logger.error(
                                    "420: クライアントエラー: 天気データ取得に失敗しました"
                                )
                            return None
                    elif response_type == 7:  # エラーレスポンス
                        error_response = ErrorResponse.from_bytes(response_data)
                        if self.debug:
                            self.logger.error("\n=== ERROR RESPONSE ===")
                            self.logger.error(
                                f"Error Code: {error_response.error_code}"
                            )
                            self.logger.error("=====================\n")

                        return {
                            "type": "error",
                            "error_code": error_response.error_code,
                        }
                    else:
                        if self.debug:
                            self.logger.error(f"不明なパケットタイプ: {response_type}")
                        return None

                except socket.timeout:
                    self.logger.error(
                        "421: クライアントエラー: 天気データ受信タイムアウト"
                    )
                    return None
        except Exception as e:
            self.logger.error(f"420: クライアントエラー: 天気データ受信エラー - {e}")
            if self.debug:
                self.logger.exception("Traceback:")
            return None

    async def _execute_location_request_async(self, request: LocationRequest):
        """非同期版 _execute_location_request"""
        try:
            start_time = time.time()

            self.debug_logger.log_request(request, "LOCATION REQUEST")

            loop = asyncio.get_running_loop()
            self.sock.setblocking(False)
            await safe_sock_sendto(
                loop, self.sock, request.to_bytes(), (self.host, self.port)
            )

            response_data, addr = await receive_with_id_async(
                self.sock, request.packet_id, 10.0
            )
            response_type = (
                int.from_bytes(response_data[2:3], byteorder="little") & 0x07
            )
            self.logger.debug(response_data)

            if response_type == 1:
                response = LocationResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "LOCATION RESPONSE")

                # レスポンス認証検証（非同期版）
                if response and not self._verify_response_auth(response):
                    self.logger.error("Location response authentication verification failed")
                    return None

                if self.debug:
                    self.logger.debug(
                        "LocationResponseを受信しました。weather_serverからの追加処理を待機します。"
                    )

                try:
                    response_data, addr = await receive_with_id_async(
                        self.sock, response.packet_id, 10.0
                    )
                    response_type = (
                        int.from_bytes(response_data[2:3], byteorder="little") & 0x07
                    )

                    if response_type == 3:
                        query_response = QueryResponse.from_bytes(response_data)
                        self.debug_logger.log_response(
                            query_response, "WEATHER RESPONSE"
                        )

                        # レスポンス認証検証（非同期版）
                        if query_response and not self._verify_response_auth(query_response):
                            self.logger.error("Weather response authentication verification failed")
                            return None

                        if query_response.is_success():
                            result = query_response.get_weather_data()

                            if result:
                                execution_time = time.time() - start_time
                                self.debug_logger.log_unified_packet_received(
                                    "Direct request", execution_time, result
                                )

                            return result
                        else:
                            if self.debug:
                                self.logger.error(
                                    "420: クライアントエラー: 天気データ取得に失敗しました"
                                )
                            return None
                    elif response_type == 7:
                        error_response = ErrorResponse.from_bytes(response_data)
                        if self.debug:
                            self.logger.error("\n=== ERROR RESPONSE ===")
                            self.logger.error(
                                f"Error Code: {error_response.error_code}"
                            )
                            self.logger.error("=====================\n")

                        return {
                            "type": "error",
                            "error_code": error_response.error_code,
                        }
                    else:
                        if self.debug:
                            self.logger.error(f"不明なパケットタイプ: {response_type}")
                        return None

                except asyncio.TimeoutError:
                    self.logger.error(
                        "421: クライアントエラー: 天気データ受信タイムアウト"
                    )
                    return None
                except Exception as e:
                    self.logger.error(
                        f"420: クライアントエラー: 天気データ受信エラー - {e}"
                    )
                    if self.debug:
                        self.logger.exception("Traceback:")
                    return None

            elif response_type == 3:
                response = QueryResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "DIRECT WEATHER RESPONSE")

                # レスポンス認証検証（非同期版、直接レスポンス）
                if response and not self._verify_response_auth(response):
                    self.logger.error("Direct weather response authentication verification failed")
                    return None

                if response.is_success():
                    result = response.get_weather_data()

                    if result:
                        execution_time = time.time() - start_time
                        self.debug_logger.log_unified_packet_received(
                            "Direct request", execution_time, result
                        )

                    return result
                else:
                    if self.debug:
                        self.logger.error(
                            "420: クライアントエラー: クエリサーバが見つからない"
                        )
                    return None

            elif response_type == 7:
                response = ErrorResponse.from_bytes(response_data)
                if self.debug:
                    self.logger.error("\n=== ERROR RESPONSE ===")
                    self.logger.error(f"Error Code: {response.error_code}")
                    self.logger.error("=====================\n")

                return {"type": "error", "error_code": response.error_code}
            else:
                if self.debug:
                    self.logger.error(f"不明なパケットタイプ: {response_type}")
                return None

        except asyncio.TimeoutError:
            self.logger.error("421: クライアントエラー: クエリサーバ接続タイムアウト")
            return None
        except Exception as e:
            self.logger.error(
                f"420: クライアントエラー: クエリサーバが見つからない - {e}"
            )
            if self.debug:
                self.logger.exception("Traceback:")
            return None

    def get_weather_simple(self, area_code, include_all=False, include_landmarks=False, day=0):
        """
        基本的な気象データを一括取得する簡便メソッド（統一命名規則版）

        Args:
            area_code: エリアコード
            include_all: すべてのデータを取得するか（警報・災害情報も含む）
            include_landmarks: ランドマークデータを取得するか
            day: 予報日（0: 今日, 1: 明日, ...）

        Returns:
            dict: 気象データ
        """
        return self.get_weather_data(
            area_code=area_code,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=include_all,
            disaster=include_all,
            landmarks=include_landmarks,
            day=day,
        )

    def get_weather_with_landmarks(self, area_code, landmarks_limit=10, landmarks_offset=0, day=0):
        """
        エリアコードから天気情報とランドマークデータを取得する専用メソッド

        Args:
            area_code: エリアコード（文字列または数値、例: "011000" または 11000）
            landmarks_limit: ランドマークデータの取得件数制限（デフォルト: 10）
            landmarks_offset: ランドマークデータの開始オフセット（デフォルト: 0）
            day: 予報日（0: 今日, 1: 明日, ...）

        Returns:
            dict: 気象データ（ランドマークデータを含む）
        """
        return self.get_weather_data(
            area_code=area_code,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            landmarks=True,
            landmarks_limit=landmarks_limit,
            landmarks_offset=landmarks_offset,
            day=day,
        )

    # 後方互換性のためのエイリアスメソッド
    def get_weather_by_area_code(
        self,
        area_code,
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=False,
        disaster=False,
        day=0,
    ):
        """後方互換性のため - get_weather_data()を使用してください"""
        return self.get_weather_data(
            area_code, weather, temperature, precipitation_prob, alert, disaster, day
        )

    def close(self):
        """ソケットを閉じる"""
        self.sock.close()


def weather_code_to_description(weather_code):
    """天気コードから説明文字列に変換"""
    weather_descriptions = {
        100: "晴れ",
        101: "晴れ時々曇り", 
        102: "晴れ一時雨",
        103: "晴れ時々雨",
        104: "晴れ一時雪",
        105: "晴れ時々雪",
        106: "晴れ一時雨か雪",
        107: "晴れ時々雨か雪",
        108: "晴れ一時雨か雷雨",
        110: "晴れ後時々曇り",
        111: "晴れ後曇り",
        112: "晴れ後一時雨",
        113: "晴れ後時々雨",
        114: "晴れ後雨",
        115: "晴れ後一時雪",
        116: "晴れ後時々雪",
        117: "晴れ後雪",
        118: "晴れ後雨か雪",
        119: "晴れ後雨か雷雨",
        120: "晴れ朝夕一時雨",
        121: "晴れ朝の内一時雨",
        122: "晴れ夕方一時雨",
        123: "晴れ山沿い雷雨",
        124: "晴れ山沿い雪",
        125: "晴れ午後は雷雨",
        126: "晴れ昼頃から雨",
        127: "晴れ夕方から雨",
        128: "晴れ夜は雨",
        130: "朝の内霧後晴れ",
        131: "晴れ明け方霧",
        132: "晴れ朝夕曇り",
        140: "晴れ時々雨で雷を伴う",
        160: "晴れ一時雪か雨",
        170: "晴れ時々雪か雨",
        181: "晴れ後雪か雨",
        200: "曇り",
        201: "曇り時々晴れ",
        202: "曇り一時雨",
        203: "曇り時々雨",
        204: "曇り一時雪",
        205: "曇り時々雪",
        206: "曇り一時雨か雪",
        207: "曇り時々雨か雪",
        208: "曇り一時雨か雷雨",
        209: "霧",
        210: "曇り後時々晴れ",
        211: "曇り後晴れ",
        212: "曇り後一時雨",
        213: "曇り後時々雨",
        214: "曇り後雨",
        215: "曇り後一時雪",
        216: "曇り後時々雪",
        217: "曇り後雪",
        218: "曇り後雨か雪",
        219: "曇り後雨か雷雨",
        220: "曇り朝夕一時雨",
        221: "曇り朝の内一時雨",
        222: "曇り夕方一時雨",
        223: "曇り日中時々晴れ",
        224: "曇り昼頃から雨",
        225: "曇り夕方から雨",
        226: "曇り夜は雨",
        228: "曇り昼頃から雪",
        229: "曇り夕方から雪",
        230: "曇り夜は雪",
        231: "曇り海上海岸は霧か霧雨",
        240: "曇り時々雨で雷を伴う",
        250: "曇り時々雪で雷を伴う",
        260: "曇り一時雪か雨",
        270: "曇り時々雪か雨",
        281: "曇り後雪か雨",
        300: "雨",
        301: "雨時々晴れ",
        302: "雨時々止む",
        303: "雨時々雪",
        304: "雨か雪",
        306: "大雨",
        308: "雨で暴風を伴う",
        309: "雨一時雪",
        311: "雨後晴れ",
        313: "雨後曇り",
        314: "雨後時々雪",
        315: "雨後雪",
        316: "雨か雪後晴れ",
        317: "雨か雪後曇り",
        320: "朝の内雨後晴れ",
        321: "朝の内雨後曇り",
        322: "雨朝晩一時雪",
        323: "雨昼頃から晴れ",
        324: "雨夕方から晴れ",
        325: "雨夜は晴",
        326: "雨夕方から雪",
        327: "雨夜は雪",
        328: "雨一時強く降る",
        329: "雨一時みぞれ",
        340: "雪か雨",
        350: "雨で雷を伴う",
        361: "雪か雨後晴れ",
        371: "雪か雨後曇り",
        400: "雪",
        401: "雪時々晴れ",
        402: "雪時々止む",
        403: "雪時々雨",
        405: "大雪",
        406: "風雪強い",
        407: "暴風雪",
        409: "雪一時雨",
        411: "雪後晴れ",
        413: "雪後曇り",
        414: "雪後雨",
        420: "朝の内雪後晴れ",
        421: "朝の内雪後曇り",
        422: "雪昼頃から晴れ",
        423: "雪夕方から晴れ",
        424: "雪夜は晴れ",
        425: "雪一時強く降る",
        426: "雪後みぞれ",
        427: "雪一時みぞれ",
        450: "雪で雷を伴う",
    }
    return weather_descriptions.get(weather_code, f"天気コード {weather_code}")

def main():
    """CLI メイン関数 - エリアコード指定で気象データとランドマークデータを取得"""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(
        description="Weather Client - 気象データとランドマークデータの取得"
    )
    parser.add_argument(
        "--area-code", "-a",
        type=str,
        help="エリアコード (例: 011000, 130010)"
    )
    parser.add_argument(
        "--landmarks", "-l",
        action="store_true",
        help="ランドマークデータを含めて取得"
    )
    parser.add_argument(
        "--landmarks-limit",
        type=int,
        default=10,
        help="ランドマークデータの取得件数制限 (デフォルト: 10)"
    )
    parser.add_argument(
        "--landmarks-offset",
        type=int,
        default=0,
        help="ランドマークデータの開始オフセット (デフォルト: 0)"
    )
    parser.add_argument(
        "--include-all", "-A",
        action="store_true",
        help="警報・災害情報も含めてすべてのデータを取得"
    )
    parser.add_argument(
        "--day", "-d",
        type=int,
        default=0,
        help="予報日 (0: 今日, 1: 明日, ..., デフォルト: 0)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="デバッグモードで実行"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="結果をJSON形式で出力"
    )

    args = parser.parse_args()

    # エリアコードが指定されていない場合はヘルプを表示
    if not args.area_code:
        parser.print_help()
        print("\n例:")
        print("  python -m WIPCommonPy.clients.weather_client --area-code 011000")
        print("  python -m WIPCommonPy.clients.weather_client --area-code 130010 --landmarks")
        print("  python -m WIPCommonPy.clients.weather_client -a 011000 -l --landmarks-limit 20")
        return

    # ロギング設定
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    if not args.json:
        print(f"Weather Client - エリアコード: {args.area_code}")
        if args.landmarks:
            print(f"ランドマークデータ取得: 有効 (limit: {args.landmarks_limit}, offset: {args.landmarks_offset})")
        print("=" * 60)

    client = WeatherClient(debug=args.debug)

    try:
        # ランドマークデータが必要な場合は専用メソッドを使用
        if args.landmarks:
            result = client.get_weather_with_landmarks(
                area_code=args.area_code,
                landmarks_limit=args.landmarks_limit,
                landmarks_offset=args.landmarks_offset,
                day=args.day,
            )
        else:
            # 通常の天気データを取得
            result = client.get_weather_simple(
                area_code=args.area_code,
                include_all=args.include_all,
                day=args.day,
            )

        if result:
            if args.json:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print("\n✓ 取得成功:")
                print("-" * 40)
                
                # 基本的な気象情報を表示
                if "weather_code" in result:
                    weather_desc = weather_code_to_description(result['weather_code'])
                    print(f"天気: {weather_desc}")
                elif "weather" in result:
                    print(f"天気: {result['weather']}")
                if "temperature" in result:
                    print(f"気温: {result['temperature']}℃")
                if "precipitation_prob" in result:
                    print(f"降水確率: {result['precipitation_prob']}%")
                
                # 警報・災害情報を表示
                if args.include_all:
                    if "alert" in result and result["alert"]:
                        print(f"警報: {', '.join(result['alert'])}")
                    if "disaster" in result and result["disaster"]:
                        print(f"災害情報: {', '.join(result['disaster'])}")
                
                # ランドマーク情報を表示
                if args.landmarks and "landmarks" in result:
                    landmarks_data = result["landmarks"]
                    print(f"\nランドマーク情報:")
                    
                    if isinstance(landmarks_data, str):
                        try:
                            landmarks_json = json.loads(landmarks_data)
                            if isinstance(landmarks_json, list):
                                for i, landmark in enumerate(landmarks_json, 1):
                                    if isinstance(landmark, dict):
                                        name = landmark.get("name", "不明")
                                        lat = landmark.get("latitude", "N/A")
                                        lon = landmark.get("longitude", "N/A")
                                        print(f"  {i}. {name} (緯度: {lat}, 経度: {lon})")
                                    else:
                                        print(f"  {i}. {landmark}")
                            else:
                                print(f"  データ: {landmarks_json}")
                        except json.JSONDecodeError:
                            print(f"  データ: {landmarks_data}")
                    else:
                        print(f"  データ: {landmarks_data}")
                    
                    # ランドマークの総数とページング情報
                    if "landmarks_total" in result:
                        print(f"  総数: {result['landmarks_total']}")
                    if "landmarks_offset" in result:
                        print(f"  オフセット: {result['landmarks_offset']}")
                        
                print("-" * 40)
        else:
            if args.json:
                print('{"error": "データの取得に失敗しました"}')
            else:
                print("\n✗ データの取得に失敗しました")

    except Exception as e:
        if args.json:
            print(f'{{"error": "エラーが発生しました: {str(e)}"}}')
        else:
            print(f"\n✗ エラーが発生しました: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
    finally:
        client.close()

    if not args.json:
        print("=" * 60)


if __name__ == "__main__":
    main()
