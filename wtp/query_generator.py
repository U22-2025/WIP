import socket
import struct
import time
import threading
import concurrent.futures
from collections import OrderedDict
import config
from packet import Request, Response
import redis


class QueryGenerator:
    def __init__(self, host='localhost', port=4111, debug=False, max_cache_size=1000, max_workers=20):
        self.DB_HOST = "localhost"
        self.DB_PORT = "6379"
        self.DB = 0
        self.VERSION = 1

        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.debug = debug
        
        # Redis接続プールの初期化
        self.redis_pool = redis.ConnectionPool(
            host=self.DB_HOST,
            port=self.DB_PORT,
            db=self.DB,
            max_connections=max_workers * 2,  # ワーカー数の2倍の接続を確保
            retry_on_timeout=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
        
        # スレッドプールの初期化
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="weather-worker"
        )
        
        # スレッドローカルストレージ
        self._thread_local = threading.local()
        
        if self.debug:
            print(f"Initialized with {max_workers} worker threads and Redis connection pool")
    
    def get_redis_client(self):
        """
        スレッドローカルなRedis接続を取得する
        
        Returns:
            redis.Redis: Redis接続オブジェクト
        """
        if not hasattr(self._thread_local, 'redis_client'):
            self._thread_local.redis_client = redis.Redis(connection_pool=self.redis_pool)
        return self._thread_local.redis_client
        
    def _hex_dump(self, data):
        """Create a hex dump of binary data"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
        
    def _debug_print_request(self, data, parsed):
        """Print debug information for request packet"""
        if not self.debug:
            return
            
        print("\n=== RECEIVED REQUEST PACKET ===")
        print(f"Total Length: {len(data)} bytes")
        print("\nCoordinates:")
        print(f"{parsed.ex_field}")
        # print(f"Longitude: {parsed.longitude}")
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("===========================\n")
        
    def _debug_print_response(self, response):
        """Print debug information for response packet"""
        if not self.debug:
            return
            
        print("\n=== SENDING RESPONSE PACKET ===")
        print(f"Total Length: {len(response)} bytes")
        print(f"Response : {response}")
        print("\nRaw Packet:")
        print(self._hex_dump(response))
        print("============================\n")

        
    def get_data_from_db(self, area_code, weather_flag, temperature_flag, pops_flag, alert_flag, disaster_flag, day):
        """
        Redisからエリアコードに基づいて気象データを取得する
        flagが1のもののみクエリを追加し、pipelineで一括実行する
        
        Args:
            area_code: エリアコード（文字列形式、例: "080010"）
            weather_flag: 天気データ取得フラグ (1で取得)
            temperature_flag: 気温データ取得フラグ (1で取得)
            pops_flag: 降水確率データ取得フラグ (1で取得)
            alert_flag: 警報データ取得フラグ (1で取得)
            disaster_flag: 災害情報データ取得フラグ (1で取得)
            
        Returns:
            dict: 取得したデータの辞書
        """
        try:
            # スレッドローカルなRedis接続を取得
            r = self.get_redis_client()
            
            # パイプラインを作成
            pipe = r.pipeline()
            
            # エリアコードを6桁の文字列に正規化
            if isinstance(area_code, int):
                area_code_str = f"{area_code:06d}"
            else:
                area_code_str = str(area_code).zfill(6)
            
            # エリアコードに基づくRedisキー
            weather_key = f"weather:{area_code_str}"
            
            # flagが1のもののみクエリを追加
            queries_added = []
            
            if weather_flag == 1:
                pipe.json().get(weather_key, f".weather[{day}]")
                queries_added.append("weather")
                
            if temperature_flag == 1:
                pipe.json().get(weather_key, f".temperature[{day}]")
                queries_added.append("temperature")
                
            if pops_flag == 1:
                pipe.json().get(weather_key, f".precipitation[{day}]")
                queries_added.append("precipitation")
                
            if alert_flag == 1:
                pipe.json().get(weather_key, f".warnings")
                queries_added.append("warnings")
                
            if disaster_flag == 1:
                pipe.json().get(weather_key, f".disaster_info")
                queries_added.append("disaster_info")
            
            # クエリが追加されていない場合は空の辞書を返す
            if not queries_added:
                if self.debug:
                    print("No flags set to 1, returning empty data")
                return {}
            
            # パイプラインを一括実行
            results = pipe.execute()
            
            # 結果を辞書にまとめる
            data = {}
            for i, query_type in enumerate(queries_added):
                data[query_type] = results[i] if results[i] is not None else []
            
            if self.debug:
                print(f"Retrieved data for area {area_code}: {data}")
                
            return data
            
        except redis.RedisError as e:
            print(f"Redis error in get_data_from_db: {e}")
            return {}
        except Exception as e:
            print(f"Error in get_data_from_db: {e}")
            return {}

    ## レスポンスを作成する
    def create_response(self, request, area_code, weather_data):
        """
        リクエストと気象データからレスポンスを作成する
        
        Args:
            request: リクエストパケット
            area_code: エリアコード
            weather_data: get_data_from_dbで取得した気象データ
            
        Returns:
            bytes: レスポンスパケットのバイト列
        """
        # 基本的なレスポンス情報
        response_params = {
            'version': self.VERSION,
            'packet_id': request.packet_id,
            'type': 3,  # レスポンスタイプ
            'ex_flag': 0,
            'timestamp': int(time.time()),
            'area_code': area_code
        }
        
        # 気象データがある場合は固定長拡張フィールドに設定
        if weather_data:
            # 天気コード (デフォルト値: 0)
            weather_code = 0
            if 'weather' in weather_data and weather_data['weather']:
                try:
                    weather_code = int(weather_data['weather']) if weather_data['weather'] else 0
                except (ValueError, IndexError):
                    weather_code = 0
            
            # 気温 (デフォルト値: 100 = 0℃)
            temperature = 100  # 0℃を表す
            if 'temperature' in weather_data and weather_data['temperature']:
                try:
                    temp_str = weather_data['temperature']
                    if temp_str and temp_str != "":
                        temp_val = int(float(temp_str))
                        temperature = temp_val + 100  # -100℃～+155℃を0-255で表現
                        temperature = max(0, min(255, temperature))  # 範囲制限
                except (ValueError, IndexError):
                    temperature = 100
            
            # 降水確率 (デフォルト値: 0%)
            pops = 0
            if 'precipitation' in weather_data and weather_data['precipitation']:
                try:
                    pops_str = weather_data['precipitation']
                    if pops_str and pops_str != "":
                        pops = int(pops_str)
                        pops = max(0, min(100, pops))  # 0-100%の範囲制限
                except (ValueError, IndexError):
                    pops = 0
            
            # 固定長拡張フィールドを追加
            response_params.update({
                'weather_code': weather_code,
                'temperature': temperature,
                'pops': pops
            })
            
            # 拡張フィールドがある場合
            ex_field = {}
            if 'warnings' in weather_data and weather_data['warnings']:
                ex_field['alert'] = weather_data['warnings']
            if 'disaster_info' in weather_data and weather_data['disaster_info']:
                ex_field['disaster'] = weather_data['disaster_info']
                
            if ex_field:
                response_params['ex_flag'] = 1
                response_params['ex_field'] = ex_field
        
        response = Response(**response_params)
        return response.to_bytes()

    def handle_request(self, data, addr):
        """
        個別のリクエストを処理する（並列実行用）
        
        Args:
            data: 受信したバイナリデータ
            addr: 送信元アドレス
        """
        try:
            thread_id = threading.current_thread().name
            if self.debug:
                print(f"[{thread_id}] Processing request from {addr}")
            
            # Start measuring processing time
            start_time = time.time()
            
            # Parse request
            parse_start = time.time()
            request = Request.from_bytes(data)
            parse_time = time.time() - parse_start
            self._debug_print_request(data, request)
            
            # リクエストタイプが2（気象データリクエスト）でない場合は無視
            if request.type != 2:
                if self.debug:
                    print(f"[{thread_id}] Invalid request type: {request.type}, expected 2")
                return
            
            # エリアコードが設定されていない場合は無視
            if not request.area_code:
                if self.debug:
                    print(f"[{thread_id}] No area code in request")
                return
            
            # Get weather data from Redis
            db_start = time.time()
            weather_data = self.get_data_from_db(
                area_code=request.area_code,
                weather_flag=request.weather_flag,
                temperature_flag=request.temperature_flag,
                pops_flag=request.pops_flag,
                alert_flag=request.alert_flag,
                disaster_flag=request.disaster_flag,
                day = request.day
            )
            db_time = time.time() - db_start
            
            # Create response
            response_start = time.time()
            response = self.create_response(request, request.area_code, weather_data)
            response_time = time.time() - response_start
            self._debug_print_response(response)
            
            # Send response and calculate total processing time
            send_start = time.time()
            self.sock.sendto(response, addr)
            send_time = time.time() - send_start
            
            total_processing_time = time.time() - start_time
            
            if self.debug:
                print(f"\n=== [{thread_id}] TIMING INFORMATION ===")
                print(f"Request receive time: {(parse_start - start_time)*1000:.2f}ms")
                print(f"Request parsing time: {parse_time*1000:.2f}ms")
                print(f"Database query time: {db_time*1000:.2f}ms")
                print(f"Response creation time: {response_time*1000:.2f}ms")
                print(f"Response send time: {send_time*1000:.2f}ms")
                print(f"Total processing time: {total_processing_time*1000:.2f}ms")
                print("========================\n")
                print(f"[{thread_id}] Sent response to {addr}")
            
        except Exception as e:
            thread_id = threading.current_thread().name
            print(f"[{thread_id}] Error processing request from {addr}: {e}")

    def run(self):
        """Start the weather data server with parallel processing"""
        print(f"Weather data server running on {self.host}:{self.port}")
        print(f"Parallel processing enabled with {self.thread_pool._max_workers} worker threads")
        
        try:
            while True:
                try:
                    # Receive request
                    data, addr = self.sock.recvfrom(1024)
                    if self.debug:
                        print(f"Main thread: Received request from {addr}, submitting to worker pool")
                    
                    # Submit request to thread pool for parallel processing
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
        """Gracefully shutdown the server"""
        print("Shutting down thread pool...")
        self.thread_pool.shutdown(wait=True)
        print("Closing socket...")
        self.sock.close()
        print("Server shutdown complete.")


if __name__ == "__main__":
    server = QueryGenerator(debug=True, max_cache_size=1000)
    server.run()
