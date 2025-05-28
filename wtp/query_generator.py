"""
気象データサーバー - リファクタリング版
責任分離とコードの簡潔性を重視した実装
"""

import socket
import threading
import concurrent.futures
import sys
import os
from packet import response_fixed
import redis
import time

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # モジュールとして使用される場合
    from .query_generator_modules.config_manager import ConfigManager
    from .query_generator_modules.weather_data_manager import WeatherDataManager
    from .query_generator_modules.response_builder import ResponseBuilder
    from .query_generator_modules.debug_helper import DebugHelper, PerformanceTimer
    from .query_generator_modules.weather_constants import ThreadConstants
    from packet import Request
except ImportError:
    # 直接実行される場合
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


class QueryGenerator:
    """気象データサーバーのメインクラス"""
    
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
        
        # 各コンポーネントの初期化
        self._init_components()
        
        # ネットワークの初期化
        self._init_network()
        
        if self.config.debug:
            print(f"QueryGenerator initialized:")
            print(self.config)
    
    def _init_components(self):
        """各コンポーネントを初期化"""
        self.debug_helper = DebugHelper(self.config.debug)
        self.weather_manager = WeatherDataManager(self.config)
        self.response_builder = ResponseBuilder(self.config)
        
        # スレッドプールの初期化
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.config.max_workers,
            thread_name_prefix=ThreadConstants.THREAD_NAME_PREFIX
        )
    
    def _init_network(self):
        """ネットワークソケットを初期化"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.config.server_host, self.config.server_port))
    
    def _parse_request(self, data):
        """
        リクエストデータをパース
        
        Args:
            data: 受信したバイナリデータ
            
        Returns:
            Request: パースされたリクエスト
        """
        return Request.from_bytes(data)
    
    def _validate_request(self, request):
        """
        リクエストの妥当性をチェック
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_message)
        """
        return self.response_builder.validate_request(request)

    def handle_request(self, data, addr):
        """
        個別のリクエストを処理する（並列実行用）
        
        Args:
            data: 受信したバイナリデータ
            addr: 送信元アドレス
        """
        timer = PerformanceTimer()
        timer.start()
        
        try:
            self.debug_helper.print_thread_info("Processing request", addr)
            
            # リクエストをパース
            timer.mark("parse_start")
            request = self._parse_request(data)
            timer.mark("parse_end")
            self.debug_helper.print_request_debug(data, request)
            
            # リクエストの妥当性をチェック
            is_valid, error_msg = self._validate_request(request)
            if not is_valid:
                self.debug_helper.print_error(error_msg, addr)
                return
            
            # 気象データを取得
            timer.mark("db_start")
            weather_data = self.weather_manager.get_weather_data(
                area_code=request.area_code,
                weather_flag=request.weather_flag,
                temperature_flag=request.temperature_flag,
                pops_flag=request.pops_flag,
                alert_flag=request.alert_flag,
                disaster_flag=request.disaster_flag,
                day=request.day
            )
            timer.mark("db_end")
            
            # レスポンスを作成
            timer.mark("response_start")
            response = self.response_builder.create_response(
                request, request.area_code, weather_data
            )
            timer.mark("response_end")
            self.debug_helper.print_response_debug(response)
            
            # レスポンスを送信
            timer.mark("send_start")
            self.sock.sendto(response, addr)
            timer.mark("send_end")
            
            # タイミング情報を出力
            if self.config.debug:
                timing_data = {
                    "Request parsing": timer.get_timing("parse_end") - timer.get_timing("parse_start"),
                    "Database query": timer.get_timing("db_end") - timer.get_timing("db_start"),
                    "Response creation": timer.get_timing("response_end") - timer.get_timing("response_start"),
                    "Response send": timer.get_timing("send_end") - timer.get_timing("send_start"),
                    "Total processing": timer.get_timing("send_end")
                }
                self.debug_helper.print_timing_info(
                    threading.current_thread().name, addr, timing_data
                )
            
            self.debug_helper.print_thread_info("Sent response", addr)
            
        except Exception as e:
            self.debug_helper.print_error("Error processing request", addr, e)

    def run(self):
        """気象データサーバーを並列処理で開始"""
        print(f"Weather data server running on {self.config.server_host}:{self.config.server_port}")
        print(f"Parallel processing enabled with {self.config.max_workers} worker threads")
        
        if self.config.debug:
            print(f"Debug mode enabled")
            print(f"Redis: {self.config.redis_host}:{self.config.redis_port}")
        
        try:
            while True:
                try:
                    # リクエストを受信
                    data, addr = self.sock.recvfrom(self.config.udp_buffer_size)
                    
                    self.debug_helper.print_info(
                        f"Main thread: Received request from {addr}, submitting to worker pool"
                    )
                    
                    # スレッドプールにリクエスト処理を投入
                    self.thread_pool.submit(self.handle_request, data, addr)
                    
                except Exception as e:
                    print(f"Error receiving request: {e}")
                    continue
                    
        except KeyboardInterrupt:
            print("\nShutting down server...")
            self.shutdown()
        except Exception as e:
            print(f"Fatal error in main loop: {e}")
            self.shutdown()
    
    def shutdown(self):
        """サーバーを適切にシャットダウン"""
        print("Shutting down thread pool...")
        self.thread_pool.shutdown(wait=True)
        print("Closing socket...")
        self.sock.close()
        print("Server shutdown complete.")


    ## レスポンスを作成する
    def create_response(self, request):
        day = request.get('day',0)
        response = response_fixed.Response(
            version=self.VERSION,
            type=self.RESPONSE_TYPE, 
            area_code = request.area_code,
            day = day,
            timestamp=int(time.time()),
            flags={
                'weather': request['flags'].get('weather', 0),
                'temperature': request['flags'].get('temperature', 0),
                'pops': request['flags'].get('pops', 0),
                'alert': request['flags'].get('alert', 0),
                'disaster': request['flags'].get('disaster', 0),
                'ex_field': request['flags'].get('ex_field', 0)
            }
        )

        r = redis.Redis(host='localhost', port=6379, db=0)
        region_info = r.get(str(response.area_code))
            
        if region_info is None:
            region_info = {
            "天気": [],
            "気温": [],
            "降水確率": [],
            "注意報・警報": [],
            "災害情報": []
            }

        # 必要なデータを抽出し、responseにセット
        if response.flags.get('weather', 0) == 1:
            weather_list = region_info.get('天気', [0]*7)
            if len(weather_list) > day:
                response.weather_code = weather_list[day]
            else:
                response.weather_code = weather_list[-1] if weather_list else 0

        if response.flags.get('temperature', 0) == 1:
            temp_list = region_info.get('気温', [0]*7)
            if len(temp_list) > day:
                response.temperature = temp_list[day]
            else:
                response.temperature = temp_list[-1] if temp_list else 0

        if response.flags.get('pops', 0) == 1:
            pops_list = region_info.get('降水確率', [0]*7)
            if len(pops_list) > day:
                response.precipitation = pops_list[day]
            else:
                response.precipitation = pops_list[-1] if pops_list else 0

        if response.flags.get('alert', 0) == 1:
            alert_list = region_info.get('注意報・警報', [])
            response.alert = alert_list

        if response.flags.get('disaster', 0) == 1:
            disaster_list = region_info.get('災害情報', [])
            response.disaster = disaster_list

if __name__ == "__main__":
    # 使用例：デバッグモードで起動
    server = QueryGenerator(debug=True)
    server.run()

