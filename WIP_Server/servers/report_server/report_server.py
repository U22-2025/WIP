"""
レポートサーバー - IoT機器データ収集専用サーバー実装
IoT機器からのType 4（レポートリクエスト）を受信してType 5（レポートレスポンス）を返す
"""

import time
import sys
import os
import threading
from datetime import datetime
from pathlib import Path
import traceback
import logging

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    # 共通ライブラリのパスも追加
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# モジュールとして使用される場合
from ..base_server import BaseServer
from common.packet import (
    ReportRequest, ReportResponse,
    ErrorResponse,
    BitFieldError
)
from common.utils.config_loader import ConfigLoader
from datetime import timedelta


class ReportServer(BaseServer):
    """レポートサーバーのメインクラス（IoT機器データ収集専用）"""
    
    def __init__(self, host=None, port=None, debug=None, max_workers=None):
        """
        初期化
        
        Args:
            host: サーバーホスト（Noneの場合は設定ファイルから取得）
            port: サーバーポート（Noneの場合は設定ファイルから取得）
            debug: デバッグモードフラグ（Noneの場合は設定ファイルから取得）
            max_workers: スレッドプールのワーカー数（Noneの場合は設定ファイルから取得）
        """
        # 設定ファイルを読み込む
        config_path = Path(__file__).parent / 'config.ini'
        try:
            self.config = ConfigLoader(config_path)
        except Exception as e:
            error_msg = f"設定ファイルの読み込みに失敗しました: {config_path} - {str(e)}"
            if debug:
                traceback.print_exc()
            raise RuntimeError(f"設定ファイル読み込みエラー: {str(e)}")
        
        # サーバー設定を取得（引数優先、なければ設定ファイル、なければデフォルト）
        if host is None:
            host = self.config.get('server', 'host', '0.0.0.0')
        if port is None:
            port = self.config.getint('server', 'port', 9999)
        if debug is None:
            debug_str = self.config.get('server', 'debug', 'false')
            debug = debug_str.lower() == 'true'
        if max_workers is None:
            max_workers = self.config.getint('server', 'max_workers', None)
        
        # 基底クラスの初期化
        super().__init__(host, port, debug, max_workers)
        
        # サーバー名を設定
        self.server_name = "ReportServer"
        
        # プロトコルバージョンを設定から取得（4ビット値に制限）
        version = self.config.getint('system', 'protocol_version', 1)
        self.version = version & 0x0F  # 4ビットにマスク
        
        # 認証設定を読み込む
        self._setup_auth()
        
        # ネットワーク設定
        self.udp_buffer_size = self.config.getint('network', 'udp_buffer_size', 4096)
        
        # ストレージ設定
        self.enable_file_logging = True  # ログファイル出力を有効化
        self.log_directory = self.config.get('storage', 'log_directory', 'logs/reports')
        self.log_file_path = Path(self.log_directory) / 'report_server.log'
        self.enable_database = self.config.getboolean('storage', 'enable_database', False)
        
        # 処理設定
        self.enable_data_validation = self.config.getboolean('processing', 'enable_data_validation', True)
        self.enable_alert_processing = self.config.getboolean('processing', 'enable_alert_processing', True)
        self.enable_disaster_processing = self.config.getboolean('processing', 'enable_disaster_processing', True)
        self.max_report_size = self.config.getint('processing', 'max_report_size', 1024)
        
        # ログファイル機能を設定
        if self.enable_file_logging:
            self._setup_log_file()
        
        # 統計情報
        self.report_count = 0
        self.success_count = 0
        
        if self.debug:
            print(f"\n[{self.server_name}] 初期化完了")
            print(f"  ホスト: {host}:{port}")
            print(f"  データ検証: {self.enable_data_validation}")
            print(f"  ログファイル: {self.log_file_path if self.enable_file_logging else '無効'}")
            print(f"  データベース: {self.enable_database}")
            print(f"  認証: {'有効' if self.auth_enabled else '無効'}")
    
    def _setup_auth(self):
        """認証設定を初期化"""
        # 認証が有効かどうか
        auth_enabled_str = self.config.get('auth', 'enable_auth', 'false')
        self.auth_enabled = auth_enabled_str.lower() == 'true'
        
        # パスフレーズ
        self.auth_passphrase = self.config.get('auth', 'passphrase', '')
        
        if self.auth_enabled and not self.auth_passphrase:
            raise ValueError("認証が有効ですが、パスフレーズが設定されていません")
    
    def validate_request(self, request):
        """
        リクエストの妥当性をチェック（BaseServerパターン）
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_code, error_message)
        """
        # データサイズチェック
        if hasattr(request, '_original_data'):
            data_size = len(request._original_data)
            if data_size > self.max_report_size:
                return False, 413, f"レポートサイズが制限を超えています: {data_size} > {self.max_report_size}"
        
        # バージョンチェック
        if request.version != self.version:
            return False, 406, f"バージョンが不正です (expected: {self.version}, got: {request.version})"
        
        # 認証チェック（認証が有効な場合）
        if self.auth_enabled:
            # リクエストに認証機能を設定
            request.enable_auth(self.auth_passphrase)
            
            # 認証ハッシュを検証
            if not request.verify_auth_from_extended_field():
                if self.debug:
                    print(f"[{self.server_name}] 認証失敗")
                return False, "403", "認証に失敗しました"
            
            if self.debug:
                print(f"[{self.server_name}] 認証成功")
        
        # タイプチェック（Type 4のみ有効）
        if request.type != 4:
            return False, 405, f"サポートされていないパケットタイプ: {request.type}"
        
        # エリアコードチェック
        if not request.area_code or request.area_code == "000000":
            return False, 402, "エリアコードが未設定"
        
        # センサーデータの検証
        if self.enable_data_validation:
            sensor_data = self._extract_sensor_data(request)
            validation_result = self._validate_sensor_data(sensor_data)
            if not validation_result['valid']:
                return False, 422, f"センサーデータの検証に失敗: {validation_result['message']}"
        
        # 専用クラスのバリデーション
        if hasattr(request, 'is_valid') and callable(getattr(request, 'is_valid')):
            if not request.is_valid():
                return False, 400, "リクエストのバリデーションに失敗"
        
        return True, None, None
    
    
    def _extract_sensor_data(self, request):
        """リクエストからセンサーデータを抽出"""
        sensor_data = {
            'area_code': request.area_code,
            'timestamp': request.timestamp,
            'data_types': []
        }
        
        # デバッグ出力でリクエストの詳細を確認（最適化版）
        if self.debug:
            flags = [
                f"weather:{getattr(request, 'weather_flag', 'N')}",
                f"temp:{getattr(request, 'temperature_flag', 'N')}",
                f"pop:{getattr(request, 'pop_flag', 'N')}",
                f"alert:{getattr(request, 'alert_flag', 'N')}",
                f"disaster:{getattr(request, 'disaster_flag', 'N')}"
            ]
            print(f"  [デバッグ] フラグ: {' '.join(flags)}")
        
        # 固定長フィールドからセンサーデータを抽出
        try:
            # 天気コード
            if hasattr(request, 'weather_flag') and request.weather_flag and hasattr(request, 'weather_code'):
                weather_code = request.weather_code
                if weather_code is not None and weather_code != 0:
                    sensor_data['weather_code'] = weather_code
            
            # 気温（内部表現から摂氏に変換）
            if hasattr(request, 'temperature_flag') and request.temperature_flag and hasattr(request, 'temperature'):
                temperature_raw = request.temperature
                if temperature_raw is not None:
                    temperature_celsius = temperature_raw - 100  # 内部表現から摂氏に変換
                    sensor_data['temperature'] = temperature_celsius
            
            # 降水確率
            if hasattr(request, 'pop_flag') and request.pop_flag and hasattr(request, 'pop'):
                pop_value = request.pop
                if pop_value is not None and pop_value != 0:
                    sensor_data['precipitation_prob'] = pop_value
            
            if self.debug:
                fields = []
                if 'weather_code' in sensor_data:
                    fields.append(f"weather:{sensor_data['weather_code']}")
                if 'temperature' in sensor_data:
                    fields.append(f"temp:{sensor_data['temperature']}℃")
                if 'precipitation_prob' in sensor_data:
                    fields.append(f"pop:{sensor_data['precipitation_prob']}%")
                print(f"  [デバッグ] 固定長: {' '.join(fields) if fields else 'なし'}")
            
        except Exception as e:
            if self.debug:
                print(f"  [デバッグ] 固定長フィールド処理エラー: {e}")
        
        # 拡張フィールドから警報・災害情報を抽出
        if hasattr(request, 'ex_field') and request.ex_field:
            try:
                ex_dict = request.ex_field.to_dict() if hasattr(request.ex_field, 'to_dict') else {}
                
                if self.debug:
                    ex_keys = list(ex_dict.keys()) if ex_dict else []
                    print(f"  [デバッグ] 拡張フィールド: {ex_keys}")
                
                # 警報情報
                if hasattr(request, 'alert_flag') and request.alert_flag and 'alert' in ex_dict:
                    sensor_data['alert'] = ex_dict['alert']
                
                # 災害情報
                if hasattr(request, 'disaster_flag') and request.disaster_flag and 'disaster' in ex_dict:
                    sensor_data['disaster'] = ex_dict['disaster']
                
                # 送信元情報
                if 'source' in ex_dict:
                    sensor_data['source'] = ex_dict['source']
                
            except Exception as e:
                if self.debug:
                    print(f"  [デバッグ] 拡張フィールド処理エラー: {e}")
                    
        return sensor_data
    
    def _validate_sensor_data(self, sensor_data):
        """センサーデータの検証"""
        try:
            # エリアコードの検証
            area_code = sensor_data.get('area_code')
            if not area_code or area_code == "000000":
                return {'valid': False, 'message': '無効なエリアコード'}
            
            # 気温の範囲チェック
            if 'temperature' in sensor_data:
                temp = sensor_data['temperature']
                if temp < -50 or temp > 60:
                    return {'valid': False, 'message': f'気温が範囲外: {temp}℃'}
            
            # 降水確率の範囲チェック
            if 'precipitation_prob' in sensor_data:
                pop = sensor_data['precipitation_prob']
                if pop < 0 or pop > 100:
                    return {'valid': False, 'message': f'降水確率が範囲外: {pop}%'}
            
            # タイムスタンプの妥当性チェック
            timestamp = sensor_data.get('timestamp', 0)
            current_time = int(datetime.now().timestamp())
            time_diff = abs(current_time - timestamp)
            if time_diff > 3600:  # 1時間以上の差
                return {'valid': False, 'message': f'タイムスタンプが古すぎます: {time_diff}秒の差'}
            
            return {'valid': True, 'message': 'OK'}
            
        except Exception as e:
            return {'valid': False, 'message': f'検証エラー: {str(e)}'}
    
    def _process_sensor_data(self, sensor_data, request):
        """センサーデータの処理"""
        processed_data = sensor_data.copy()
        
        # 警報処理
        if self.enable_alert_processing and 'alert' in sensor_data:
            processed_data['alert_processed'] = True
            if self.debug:
                print(f"  警報データを処理しました: {sensor_data['alert']}")
        
        # 災害情報処理
        if self.enable_disaster_processing and 'disaster' in sensor_data:
            processed_data['disaster_processed'] = True
            if self.debug:
                print(f"  災害情報を処理しました: {sensor_data['disaster']}")
        
        # 処理時刻を追加
        processed_data['processed_at'] = datetime.now().isoformat()
        
        return processed_data
    
    def _setup_log_file(self):
        """ログファイルの設定"""
        try:
            # ログディレクトリを作成
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # ログファイルの初期化（存在しない場合はヘッダーを書き込み）
            if not self.log_file_path.exists():
                with open(self.log_file_path, 'w', encoding='utf-8') as f:
                    f.write("timestamp,area_code,weather_code,temperature,precipitation_prob,alert,disaster\n")
            
            if self.debug:
                print(f"[{self.server_name}] ログファイルを初期化しました: {self.log_file_path}")
                
        except Exception as e:
            print(f"[{self.server_name}] ログファイル初期化エラー: {e}")
            if self.debug:
                traceback.print_exc()
    
    def _log_report_data(self, request, sensor_data, source_addr=None):
        """レポートデータをログファイルに追記（高速化版）"""
        if not self.enable_file_logging:
            return
            
        try:
            # CSVライクな1行を作成
            timestamp = datetime.now().isoformat()
            area_code = request.area_code
            weather_code = sensor_data.get('weather_code', '')
            temperature = sensor_data.get('temperature', '')
            precipitation_prob = sensor_data.get('precipitation_prob', '')
            
            # 配列データを文字列に変換
            alert_data = sensor_data.get('alert', '')
            if isinstance(alert_data, list):
                alert_data = "; ".join(str(x) for x in alert_data)
            
            disaster_data = sensor_data.get('disaster', '')
            if isinstance(disaster_data, list):
                disaster_data = "; ".join(str(x) for x in disaster_data)
            
            # CSV形式の行を作成
            log_line = f"{timestamp},{area_code},{weather_code},{temperature},{precipitation_prob},{alert_data},{disaster_data}\n"
            
            # ログファイルに追記（単純な追記のため高速）
            with open(self.log_file_path, 'a', encoding='utf-8') as f:
                f.write(log_line)
            
            if self.debug:
                print(f"  ✓ ログファイルに追記: {area_code}")
            
        except Exception as e:
            print(f"[{self.server_name}] ログファイル記録エラー: {e}")
            if self.debug:
                traceback.print_exc()
    
    def _save_to_database(self, request, sensor_data, source_addr=None):
        """データベースに保存（実装予定）"""
        if self.debug:
            print(f"  [{self.server_name}] データベース保存: {sensor_data['area_code']} (未実装)")
        # TODO: データベース保存機能を実装
        pass
    
    
    def create_response(self, request):
        """
        レスポンスを作成（BaseServerパターン - Type 4 → Type 5）
        
        Args:
            request: ReportRequestオブジェクト
            
        Returns:
            レスポンスのバイナリデータ
        """
        start_time = time.time()
        timing_info = {}
        
        try:
            # レポートカウント増加
            with self.lock:
                self.report_count += 1
            
            # 常にリクエスト受信をログ出力
            print(f"\n[{self.server_name}] ===== REPORT REQUEST RECEIVED =====")
            print(f"  パケットID: {request.packet_id}")
            print(f"  エリアコード: {request.area_code}")
            print(f"  タイムスタンプ: {time.ctime(request.timestamp)}")
            print(f"  レポート番号: {self.report_count}")
            
            # センサーデータの抽出（時間計測）
            extract_start = time.time()
            sensor_data = self._extract_sensor_data(request)
            timing_info['extract'] = time.time() - extract_start
            print(f"  センサーデータタイプ: {sensor_data.get('data_types', [])}")
            
            # データ処理（時間計測）
            process_start = time.time()
            processed_data = self._process_sensor_data(sensor_data, request)
            timing_info['process'] = time.time() - process_start
            
            # ログファイルに記録（時間計測）
            log_start = time.time()
            self._log_report_data(request, sensor_data, None)
            timing_info['log'] = time.time() - log_start
            if self.enable_file_logging:
                print(f"  ✓ ログファイル記録完了 ({timing_info['log']*1000:.1f}ms)")
            
            # データベース保存（オプション）
            if self.enable_database:
                db_start = time.time()
                self._save_to_database(request, sensor_data, None)
                timing_info['database'] = time.time() - db_start
            
            # ACKレスポンス（Type 5）を作成（時間計測）
            response_start = time.time()
            response = ReportResponse.create_ack_response(
                request=request,
                version=self.version
            )
            timing_info['response'] = time.time() - response_start
            
            # 成功カウント
            with self.lock:
                self.success_count += 1
            
            # 総処理時間
            timing_info['total'] = time.time() - start_time
            
            print(f"  ✓ ACKレスポンス作成完了 ({timing_info['response']*1000:.1f}ms)")
            print(f"  ✓ 成功率: {(self.success_count/self.report_count)*100:.1f}%")
            
            # 処理時間の詳細を出力
            print(f"  📊 処理時間詳細:")
            print(f"    - データ抽出: {timing_info['extract']*1000:.1f}ms")
            print(f"    - データ処理: {timing_info['process']*1000:.1f}ms")
            if self.enable_file_logging:
                print(f"    - ログ記録: {timing_info['log']*1000:.1f}ms")
            if 'database' in timing_info:
                print(f"    - DB保存: {timing_info['database']*1000:.1f}ms")
            print(f"    - レスポンス作成: {timing_info['response']*1000:.1f}ms")
            print(f"    - 合計: {timing_info['total']*1000:.1f}ms")
            
            # 遅延警告（20ms以上の場合）
            if timing_info['total'] > 0.02:
                print(f"  ⚠️  遅延検出: 総処理時間が{timing_info['total']*1000:.1f}msです")
                if self.enable_file_logging and timing_info['log'] > 0.005:
                    print(f"     - ログ記録が遅い: {timing_info['log']*1000:.1f}ms")
                if timing_info['extract'] > 0.005:
                    print(f"     - データ抽出が遅い: {timing_info['extract']*1000:.1f}ms")
            
            print(f"  ===== RESPONSE SENT =====\n")
            
            return response.to_bytes()
            
        except Exception as e:
            error_msg = f"レスポンス作成中にエラーが発生しました: {e}"
            print(f"❌ [{self.server_name}] {error_msg}")
            if self.debug:
                traceback.print_exc()
            raise
    
    def parse_request(self, data):
        """
        リクエストデータをパース（レポートパケット専用）
        
        Args:
            data: 受信したバイナリデータ
            
        Returns:
            ReportRequestインスタンス
        """
        # まず基本的なパケットを解析してタイプを確認
        from common.packet import Request
        temp_request = Request.from_bytes(data)
        packet_type = temp_request.type
        
        # Type 4のみサポート
        if packet_type == 4:
            return ReportRequest.from_bytes(data)
        else:
            raise ValueError(f"サポートされていないパケットタイプ: {packet_type}")
    
    def _debug_print_request(self, data, parsed):
        """リクエストのデバッグ情報を出力"""
        if not self.debug:
            return
            
        print(f"\n[{self.server_name}] === 受信レポートパケット ===")
        print(f"Total Length: {len(data)} bytes")
        print(f"Packet Class: {type(parsed).__name__}")
        
        print("\nHeader:")
        print(f"Version: {parsed.version}")
        print(f"Type: {parsed.type}")
        print(f"Area Code: {parsed.area_code}")
        print(f"Packet ID: {parsed.packet_id}")
        print(f"Timestamp: {time.ctime(parsed.timestamp)}")
        
        print("\nFlags:")
        print(f"Weather: {parsed.weather_flag}")
        print(f"Temperature: {parsed.temperature_flag}")
        print(f"POP: {parsed.pop_flag}")
        print(f"Alert: {parsed.alert_flag}")
        print(f"Disaster: {parsed.disaster_flag}")
        
        # センサーデータ情報
        sensor_data = self._extract_sensor_data(parsed)
        print(f"\nSensor Data: {sensor_data}")
        
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("========================\n")
    
    def get_statistics(self):
        """サーバー統計情報を取得"""
        with self.lock:
            return {
                'server_name': self.server_name,
                'total_requests': self.request_count,
                'total_reports': self.report_count,
                'successful_reports': self.success_count,
                'errors': self.error_count,
                'success_rate': (self.success_count / self.report_count * 100) if self.report_count > 0 else 0,
                'uptime': time.time() - self.start_time if hasattr(self, 'start_time') else 0
            }
    
    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理"""
        if self.debug:
            print(f"[{self.server_name}] クリーンアップ完了")


if __name__ == "__main__":
    # 設定ファイルから読み込んで起動
    server = ReportServer()
    server.run()