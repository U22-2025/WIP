"""
Report Client - IoT機器データ収集専用クライアント
レポートリクエストを天気サーバー経由でレポートサーバーにセンサーデータを送信する
"""

import socket
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Union, List
from .report_packet import ReportRequest, ReportResponse
from .error_response import ErrorResponse
import traceback
import threading
import random


class PacketIDGenerator12Bit:
    """12ビットパケットIDジェネレーター（循環インポート回避のため内部実装）"""
    def __init__(self):
        self._lock = threading.Lock()
        self._current = random.randint(0, 4095)  # 0 - 4095
        self._max_id = 4096  # 2^12

    def next_id(self) -> int:
        with self._lock:
            pid = self._current
            self._current = (self._current + 1) % self._max_id
            return pid


class ReportClient:
    """IoT機器からのセンサーデータレポート送信用クライアント"""
    
    def __init__(self, host='localhost', port=4110, debug=False):
        """
        初期化
        
        Args:
            host: 天気サーバーのホスト（レポートを転送）
            port: 天気サーバーのポート
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
        
        # 収集データをメンバ変数として保持
        self.area_code: Optional[Union[str, int]] = None
        self.weather_code: Optional[int] = None
        self.temperature: Optional[float] = None
        self.precipitation_prob: Optional[int] = None
        self.alert: Optional[List[str]] = None
        self.disaster: Optional[List[str]] = None
        
    def set_sensor_data(self, area_code: Union[str, int],
                       weather_code: Optional[int] = None,
                       temperature: Optional[float] = None,
                       precipitation_prob: Optional[int] = None,
                       alert: Optional[List[str]] = None,
                       disaster: Optional[List[str]] = None):
        """
        センサーデータを設定
        
        Args:
            area_code: エリアコード
            weather_code: 天気コード
            temperature: 気温（摂氏）
            precipitation_prob: 降水確率（0-100%）
            alert: 警報情報
            disaster: 災害情報
        """
        self.area_code = area_code
        self.weather_code = weather_code
        self.temperature = temperature
        self.precipitation_prob = precipitation_prob
        self.alert = alert
        self.disaster = disaster
        
        if self.debug:
            self.logger.debug(f"センサーデータを設定: エリア={area_code}, 天気={weather_code}, "
                            f"気温={temperature}℃, 降水確率={precipitation_prob}%")
    
    def set_area_code(self, area_code: Union[str, int]):
        """エリアコードを設定"""
        self.area_code = area_code
        
    def set_weather_code(self, weather_code: int):
        """天気コードを設定"""
        self.weather_code = weather_code
        
    def set_temperature(self, temperature: float):
        """気温を設定（摂氏）"""
        self.temperature = temperature
        
    def set_precipitation_prob(self, precipitation_prob: int):
        """降水確率を設定（0-100%）"""
        self.precipitation_prob = precipitation_prob
        
    def set_alert(self, alert: List[str]):
        """警報情報を設定"""
        self.alert = alert
        
    def set_disaster(self, disaster: List[str]):
        """災害情報を設定"""
        self.disaster = disaster
        
        
    def _hex_dump(self, data):
        """バイナリデータのhexダンプを作成"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
        
    def _debug_print_request(self, request):
        """リクエストのデバッグ情報を出力"""
        if not self.debug:
            return
            
        self.logger.debug("\n=== SENDING REPORT REQUEST PACKET ===")
        self.logger.debug(f"Request Type: Report Data (Type 4)")
        self.logger.debug(f"Total Length: {len(request.to_bytes())} bytes")
        
        self.logger.debug("\nHeader:")
        self.logger.debug(f"Version: {request.version}")
        self.logger.debug(f"Type: {request.type}")
        self.logger.debug(f"Packet ID: {request.packet_id}")
        self.logger.debug(f"Timestamp: {time.ctime(request.timestamp)}")
        self.logger.debug(f"Area Code: {request.area_code}")
        
        self.logger.debug("\nFlags:")
        self.logger.debug(f"Weather: {request.weather_flag}")
        self.logger.debug(f"Temperature: {request.temperature_flag}")
        self.logger.debug(f"POP: {request.pop_flag}")
        self.logger.debug(f"Alert: {request.alert_flag}")
        self.logger.debug(f"Disaster: {request.disaster_flag}")
        
        self.logger.debug("\nSensor Data:")
        if request.weather_flag and hasattr(request, 'weather_code'):
            self.logger.debug(f"Weather Code: {request.weather_code}")
        if request.temperature_flag and hasattr(request, 'temperature'):
            temp_celsius = getattr(request, 'temperature', 0) - 100
            self.logger.debug(f"Temperature: {temp_celsius}℃")
        if request.pop_flag and hasattr(request, 'pop'):
            self.logger.debug(f"Precipitation Prob: {request.pop}%")
            
        
        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(request.to_bytes()))
        self.logger.debug("====================================\n")
        
    def _debug_print_response(self, response):
        """レスポンスのデバッグ情報を出力"""
        if not self.debug:
            return
            
        self.logger.debug("\n=== RECEIVED REPORT RESPONSE PACKET ===")
        self.logger.debug(f"Response Type: {response.type}")
        self.logger.debug(f"Total Length: {len(response.to_bytes())} bytes")
        
        self.logger.debug("\nHeader:")
        self.logger.debug(f"Version: {response.version}")
        self.logger.debug(f"Type: {response.type}")
        self.logger.debug(f"Area Code: {response.area_code}")
        self.logger.debug(f"Packet ID: {response.packet_id}")
        self.logger.debug(f"Timestamp: {time.ctime(response.timestamp)}")
        
        if hasattr(response, 'is_success'):
            self.logger.debug(f"Success: {response.is_success()}")
            
        if hasattr(response, 'get_response_summary'):
            summary = response.get_response_summary()
            self.logger.debug(f"Summary: {summary}")
        
        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(response.to_bytes()))
        self.logger.debug("=====================================\n")
        
    def send_report(self) -> Optional[Dict[str, Any]]:
        """
        設定されたセンサーデータでレポートを送信
        
        Returns:
            dict: レスポンス情報、またはNone（エラー時）
        """
        if self.area_code is None:
            self.logger.error("エリアコードが設定されていません")
            return None
            
        try:
            start_time = time.time()
            
            # レポートリクエストを作成
            request = ReportRequest.create_sensor_data_report(
                area_code=self.area_code,
                weather_code=self.weather_code,
                temperature=self.temperature,
                precipitation_prob=self.precipitation_prob,
                alert=self.alert,
                disaster=self.disaster,
                version=self.VERSION
            )
            
            
            self._debug_print_request(request)
            
            # リクエスト送信
            self.sock.sendto(request.to_bytes(), (self.host, self.port))
            
            # レスポンスを受信
            response_data, addr = self.sock.recvfrom(1024)
            
            # パケットタイプに基づいて適切なレスポンスクラスを選択
            response_type = int.from_bytes(response_data[2:3], byteorder='little') & 0x07
            
            if response_type == 5:  # レポートレスポンス（ACK）
                response = ReportResponse.from_bytes(response_data)
                self._debug_print_response(response)
                
                if response.is_success():
                    result = {
                        'type': 'report_ack',
                        'success': True,
                        'area_code': response.area_code,
                        'packet_id': response.packet_id,
                        'timestamp': response.timestamp,
                        'response_time_ms': (time.time() - start_time) * 1000
                    }
                    
                    # レスポンス要約情報を追加
                    if hasattr(response, 'get_response_summary'):
                        summary = response.get_response_summary()
                        result.update(summary)
                    
                    if self.debug:
                        self.logger.debug(f"\n✓ レポート送信成功: {result}")
                    
                    return result
                else:
                    self.logger.error("レポート送信失敗: サーバーからエラーレスポンス")
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
                    'success': False
                }
            else:
                self.logger.error(f"不明なパケットタイプ: {response_type}")
                return None
            
        except socket.timeout:
            self.logger.error("レポートサーバー接続タイムアウト")
            return None
        except Exception as e:
            self.logger.error(f"レポート送信エラー: {e}")
            if self.debug:
                self.logger.exception("Traceback:")
            return None
    
    def send_current_data(self) -> Optional[Dict[str, Any]]:
        """
        現在設定されているデータでレポートを送信（send_reportのエイリアス）
        
        Returns:
            dict: レスポンス情報、またはNone（エラー時）
        """
        return self.send_report()
    
    def clear_data(self):
        """設定されているセンサーデータをクリア"""
        self.area_code = None
        self.weather_code = None
        self.temperature = None
        self.precipitation_prob = None
        self.alert = None
        self.disaster = None
        
        if self.debug:
            self.logger.debug("センサーデータをクリアしました")
    
    def get_current_data(self) -> Dict[str, Any]:
        """
        現在設定されているセンサーデータを取得
        
        Returns:
            dict: 現在のセンサーデータ
        """
        return {
            'area_code': self.area_code,
            'weather_code': self.weather_code,
            'temperature': self.temperature,
            'precipitation_prob': self.precipitation_prob,
            'alert': self.alert,
            'disaster': self.disaster
        }
    
    def close(self):
        """ソケットを閉じる"""
        self.sock.close()
