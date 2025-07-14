"""
気象データサーバー - リファクタリング版
基底クラスを継承した実装
"""


import sys
import os
from pathlib import Path
from datetime import datetime
import schedule
import threading
import time
import traceback

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# モジュールとして使用される場合
from ..base_server import BaseServer
from .modules.weather_data_manager import WeatherDataManager
from .modules.response_builder import ResponseBuilder
from .modules.debug_helper import DebugHelper
from .modules.weather_constants import ThreadConstants
from common.packet import QueryRequest, QueryResponse
from common.utils.config_loader import ConfigLoader
from common.packet import ErrorResponse
from common.packet.debug.debug_logger import create_debug_logger, PacketDebugLogger
from WIP_Server.scripts.update_weather_data import update_redis_weather_data
from WIP_Server.scripts.update_alert_disaster_data import main as update_alert_disaster_main


class QueryServer(BaseServer):
    """気象データサーバーのメインクラス（基底クラス継承版）"""
    
    def __init__(self, host=None, port=None, debug=None, max_workers=None, noupdate=False):
        """
        初期化
        
        Args:
            host: サーバーホスト（Noneの場合は設定ファイルから取得）
            port: サーバーポート（Noneの場合は設定ファイルから取得）
            debug: デバッグモード（Noneの場合は設定ファイルから取得）
            max_workers: ワーカー数（Noneの場合は設定ファイルから取得）
        """
        # 設定ファイルを読み込む
        config_path = Path(__file__).parent / 'config.ini'
        self.config = ConfigLoader(config_path)
        
        # サーバー設定を取得（引数優先、なければ設定ファイル、なければデフォルト）
        if host is None:
            host = self.config.get('server', 'host', '0.0.0.0')
        if port is None:
            port = self.config.getint('server', 'port', 4111)
        if debug is None:
            debug_str = self.config.get('server', 'debug', 'false')
            debug = debug_str.lower() == 'true'
        if max_workers is None:
            max_workers = self.config.getint('server', 'max_workers', ThreadConstants.DEFAULT_MAX_WORKERS)
        
        # 基底クラスの初期化
        super().__init__(host, port, debug, max_workers)
        
        # サーバー名を設定
        self.server_name = "QueryServer"
        
        # 認証設定を初期化
        self._init_auth_config()
        
        # プロトコルバージョンを設定から取得
        self.version = self.config.getint('system', 'protocol_version', 1)
        
        # 各コンポーネントの初期化
        self._setup_components()
        
        # デバッグロガーの初期化
        self.logger = create_debug_logger(f"{self.server_name}", self.debug)
        
        # 統一デバッグロガーの初期化
        self.packet_debug_logger = PacketDebugLogger("QueryServer")
        
        # noupdateフラグがFalseの場合のみ起動時更新を実行
        if not noupdate:
            # 起動時に気象データを更新
            self._update_weather_data_scheduled()

            # 起動時に警報と災害情報を更新
            self._update_disaster_alert_scheduled()
        
        # スケジューラーを開始（loggerが初期化された後）
        self._setup_scheduler()
    
    def _init_auth_config(self):
        """認証設定を環境変数から読み込み（QueryServer固有）"""
        # QueryServer自身の認証設定
        auth_enabled = os.getenv('QUERY_SERVER_AUTH_ENABLED', 'false').lower() == 'true'
        auth_passphrase = os.getenv('QUERY_SERVER_PASSPHRASE', '')
        
        self.auth_enabled = auth_enabled
        self.auth_passphrase = auth_passphrase
        
        
        # スキップエリアリストを初期化
        self.skip_area = []
    
    def _setup_components(self):
        """各コンポーネントを初期化"""
        # デバッグヘルパー
        self.debug_helper = DebugHelper(self.debug)
        
        # 気象データマネージャー（設定情報を渡す）
        weather_config = {
            'redis_host': self.config.get('redis', 'host', 'localhost'),
            'redis_port': self.config.getint('redis', 'port', 6379),
            'redis_db': self.config.getint('redis', 'db', 0),
            'debug': self.debug,
            'max_workers': self.max_workers,
            'version': self.version,
            'cache_enabled': self.config.getboolean('cache', 'enable_redis_cache', True)
        }
        self.weather_manager = WeatherDataManager(weather_config)
        
        # レスポンスビルダー
        response_config = {
            'debug': self.debug,
            'version': self.version
        }
        self.response_builder = ResponseBuilder(response_config)
    
    def parse_request(self, data):
        """
        リクエストデータをパース
        
        Args:
            data: 受信したバイナリデータ
            
        Returns:
            Request: パースされたリクエスト
        """
        return QueryRequest.from_bytes(data)
    
    def validate_request(self, request):
        """
        リクエストの妥当性をチェック
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # 認証チェック（基底クラスの共通メソッドを使用）
        auth_valid, auth_error_code, auth_error_msg = self.validate_auth(request)
        if not auth_valid:
            return False, auth_error_code, auth_error_msg
        
        # バージョンのチェック
        if request.version != self.version:
            return False, "403", f"バージョンが不正です (expected: {self.version}, got: {request.version})"
        
        # タイプのチェック
        if request.type != 2:
            return False, "400", f"不正なパケットタイプ: {request.type}"
        
        # 地域コードのチェック
        if not request.area_code or request.area_code == "000000":
            return False, "402", "エリアコードが未設定"
        
        # フラグのチェック（少なくとも1つは必要）
        if not any([request.weather_flag, request.temperature_flag, 
                   request.pop_flag, request.alert_flag, request.disaster_flag]):
            return False, "400", "不正なパケット"
        
        return True, None, None
    
    def create_response(self, request):
        """
        レスポンスを作成
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            レスポンスのバイナリデータ
        """
        start_time = time.time()
        
        # リクエストのバリデーション
        is_valid, error_code, error_msg = self.validate_request(request)
        if not is_valid:
            # ErrorResponseを作成して返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code=error_code,
                timestamp=int(datetime.now().timestamp())
            )
            self.logger.debug(f"{error_code}: [{self.server_name}] エラーレスポンスを生成: {error_code}")
            return error_response.to_bytes()

        try:
            # デバッグ：リクエストの状態を確認
            
            # 気象データを取得
            weather_data = self.weather_manager.get_weather_data(
                area_code=request.area_code,
                weather_flag=request.weather_flag,
                temperature_flag=request.temperature_flag,
                pop_flag=request.pop_flag,
                alert_flag=request.alert_flag,
                disaster_flag=request.disaster_flag,
                day=request.day
            )
            
            # QueryResponseクラスのcreate_query_responseメソッドを使用
            response = QueryResponse.create_query_response(
                request=request,
                weather_data=weather_data,
                version=self.version
            )
            
            # 座標情報がある場合は拡張フィールドに追加
            if hasattr(request, 'get_coordinates'):
                coords = request.get_coordinates()
                if coords and coords[0] is not None and coords[1] is not None:
                    lat, long = coords
                    if hasattr(response, 'ex_field') and response.ex_field:
                        response.ex_field.latitude = lat
                        response.ex_field.longitude = long
                        response.ex_flag = 1
                        self.logger.debug(f"[{self.server_name}] 座標をレスポンスに追加しました: {lat},{long}")
        except Exception as e:
            # 内部エラー発生時は500エラーを返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code="520",
                timestamp=int(datetime.now().timestamp())
            )
            self.logger.debug(f"520: [{self.server_name}] エラーレスポンスを生成: {error_code}")
            return error_response.to_bytes()
        
        # 統一されたデバッグ出力を追加
        execution_time = time.time() - start_time
        debug_data = {
            'area_code': request.area_code,
            'timestamp': response.timestamp,
            'weather_code': response.weather_code if response.weather_flag else 'N/A',
            'temperature': response.temperature - 100 if response.temperature_flag else 'N/A',
            'precipitation_prob': response.pop if response.pop_flag else 'N/A',
            'alert': response.ex_field.get('alert', []) if hasattr(response, 'ex_field') and response.ex_field else [],
            'disaster': response.ex_field.get('disaster', []) if hasattr(response, 'ex_field') and response.ex_field else []
        }
        self.packet_debug_logger.log_unified_packet_received(
            "Direct request",
            execution_time,
            debug_data
        )
        
        return response.to_bytes()
    
    def _debug_print_request(self, data, parsed):
        """リクエストのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print(f"\n[{self.server_name}] === 受信リクエストパケット ===")
        print(f"Total Length: {len(data)} bytes")
        print("\nHeader:")
        print(f"Version: {parsed.version}")
        print(f"Type: {parsed.type}")
        print(f"Area Code: {parsed.area_code}")
        print(f"Day: {parsed.day}")
        print("\nFlags:")
        print(f"Weather: {parsed.weather_flag}")
        print(f"Temperature: {parsed.temperature_flag}")
        print(f"pop: {parsed.pop_flag}")
        print(f"Alert: {parsed.alert_flag}")
        print(f"Disaster: {parsed.disaster_flag}")
        print(f"Extended Field Flag: {parsed.ex_flag}")
        
        # ex_fieldの詳細を表示
        if hasattr(parsed, 'ex_field'):
            print(f"\nExtended Field content: {parsed.ex_field}")
            if hasattr(parsed.ex_field, 'source') and parsed.ex_field.source:
                print(f"  Source: {parsed.ex_field.source[0]}:{parsed.ex_field.source[1]}")
        else:
            print("\nパースされたリクエストに ex_field 属性がありません！")
        
        print("===========================\n")
    
    def _debug_print_response(self, response, request=None):
        """レスポンスのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print(f"\n[{self.server_name}] === 送信レスポンスパケット ===")
        print(f"Total Length: {len(response)} bytes")
        
        # レスポンスオブジェクトの詳細情報を表示
        try:
            resp_obj = QueryResponse.from_bytes(response)
            print("\nResponse Data:")
            if resp_obj.weather_flag:
                print(f"Weather Code: {resp_obj.weather_code}")
            if resp_obj.temperature_flag:
                actual_temp = resp_obj.temperature - 100
                print(f"Temperature: {resp_obj.temperature} ({actual_temp}℃)")
            if resp_obj.pop_flag:
                print(f"precipitation_prob: {resp_obj.pop}%")
            if hasattr(resp_obj, 'ex_field') and resp_obj.ex_field:
                print(f"Extended Fields: {resp_obj.ex_field}")
                if hasattr(resp_obj.ex_field, 'source') and resp_obj.ex_field.source:
                    print(f"  Source: {resp_obj.ex_field.source[0]}:{resp_obj.ex_field.source[1]}")
        except:
            pass
        
        print("============================\n")
    
    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理（オーバーライド）"""
        # WeatherDataManagerのクリーンアップ
        if hasattr(self, 'weather_manager'):
            self.weather_manager.close()

    def _setup_scheduler(self):
        """
        気象データ更新のスケジューラーを開始
        """
        update_times_str = self.config.get('schedule', 'weather_update_time', '03:00')
        update_times = [t.strip() for t in update_times_str.split(',')]
        
        self.logger.debug(f"[{self.server_name}] 気象データ更新を毎日 {', '.join(update_times)} にスケジュールします。")
        
        for update_time in update_times:
            schedule.every().day.at(update_time).do(self._update_weather_data_scheduled)
        
        # configからskip_areaの確認と更新間隔を取得
        skip_area_interval = self.config.getint('schedule', 'skip_area_check_interval_minutes', 10)
        self.logger.debug(f"[{self.server_name}] skip_areaの確認と更新を {skip_area_interval} 分ごとにスケジュールします。")
        schedule.every(skip_area_interval).minutes.do(self._check_and_update_skip_area_scheduled)
        
        # configから災害情報更新間隔を取得
        disaster_alert_interval = self.config.getint('schedule', 'disaster_alert_update_time', 10)
        self.logger.debug(f"[{self.server_name}] 災害情報と気象注意報の更新を {disaster_alert_interval} 分ごとにスケジュールします。")
        schedule.every(disaster_alert_interval).minutes.do(self._update_disaster_alert_scheduled)

        # スケジュールを実行するスレッドを開始
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(30) # 30秒ごとにチェック

        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()

    def _update_weather_data_scheduled(self):
        """
        スケジュールされた気象データ更新処理
        """
        self.logger.debug(f"[{self.server_name}] スケジュールされた気象データ更新を実行中...")
        try:
            # WIP_Server/scripts/update_weather_data.py の関数を呼び出す
            self.skip_area = update_redis_weather_data(debug=self.debug)
            self.logger.debug(f"[{self.server_name}] 気象データ更新完了。{len(self.skip_area)} エリアがスキップされました。")
        except Exception as e:
            print(f"[{self.server_name}] 気象データ更新エラー: {e}")
            self.logger.debug(traceback.format_exc())

    def _check_and_update_skip_area_scheduled(self):
        """
        スケジュールされたskip_areaの確認と更新処理
        """
        self.logger.debug(f"[{self.server_name}] スケジュールされたskip_areaの確認と更新を実行中...")
        
        if self.skip_area:
            self.logger.debug(f"[{self.server_name}] skip_areaに地域コードが存在します: {self.skip_area}")
            self.logger.debug(f"[{self.server_name}] update_redis_weather_dataをskip_areaを引数に実行します。")
            try:
                # skip_areaを引数としてupdate_redis_weather_dataを呼び出す
                updated_skip_area = update_redis_weather_data(debug=self.debug, area_codes=self.skip_area)
                self.skip_area = updated_skip_area
                self.logger.debug(f"[{self.server_name}] skip_areaの更新完了。現在のskip_area: {self.skip_area}")
            except Exception as e:
                print(f"[{self.server_name}] skip_area更新エラー: {e}")
                self.logger.debug(traceback.format_exc())
        else:
            self.logger.debug(f"[{self.server_name}] skip_areaは空です。更新はスキップされます。")

    def _update_disaster_alert_scheduled(self):
        """
        スケジュールされた災害情報と気象注意報の更新処理
        """
        self.logger.debug(f"[{self.server_name}] スケジュールされた災害情報と気象注意報の更新を実行中...")
        try:
            # WIP_Server/scripts/update_alert_disaster_data.py の main() 関数を呼び出す
            update_alert_disaster_main()
            self.logger.debug(f"[{self.server_name}] 災害情報と気象注意報の更新完了。")
        except Exception as e:
            print(f"[{self.server_name}] 災害情報と気象注意報の更新エラー: {e}")
            self.logger.debug(traceback.format_exc())


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='気象データサーバーを起動します')
    parser.add_argument('--noupdate', action='store_true', help='起動時の自動気象情報更新をスキップ')
    args = parser.parse_args()

    # 設定ファイルから読み込んで起動
    server = QueryServer(noupdate=args.noupdate)
    server.run()
