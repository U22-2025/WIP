"""
気象データサーバー - リファクタリング版
基底クラスを継承した実装
"""


import sys
import os
import time
from pathlib import Path

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# モジュールとして使用される場合
from ..base_server import BaseServer
from .modules.weather_data_manager import WeatherDataManager
from .modules.response_builder import ResponseBuilder
from .modules.debug_helper import DebugHelper, PerformanceTimer
from .modules.weather_constants import ThreadConstants
from common.packet import Request, Response, BitFieldError
from common.utils.config_loader import ConfigLoader


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
        
        if self.debug:
            print(f"\n[Query Server] Configuration:")
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
            'weather_output_file': self.config.get('database', 'weather_output_file', 'wtp/resources/test.json'),
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
        return Request.from_bytes(data)
    
    def validate_request(self, request):
        """
        リクエストの妥当性をチェック
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # バージョンとタイプのチェック
        if request.version != self.version or request.type != 2:
            return False, "Invalid version or type"
        
        # 地域コードのチェック
        if not request.area_code or request.area_code == "000000":
            return False, "Invalid area code"
        
        # フラグのチェック（少なくとも1つは必要）
        if not any([request.weather_flag, request.temperature_flag, 
                   request.pop_flag, request.alert_flag, request.disaster_flag]):
            return False, "No data flags set"
        
        return True, None
    
    def create_response(self, request):
        """
        レスポンスを作成
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            レスポンスのバイナリデータ
        """
        # デバッグ：リクエストの状態を確認
        if self.debug:
            print(f"\n[QueryServer] Creating response for request:")
            print(f"  Area code: {request.area_code}")
            print(f"  ex_flag: {request.ex_flag}")
            if hasattr(request, 'ex_field'):
                print(f"  ex_field: {request.ex_field}")
            else:
                print("  NO ex_field attribute!")
        
        # レスポンスオブジェクトを作成
        response = Response(
            version=self.version,
            packet_id=request.packet_id,
            type=3,  # Response type (Type 3 for weather data response)
            area_code=request.area_code,
            day=request.day,
            timestamp=int(time.time()),
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
                    print(f"[QueryServer] Copied source to response: {source}")
        else:
            if self.debug:
                print("[QueryServer] WARNING: No ex_field in request!")
        
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
                response.ex_field.set('alert', weather_data['warnings'])
                response.ex_flag = 1
            
            if request.disaster_flag and 'disaster_info' in weather_data:
                response.ex_field.set('disaster', weather_data['disaster_info'])
                response.ex_flag = 1
        else:
            # デフォルト値を設定
            if request.weather_flag:
                response.weather_code = 0
            if request.temperature_flag:
                response.temperature = 100  # 0℃
            if request.pop_flag:
                response.pop = 0
        
        # 最終確認
        if self.debug:
            print(f"[QueryServer] Final response state:")
            print(f"  ex_flag: {response.ex_flag}")
            print(f"  ex_field: {response.ex_field}")
        
        return response.to_bytes()
    
    def _debug_print_request(self, data, parsed):
        """リクエストのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print("\n=== RECEIVED REQUEST PACKET ===")
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
        else:
            print("\nNo ex_field attribute in parsed request!")
        
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("===========================\n")
    
    def _debug_print_response(self, response, request=None):
        """レスポンスのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print("\n=== SENDING RESPONSE PACKET ===")
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


if __name__ == "__main__":
    # 設定ファイルから読み込んで起動
    server = QueryServer()
    server.run()
