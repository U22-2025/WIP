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
from common.packet import LocationRequest, LocationResponse, QueryRequest, QueryResponse, ErrorResponse
from common.packet.debug import create_debug_logger
from common.clients.utils.packet_id_generator import PacketIDGenerator12Bit
from common.clients.utils import receive_with_id, receive_with_id_async
PIDG = PacketIDGenerator12Bit()


class WeatherClient:
    """Weather Serverと通信するクライアント（専用パケットクラス使用）"""

    def __init__(self, host=None, port=None, debug=False):
        if host is None:
            host = os.getenv('WEATHER_SERVER_HOST', 'localhost')
        if port is None:
            port = int(os.getenv('WEATHER_SERVER_PORT', '4110'))
        """
        初期化
        
        Args:
            host: Weather Serverのホスト
            port: Weather Serverのポート
            debug: デバッグモード
        """
        self.host = host
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
        
        
    def get_weather_data(self, area_code,
                        weather=True, temperature=True,
                        precipitation_prob=True, alert=False, disaster=False,
                        day=0):
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
            version=self.VERSION
        )
        
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
            response_type = int.from_bytes(response_data[2:3], byteorder='little') & 0x07
            
            if response_type == 3:  # 天気レスポンス
                response = QueryResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "WEATHER DATA RESPONSE")
                
                if response.is_success():
                    result = response.get_weather_data()
                    
                    # 統一フォーマットでの成功ログ出力
                    if result:
                        execution_time = time.time() - start_time
                        self.debug_logger.log_unified_packet_received("Direct request", execution_time, result)
                    
                    return result
                else:
                    if self.debug:
                        self.logger.error("420: クライアントエラー: クエリサーバが見つからない")
                    return None
                    
            elif response_type == 7:  # エラーレスポンス
                response = ErrorResponse.from_bytes(response_data)
                if self.debug:
                    self.logger.error("\n=== ERROR RESPONSE ===")
                    self.logger.error(f"Error Code: {response.error_code}")
                    self.logger.error("=====================\n")
                
                return {
                    'type': 'error',
                    'error_code': response.error_code,
                }
            else:
                if self.debug:
                    self.logger.error(f"不明なパケットタイプ: {response_type}")
                return None
            
        except socket.timeout:
            self.logger.error("421: クライアントエラー:  クエリサーバ接続タイムアウト")
            return None
        except Exception as e:
            self.logger.error(f"420: クライアントエラー: クエリサーバが見つからない - {e}")
            if self.debug:
                self.logger.exception("Traceback:")
            return None

    async def _execute_query_request_async(self, request: QueryRequest):
        """非同期版 _execute_query_request"""
        try:
            start_time = time.time()

            self.debug_logger.log_request(request, "WEATHER DATA REQUEST")

            loop = asyncio.get_running_loop()
            self.sock.setblocking(False)
            await loop.sock_sendto(self.sock, request.to_bytes(), (self.host, self.port))

            response_data, addr = await receive_with_id_async(self.sock, request.packet_id, 10.0)
            self.logger.debug(response_data)

            response_type = int.from_bytes(response_data[2:3], byteorder="little") & 0x07

            if response_type == 3:
                response = QueryResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "WEATHER DATA RESPONSE")

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
                        self.logger.error("420: クライアントエラー: クエリサーバが見つからない")
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
            self.logger.error("421: クライアントエラー:  クエリサーバ接続タイムアウト")
            return None
        except Exception as e:
            self.logger.error(f"420: クライアントエラー: クエリサーバが見つからない - {e}")
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
            response_type = int.from_bytes(response_data[2:3], byteorder='little') & 0x07
            self.logger.debug(response_data)
            
            if response_type == 1:  # Location レスポンス
                response = LocationResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "LOCATION RESPONSE")
                
                if self.debug:
                    self.logger.debug("LocationResponseを受信しました。weather_serverからの追加処理を待機します。")
                
                # weather_serverが座標解決後、直接query_serverにリクエストを送信し、
                # その結果をクライアントに返すため、ここでは追加のリクエストは送信しません。
                # 次のレスポンス（Type 3）を待機します。
                try:
                    # 次のレスポンス（天気データ）を受信
                    response_data, addr = self.sock.recvfrom(1024)
                    response_type = int.from_bytes(response_data[2:3], byteorder='little') & 0x07
                    
                    if response_type == 3:  # 天気レスポンス
                        query_response = QueryResponse.from_bytes(response_data)
                        self.debug_logger.log_response(query_response, "WEATHER RESPONSE")
                        
                        if query_response.is_success():
                            result = query_response.get_weather_data()
                            
                            # 統一フォーマットでの成功ログ出力
                            if result:
                                execution_time = time.time() - start_time
                                self.debug_logger.log_unified_packet_received("Direct request", execution_time, result)
                            
                            return result
                        else:
                            if self.debug:
                                self.logger.error("420: クライアントエラー: 天気データ取得に失敗しました")
                            return None
                    elif response_type == 7:  # エラーレスポンス
                        error_response = ErrorResponse.from_bytes(response_data)
                        if self.debug:
                            self.logger.error("\n=== ERROR RESPONSE ===")
                            self.logger.error(f"Error Code: {error_response.error_code}")
                            self.logger.error("=====================\n")
                        
                        return {
                            'type': 'error',
                            'error_code': error_response.error_code,
                        }
                    else:
                        if self.debug:
                            self.logger.error(f"不明なパケットタイプ: {response_type}")
                        return None
                        
                except socket.timeout:
                    self.logger.error("421: クライアントエラー: 天気データ受信タイムアウト")
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
            await loop.sock_sendto(self.sock, request.to_bytes(), (self.host, self.port))

            response_data, addr = await receive_with_id_async(self.sock, request.packet_id, 10.0)
            response_type = int.from_bytes(response_data[2:3], byteorder="little") & 0x07
            self.logger.debug(response_data)

            if response_type == 1:
                response = LocationResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "LOCATION RESPONSE")

                if self.debug:
                    self.logger.debug(
                        "LocationResponseを受信しました。weather_serverからの追加処理を待機します。"
                    )

                try:
                    response_data, addr = await receive_with_id_async(self.sock, response.packet_id, 10.0)
                    response_type = int.from_bytes(response_data[2:3], byteorder="little") & 0x07

                    if response_type == 3:
                        query_response = QueryResponse.from_bytes(response_data)
                        self.debug_logger.log_response(query_response, "WEATHER RESPONSE")

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
                                self.logger.error("420: クライアントエラー: 天気データ取得に失敗しました")
                            return None
                    elif response_type == 7:
                        error_response = ErrorResponse.from_bytes(response_data)
                        if self.debug:
                            self.logger.error("\n=== ERROR RESPONSE ===")
                            self.logger.error(f"Error Code: {error_response.error_code}")
                            self.logger.error("=====================\n")

                        return {"type": "error", "error_code": error_response.error_code}
                    else:
                        if self.debug:
                            self.logger.error(f"不明なパケットタイプ: {response_type}")
                        return None

                except asyncio.TimeoutError:
                    self.logger.error("421: クライアントエラー: 天気データ受信タイムアウト")
                    return None
                except Exception as e:
                    self.logger.error(f"420: クライアントエラー: 天気データ受信エラー - {e}")
                    if self.debug:
                        self.logger.exception("Traceback:")
                    return None

            elif response_type == 3:
                response = QueryResponse.from_bytes(response_data)
                self.debug_logger.log_response(response, "DIRECT WEATHER RESPONSE")

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
                        self.logger.error("420: クライアントエラー: クエリサーバが見つからない")
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
            self.logger.error(f"420: クライアントエラー: クエリサーバが見つからない - {e}")
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
            day=day
        )

    # 後方互換性のためのエイリアスメソッド
    def get_weather_by_area_code(self, area_code,
                                weather=True, temperature=True,
                                precipitation_prob=True, alert=False, disaster=False,
                                day=0):
        """後方互換性のため - get_weather_data()を使用してください"""
        return self.get_weather_data(area_code, weather, temperature, precipitation_prob, alert, disaster, day)
        
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
            version=client.VERSION
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
            version=client.VERSION
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
            version=client.VERSION
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
            disaster=True
        )
        
        if result:
            client.debug_logger.log_success_result(result, "AREA CODE WEATHER REQUEST")
        else:
            logger.error("\n✗ Failed to get weather data")
            
    finally:
        client.close()
        
    logger.info("\n" + "="*70)
    logger.info("Enhanced Weather Client Example completed")
    logger.info("✓ Using specialized packet classes for improved usability")


if __name__ == "__main__":
    main()
