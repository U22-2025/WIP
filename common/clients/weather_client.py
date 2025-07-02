"""
Weather Client - 改良版（専用パケットクラス使用）
Weather Serverプロキシと通信するクライアント
"""

import socket
import time
import logging
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from common.packet import WeatherRequest, WeatherResponse, ErrorResponse
from common.clients.utils.packet_id_generator import PacketIDGenerator12Bit
import traceback
PIDG = PacketIDGenerator12Bit()


class WeatherClient:
    """Weather Serverと通信するクライアント（専用パケットクラス使用）"""
    
    def __init__(self, host=os.getenv('WEATHER_SERVER_HOST'), port=int(os.getenv('WEATHER_SERVER_PORT')), debug=False):
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

        self.logger.debug("\n=== SENDING REQUEST PACKET ===")
        self.logger.debug(f"Request Type: {request_type}")
        self.logger.debug(f"Total Length: {len(request.to_bytes())} bytes")
        
        # 専用クラスのサマリー情報を使用
        if hasattr(request, 'get_request_summary'):
            summary = request.get_request_summary()
            self.logger.debug(f"\nRequest Summary: {summary}")
        
        self.logger.debug("\nHeader:")
        self.logger.debug(f"Version: {request.version}")
        self.logger.debug(f"Type: {request.type}")
        self.logger.debug(f"Packet ID: {request.packet_id}")
        self.logger.debug(f"Timestamp: {time.ctime(request.timestamp)}")
        
        if request.type == 0:
            # 座標解決リクエスト
            if hasattr(request, 'ex_field') and request.ex_field:
                self.logger.debug(f"Latitude: {request.ex_field.get('latitude')}")
                self.logger.debug(f"Longitude: {request.ex_field.get('longitude')}")
        elif request.type == 2:
            # 気象データリクエスト
            self.logger.debug(f"Area Code: {request.area_code}")
            self.logger.debug("\nFlags:")
            self.logger.debug(f"Weather: {request.weather_flag}")
            self.logger.debug(f"Temperature: {request.temperature_flag}")
            self.logger.debug(f"pop: {request.pop_flag}")
            self.logger.debug(f"Alert: {request.alert_flag}")
            self.logger.debug(f"Disaster: {request.disaster_flag}")
            
        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(request.to_bytes()))
        self.logger.debug("============================\n")
        
    def _debug_print_response(self, response):
        """レスポンスのデバッグ情報を出力（改良版）"""

        self.logger.debug("\n=== RECEIVED RESPONSE PACKET ===")
        self.logger.debug(f"Response Type: {response.type}")
        self.logger.debug(f"Total Length: {len(response.to_bytes())} bytes")
        
        # 専用クラスのメソッドを使用
        if hasattr(response, 'get_weather_data'):
            weather_data = response.get_weather_data()
            self.logger.debug(f"\nWeather Data: {weather_data}")
            self.logger.debug(f"Success: {response.is_success()}")
        
        self.logger.debug("\nHeader:")
        self.logger.debug(f"Version: {response.version}")
        self.logger.debug(f"Type: {response.type}")
        self.logger.debug(f"Area Code: {response.area_code}")
        self.logger.debug(f"Packet ID: {response.packet_id}")
        self.logger.debug(f"Timestamp: {time.ctime(response.timestamp)}")
        
        if response.type == 3:
            # 気象データレスポンス（専用メソッド使用）
            if hasattr(response, 'get_weather_code'):
                weather_code = response.get_weather_code()
                if weather_code is not None:
                    self.logger.debug(f"\nWeather Code: {weather_code}")
            
            if hasattr(response, 'get_temperature_celsius'):
                temp = response.get_temperature_celsius()
                if temp is not None:
                    self.logger.debug(f"Temperature: {temp}℃")
            
            if hasattr(response, 'get_precipitation_prob'):
                pop = response.get_precipitation_prob()
                if pop is not None:
                    self.logger.debug(f"precipitation_prob: {pop}%")
                    
            if hasattr(response, 'get_alert'):
                alert = response.get_alert()
                if alert:
                    self.logger.debug(f"Alert: {alert}")
                    
            if hasattr(response, 'get_disaster_info'):
                disaster = response.get_disaster_info()
                if disaster:
                    self.logger.debug(f"Disaster Info: {disaster}")
            
        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(response.to_bytes()))
        self.logger.debug("==============================\n")
        
    def get_weather_by_coordinates(self, latitude, longitude, 
                                  weather=True, temperature=True, 
                                  precipitation_prob=True, alert=False, disaster=False,
                                  day=0):
        """
        座標から天気情報を取得（Type 0 → Type 3）
        
        Args:
            latitude: 緯度
            longitude: 経度
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation_prob: 降水確率データを取得するか
            alert: 警報データを取得するか
            disaster: 災害情報データを取得するか
            day: 予報日（0: 今日, 1: 明日, ...）
            
        Returns:
            dict: 気象データ
        """
        try:
            start_time = time.time()
            
            # 専用クラスでリクエスト作成（大幅に簡潔になった）
            request = WeatherRequest.create_by_coordinates(
                latitude=latitude,
                longitude=longitude,
                packet_id=self.PIDG.next_id(),
                weather=weather,
                temperature=temperature,
                precipitation_prob=precipitation_prob,
                alert=alert,
                disaster=disaster,
                day=day,
                version=self.VERSION
            )
            
            self._debug_print_request(request, "Location Resolution (Type 0)")
            
            # リクエスト送信
            self.sock.sendto(request.to_bytes(), (self.host, self.port))
            
            # レスポンスを受信
            response_data, addr = self.sock.recvfrom(1024)
            
            # パケットタイプに基づいて適切なレスポンスクラスを選択
            response_type = int.from_bytes(response_data[2:3], byteorder='little') & 0x07
            self.logger.debug(response_data)
            
            if response_type == 3:  # 天気レスポンス
                response = WeatherResponse.from_bytes(response_data)
                self._debug_print_response(response)
                
                if response.is_success():
                    result = response.get_weather_data()
                    
                    total_time = time.time() - start_time
                    if self.debug:
                        self.logger.debug("\n=== TIMING INFORMATION ===")
                        self.logger.debug(f"Total operation time: {total_time*1000:.2f}ms")
                        self.logger.debug("========================\n")
                    
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
            self.logger.error("421: クライアントエラー: クエリサーバ接続タイムアウト")
            return None
        except Exception as e:
            self.logger.error(f"420: クライアントエラー: クエリサーバが見つからない - {e}")
            if self.debug:
                self.logger.exception("Traceback:")
            return None
        
    def get_weather_by_area_code(self, area_code, 
                                weather=True, temperature=True, 
                                precipitation_prob=True, alert=False, disaster=False,
                                day=0):
        """
        エリアコードから天気情報を取得（Type 2 → Type 3）
        
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
        try:
            start_time = time.time()
            
            # 専用クラスでリクエスト作成（大幅に簡潔になった）
            request = WeatherRequest.create_by_area_code(
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
            
            self._debug_print_request(request, "Weather Data (Type 2)")
            
            # リクエスト送信
            self.sock.sendto(request.to_bytes(), (self.host, self.port))
            
            # レスポンスを受信
            response_data, addr = self.sock.recvfrom(1024)
            self.logger.debug(response_data)
            
            # パケットタイプに基づいて適切なレスポンスクラスを選択
            response_type = int.from_bytes(response_data[2:3], byteorder='little') & 0x07
            
            if response_type == 3:  # 天気レスポンス
                response = WeatherResponse.from_bytes(response_data)
                self._debug_print_response(response)
                
                if response.is_success():
                    result = response.get_weather_data()
                    
                    total_time = time.time() - start_time
                    if self.debug:
                        self.logger.debug("\n=== TIMING INFORMATION ===")
                        self.logger.debug(f"Total operation time: {total_time*1000:.2f}ms")
                        self.logger.debug("========================\n")
                    
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
        # 例1: 座標から天気情報を取得
        logger.info("\n1. Getting weather by coordinates (Tokyo)")
        logger.info("-" * 30)
        
        result = client.get_weather_by_coordinates(
            latitude=35.6895,
            longitude=139.6917,
            weather=True,
            temperature=True,
            precipitation_prob=True
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
        else:
            logger.error("\n✗ Failed to get weather data")
        
        
        result = client.get_weather_by_area_code(
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
