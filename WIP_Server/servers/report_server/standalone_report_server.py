"""
独立型レポートサーバー - dotenv依存なし
IoT機器からのType 4（レポートリクエスト）を受信してType 5（レポートレスポンス）を返す
"""

import socket
import time
import threading
import json
import sys
import os
from datetime import datetime
from pathlib import Path
import traceback
import logging
import configparser
import re

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from common.packet import ReportRequest, ReportResponse, ErrorResponse


class StandaloneReportServer:
    """独立型レポートサーバー（dotenv依存なし）"""
    
    def __init__(self, host='localhost', port=9999, debug=False):
        """
        初期化
        
        Args:
            host: サーバーホスト
            port: サーバーポート
            debug: デバッグモード
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.server_name = "StandaloneReportServer"
        self.version = 1
        
        # 統計情報
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.start_time = None
        self.lock = threading.Lock()
        
        # ソケットの初期化
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind((self.host, self.port))
            if self.debug:
                print(f"[{self.server_name}] Socket bound to {self.host}:{self.port}")
        except Exception as e:
            print(f"[{self.server_name}] Failed to initialize socket: {e}")
            raise
        
        # ログ設定
        if self.debug:
            self._setup_logging()
    
    def _setup_logging(self):
        """ログ設定"""
        try:
            log_dir = Path("logs/reports")
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / f"report_{datetime.now().strftime('%Y%m%d')}.log"
            
            self.logger = logging.getLogger(self.server_name)
            self.logger.setLevel(logging.INFO)
            
            if not self.logger.handlers:
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)
                
            if self.debug:
                print(f"[{self.server_name}] Logging to: {log_file}")
        except Exception as e:
            print(f"[{self.server_name}] Failed to setup logging: {e}")
    
    def _hex_dump(self, data):
        """バイナリデータのhexダンプ"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
    
    def _debug_print_request(self, data, parsed, addr):
        """リクエストのデバッグ情報を出力"""
        if not self.debug:
            return
            
        print(f"\n[{self.server_name}] === RECEIVED REPORT REQUEST ===")
        print(f"From: {addr}")
        print(f"Total Length: {len(data)} bytes")
        print(f"Packet Class: {type(parsed).__name__}")
        
        print(f"\nHeader:")
        print(f"Version: {parsed.version}")
        print(f"Type: {parsed.type}")
        print(f"Area Code: {parsed.area_code}")
        print(f"Packet ID: {parsed.packet_id}")
        print(f"Timestamp: {time.ctime(parsed.timestamp)}")
        
        print(f"\nFlags:")
        print(f"Weather: {parsed.weather_flag}")
        print(f"Temperature: {parsed.temperature_flag}")
        print(f"POP: {parsed.pop_flag}")
        print(f"Alert: {parsed.alert_flag}")
        print(f"Disaster: {parsed.disaster_flag}")
        
        print(f"\nRaw Packet:")
        print(self._hex_dump(data))
        print("=============================================\n")
    
    def _debug_print_response(self, response_data, addr):
        """レスポンスのデバッグ情報を出力"""
        if not self.debug:
            return
            
        print(f"\n[{self.server_name}] === SENDING REPORT RESPONSE ===")
        print(f"To: {addr}")
        print(f"Total Length: {len(response_data)} bytes")
        print(f"Response Type: Type 5 (ACK)")
        
        print(f"\nRaw Response:")
        print(self._hex_dump(response_data))
        print("============================================\n")
    
    def handle_request(self, data, addr):
        """リクエストの処理"""
        start_time = time.time()
        
        with self.lock:
            self.request_count += 1
        
        if self.debug:
            print(f"\n[{self.server_name}] Received {len(data)} bytes from {addr}")
            print(f"Total requests so far: {self.request_count}")
        
        try:
            # リクエストをパース
            request = ReportRequest.from_bytes(data)
            
            # デバッグ出力
            self._debug_print_request(data, request, addr)
            
            # バリデーション
            if request.type != 4:
                raise ValueError(f"Expected Type 4, got Type {request.type}")
            
            if request.version != self.version:
                raise ValueError(f"Version mismatch: expected {self.version}, got {request.version}")
            
            # センサーデータの抽出
            sensor_data = self._extract_sensor_data(request)
            
            if self.debug:
                print(f"[{self.server_name}] Extracted sensor data: {sensor_data}")
            
            # ログ記録
            if hasattr(self, 'logger'):
                log_entry = {
                    'timestamp': datetime.now().isoformat(),
                    'packet_id': request.packet_id,
                    'area_code': request.area_code,
                    'source_address': f"{addr[0]}:{addr[1]}",
                    'sensor_data': sensor_data
                }
                self.logger.info(f"REPORT: {json.dumps(log_entry, ensure_ascii=False)}")
            
            # ACKレスポンス（Type 5）を作成
            response = ReportResponse.create_ack_response(
                request=request,
                version=self.version
            )
            
            response_data = response.to_bytes()
            
            # デバッグ出力
            self._debug_print_response(response_data, addr)
            
            # レスポンスを送信
            bytes_sent = self.sock.sendto(response_data, addr)
            
            if bytes_sent != len(response_data):
                raise RuntimeError(f"Send failed: {bytes_sent}/{len(response_data)} bytes")
            
            # 成功カウント
            with self.lock:
                self.success_count += 1
            
            processing_time = (time.time() - start_time) * 1000
            
            if self.debug:
                print(f"[{self.server_name}] ✓ ACK sent successfully!")
                print(f"Response size: {len(response_data)} bytes")
                print(f"Processing time: {processing_time:.2f}ms")
                print(f"Success rate: {(self.success_count/self.request_count)*100:.1f}%")
            
        except Exception as e:
            with self.lock:
                self.error_count += 1
            
            error_msg = f"Request processing failed: {e}"
            print(f"[{self.server_name}] ✗ {error_msg}")
            
            if self.debug:
                traceback.print_exc()
            
            # エラーレスポンスを送信
            try:
                packet_id = getattr(request, 'packet_id', 0) if 'request' in locals() else 0
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=packet_id,
                    error_code=530,
                    timestamp=int(datetime.now().timestamp())
                )
                
                error_data = error_response.to_bytes()
                self.sock.sendto(error_data, addr)
                
                if self.debug:
                    print(f"[{self.server_name}] Error response sent to {addr}")
                    
            except Exception as err_e:
                print(f"[{self.server_name}] Failed to send error response: {err_e}")
    
    def _extract_sensor_data(self, request):
        """リクエストからセンサーデータを抽出"""
        sensor_data = {
            'area_code': request.area_code,
            'timestamp': request.timestamp,
            'data_types': []
        }
        
        # フラグに基づいてデータを抽出
        if request.weather_flag and hasattr(request, 'weather_code'):
            sensor_data['weather_code'] = getattr(request, 'weather_code', None)
            sensor_data['data_types'].append('weather')
        
        if request.temperature_flag and hasattr(request, 'temperature'):
            temp_raw = getattr(request, 'temperature', 100)
            sensor_data['temperature'] = temp_raw - 100
            sensor_data['data_types'].append('temperature')
        
        if request.pop_flag and hasattr(request, 'pop'):
            sensor_data['precipitation_prob'] = getattr(request, 'pop', None)
            sensor_data['data_types'].append('precipitation')
        
        # 拡張フィールドの処理
        if hasattr(request, 'ex_field') and request.ex_field:
            ex_dict = request.ex_field.to_dict()
            
            if request.alert_flag and 'alert' in ex_dict:
                sensor_data['alert'] = ex_dict['alert']
                sensor_data['data_types'].append('alert')
            
            if request.disaster_flag and 'disaster' in ex_dict:
                sensor_data['disaster'] = ex_dict['disaster']
                sensor_data['data_types'].append('disaster')
            
            source_info = request.get_source_info()
            if source_info:
                sensor_data['source'] = source_info
        
        return sensor_data
    
    def get_statistics(self):
        """統計情報を取得"""
        with self.lock:
            uptime = time.time() - self.start_time if self.start_time else 0
            return {
                'server_name': self.server_name,
                'uptime': uptime,
                'total_requests': self.request_count,
                'successful_reports': self.success_count,
                'errors': self.error_count,
                'success_rate': (self.success_count / self.request_count * 100) if self.request_count > 0 else 0
            }
    
    def run(self):
        """サーバーを開始"""
        print(f"[{self.server_name}] Starting on {self.host}:{self.port}")
        print(f"Waiting for Type 4 (Report Request) packets...")
        if self.debug:
            print("Debug mode enabled")
        print("-" * 50)
        
        self.start_time = time.time()
        
        try:
            while True:
                try:
                    # リクエストを受信
                    data, addr = self.sock.recvfrom(4096)
                    
                    if self.debug:
                        print(f"\n[{self.server_name}] Got packet from {addr}")
                    
                    # リクエストを処理（メインスレッドで処理）
                    self.handle_request(data, addr)
                    
                except socket.timeout:
                    continue
                except socket.error as e:
                    if self.debug:
                        print(f"[{self.server_name}] Socket error: {e}")
                    continue
                except Exception as e:
                    print(f"[{self.server_name}] Error receiving request: {e}")
                    if self.debug:
                        traceback.print_exc()
                    continue
                    
        except KeyboardInterrupt:
            print(f"\n[{self.server_name}] Shutting down...")
            self.stop()
    
    def stop(self):
        """サーバーを停止"""
        print(f"[{self.server_name}] Stopping...")
        
        # 統計情報を表示
        stats = self.get_statistics()
        print(f"\nFinal Statistics:")
        print(f"  Uptime: {stats['uptime']:.1f} seconds")
        print(f"  Total requests: {stats['total_requests']}")
        print(f"  Successful reports: {stats['successful_reports']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        
        # ソケットを閉じる
        if self.sock:
            self.sock.close()
        
        print(f"[{self.server_name}] Stopped.")


if __name__ == "__main__":
    server = StandaloneReportServer(host='localhost', port=9999, debug=True)
    try:
        server.run()
    except KeyboardInterrupt:
        pass