"""
位置解決サーバー - リファクタリング版
基底クラスを継承した実装
"""

import psycopg2
from psycopg2 import pool
import sys
import os
from pathlib import Path
from datetime import datetime
from common.utils.cache import Cache
from common.packet import ErrorResponse
from common.packet import ExtendedField
from common.packet.debug.debug_logger import PacketDebugLogger
from ..common.log_config import UnifiedLogFormatter

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# モジュールとして使用される場合
from ..base_server import BaseServer
from common.packet import Request, Response
from common.utils.config_loader import ConfigLoader


class LocationServer(BaseServer):
    """位置解決サーバーのメインクラス（基底クラス継承版）"""
    
    def __init__(self, host=None, port=None, debug=None, max_workers=None, max_cache_size=None, config_path: str | Path | None = None):
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
        cfg_path = Path(config_path) if config_path else Path(__file__).parent / 'config.ini'
        self.config = ConfigLoader(cfg_path)
        
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
        self.cache_enabled = self.config.getboolean('cache', 'enable_cache', True)
        
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
        
        # 認証設定を初期化
        self._init_auth_config()
        
        # プロトコルバージョンを設定から取得
        self.version = self.config.getint('system', 'protocol_version', 1)
        
        # データベース接続とキャッシュの初期化
        self._setup_database()
        self._setup_cache(max_cache_size, self.cache_enabled)
        
        # 統一デバッグロガーの初期化
        self.packet_debug_logger = PacketDebugLogger("LocationServer")
    
    def _init_auth_config(self):
        """認証設定を環境変数から読み込み（LocationServer固有）"""
        # LocationServer自身の認証設定
        auth_enabled = os.getenv('LOCATION_SERVER_AUTH_ENABLED', 'false').lower() == 'true'
        auth_passphrase = os.getenv('LOCATION_SERVER_PASSPHRASE', '')
        
        self.auth_enabled = auth_enabled
        self.auth_passphrase = auth_passphrase
        
    
    def _setup_database(self):
        """データベース接続プールを初期化"""
        try:
            # Initialize connection pool
            self.connection_pool = pool.SimpleConnectionPool(
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
                print(f"[{self.server_name}] データベース {self.DB_NAME} に正常に接続しました")
            
        except (Exception, psycopg2.Error) as error:
            print(f"PostgreSQL データベースへの接続エラー: {error}")
            if hasattr(self, 'connection_pool'):
                self.connection_pool.closeall()
            raise SystemExit(1)
    
    def _setup_cache(self, max_cache_size, enabled=True):
        """キャッシュを初期化"""
        self.cache = Cache(enabled=enabled)
        if self.debug:
            state = "enabled" if enabled else "disabled"
            print(f"[{self.server_name}] TTLベースのキャッシュを初期化しました ({state})")
    
    def parse_request(self, data):
        """
        リクエストデータをパース
        
        Args:
            data: 受信したバイナリデータ
            
        Returns:
            Request: パースされたリクエスト
        """
        temp_request = Request.from_bytes(data)
        if temp_request.type == 7:
            return ErrorResponse.from_bytes(data)
        return temp_request

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
        基本的なリクエストの妥当性をチェック（BaseServer用）
        詳細なバリデーション（認証など）はcreate_response内で実行
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_code, error_message)
        """
        # 基本的なパケット形式のチェックのみ
        if not hasattr(request, 'packet_id'):
            return False, "400", "無効なパケット形式です"
        
        return True, None, None
    
    def _validate_request_detailed(self, request):
        """
        詳細なリクエストの妥当性をチェック（create_response内で使用）
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_code, error_message)
        """
        # 認証チェック（基底クラスの共通メソッドを使用）
        auth_valid, auth_error_code, auth_error_msg = self.validate_auth(request)
        if not auth_valid:
            return False, auth_error_code, auth_error_msg
        
        # 拡張フィールドが必要
        if not hasattr(request, 'ex_flag') or request.ex_flag != 1:
            return False, "400", "拡張フィールドが設定されていません"
        
        # 緯度経度が必要
        if not hasattr(request, 'ex_field') or not request.ex_field:
            return False, "400", "拡張フィールドオブジェクトが存在しません"
        
        # ExtendedFieldオブジェクトのgetメソッドを使用
        latitude = request.ex_field.get("latitude")
        longitude = request.ex_field.get("longitude")
        if not latitude or not longitude:
            return False, "401", "緯度経度の情報が不足しています"
        
        return True, None, None

    def create_response(self, request):
        """
        レスポンスを作成
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            レスポンスのバイナリデータ
        """
        import time
        start_time = time.time()
        
        # リクエストの詳細バリデーション
        is_valid, error_code, error_msg = self._validate_request_detailed(request)
        if not is_valid:
            # ErrorResponseを作成して返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code=error_code,
                timestamp=int(datetime.now().timestamp())
            )
            
            # 元のリクエストからsource情報を引き継ぐ
            if hasattr(request, 'ex_field') and request.ex_field:
                source = request.ex_field.get('source')
                if source:
                    error_response.ex_field = ExtendedField()
                    error_response.ex_field.source = source
                    error_response.ex_flag = 1
                    if self.debug:
                        print(f"[{self.server_name}] バリデーションエラーレスポンスにsource情報を設定: {source}")
            
            if self.debug:
                print(f"[{self.server_name}] バリデーションエラーレスポンス作成 (コード: {error_code})")
            
            return error_response.to_bytes()
    
        # 位置情報から地域コードを取得
        try:
            area_code = self._get_area_code_from_coordinates(
                request.ex_field.get("longitude"),
                request.ex_field.get("latitude")
            )
            
            # レスポンスを作成
            response = Response(
                version=self.version,
                packet_id=request.packet_id,
                type=1,  # Response type
                day=request.day,
                weather_flag=request.weather_flag,
                temperature_flag=request.temperature_flag,
                pop_flag=request.pop_flag,
                alert_flag=request.alert_flag,
                disaster_flag=request.disaster_flag,
                ex_flag=1,
                timestamp=int(datetime.now().timestamp()),
                area_code=int(area_code) if area_code else 0
            )
            
            # sourceのみを引き継ぐ（座標は破棄）
            # ExtendedFieldオブジェクトはResponseコンストラクタで自動作成される
            if hasattr(request, 'ex_field') and request.ex_field:
                source = request.ex_field.get('source')
                if source:
                    response.ex_field.source = source
                    if self.debug:
                        print(f"[位置情報サーバー] 送信元をレスポンスにコピーしました: {source[0]}:{source[1]}")

                latitude = request.ex_field.get('latitude')
                longitude = request.ex_field.get('longitude')
                if latitude and longitude:
                    response.ex_field.latitude = latitude
                    response.ex_field.longitude = longitude
                    if self.debug:
                        print ("座標解決レスポンスに座標を追加しました")
            
            # 統一されたデバッグ出力を追加
            execution_time = time.time() - start_time
            debug_data = {
                'area_code': area_code,
                'timestamp': response.timestamp,
                'latitude': request.ex_field.get('latitude'),
                'longitude': request.ex_field.get('longitude')
            }
            self.packet_debug_logger.log_unified_packet_received(
                "Location resolution",
                execution_time,
                debug_data
            )
            
            return response.to_bytes()
            
        except Exception as e:
            # 内部エラー発生時は500エラーを返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code="510",
                timestamp=int(datetime.now().timestamp())
            )
            
            # 元のリクエストからsource情報を引き継ぐ
            if hasattr(request, 'ex_field') and request.ex_field:
                source = request.ex_field.get('source')
                if source:
                    error_response.ex_field = ExtendedField()
                    error_response.ex_field.source = source
                    error_response.ex_flag = 1
                    if self.debug:
                        print(f"[{self.server_name}] 内部エラーレスポンスにsource情報を設定: {source}")
            
            if self.debug:
                print(f"[{self.server_name}] 内部エラーレスポンス作成 (コード: 510, エラー: {e})")
            
            return error_response.to_bytes()
    
    def _get_area_code_from_coordinates(self, longitude, latitude):
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
                print(f"[{self.server_name}] キャッシュヒット！")
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
                print(f"[{self.server_name}] ({longitude}, {latitude}) のクエリ結果: {district_code}")
            
            return district_code
            
        except Exception as e:
            print(f"データベースエラー: {e}")
            return None
            
        finally:
            if conn:
                # Return connection to pool
                cursor.close()
                self.connection_pool.putconn(conn)
    
    def _debug_print_request(self, data, parsed, addr=None):
        """リクエストのデバッグ情報を出力（統一フォーマット）"""
        if not self.debug:
            return

        details = {
            "Version": getattr(parsed, "version", "N/A"),
            "Type": getattr(parsed, "type", "N/A"),
            "Packet ID": getattr(parsed, "packet_id", "N/A"),
        }
        if hasattr(parsed, 'ex_field') and parsed.ex_field:
            if parsed.ex_field.get('latitude'):
                details['Latitude'] = parsed.ex_field.get('latitude')
            if parsed.ex_field.get('longitude'):
                details['Longitude'] = parsed.ex_field.get('longitude')

        log = UnifiedLogFormatter.format_communication_log(
            server_name=self.server_name,
            direction="recv from",
            remote_addr=addr[0] if addr else "unknown",
            remote_port=addr[1] if addr else 0,
            packet_size=len(data),
            packet_details=details,
        )
        print(log)
    
    def _debug_print_response(self, response, addr=None, request=None):
        """レスポンス送信時のログを出力（統一フォーマット）"""

        details = {}
        if self.debug:
            try:
                resp_obj = Response.from_bytes(response)
                details['Area Code'] = resp_obj.area_code
            except Exception:
                pass

        log = UnifiedLogFormatter.format_communication_log(
            server_name=self.server_name,
            direction="sent to",
            remote_addr=addr[0] if addr else "unknown",
            remote_port=addr[1] if addr else 0,
            packet_size=len(response),
            packet_details=details if self.debug and details else None,
        )
        print(log)
    
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
