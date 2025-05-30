"""
気象データサーバー - リファクタリング版
基底クラスを継承した実装
"""


import sys
import os
import time

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    # モジュールとして使用される場合
    from ..base_server import BaseServer
    from .modules.config_manager import ConfigManager
    from .modules.weather_data_manager import WeatherDataManager
    from .modules.response_builder import ResponseBuilder
    from .modules.debug_helper import DebugHelper, PerformanceTimer
    from .modules.weather_constants import ThreadConstants
    from ...packet import Request, Response, BitFieldError
except ImportError:
    # 直接実行される場合
    from wtp.servers.base_server import BaseServer
    from wtp.servers.query_server.modules.config_manager import ConfigManager
    from wtp.servers.query_server.modules.weather_data_manager import WeatherDataManager
    from wtp.servers.query_server.modules.response_builder import ResponseBuilder
    from wtp.servers.query_server.modules.debug_helper import DebugHelper, PerformanceTimer
    from wtp.servers.query_server.modules.weather_constants import ThreadConstants
    from wtp.packet import Request, Response, BitFieldError


class QueryServer(BaseServer):
    """気象データサーバーのメインクラス（基底クラス継承版）"""
    
    def __init__(self, host=None, port=None, debug=None, max_workers=None):
        """
        初期化
        
        Args:
            host: サーバーホスト（Noneの場合は設定から取得）
            port: サーバーポート（Noneの場合は設定から取得）
            debug: デバッグモード（Noneの場合は設定から取得）
            max_workers: ワーカー数（Noneの場合は設定から取得）
        """
        # 設定管理の初期化
        self.config = ConfigManager()
        
        # パラメータの上書き
        if host is not None:
            self.config.server_host = host
        if port is not None:
            self.config.server_port = port
        if debug is not None:
            self.config.debug = debug
        if max_workers is not None:
            self.config.max_workers = max_workers
        
        # 設定の妥当性チェック
        self.config.validate_config()
        
        # 基底クラスの初期化（max_workersも渡す）
        super().__init__(
            host=self.config.server_host,
            port=self.config.server_port,
            debug=self.config.debug,
            max_workers=self.config.max_workers
        )
        
        # サーバー名を設定
        self.server_name = "QueryServer"
        
        # 各コンポーネントの初期化
        self._init_components()
        
        if self.debug:
            print(f"QueryServer initialized:")
            print(self.config)
    
    def _init_components(self):
        """各コンポーネントを初期化"""
        self.debug_helper = DebugHelper(self.config.debug)
        self.weather_manager = WeatherDataManager(self.config)
        self.response_builder = ResponseBuilder(self.config)
    
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
                   request.pops_flag, request.alert_flag, request.disaster_flag]):
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
            pops_flag=request.pops_flag,
            alert_flag=request.alert_flag,
            disaster_flag=request.disaster_flag,
            ex_flag=1
        )
        
        # 気象データを取得
        weather_data = self.weather_manager.get_weather_data(
            area_code=request.area_code,
            weather_flag=request.weather_flag,
            temperature_flag=request.temperature_flag,
            pops_flag=request.pops_flag,
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
            
            if request.temperature_flag and 'temperature' in weather_data:
                # 文字列を整数に変換（リストの場合は最初の要素）
                temp_data = weather_data['temperature']
                if isinstance(temp_data, list):
                    actual_temp = int(temp_data[0]) if temp_data else 25
                else:
                    actual_temp = int(temp_data) if temp_data else 25
                # パケットフォーマットに合わせて変換（実際の温度 + 100）
                response.temperature = actual_temp + 100
            
            if request.pops_flag and 'precipitation' in weather_data:
                # 文字列を整数に変換（リストの場合は最初の要素）
                pops_value = weather_data['precipitation']
                if isinstance(pops_value, list):
                    response.pops = int(pops_value[0]) if pops_value else 0
                else:
                    response.pops = int(pops_value) if pops_value else 0
            
            # 拡張フィールドの処理
            if request.ex_flag:
                response.ex_field = {}
                
                # sourceを引き継ぐ
                if hasattr(request, 'ex_field') and request.ex_field and 'source' in request.ex_field:
                    response.ex_field['source'] = request.ex_field['source']
                
                # alert/disasterを追加
                if request.alert_flag and 'warnings' in weather_data:
                    response.ex_field['alert'] = weather_data['warnings']
                
                if request.disaster_flag and 'disaster_info' in weather_data:
                    response.ex_field['disaster'] = weather_data['disaster_info']
        
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
        print(f"PoPs: {parsed.pops_flag}")
        print(f"Alert: {parsed.alert_flag}")
        print(f"Disaster: {parsed.disaster_flag}")
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
            if resp_obj.pops_flag:
                print(f"Precipitation: {resp_obj.pops}%")
            if resp_obj.ex_field:
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
    # 使用例：デバッグモードで起動
    server = QueryServer(host = "0.0.0.0", port = 4111, debug=True)
    server.run()
