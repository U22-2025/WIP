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
from .modules.debug_helper import DebugHelper, PerformanceTimer
from .modules.weather_constants import ThreadConstants
from common.packet import Request, Response, BitFieldError, DynamicFormat
from common.utils.config_loader import ConfigLoader
from common.packet import ErrorResponse
# YAML定義ファイルのパス
ROOT_DIR = Path(__file__).resolve().parents[3]
REQUEST_YAML = ROOT_DIR / "common" / "packet" / "request_format.yml"
RESPONSE_YAML = ROOT_DIR / "common" / "packet" / "response_format.yml"
from WIP_Server.scripts.update_weather_data import update_redis_weather_data


class QueryServer(BaseServer):
    """気象データサーバーのメインクラス（基底クラス継承版）"""
    
    def __init__(self, host=None, port=None, debug=None, max_workers=None):
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
        
        # プロトコルバージョンを設定から取得
        self.version = self.config.getint('system', 'protocol_version', 1)
        
        # 各コンポーネントの初期化
        self._init_components()
        
        # スキップエリアリストを初期化
        self.skip_area = []

        # スケジューラーを開始
        self._start_weather_update_scheduler()

        if self.debug:
            print(f"\n[クエリサーバー] 設定:")
            print(f"  Server: {host}:{port}")
            print(f"  Protocol Version: {self.version}")
            print(f"  Max Workers: {max_workers}")
    
    def _init_components(self):
        """各コンポーネントを初期化"""
        # デバッグヘルパー
        self.debug_helper = DebugHelper(self.debug)
        
        # 気象データマネージャー（設定情報を渡す）
        weather_config = {
            'redis_host': self.config.get('redis', 'host', 'localhost'),
            'redis_port': self.config.getint('redis', 'port', 6379),
            'redis_db': self.config.getint('redis', 'db', 0),
            'weather_output_file': self.config.get('database', 'weather_output_file', 'wip/resources/test.json'),
            'debug': self.debug,
            'max_workers': self.max_workers,
            'version': self.version
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
        dyn = DynamicFormat.from_bytes(str(REQUEST_YAML), data)
        return Request(bitstr=dyn.to_bits())
    
    def validate_request(self, request):
        """
        リクエストの妥当性をチェック
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_message)
        """
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
            if self.debug:
                print(f"{error_code}: [クエリサーバー] エラーレスポンスを生成: {error_code}")
            return error_response.to_bytes()

        try:
            # デバッグ：リクエストの状態を確認
            if self.debug:
                print(f"\n[クエリサーバー] リクエストに対するレスポンスを作成中:")
                print(f"  Area code: {request.area_code}")
                print(f"  ex_flag: {request.ex_flag}")
                if hasattr(request, 'ex_field'):
                    print(f"  ex_field: {request.ex_field}")
                else:
                    print("  ex_field 属性がありません！")
            
            # レスポンスオブジェクトを作成
            response = Response(
                version=self.version,
                packet_id=request.packet_id,
                type=3,  # Response type (Type 3 for weather data response)
                area_code=request.area_code,
                day=request.day,
                timestamp=int(datetime.now().timestamp()),
                weather_flag=request.weather_flag,
                temperature_flag=request.temperature_flag,
                pop_flag=request.pop_flag,
                alert_flag=request.alert_flag,
                disaster_flag=request.disaster_flag,
                ex_flag=0  # 初期値は0
            )
            
            # ex_fieldの処理（ExtendedFieldオブジェクトはResponseコンストラクタで自動作成される）
            if hasattr(request, 'ex_field') and request.ex_field:
                # sourceがある場合は必ずコピー
                source = request.ex_field.get('source')
                if source:
                    response.ex_field.set('source', source)
                    response.ex_flag = 1  # ex_fieldがあるのでフラグを1に
                    if self.debug:
                        print(f"[クエリサーバー] 送信元をレスポンスにコピーしました: {source}")

                lat = request.ex_field.get('latitude')
                long = request.ex_field.get('longitude')
                # lat, long = request.get_coordinates()
                if lat and long:
                    response.ex_field.set('latitude', lat)
                    response.ex_field.set('longitude', long)
                    response.ex_flag = 1  # ex_fieldがあるのでフラグを1に
                    if self.debug:
                        print(f"[クエリサーバー] 座標をレスポンスにコピーしました: {lat},{long}")

            else:
                if self.debug:
                    print("[クエリサーバー] 警告: リクエストに ex_field がありません！")
            
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
            
            # 気象データをレスポンスに設定
            if weather_data:
                if request.weather_flag and 'weather' in weather_data:
                    # 文字列を整数に変換（リストの場合は最初の要素）
                    weather_value = weather_data['weather']
                    if isinstance(weather_value, list):
                        response.weather_code = int(weather_value[0]) if weather_value else 0
                    else:
                        response.weather_code = int(weather_value) if weather_value else 0
                else:
                    response.weather_code = 0
                
                if request.temperature_flag and 'temperature' in weather_data:
                    # 文字列を整数に変換（リストの場合は最初の要素）
                    temp_data = weather_data['temperature']
                    if isinstance(temp_data, list):
                        actual_temp = int(temp_data[0]) if temp_data else 25
                    else:
                        actual_temp = int(temp_data) if temp_data else 25
                    # パケットフォーマットに合わせて変換（実際の温度 + 100）
                    response.temperature = actual_temp + 100
                else:
                    response.temperature = 100  # 0℃
                
                if request.pop_flag and 'precipitation_prob' in weather_data:
                    # 文字列を整数に変換（リストの場合は最初の要素）
                    pop_value = weather_data['precipitation_prob']
                    if isinstance(pop_value, list):
                        response.pop = int(pop_value[0]) if pop_value else 0
                    else:
                        response.pop = int(pop_value) if pop_value else 0
                else:
                    response.pop = 0
                
                # alert/disasterを追加（ExtendedFieldのsetメソッドを使用）
                if request.alert_flag and 'warnings' in weather_data:
                    warnings = weather_data['warnings']
                    if not isinstance(warnings, list):
                        warnings = [warnings]
                    response.ex_field.set('alert', warnings)
                    response.ex_flag = 1
                
                if request.disaster_flag and 'disaster' in weather_data:
                    response.ex_field.set('disaster', weather_data['disaster'])
                    response.ex_flag = 1
            else:
                # デフォルト値を設定
                if request.weather_flag:
                    response.weather_code = 0
                if request.temperature_flag:
                    response.temperature = 100  # 0℃
                if request.pop_flag:
                    response.pop = 0
        except Exception as e:
            # 内部エラー発生時は500エラーを返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code="520",
                timestamp=int(datetime.now().timestamp())
            )
            if self.debug:
                print(f"520: [クエリサーバー] エラーレスポンスを生成: {error_code}")
            return error_response.to_bytes()
        
        # 最終確認
        if self.debug:
            print(f"[クエリサーバー] 最終レスポンス状態:")
            print(f"  ex_flag: {response.ex_flag}")
            print(f"  ex_field: {response.ex_field}")
        
        dyn_resp = DynamicFormat.load(str(RESPONSE_YAML))
        dyn_resp.set(**{k: getattr(response,k) for k in ["version","packet_id","type","weather_flag","temperature_flag","pop_flag","alert_flag","disaster_flag","ex_flag","day","reserved","timestamp","area_code","checksum","weather_code","temperature","pop"] if hasattr(response,k)})
        dyn_resp.set_extended(**response.ex_field.to_dict())
        return dyn_resp.to_bytes()
    
    def _debug_print_request(self, data, parsed):
        """リクエストのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print("\n=== 受信リクエストパケット ===")
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
        
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("===========================\n")
    
    def _debug_print_response(self, response, request=None):
        """レスポンスのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print("\n=== 送信レスポンスパケット ===")
        print(f"Total Length: {len(response)} bytes")
        
        # レスポンスオブジェクトの詳細情報を表示
        try:
            resp_obj = Response.from_bytes(response)
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
        
        print("\nRaw Packet:")
        print(self._hex_dump(response))
        print("============================\n")
    
    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理（オーバーライド）"""
        # WeatherDataManagerのクリーンアップ
        if hasattr(self, 'weather_manager'):
            self.weather_manager.close()

    def _start_weather_update_scheduler(self):
        """
        気象データ更新のスケジューラーを開始
        """
        update_times_str = self.config.get('schedule', 'weather_update_time', '03:00')
        update_times = [t.strip() for t in update_times_str.split(',')]
        
        if self.debug:
            print(f"[クエリサーバー] 気象データ更新を毎日 {', '.join(update_times)} にスケジュールします。")
        
        for update_time in update_times:
            schedule.every().day.at(update_time).do(self.update_weather_data_scheduled)
        
        # configからskip_areaの確認と更新間隔を取得
        skip_area_interval = self.config.getint('schedule', 'skip_area_check_interval_minutes', 10)
        if self.debug:
            print(f"[クエリサーバー] skip_areaの確認と更新を {skip_area_interval} 分ごとにスケジュールします。")
        schedule.every(skip_area_interval).minutes.do(self.check_and_update_skip_area_scheduled)

        # スケジュールを実行するスレッドを開始
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(30) # 30秒ごとにチェック

        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()

    def update_weather_data_scheduled(self):
        """
        スケジュールされた気象データ更新処理
        """
        if self.debug:
            print(f"[クエリサーバー] スケジュールされた気象データ更新を実行中...")
        try:
            # WIP_Server/scripts/update_weather_data.py の関数を呼び出す
            self.skip_area = update_redis_weather_data(debug=self.debug)
            if self.debug:
                print(f"[クエリサーバー] 気象データ更新完了。{len(self.skip_area)} エリアがスキップされました。")
        except Exception as e:
            print(f"[クエリサーバー] 気象データ更新エラー: {e}")
            if self.debug:
                traceback.print_exc()

    def check_and_update_skip_area_scheduled(self):
        """
        スケジュールされたskip_areaの確認と更新処理
        """
        if self.debug:
            print(f"[クエリサーバー] スケジュールされたskip_areaの確認と更新を実行中...")
        
        if self.skip_area:
            if self.debug:
                print(f"[クエリサーバー] skip_areaに地域コードが存在します: {self.skip_area}")
                print(f"[クエリサーバー] update_redis_weather_dataをskip_areaを引数に実行します。")
            try:
                # skip_areaを引数としてupdate_redis_weather_dataを呼び出す
                updated_skip_area = update_redis_weather_data(debug=self.debug, area_codes=self.skip_area)
                self.skip_area = updated_skip_area
                if self.debug:
                    print(f"[クエリサーバー] skip_areaの更新完了。現在のskip_area: {self.skip_area}")
            except Exception as e:
                print(f"[クエリサーバー] skip_area更新エラー: {e}")
                if self.debug:
                    traceback.print_exc()
        else:
            if self.debug:
                print(f"[クエリサーバー] skip_areaは空です。更新はスキップされます。")


if __name__ == "__main__":
    # 設定ファイルから読み込んで起動
    server = QueryServer()
    server.run()
