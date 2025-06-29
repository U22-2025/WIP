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
from common.packet import WeatherRequest, WeatherResponse, ErrorResponse, LocationResponse
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
        self.VERSION = 1
        self.PIDG = PacketIDGenerator12Bit()
        
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
            print(f"pop: {request.pop_flag}")
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
        
        if response.type == 1:
            # 座標解決レスポンス
            print(f"\nArea Code: {response.area_code}")
            print(f"Location Name: {response.location_name}")
            print(f"Success: {response.is_valid()}")
            
        elif response.type == 3:
            # 気象データレスポンス（専用メソッド使用）
            if hasattr(response, 'get_weather_code'):
                weather_code = response.get_weather_code()
                if weather_code is not None:
                    print(f"\nWeather Code: {weather_code}")
            
            if hasattr(response, 'get_temperature_celsius'):
                temp = response.get_temperature_celsius()
                if temp is not None:
                    print(f"Temperature: {temp}℃")
            
            if hasattr(response, 'get_precipitation_prob'):
                pop = response.get_precipitation_prob()
                if pop is not None:
                    print(f"precipitation_prob: {pop}%")
                    
            if hasattr(response, 'get_alert'):
                alert = response.get_alert()
                if alert:
                    print(f"Alert: {alert}")
                    
            if hasattr(response, 'get_disaster_info'):
                disaster = response.get_disaster_info()
                if disaster:
                    print(f"Disaster Info: {disaster}")
            
        print("\nRaw Packet:")
        print(self._hex_dump(response.to_bytes()))
        print("==============================\n")
        
    def get_weather_by_coordinates(self, latitude, longitude,
                                  weather=True, temperature=True,
                                  precipitation_prob=True, alert=False, disaster=False,
                                  day=0):
        """
        座標から天気情報を取得（Type 0 → Type 1 → Type 3）
        
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
            
            # パケットタイプの解析とバリデーション
            if len(response_data) < 2:
                if self.debug:
                    print("422: クライアントエラー: パケットサイズ不足")
                return None
                
            try:
                # パケットサイズチェック (最小3バイト必要)
                if len(response_data) < 3:
                    if self.debug:
                        print("422: クライアントエラー: パケットサイズ不足 (typeフィールド取得不可)")
                    return None
                    
                # リトルエンディアンで3バイト目の下位3ビットからタイプを抽出 (ビット17-19)
                response_type = (response_data[2] & 0x07)  # 下位3ビット
                
                if self.debug:
                    # 生のパケットデータをバイナリ形式で出力
                    print(f"Full packet data (binary): {''.join(f'{b:08b}' for b in response_data[:4])}")
                    print(f"Byte[2] (binary): {response_data[2]:08b}")
                    print(f"Extracted type: {response_type:03b} (binary)")
                    print(f"Expected position: bits 16-18 (little endian) - should be lower 3 bits of byte[2]")
                if self.debug:
                    print(f"Detected packet type: {response_type} (Hex: {response_data[1:2].hex()})")
                    print(f"Full packet header: {response_data[:4].hex()}")
                    
                if response_type == 1:  # 座標解決レスポンス
                    response = LocationResponse.from_bytes(response_data)
                    self._debug_print_response(response)
                    
                    if response.is_valid():
                        # タイプ2リクエストを自動送信
                        return self.get_weather_by_area_code(
                            area_code=response.area_code,
                            weather=weather,
                            temperature=temperature,
                            precipitation_prob=precipitation_prob,
                            alert=alert,
                            disaster=disaster,
                            day=day
                        )
                    if self.debug:
                        print("422: クライアントエラー: 無効な座標解決レスポンス")
                    return None
                        
                elif response_type == 3:  # 天気レスポンス
                    response = WeatherResponse.from_bytes(response_data)
                    self._debug_print_response(response)
                    
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
                            print("420: クライアントエラー: クエリサーバが見つからない")
                        return None
                        
                elif response_type == 7:  # エラーレスポンス
                    return self._handle_error_response(response_data)
                    
                else:
                    if self.debug:
                        print(f"不明なパケットタイプ: {response_type}")
                        print("Raw Data:", self._hex_dump(response_data))
                    return None
                    
            except ValueError as e:
                if self.debug:
                    print(f"パケット解析エラー (ValueError): {str(e)}")
                    print("Raw Data:", self._hex_dump(response_data))
                return None
            except Exception as e:
                if self.debug:
                    print(f"予期せぬパケット解析エラー: {str(e)}")
                    traceback.print_exc()
                return None
            
        except socket.timeout as e:
            print(f"421: クライアントエラー: クエリサーバ接続タイムアウト - {e}")
            if self.debug:
                traceback.print_exc()
            return None
        except Exception as e:
            print(f"420: クライアントエラー: クエリサーバが見つからない - {e}")
            if self.debug:
                traceback.print_exc()
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
            
            # パケットタイプに基づいて適切なレスポンスクラスを選択 (little endianに統一)
            # パケットサイズチェック (最小3バイト必要)
            if len(response_data) < 3:
                if self.debug:
                    print("422: クライアントエラー: パケットサイズ不足 (typeフィールド取得不可)")
                return None
                
            # パケットタイプを正しく判定 (3バイト目の上位3ビット(5-7ビット)から抽出)
            if len(response_data) < 3:
                if self.debug:
                    print("422: クライアントエラー: パケットサイズ不足 (typeフィールド取得不可)")
                return None
             
            # ビッグエンディアンで先頭バイトからタイプを抽出 (ビット5-7)
            response_type = (response_data[2] & 0x07)  # 上位3ビット
             
            if self.debug:
                # 生のパケットデータをバイナリ形式で出力
                print(f"Full packet data (binary): {''.join(f'{b:08b}' for b in response_data[:4])}")
                print(f"Byte[2] (binary): {response_data[2]:08b}")
                print(f"Extracted type: {response_type:03b} (binary)")
                print(f"Expected position: bits 16-18 (little endian) - should be lower 3 bits of byte[2]")
            
            if response_type == 3:  # 天気レスポンス
                response = WeatherResponse.from_bytes(response_data)
                self._debug_print_response(response)
                
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
                        print("420: クライアントエラー: クエリサーバが見つからない")
                    return None
                    
            elif response_type == 7:  # エラーレスポンス
                return self._handle_error_response(response_data)
            else:
                if self.debug:
                    print(f"不明なパケットタイプ: {response_type}")
                return None
            
        except socket.timeout:
            print("421: クライアントエラー:  クエリサーバ接続タイムアウト")
            return None
        except Exception as e:
            print(f"420: クライアントエラー: クエリサーバが見つからない - {e}")
            if self.debug:
                traceback.print_exc()
            return None
        
    def _handle_error_response(self, response_data):
        """エラーレスポンスを処理するヘルパー関数
        
        Args:
            response_data: 受信した生のレスポンスデータ
            
        Returns:
            dict: エラー情報を含む辞書
        """
        # 基本的なエラーレスポンス構造
        error_response = {
            'type': 'error',
            'error_code': 500,
            'packet_id': 0,
            'message': 'Unknown error',
            'raw_data': self._hex_dump(response_data) if self.debug else None
        }

        # 基本的なパケットバリデーション
        if len(response_data) < 3:  # 最小ヘッダサイズチェック (typeフィールドまで)
            if self.debug:
                print(f"422: クライアントエラー: パケットサイズ不足 ({len(response_data)} bytes)")
            error_response.update({
                'error_code': 422,
                'message': 'Invalid packet size'
            })
            return error_response
            
        if self.debug:
            print("\n=== RAW ERROR PACKET ===")
            print(self._hex_dump(response_data))
            print("======================")
            
        # packet_idを抽出 (失敗時は0を使用)
        try:
            packet_id = int.from_bytes(response_data[0:2], byteorder='little', signed=False)
            if not (0 <= packet_id <= 0xFFF):  # 12-bit範囲チェック
                if self.debug:
                    print(f"422: 無効なpacket_id: {packet_id}, デフォルト値0を使用")
                packet_id = 0
            error_response['packet_id'] = packet_id
        except Exception as e:
            if self.debug:
                print(f"packet_id抽出エラー: {str(e)}, デフォルト値0を使用")

        # エラーコードを抽出 (3バイト目のビット3-7)
        try:
            error_code = (response_data[2] & 0xF8) >> 3  # ビット3-7を抽出
            error_response['error_code'] = error_code
        except Exception as e:
            if self.debug:
                print(f"error_code抽出エラー: {str(e)}")

        # 可能ならErrorResponseクラスで解析を試みる
        try:
            response = ErrorResponse.from_bytes(response_data)
            error_response.update({
                'error_code': response.error_code,
                'message': getattr(response, 'message', 'Unknown error')
            })
        except Exception as e:
            if self.debug:
                print("\n=== ERROR PACKET DECODE FAILED ===")
                print(f"Error: {str(e)}")
                print("===============================\n")
            error_response['message'] = f"Invalid error packet: {str(e)}"

        if self.debug:
            print("\n=== FINAL ERROR RESPONSE ===")
            print(f"Error Code: {error_response['error_code']}")
            print(f"Packet ID: {error_response['packet_id']}")
            print(f"Message: {error_response['message']}")
            print("===========================\n")
            
        return error_response

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
            precipitation_prob=True
        )
        
        if result:
            print("\n✓ Success!")
            print(f"Area Code: {result.get('area_code')}")
            print(f"Timestamp: {time.ctime(result.get('timestamp', 0))}")
            if 'weather_code' in result:
                print(f"Weather Code: {result['weather_code']}")
            if 'temperature' in result:
                print(f"Temperature: {result['temperature']}°C")
            if 'precipitation_prob' in result:
                print(f"precipitation_prob: {result['precipitation_prob']}%")
        else:
            print("\n✗ Failed to get weather data")
        
        # 例2: エリアコードから天気情報を取得
        print("\n\n2. Getting weather by area code (Sapporo: 011000)")
        print("-" * 30)
        
        result = client.get_weather_by_area_code(
            area_code="011000",
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=True,
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
            if 'precipitation_prob' in result:
                print(f"precipitation_prob: {result['precipitation_prob']}%")
            if 'alert' in result:
                print(f"Alert: {result['alert']}")
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
