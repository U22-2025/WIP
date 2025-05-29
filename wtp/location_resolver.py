"""
位置解決サーバー - リファクタリング版
基底クラスを継承した実装
"""

import socket
import struct
import psycopg2
from psycopg2 import pool
import time
from collections import OrderedDict
import sys
import os
from dotenv import load_dotenv

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # モジュールとして使用される場合
    from .base_server import BaseServer
    from .packet import Request, Response, BitFieldError
except ImportError:
    # 直接実行される場合
    from base_server import BaseServer
    from packet import Request, Response, BitFieldError


class LRUCache:
    """LRU（Least Recently Used）キャッシュの実装"""
    
    def __init__(self, maxsize=1000):
        self.cache = OrderedDict()
        self.maxsize = maxsize

    def __getitem__(self, key):
        value = self.cache.pop(key)
        self.cache[key] = value  # Move to end (most recently used)
        return value

    def __setitem__(self, key, value):
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)  # Remove least recently used
        self.cache[key] = value

    def __contains__(self, key):
        return key in self.cache


class LocationResolver(BaseServer):
    """位置解決サーバーのメインクラス（基底クラス継承版）"""
    
    def __init__(self, host='localhost', port=None, debug=False, max_workers=None, max_cache_size=None):
        """
        初期化
        
        Args:
            host: サーバーホスト
            port: サーバーポート（Noneの場合は環境変数から取得）
            debug: デバッグモードフラグ
            max_workers: スレッドプールのワーカー数（Noneの場合はCPU数*2）
            max_cache_size: キャッシュの最大サイズ（Noneの場合は環境変数から取得）
        """
        # 環境変数を読み込む
        load_dotenv()
        
        # ポートとキャッシュサイズを環境変数から取得
        if port is None:
            port = int(os.getenv('LOCATION_RESOLVER_PORT', 4109))
        if max_cache_size is None:
            max_cache_size = int(os.getenv('MAX_CACHE_SIZE', 1000))
        
        # Database configuration from environment
        self.DB_NAME = os.getenv('DB_NAME', 'weather_forecast_map')
        self.DB_USER = os.getenv('DB_USERNAME', 'postgres')
        self.DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
        self.DB_HOST = os.getenv('DB_HOST', 'localhost')
        self.DB_PORT = os.getenv('DB_PORT', '5432')
        
        # 基底クラスの初期化（max_workersも渡す）
        super().__init__(host, port, debug, max_workers)
        
        # サーバー名を設定
        self.server_name = "LocationResolver"
        
        # データベース接続とキャッシュの初期化
        self._init_database()
        self._init_cache(max_cache_size)
        
        # Weather server configuration
        self.weather_server_ip = "127.0.0.1"  # Default to localhost
    
    def _init_database(self):
        """データベース接続プールを初期化"""
        try:
            # Initialize connection pool
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                1,  # minimum number of connections
                10,  # maximum number of connections
                dbname=self.DB_NAME,
                user=self.DB_USER,
                password=self.DB_PASSWORD,
                host=self.DB_HOST,
                port=self.DB_PORT
            )
            
            # Test database connection
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            cursor.close()
            self.connection_pool.putconn(conn)
            
            if self.debug:
                print(f"Successfully connected to database {self.DB_NAME}")
            
        except (Exception, psycopg2.Error) as error:
            print(f"Error connecting to PostgreSQL database: {error}")
            if hasattr(self, 'connection_pool'):
                self.connection_pool.closeall()
            raise SystemExit(1)
    
    def _init_cache(self, max_cache_size):
        """キャッシュを初期化"""
        self.cache = LRUCache(maxsize=max_cache_size)
        if self.debug:
            print(f"Initialized LRU cache with max size: {max_cache_size}")
    
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
        # 拡張フィールドが必要
        if not hasattr(request, 'ex_flag') or request.ex_flag != 1:
            return False, "Extended field is required"
        
        # 緯度経度が必要
        if not hasattr(request, 'ex_field') or not request.ex_field:
            return False, "Extended field is empty"
        
        if not request.ex_field.get("latitude") or not request.ex_field.get("longitude"):
            return False, "Latitude and longitude are required"
        
        return True, None
    
    def create_response(self, request):
        """
        レスポンスを作成
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            レスポンスのバイナリデータ
        """
        # 位置情報から地域コードを取得
        area_code = self.get_district_code(
            request.ex_field.get("longitude"),
            request.ex_field.get("latitude")
        )
        
        # レスポンスを作成
        response = Response(
            version=self.version,
            packet_id=request.packet_id,
            type=1,  # Response type
            ex_flag=1,
            timestamp=int(time.time()),
            area_code=int(area_code) if area_code else 0
        )
        
        # sourceのみを引き継ぐ（座標は破棄）
        if hasattr(request, 'ex_field') and request.ex_field and 'source' in request.ex_field:
            response.ex_field = {'source': request.ex_field['source']}
        else:
            response.ex_field = {}
        
        return response.to_bytes()
    
    def get_district_code(self, longitude, latitude):
        """
        緯度経度から地域コードを取得（キャッシュ機能付き）
        
        Args:
            longitude: 経度
            latitude: 緯度
            
        Returns:
            地域コード（文字列）またはNone
        """
        # Create cache key
        cache_key = f"{longitude},{latitude}"
        
        # Check cache first
        if cache_key in self.cache:
            if self.debug:
                print("Cache hit!")
            return self.cache[cache_key]
        
        conn = None
        try:
            # Get connection from pool
            conn = self.connection_pool.getconn()
            cursor = conn.cursor()
            
            query = f"""
            SELECT code
            FROM districts
            WHERE ST_Within(
                ST_GeomFromText('POINT({longitude} {latitude})', 6668),
                geom
            );
            """
            cursor.execute(query)
            result = cursor.fetchone()
            
            district_code = result[0] if result else None
            
            # Store in cache
            self.cache[cache_key] = district_code
            
            if self.debug:
                print(f"Query result for ({longitude}, {latitude}): {district_code}")
            
            return district_code
            
        except Exception as e:
            print(f"Database error: {e}")
            return None
            
        finally:
            if conn:
                # Return connection to pool
                cursor.close()
                self.connection_pool.putconn(conn)
    
    def _debug_print_request(self, data, parsed):
        """リクエストのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print("\n=== RECEIVED REQUEST PACKET ===")
        print(f"Total Length: {len(data)} bytes")
        print("\nHeader:")
        print(f"Version: {parsed.version}")
        print(f"Type: {parsed.type}")
        print(f"Packet ID: {parsed.packet_id}")
        print("\nCoordinates:")
        if hasattr(parsed, 'ex_field') and parsed.ex_field:
            print(f"Latitude: {parsed.ex_field.get('latitude')}")
            print(f"Longitude: {parsed.ex_field.get('longitude')}")
        else:
            print("No coordinates in request")
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("===========================\n")
    
    def _debug_print_response(self, response, request=None):
        """レスポンスのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print("\n=== SENDING RESPONSE PACKET ===")
        print(f"Total Length: {len(response)} bytes")
        
        # レスポンスから地域コードを抽出（デバッグ用）
        try:
            resp_obj = Response.from_bytes(response)
            print(f"Area Code: {resp_obj.area_code}")
        except:
            pass
        
        print(f"Weather Server IP: {self.weather_server_ip}")
        print("\nRaw Packet:")
        print(self._hex_dump(response))
        print("============================\n")
    
    def _print_timing_info(self, addr, timing_info):
        """タイミング情報を出力（オーバーライド）"""
        # 基底クラスの処理に加えて、データベースクエリ時間も出力
        print(f"\n=== TIMING INFORMATION for {addr} ===")
        print(f"Request parsing time: {timing_info.get('parse', 0)*1000:.2f}ms")
        
        # データベースクエリ時間は response creation に含まれる
        response_time = timing_info.get('response', 0)
        print(f"Database query + Response creation time: {response_time*1000:.2f}ms")
        
        print(f"Response send time: {timing_info.get('send', 0)*1000:.2f}ms")
        print(f"Total processing time: {timing_info.get('total', 0)*1000:.2f}ms")
        print("================================\n")
    
    def print_statistics(self):
        """統計情報を出力（オーバーライド）"""
        # 基底クラスの統計情報
        super().print_statistics()
        
        # キャッシュの統計情報を追加
        if hasattr(self, 'cache'):
            print(f"\n=== CACHE STATISTICS ===")
            print(f"Cache size: {len(self.cache.cache)}/{self.cache.maxsize}")
            print("========================\n")
    
    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理（オーバーライド）"""
        # データベース接続プールをクローズ
        if hasattr(self, 'connection_pool'):
            print("Closing database connection pool...")
            self.connection_pool.closeall()
            print("Database connections closed.")


if __name__ == "__main__":
    server = LocationResolver(host = "0.0.0.0", port=4109, debug=True)
    server.run()
