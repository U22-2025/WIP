"""
Weather Client - 改良版（専用パケットクラス使用）
Weather Serverプロキシと通信するクライアント
"""

import socket
import time
from datetime import datetime
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from common.packet import WeatherRequest, WeatherResponse
from common.clients.utils.packet_id_generator import PacketIDGenerator12Bit

PIDG = PacketIDGenerator12Bit()


class WeatherClient:
    """Weather Serverと通信するクライアント（専用パケットクラス使用）"""
    
    def __init__(self, host='localhost', port=4110, debug=False):
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
        self.VERSION = 1
        
    def _hex_dump(self, data):
        """バイナリデータのhexダンプを作成"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
        
    def _debug_print_request(self, request, request_type):
        """リクエストのデバッグ情報を出力（改良版）"""
        if not self.debug:
            return
            
        print("\n=== SENDING REQUEST PACKET ===")
        print(f"Request Type: {request_type}")
        print(f"Total Length: {len(request.to_bytes())} bytes")
        
        # 専用クラスのサマリー情報を使用
        if hasattr(request, 'get_request_summary'):
            summary = request.get_request_summary()
            print(f"\nRequest Summary: {summary}")
        
        print("\nHeader:")
        print(f"Version: {request.version}")
        print(f"Type: {request.type}")
        print(f"Packet ID: {request.packet_id}")
        print(f"Timestamp: {time.ctime(request.timestamp)}")
        
        if request.type == 0:
            # 座標解決リクエスト
            if hasattr(request, 'ex_field') and request.ex_field:
                print(f"Latitude: {request.ex_field.get('latitude')}")
                print(f"Longitude: {request.ex_field.get('longitude')}")
        elif request.type == 2:
            # 気象データリクエスト
            print(f"Area Code: {request.area_code}")
            print("\nFlags:")
            print(f"Weather: {request.weather_flag}")
            print(f"Temperature: {request.temperature_flag}")
            print(f"PoPs: {request.pops_flag}")
            print(f"Alert: {request.alert_flag}")
            print(f"Disaster: {request.disaster_flag}")
            
        print("\nRaw Packet:")
        print(self._hex_dump(request.to_bytes()))
        print("============================\n")
        
    def _debug_print_response(self, response):
        """レスポンスのデバッグ情報を出力（改良版）"""
        if not self.debug:
            return
            
        print("\n=== RECEIVED RESPONSE PACKET ===")
        print(f"Response Type: {response.type}")
        print(f"Total Length: {len(response.to_bytes())} bytes")
        
        # 専用クラスのメソッドを使用
        if hasattr(response, 'get_weather_data'):
            weather_data = response.get_weather_data()
            print(f"\nWeather Data: {weather_data}")
            print(f"Success: {response.is_success()}")
        
        print("\nHeader:")
        print(f"Version: {response.version}")
        print(f"Type: {response.type}")
        print(f"Area Code: {response.area_code}")
        print(f"Packet ID: {response.packet_id}")
        print(f"Timestamp: {time.ctime(response.timestamp)}")
        
        if response.type == 3:
            # 気象データレスポンス（専用メソッド使用）
            if hasattr(response, 'get_weather_code'):
                weather_code = response.get_weather_code()
                if weather_code is not None:
                    print(f"\nWeather Code: {weather_code}")
            
            if hasattr(response, 'get_temperature_celsius'):
                temp = response.get_temperature_celsius()
                if temp is not None:
                    print(f"Temperature: {temp}℃")
            
            if hasattr(response, 'get_precipitation_percentage'):
                pops = response.get_precipitation_percentage()
                if pops is not None:
                    print(f"Precipitation: {pops}%")
                    
            if hasattr(response, 'get_alerts'):
                alerts = response.get_alerts()
                if alerts:
                    print(f"Alerts: {alerts}")
                    
            if hasattr(response, 'get_disaster_info'):
                disaster = response.get_disaster_info()
                if disaster:
                    print(f"Disaster Info: {disaster}")
            
        print("\nRaw Packet:")
        print(self._hex_dump(response.to_bytes()))
        print("==============================\n")
        
    def get_weather_by_coordinates(self, latitude, longitude, 
                                  weather=True, temperature=True, 
                                  precipitation=True, alerts=False, disaster=False,
                                  day=0):
        """
        座標から天気情報を取得（Type 0 → Type 3）
        
        Args:
            latitude: 緯度
            longitude: 経度
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation: 降水確率データを取得するか
            alerts: 警報データを取得するか
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
                packet_id=PIDG.next_id(),
                weather=weather,
                temperature=temperature,
                precipitation=precipitation,
                alerts=alerts,
                disaster=disaster,
                day=day,
                version=self.VERSION
            )
            
            self._debug_print_request(request, "Location Resolution (Type 0)")
            
            # リクエスト送信
            self.sock.sendto(request.to_bytes(), (self.host, self.port))
            
            # Type 3: 気象データレスポンスを受信（専用クラス使用）
            response_data, addr = self.sock.recvfrom(1024)
            response = WeatherResponse.from_bytes(response_data)
            
            self._debug_print_response(response)
            
            # 専用クラスのメソッドで結果を簡単に取得
            if response.is_success():
                result = response.get_weather_data()
                
                total_time = time.time() - start_time
                if self.debug:
                    print("\n=== TIMING INFORMATION ===")
                    print(f"Total operation time: {total_time*1000:.2f}ms")
                    print("========================\n")
                
                return result
            else:
                if self.debug:
                    print("Response indicates failure")
                return None
            
        except socket.timeout:
            print("Timeout waiting for response")
            return None
        except Exception as e:
            print(f"Error: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None
        
    def get_weather_by_area_code(self, area_code, 
                                weather=True, temperature=True, 
                                precipitation=True, alerts=False, disaster=False,
                                day=0):
        """
        エリアコードから天気情報を取得（Type 2 → Type 3）
        
        Args:
            area_code: エリアコード（文字列または数値、例: "011000" または 11000）
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation: 降水確率データを取得するか
            alerts: 警報データを取得するか
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
                packet_id=PIDG.next_id(),
                weather=weather,
                temperature=temperature,
                precipitation=precipitation,
                alerts=alerts,
                disaster=disaster,
                day=day,
                version=self.VERSION
            )
            
            self._debug_print_request(request, "Weather Data (Type 2)")
            
            # リクエスト送信
            self.sock.sendto(request.to_bytes(), (self.host, self.port))
            
            # Type 3: 気象データレスポンスを受信（専用クラス使用）
            response_data, addr = self.sock.recvfrom(1024)
            response = WeatherResponse.from_bytes(response_data)
            
            self._debug_print_response(response)
            
            # 専用クラスのメソッドで結果を簡単に取得
            if response.is_success():
                result = response.get_weather_data()
                
                total_time = time.time() - start_time
                if self.debug:
                    print("\n=== TIMING INFORMATION ===")
                    print(f"Total operation time: {total_time*1000:.2f}ms")
                    print("========================\n")
                
                return result
            else:
                if self.debug:
                    print("Response indicates failure")
                return None
            
        except socket.timeout:
            print("Timeout waiting for response")
            return None
        except Exception as e:
            print(f"Error: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return None
        
    def close(self):
        """ソケットを閉じる"""
        self.sock.close()


def main():
    """メイン関数 - 使用例（専用パケットクラス版）"""
    print("Weather Client Example (Enhanced with Specialized Packet Classes)")
    print("=" * 70)
    
    client = WeatherClient(debug=True)
    
    try:
        # 例1: 座標から天気情報を取得
        print("\n1. Getting weather by coordinates (Tokyo)")
        print("-" * 30)
        
        result = client.get_weather_by_coordinates(
            latitude=35.6895,
            longitude=139.6917,
            weather=True,
            temperature=True,
            precipitation=True
        )
        
        if result:
            print("\n✓ Success!")
            print(f"Area Code: {result.get('area_code')}")
            print(f"Timestamp: {time.ctime(result.get('timestamp', 0))}")
            if 'weather_code' in result:
                print(f"Weather Code: {result['weather_code']}")
            if 'temperature' in result:
                print(f"Temperature: {result['temperature']}°C")
            if 'precipitation' in result:
                print(f"Precipitation: {result['precipitation']}%")
        else:
            print("\n✗ Failed to get weather data")
        
        # 例2: エリアコードから天気情報を取得
        print("\n\n2. Getting weather by area code (Sapporo: 011000)")
        print("-" * 30)
        
        result = client.get_weather_by_area_code(
            area_code="011000",
            weather=True,
            temperature=True,
            precipitation=True,
            alerts=True,
            disaster=True
        )
        
        if result:
            print("\n✓ Success!")
            print(f"Area Code: {result.get('area_code')}")
            print(f"Timestamp: {time.ctime(result.get('timestamp', 0))}")
            if 'weather_code' in result:
                print(f"Weather Code: {result['weather_code']}")
            if 'temperature' in result:
                print(f"Temperature: {result['temperature']}°C")
            if 'precipitation' in result:
                print(f"Precipitation: {result['precipitation']}%")
            if 'alerts' in result:
                print(f"Alerts: {result['alerts']}")
            if 'disaster' in result:
                print(f"Disaster Info: {result['disaster']}")
        else:
            print("\n✗ Failed to get weather data")
            
    finally:
        client.close()
        
    print("\n" + "="*70)
    print("Enhanced Weather Client Example completed")
    print("✓ Using specialized packet classes for improved usability")


if __name__ == "__main__":
    main()
