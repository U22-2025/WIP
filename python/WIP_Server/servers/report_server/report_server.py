"""
レポートサーバー - IoT機器データ収集専用サーバー実装
IoT機器からのType 4（レポートリクエスト）を受信してType 5（レポートレスポンス）を返す
"""

import time
import sys
import os
from datetime import datetime
from pathlib import Path
import traceback

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    # 共通ライブラリのパスも追加
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# モジュールとして使用される場合
from ..base_server import BaseServer
from common.packet import ReportRequest, ReportResponse
from common.utils.config_loader import ConfigLoader
from common.packet.debug.debug_logger import PacketDebugLogger
from ..common.log_config import UnifiedLogFormatter
# JSON_DIR references removed
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
        
        # 認証設定を初期化
        self._init_auth_config()
        
        # プロトコルバージョンを設定から取得（4ビット値に制限）
        version = self.config.getint('system', 'protocol_version', 1)
        self.version = version & 0x0F  # 4ビットにマスク
        
        # ネットワーク設定
        self.udp_buffer_size = self.config.getint('network', 'udp_buffer_size', 4096)
        
        # データ検証設定
        self.enable_data_validation = self.config.getboolean('validation', 'enable_data_validation', True)
        self.enable_alert_processing = self.config.getboolean('processing', 'enable_alert_processing', True)
        self.enable_disaster_processing = self.config.getboolean('processing', 'enable_disaster_processing', True)
        # ファイルログ機能は削除
        self.enable_database = self.config.getboolean('database', 'enable_database', False)
        
        # レポートサイズ制限
        self.max_report_size = self.config.getint('validation', 'max_report_size', 4096)
        
        # ログファイル設定は削除
        
        # 統計情報
        self.report_count = 0
        self.success_count = 0
        
        # ログファイル初期化は削除
        
        # 統一デバッグロガーの初期化
        self.packet_debug_logger = PacketDebugLogger("ReportServer")
    
    def _init_auth_config(self):
        """認証設定を環境変数から読み込み（ReportServer固有）"""
        # ReportServer自身の認証設定
        auth_enabled = os.getenv('REPORT_SERVER_AUTH_ENABLED', 'false').lower() == 'true'
        auth_passphrase = os.getenv('REPORT_SERVER_PASSPHRASE', '')
        request_auth_enabled = os.getenv('REPORT_SERVER_REQUEST_AUTH_ENABLED', 'false').lower() == 'true'
        
        self.auth_enabled = auth_enabled
        self.auth_passphrase = auth_passphrase
        self.request_auth_enabled = request_auth_enabled
        
    
    def _get_response_auth_config(self):
        """レスポンス認証設定を取得"""
        return os.getenv('REPORT_SERVER_RESPONSE_AUTH_ENABLED', 'false').lower() == 'true'
    
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
        
        # 認証チェック（基底クラスの共通メソッドを使用）
        auth_valid, auth_error_code, auth_error_msg = self.validate_auth(request)
        if not auth_valid:
            return False, auth_error_code, auth_error_msg
        
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
    
    # _setup_log_file method removed
    
    # _log_report_data method removed
    
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
            
            # ログファイル記録は削除
            
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
            
            # 認証フラグ設定（認証が有効でレスポンス認証が有効な場合）
            if self.auth_enabled and self._get_response_auth_config():
                response.enable_auth(self.auth_passphrase)
                response.set_auth_flags()
                print(f"[{self.server_name}] Response Auth: ✓")
            else:
                print(f"[{self.server_name}] Response Auth: disabled")
            
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
            # ログ記録表示は削除
            if 'database' in timing_info:
                print(f"    - DB保存: {timing_info['database']*1000:.1f}ms")
            print(f"    - レスポンス作成: {timing_info['response']*1000:.1f}ms")
            print(f"    - 合計: {timing_info['total']*1000:.1f}ms")
            
            # 遅延警告（20ms以上の場合）
            if timing_info['total'] > 0.02:
                print(f"  ⚠️  遅延検出: 総処理時間が{timing_info['total']*1000:.1f}msです")
                # ログ記録関連の警告は削除
                if timing_info['extract'] > 0.005:
                    print(f"     - データ抽出が遅い: {timing_info['extract']*1000:.1f}ms")
            
            print(f"  ===== RESPONSE SENT =====\n")
            
            # 統一されたデバッグ出力を追加
            debug_data = {
                'area_code': request.area_code,
                'timestamp': request.timestamp,
                'weather_code': sensor_data.get('weather_code', 'N/A'),
                'temperature': sensor_data.get('temperature', 'N/A'),
                'precipitation_prob': sensor_data.get('precipitation_prob', 'N/A'),
                'alert': sensor_data.get('alert', []),
                'disaster': sensor_data.get('disaster', [])
            }
            self.packet_debug_logger.log_unified_packet_received(
                "IoT report processing",
                timing_info['total'],
                debug_data
            )
            
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
        """リクエストのデバッグ情報を出力（統一フォーマット）"""
        if not self.debug:
            return

        details = {
            "Version": getattr(parsed, "version", "N/A"),
            "Type": getattr(parsed, "type", "N/A"),
            "Area Code": getattr(parsed, "area_code", "N/A"),
            "Packet ID": getattr(parsed, "packet_id", "N/A"),
            "Timestamp": time.ctime(getattr(parsed, "timestamp", 0)),
            "Weather": getattr(parsed, "weather_flag", False),
            "Temperature": getattr(parsed, "temperature_flag", False),
            "POP": getattr(parsed, "pop_flag", False),
            "Alert": getattr(parsed, "alert_flag", False),
            "Disaster": getattr(parsed, "disaster_flag", False),
        }

        sensor_data = self._extract_sensor_data(parsed)
        details["Sensor Data"] = sensor_data

        log = UnifiedLogFormatter.format_communication_log(
            server_name=self.server_name,
            direction="recv from",
            remote_addr="unknown",
            remote_port=0,
            packet_size=len(data),
            packet_details=details,
        )
        print(log)
    
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