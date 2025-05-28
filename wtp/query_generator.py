"""
気象データサーバー - リファクタリング版
基底クラスを継承した実装
"""

import concurrent.futures
import sys
import os
import threading
import time

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # モジュールとして使用される場合
    from .base_server import BaseServer
    from .query_generator_modules.config_manager import ConfigManager
    from .query_generator_modules.weather_data_manager import WeatherDataManager
    from .query_generator_modules.response_builder import ResponseBuilder
    from .query_generator_modules.debug_helper import DebugHelper, PerformanceTimer
    from .query_generator_modules.weather_constants import ThreadConstants
    from packet import Request
except ImportError:
    # 直接実行される場合
    from base_server import BaseServer
    from query_generator_modules.config_manager import ConfigManager
    from query_generator_modules.weather_data_manager import WeatherDataManager
    from query_generator_modules.response_builder import ResponseBuilder
    from query_generator_modules.debug_helper import DebugHelper, PerformanceTimer
    from query_generator_modules.weather_constants import ThreadConstants
    # packetモジュールのインポート
    try:
        from wtp.packet import Request
    except ImportError:
        from packet import Request


class QueryGenerator(BaseServer):
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
        self.server_name = "QueryGenerator"
        
        # 各コンポーネントの初期化
        self._init_components()
        
        if self.debug:
            print(f"QueryGenerator initialized:")
            print(self.config)
    
    def _init_components(self):
        """各コンポーネントを初期化"""
        self.debug_helper = DebugHelper(self.config.debug)
        self.weather_manager = WeatherDataManager(self.config)
        self.response_builder = ResponseBuilder(self.config)
        
        # 基底クラスのスレッドプールを使用するため、独自のスレッドプールは不要
    
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
        return self.response_builder.validate_request(request)
    
    def create_response(self, request):
        """
        レスポンスを作成
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            レスポンスのバイナリデータ
        """
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
        
        # レスポンスを作成
        response = self.response_builder.create_response(
            request, request.area_code, weather_data
        )
        
        return response
    
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
    
    def run(self):
        """気象データサーバーを並列処理で開始（オーバーライド）"""
        print(f"Weather data server running on {self.host}:{self.port}")
        print(f"Parallel processing enabled with {self.config.max_workers} worker threads")
        
        if self.debug:
            print(f"Debug mode enabled")
            print(f"Redis: {self.config.redis_host}:{self.config.redis_port}")
        
        self.start_time = time.time()
        
        try:
            while True:
                try:
                    # リクエストを受信
                    data, addr = self.sock.recvfrom(self.config.udp_buffer_size)
                    
                    self.debug_helper.print_info(
                        f"Main thread: Received request from {addr}, submitting to worker pool"
                    )
                    
                    # スレッドプールにリクエスト処理を投入
                    self.thread_pool.submit(self.handle_request_parallel, data, addr)
                    
                except Exception as e:
                    print(f"Error receiving request: {e}")
                    continue
                    
        except KeyboardInterrupt:
            print("\nShutting down server...")
            self.shutdown()
        except Exception as e:
            print(f"Fatal error in main loop: {e}")
            self.shutdown()
    
    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理（オーバーライド）"""
        print("Shutting down thread pool...")
        self.thread_pool.shutdown(wait=True)
        print("Thread pool shutdown complete.")


if __name__ == "__main__":
    # 使用例：デバッグモードで起動
    server = QueryGenerator(debug=True)
    server.run()
