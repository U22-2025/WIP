"""
Weather Client - 最新版
Weather Serverプロキシと通信するクライアント
"""

import socket
import time
import sys
import os
from datetime import datetime

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wtp.packet import Request, Response
from wtp.packet_id_12bit import PacketIDGenerator12Bit

PIDG = PacketIDGenerator12Bit()


class WeatherClient:
    """Weather Serverと通信するクライアント"""
    
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
        """リクエストのデバッグ情報を出力"""
        if not self.debug:
            return
            
        print("\n=== SENDING REQUEST PACKET ===")
        print(f"Request Type: {request_type}")
        print(f"Total Length: {len(request.to_bytes())} bytes")
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
        """レスポンスのデバッグ情報を出力"""
        if not self.debug:
            return
            
        print("\n=== RECEIVED RESPONSE PACKET ===")
        print(f"Response Type: {response.type}")
        print(f"Total Length: {len(response.to_bytes())} bytes")
        print("\nHeader:")
        print(f"Version: {response.version}")
        print(f"Type: {response.type}")
        print(f"Area Code: {response.area_code}")
        print(f"Packet ID: {response.packet_id}")
        print(f"Timestamp: {time.ctime(response.timestamp)}")
        
        if response.type == 3:
            # 気象データレスポンス
            if response.weather_flag and hasattr(response, 'weather_code'):
                print(f"\nWeather Code: {response.weather_code}")
            if response.temperature_flag and hasattr(response, 'temperature'):
                actual_temp = response.temperature - 100
                print(f"Temperature: {response.temperature} ({actual_temp}℃)")
            if response.pops_flag and hasattr(response, 'pops'):
                print(f"Precipitation: {response.pops}%")
                
        if hasattr(response, 'ex_field') and response.ex_field:
            print(f"\nExtended Field: {response.ex_field}")
            
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
            
            # Type 0: 座標解決リクエストを作成
            request = Request(
                version=self.VERSION,
                packet_id=PIDG.next_id(),
                type=0,  # 座標解決リクエスト
                timestamp=int(datetime.now().timestamp()),
                weather_flag=1 if weather else 0,
                temperature_flag=1 if temperature else 0,
                pops_flag=1 if precipitation else 0,
                alert_flag=1 if alerts else 0,
                disaster_flag=1 if disaster else 0,
                day=day,
                ex_field={
                    "latitude": latitude,
                    "longitude": longitude
                },
                ex_flag=1
            )
            
            self._debug_print_request(request, "Location Resolution (Type 0)")
            
            # リクエスト送信
            self.sock.sendto(request.to_bytes(), (self.host, self.port))
            
            # Type 3: 気象データレスポンスを受信
            response_data, addr = self.sock.recvfrom(1024)
            response = Response.from_bytes(response_data)
            
            self._debug_print_response(response)
            
            # 結果を整形
            result = {
                'area_code': response.area_code,
                'timestamp': response.timestamp,
                'type': response.type
            }
            
            if response.weather_flag and hasattr(response, 'weather_code'):
                result['weather_code'] = response.weather_code
            if response.temperature_flag and hasattr(response, 'temperature'):
                result['temperature'] = response.temperature - 100  # 実際の気温に変換
            if response.pops_flag and hasattr(response, 'pops'):
                result['precipitation'] = response.pops
                
            if hasattr(response, 'ex_field') and response.ex_field:
                if 'alert' in response.ex_field:
                    result['alerts'] = response.ex_field['alert']
                if 'disaster' in response.ex_field:
                    result['disaster'] = response.ex_field['disaster']
            
            total_time = time.time() - start_time
            
            if self.debug:
                print("\n=== TIMING INFORMATION ===")
                print(f"Total operation time: {total_time*1000:.2f}ms")
                print("========================\n")
            
            return result
            
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
            
            # エリアコードを6桁の文字列に正規化
            if isinstance(area_code, int):
                area_code_str = f"{area_code:06d}"
            else:
                area_code_str = str(area_code).zfill(6)
            
            # Type 2: 気象データリクエストを作成
            request = Request(
                version=self.VERSION,
                packet_id=PIDG.next_id(),
                type=2,  # 気象データリクエスト
                timestamp=int(datetime.now().timestamp()),
                area_code=area_code_str,
                weather_flag=1 if weather else 0,
                temperature_flag=1 if temperature else 0,
                pops_flag=1 if precipitation else 0,
                alert_flag=1 if alerts else 0,
                disaster_flag=1 if disaster else 0,
                day=day
            )
            
            self._debug_print_request(request, "Weather Data (Type 2)")
            
            # リクエスト送信
            self.sock.sendto(request.to_bytes(), (self.host, self.port))
            
            # Type 3: 気象データレスポンスを受信
            response_data, addr = self.sock.recvfrom(1024)
            response = Response.from_bytes(response_data)
            
            self._debug_print_response(response)
            
            # 結果を整形
            result = {
                'area_code': response.area_code,
                'timestamp': response.timestamp,
                'type': response.type
            }
            
            if response.weather_flag and hasattr(response, 'weather_code'):
                result['weather_code'] = response.weather_code
            if response.temperature_flag and hasattr(response, 'temperature'):
                result['temperature'] = response.temperature - 100  # 実際の気温に変換
            if response.pops_flag and hasattr(response, 'pops'):
                result['precipitation'] = response.pops
                
            if hasattr(response, 'ex_field') and response.ex_field:
                if 'alert' in response.ex_field:
                    result['alerts'] = response.ex_field['alert']
                if 'disaster' in response.ex_field:
                    result['disaster'] = response.ex_field['disaster']
            
            total_time = time.time() - start_time
            
            if self.debug:
                print("\n=== TIMING INFORMATION ===")
                print(f"Total operation time: {total_time*1000:.2f}ms")
                print("========================\n")
            
            return result
            
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
    """メイン関数 - 使用例"""
    print("Weather Client Example")
    print("=" * 50)
    
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
            print(f"Area Code: {result['area_code']}")
            print(f"Timestamp: {time.ctime(result['timestamp'])}")
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
            print(f"Area Code: {result['area_code']}")
            print(f"Timestamp: {time.ctime(result['timestamp'])}")
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
        
    print("\n" + "="*50)
    print("Example completed")


if __name__ == "__main__":
    main()
