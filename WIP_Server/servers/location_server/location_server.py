"""
位置解決サーバー - リファクタリング版
基底クラスを継承した実装
"""

import psycopg2
from psycopg2 import pool
import time
import sys
import os
from pathlib import Path
from datetime import datetime
from common.utils.cache import Cache
from common.packet import ErrorResponse

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# モジュールとして使用される場合
from ..base_server import BaseServer
from common.packet import Request, Response, BitFieldError, DynamicFormat
# YAML 定義ファイルへのパス
ROOT_DIR = Path(__file__).resolve().parents[3]
REQUEST_YAML = ROOT_DIR / "common" / "packet" / "request_format.yml"
RESPONSE_YAML = ROOT_DIR / "common" / "packet" / "response_format.yml"
from common.utils.config_loader import ConfigLoader


class LocationServer(BaseServer):
    """位置解決サーバーのメインクラス（基底クラス継承版）"""
    
    def __init__(self, host=None, port=None, debug=None, max_workers=None, max_cache_size=None):
        """
        初期化
        
        Args:
            host: サーバーホスト（Noneの場合は設定ファイルから取得）
            port: サーバーポート（Noneの場合は設定ファイルから取得）
            debug: デバッグモードフラグ（Noneの場合は設定ファイルから取得）
            max_workers: スレッドプールのワーカー数（Noneの場合は設定ファイルから取得）
            max_cache_size: キャッシュの最大サイズ（Noneの場合は設定ファイルから取得）
        """
        # 設定ファイルを読み込む
        config_path = Path(__file__).parent / 'config.ini'
        self.config = ConfigLoader(config_path)
        
        # サーバー設定を取得（引数優先、なければ設定ファイル、なければデフォルト）
        if host is None:
            host = self.config.get('server', 'host', '0.0.0.0')
        if port is None:
            port = self.config.getint('server', 'port', 4109)
        if debug is None:
            debug_str = self.config.get('server', 'debug', 'false')
            debug = debug_str.lower() == 'true'
        if max_workers is None:
            max_workers = self.config.getint('server', 'max_workers', None)
        if max_cache_size is None:
            max_cache_size = self.config.getint('cache', 'max_cache_size', 1000)
        
        # データベース設定を読み込む
        self.DB_NAME = self.config.get('database', 'name', 'weather_forecast_map')
        self.DB_USER = self.config.get('database', 'user', 'postgres')
        self.DB_PASSWORD = self.config.get('database', 'password')
        self.DB_HOST = self.config.get('database', 'host', 'localhost')
        self.DB_PORT = self.config.get('database', 'port', '5432')
        
        # パスワードが設定されていない場合はエラー
        if not self.DB_PASSWORD:
            raise ValueError("Database password is not set. Please set DB_PASSWORD in environment variables.")
        
        # 基底クラスの初期化
        super().__init__(host, port, debug, max_workers)
        
        # サーバー名を設定
        self.server_name = "LocationServer"
        
        # プロトコルバージョンを設定から取得
        self.version = self.config.getint('system', 'protocol_version', 1)
        
        # データベース接続とキャッシュの初期化
        self._init_database()
        self._init_cache(max_cache_size)
        
        # Weather server configuration
        self.weather_host = "127.0.0.1"  # Default to localhost
        
        if self.debug:
            print(f"\n[位置情報サーバー] 設定:")
            print(f"  Server: {host}:{port}")
            print(f"  Database: {self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}")
            print(f"  Cache size: {max_cache_size}")
            print(f"  Protocol Version: {self.version}")
    
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
                print(f"データベース {self.DB_NAME} に正常に接続しました")
            
        except (Exception, psycopg2.Error) as error:
            print(f"PostgreSQL データベースへの接続エラー: {error}")
            if hasattr(self, 'connection_pool'):
                self.connection_pool.closeall()
            raise SystemExit(1)
    
    def _init_cache(self, max_cache_size):
        """キャッシュを初期化"""
        self.cache = Cache()
        if self.debug:
            print(f"TTLベースのキャッシュを初期化しました")
    
    def parse_request(self, data):
        """
        リクエストデータをパース
        
        Args:
            data: 受信したバイナリデータ
            
        Returns:
            Request: パースされたリクエスト
        """
        dyn = DynamicFormat.from_bytes(str(REQUEST_YAML), data)
        if dyn.values.get("type") == 7:
            return ErrorResponse.from_bytes(data)
        return Request(bitstr=dyn.to_bits())

    def handle_request(self, data, addr):
        """エラーパケットを中継"""
        try:
            req = self.parse_request(data)
            if req.type == 7:
                if req.ex_field and req.ex_field.contains('source'):
                    source = req.ex_field.source
                    if isinstance(source, tuple) and len(source) == 2:
                        host, port = source
                        try:
                            port = int(port)
                            self.sock.sendto(data, (host, port))
                            if self.debug:
                                print(f"[位置情報サーバー] エラーパケットを {host}:{port} に転送しました")
                        except Exception as e:
                            print(f"[位置情報サーバー] エラーパケット転送失敗: {e}")
                return
        except Exception:
            pass
        super().handle_request(data, addr)
    
    def validate_request(self, request):
        """
        リクエストの妥当性をチェック
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_code, error_message)
        """
        # 拡張フィールドが必要
        if not hasattr(request, 'ex_flag') or request.ex_flag != 1:
            return False, "400", "ex_flag が 1 ではありません"
        
        # 緯度経度が必要
        if not hasattr(request, 'ex_field') or not request.ex_field:
            return False, "400", "ex_field がありません"
        
        # ExtendedFieldオブジェクトのgetメソッドを使用
        latitude = request.ex_field.get("latitude")
        longitude = request.ex_field.get("longitude")
        if not latitude or not longitude:
            return False, "401", "座標が不足しています"
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
            # sourceをコピー
            if hasattr(request, "ex_field") and request.ex_field:
                src = request.ex_field.get("source")
                if src:
                    error_response.ex_field.source = src
                    error_response.ex_flag = 1
            return error_response.to_bytes()
    
        # 位置情報から地域コードを取得
        try:
            area_code = self.get_district_code(
                request.ex_field.get("longitude"),
                request.ex_field.get("latitude")
            )
            
            # レスポンスを作成
            resp = DynamicFormat.load(str(RESPONSE_YAML))
            resp.set(version=self.version, packet_id=request.packet_id, type=1, day=request.day, weather_flag=request.weather_flag, temperature_flag=request.temperature_flag, pop_flag=request.pop_flag, alert_flag=request.alert_flag, disaster_flag=request.disaster_flag, ex_flag=1, timestamp=int(datetime.now().timestamp()), area_code=int(area_code) if area_code else 0)
            
            # sourceのみを引き継ぐ（座標は破棄）
            # ExtendedFieldオブジェクトはResponseコンストラクタで自動作成される
            if hasattr(request, 'ex_field') and request.ex_field:
                source = request.ex_field.get('source')
                if source:
                    resp.ex_field.source = source
                    if self.debug:
                        print(f"[位置情報サーバー] 送信元をレスポンスにコピーしました: {source[0]}:{source[1]}")

                latitude = request.ex_field.get('latitude')
                longitude = request.ex_field.get('longitude')
                if latitude and longitude:
                    resp.ex_field.latitude = latitude
                    resp.ex_field.longitude = longitude
                    if self.debug:
                        print ("座標解決レスポンスに座標を追加しました")
            
            return resp.to_bytes()
            
        except Exception as e:
            # 内部エラー発生時は510エラーを返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code="510",
                timestamp=int(datetime.now().timestamp())
            )
            # sourceをコピー
            if hasattr(request, "ex_field") and request.ex_field:
                src = request.ex_field.get("source")
                if src:
                    error_response.ex_field.source = src
                    error_response.ex_flag = 1
            if self.debug:
                print(f"510: [位置情報サーバー] エラーレスポンスを生成: {error_response.error_code}")
            return error_response.to_bytes()
    
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
        cached_value = self.cache.get(cache_key)
        if cached_value is not None:
            if self.debug:
                print("キャッシュヒット！")
            return cached_value
        
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
            self.cache.set(cache_key, district_code)
            
            if self.debug:
                print(f"({longitude}, {latitude}) のクエリ結果: {district_code}")
            
            return district_code
            
        except Exception as e:
            print(f"データベースエラー: {e}")
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
            
        print("\n=== 受信リクエストパケット ===")
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
            print("リクエストに座標がありません")
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("===========================\n")
    
    def _debug_print_response(self, response, request=None):
        """レスポンスのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print("\n=== 送信レスポンスパケット ===")
        print(f"Total Length: {len(response)} bytes")
        
        # レスポンスから地域コードを抽出（デバッグ用）
        try:
            resp_obj = Response.from_bytes(response)
            print(f"Area Code: {resp_obj.area_code}")
        except:
            pass
        
        print(f"Weather Server IP: {self.weather_host}")
        print("\nRaw Packet:")
        print(self._hex_dump(response))
        print("============================\n")
    
    def _print_timing_info(self, addr, timing_info):
        """タイミング情報を出力（オーバーライド）"""
        # 基底クラスの処理に加えて、データベースクエリ時間も出力
        print(f"\n=== {addr} のタイミング情報 ===")
        print(f"Request parsing time: {timing_info.get('parse', 0)*1000:.2f}ms")
        
        # データベースクエリ時間は response creation に含まれる
        response_time = timing_info.get('response', 0)
        print(f"データベースクエリ + レスポンス作成時間: {response_time*1000:.2f}ms")
        
        print(f"レスポンス送信時間: {timing_info.get('send', 0)*1000:.2f}ms")
        print(f"総処理時間: {timing_info.get('total', 0)*1000:.2f}ms")
        print("================================\n")
    
    def print_statistics(self):
        """統計情報を出力（オーバーライド）"""
        # 基底クラスの統計情報
        super().print_statistics()
        
        # キャッシュの統計情報を追加
        if hasattr(self, 'cache'):
            print(f"\n=== キャッシュ統計 ===")
            print(f"Cache size: {self.cache.size()}")
            print("========================\n")
    
    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理（オーバーライド）"""
        # データベース接続プールをクローズ
        if hasattr(self, 'connection_pool'):
            print("データベース接続プールをクローズ中...")
            self.connection_pool.closeall()
            print("データベース接続をクローズしました。")


if __name__ == "__main__":
    # 設定ファイルから読み込んで起動
    server = LocationServer()
    server.run()
