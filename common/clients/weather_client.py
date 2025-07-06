"""
Weather Client - 改良版（専用パケットクラス使用）
Weather Serverプロキシと通信するクライアント
"""

import socket
import time
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Union
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from common.packet import LocationRequest, LocationResponse, QueryRequest, QueryResponse, ErrorResponse
from common.clients.utils.packet_id_generator import PacketIDGenerator12Bit
import traceback
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
        self.VERSION = 1
        self.PIDG = PacketIDGenerator12Bit()
        
    def _hex_dump(self, data):
        """バイナリデータのhexダンプを作成"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
        
    def _debug_print_request(self, request, request_type):
        """リクエストのデバッグ情報を出力（改良版）"""
        if request.type == 0:
            coords = request.get_coordinates() if hasattr(request, 'get_coordinates') else None
            self.logger.debug(f"Sending location request: {coords}")
        elif request.type == 2:
            self.logger.debug(f"Sending query request: area_code={request.area_code}")
        
    def _debug_print_response(self, response):
        """レスポンスのデバッグ情報を出力（改良版）"""
        if response.type == 3:
            success = response.is_success() if hasattr(response, 'is_success') else False
            self.logger.debug(f"Received weather response: success={success}")
        elif response.type == 1:
            area_code = response.get_area_code() if hasattr(response, 'get_area_code') else None
            self.logger.debug(f"Received location response: area_code={area_code}")
        else:
            self.logger.debug(f"Received response: type={response.type}")
        
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
            
            self._debug_print_request(request, "Weather Data (Type 2)")
            
            # リクエスト送信とレスポンス受信
            network_start = time.time()
            self.sock.sendto(request.to_bytes(), (self.host, self.port))
            response_data, addr = self.sock.recvfrom(1024)
            network_time = time.time() - network_start
            
            # パケットタイプに基づいて適切なレスポンスクラスを選択
            response_type = int.from_bytes(response_data[2:3], byteorder='little') & 0x07
            
            if response_type == 3:  # 天気レスポンス
                response = QueryResponse.from_bytes(response_data)
                self._debug_print_response(response)
                
                if response.is_success():
                    result = response.get_weather_data()
                    
                    total_time = time.time() - start_time
                    if self.debug:
                        self.logger.debug(f"Weather query timing: network={network_time*1000:.1f}ms, total={total_time*1000:.1f}ms")
                    
                    return result
                else:
                    if self.debug:
                        self.logger.error("420: クライアントエラー: クエリサーバが見つからない")
                    return None
                    
            elif response_type == 7:  # エラーレスポンス
                response = ErrorResponse.from_bytes(response_data)
                if self.debug:
                    self.logger.error(f"Error response: {response.error_code}")
                
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
            
            self._debug_print_request(request, "Location Resolution (Type 0)")
            
            # リクエスト送信とレスポンス受信
            network_start = time.time()
            self.sock.sendto(request.to_bytes(), (self.host, self.port))
            response_data, addr = self.sock.recvfrom(1024)
            network_time = time.time() - network_start
            
            # パケットタイプに基づいて適切なレスポンスクラスを選択
            response_type = int.from_bytes(response_data[2:3], byteorder='little') & 0x07
            
            if response_type == 1:  # Location レスポンス
                response = LocationResponse.from_bytes(response_data)
                self._debug_print_response(response)
                
                # LocationResponseからQueryRequestを作成
                query_request = QueryRequest.from_location_response(response)
                
                # QueryRequestを実行
                return self._execute_query_request(query_request)
                    
            elif response_type == 3:  # 天気レスポンス（直接応答）
                response = QueryResponse.from_bytes(response_data)
                self._debug_print_response(response)
                
                if response.is_success():
                    result = response.get_weather_data()
                    
                    total_time = time.time() - start_time
                    if self.debug:
                        self.logger.debug(f"Location query timing: network={network_time*1000:.1f}ms, total={total_time*1000:.1f}ms")
                    
                    return result
                else:
                    if self.debug:
                        self.logger.error("420: クライアントエラー: クエリサーバが見つからない")
                    return None
                    
            elif response_type == 7:  # エラーレスポンス
                response = ErrorResponse.from_bytes(response_data)
                if self.debug:
                    self.logger.error(f"Error response: {response.error_code}")
                
                return {
                    'type': 'error',
                    'error_code': response.error_code,
                }
            else:
                if self.debug:
                    self.logger.error(f"不明なパケットタイプ: {response_type}")
                return None
            
        except socket.timeout:
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
            logger.info("\n✓ Success!")
            logger.info(f"Area Code: {result.get('area_code')}")
            logger.info(f"Timestamp: {time.ctime(result.get('timestamp', 0))}")
            if 'weather_code' in result:
                logger.info(f"Weather Code: {result['weather_code']}")
            if 'temperature' in result:
                logger.info(f"Temperature: {result['temperature']}°C")
            if 'precipitation_prob' in result:
                logger.info(f"precipitation_prob: {result['precipitation_prob']}%")
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
            logger.info("\n✓ Success!")
            logger.info(f"Area Code: {result.get('area_code')}")
            logger.info(f"Timestamp: {time.ctime(result.get('timestamp', 0))}")
            if 'weather_code' in result:
                logger.info(f"Weather Code: {result['weather_code']}")
            if 'temperature' in result:
                logger.info(f"Temperature: {result['temperature']}°C")
            if 'precipitation_prob' in result:
                logger.info(f"precipitation_prob: {result['precipitation_prob']}%")
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
            logger.info("\n✓ Success!")
            logger.info(f"Area Code: {result.get('area_code')}")
            logger.info(f"Timestamp: {time.ctime(result.get('timestamp', 0))}")
            if 'weather_code' in result:
                logger.info(f"Weather Code: {result['weather_code']}")
            if 'temperature' in result:
                logger.info(f"Temperature: {result['temperature']}°C")
            if 'precipitation_prob' in result:
                logger.info(f"precipitation_prob: {result['precipitation_prob']}%")
            if 'alert' in result:
                logger.info(f"Alert: {result['alert']}")
            if 'disaster' in result:
                logger.info(f"Disaster Info: {result['disaster']}")
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
            logger.info("\n✓ Success!")
            logger.info(f"Area Code: {result.get('area_code')}")
            logger.info(f"Timestamp: {time.ctime(result.get('timestamp', 0))}")
            if 'weather_code' in result:
                logger.info(f"Weather Code: {result['weather_code']}")
            if 'temperature' in result:
                logger.info(f"Temperature: {result['temperature']}°C")
            if 'precipitation_prob' in result:
                logger.info(f"precipitation_prob: {result['precipitation_prob']}%")
            if 'alert' in result:
                logger.info(f"Alert: {result['alert']}")
            if 'disaster' in result:
                logger.info(f"Disaster Info: {result['disaster']}")
        else:
            logger.error("\n✗ Failed to get weather data")
            
    finally:
        client.close()
        
    logger.info("\n" + "="*70)
    logger.info("Enhanced Weather Client Example completed")
    logger.info("✓ Using specialized packet classes for improved usability")


if __name__ == "__main__":
    main()
