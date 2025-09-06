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
            day: 予報日（0: 今日, 1: 明日, ...）

        Returns:
            dict: 気象データ
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

    def get_weather_simple(self, area_code, include_all=False, day=0):
        """
        基本的な気象データを一括取得する簡便メソッド（統一命名規則版）

        Args:
            area_code: エリアコード
            include_all: すべてのデータを取得するか（警報・災害情報も含む）
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


def main():
    """メイン関数 - 使用例（専用パケットクラス版）"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Weather Client Example (Enhanced with Specialized Packet Classes)")
    logger.info("=" * 70)

    client = WeatherClient(debug=True)

    try:
        # 例1: 座標から天気情報を取得（従来の方法）
        logger.info("\n1. Getting weather by coordinates (Tokyo) - Traditional method")
        logger.info("-" * 55)

        request = LocationRequest.create_coordinate_lookup(
            latitude=35.6895,
            longitude=139.6917,
            packet_id=client.PIDG.next_id(),
            weather=True,
            temperature=True,
            precipitation_prob=True,
            version=client.VERSION,
        )
        result = client._execute_location_request(request=request)

        if result:
            client.debug_logger.log_success_result(result, "COORDINATE WEATHER REQUEST")
        else:
            logger.error("\n✗ Failed to get weather data")

        # 例2: LocationRequestインスタンスを使用する方法
        logger.info("\n2. Getting weather with LocationRequest instance")
        logger.info("-" * 45)

        # LocationRequestインスタンスを事前作成
        location_request = LocationRequest.create_coordinate_lookup(
            latitude=35.6895,
            longitude=139.6917,
            packet_id=client.PIDG.next_id(),
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=True,
            disaster=True,
            version=client.VERSION,
        )

        # インスタンスを使用して実行
        result = client._execute_location_request(location_request)

        if result:
            client.debug_logger.log_success_result(result, "LOCATION REQUEST INSTANCE")
        else:
            logger.error("\n✗ Failed to get weather data")

        # 例3: QueryRequestインスタンスを使用する方法
        logger.info("\n3. Getting weather with QueryRequest instance")
        logger.info("-" * 45)

        # QueryRequestインスタンスを事前作成
        query_request = QueryRequest.create_query_request(
            area_code="011000",
            packet_id=client.PIDG.next_id(),
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=True,
            disaster=True,
            version=client.VERSION,
        )

        # インスタンスを使用して実行
        result = client._execute_query_request(query_request)

        if result:
            client.debug_logger.log_success_result(result, "QUERY REQUEST INSTANCE")
        else:
            logger.error("\n✗ Failed to get weather data")

        # 例4: 従来の方法でエリアコードから天気情報を取得
        logger.info("\n4. Getting weather by area code - Traditional method")
        logger.info("-" * 55)

        result = client.get_weather_data(
            area_code="011000",
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=True,
            disaster=True,
        )

        if result:
            client.debug_logger.log_success_result(result, "AREA CODE WEATHER REQUEST")
        else:
            logger.error("\n✗ Failed to get weather data")

    finally:
        client.close()

    logger.info("\n" + "=" * 70)
    logger.info("Enhanced Weather Client Example completed")
    logger.info("✓ Using specialized packet classes for improved usability")


