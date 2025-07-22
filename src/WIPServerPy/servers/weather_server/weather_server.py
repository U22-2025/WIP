"""
天気サーバー - プロキシサーバー実装（改良版：専用パケットクラス使用）
他のサーバーへリクエストを転送し、レスポンスを返す
"""

import time
import sys
import os
import threading
from datetime import datetime
from pathlib import Path
import traceback

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    # 共通ライブラリのパスも追加
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# モジュールとして使用される場合
from ..base_server import BaseServer
from .handlers import WeatherRequestHandlers
from WIPCommonPy.clients.location_client import LocationClient
from WIPCommonPy.clients.query_client import QueryClient
from WIPCommonPy.utils.config_loader import ConfigLoader
from WIPCommonPy.packet import ErrorResponse
from WIPCommonPy.packet.debug.debug_logger import create_debug_logger


class WeatherServer(WeatherRequestHandlers, BaseServer):
    """天気サーバーのメインクラス（プロキシサーバー・専用パケットクラス使用）"""
    
    def __init__(self, host=None, port=None, debug=None, max_workers=None):
        """
        初期化
        
        Args:
            host: サーバーホスト（Noneの場合は設定ファイルから取得）
            port: サーバーポート（Noneの場合は設定ファイルから取得）
            debug: デバッグモードフラグ（Noneの場合は設定ファイルから取得）
            max_workers: スレッドプールのワーカー数（Noneの場合は設定ファイルから取得）
        """
        # 設定ファイルを読み込む
        config_path = Path(__file__).parent / 'config.ini'
        try:
            self.config = ConfigLoader(config_path)
        except Exception as e:
            error_msg = f"設定ファイルの読み込みに失敗しました: {config_path} - {str(e)}"
            self.logger.debug(traceback.format_exc())
            raise RuntimeError(f"設定ファイル読み込みエラー: {str(e)}")
        
        # サーバー設定を取得（引数優先、なければ設定ファイル、なければデフォルト）
        if host is None:
            host = self.config.get('server', 'host', '0.0.0.0')
        if port is None:
            port = self.config.getint('server', 'port', 4110)
        if debug is None:
            debug_str = self.config.get('server', 'debug', 'false')
            debug = debug_str.lower() == 'true'
        if max_workers is None:
            max_workers = self.config.getint('server', 'max_workers', None)
        
        # 基底クラスの初期化
        super().__init__(host, port, debug, max_workers)
        
        # サーバー名を設定
        self.server_name = "WeatherServer"
        
        # プロトコルバージョンを設定から取得（4ビット値に制限）
        version = self.config.getint('system', 'protocol_version', 1)
        self.version = version & 0x0F  # 4ビットにマスク
        
        # 他のサーバーへの接続設定を読み込む
        self.location_resolver_host = self.config.get('connections', 'location_server_host', 'localhost')
        self.location_resolver_port = self.config.getint('connections', 'location_server_port', 4109)
        self.query_generator_host = self.config.get('connections', 'query_server_host', 'localhost')
        self.query_generator_port = self.config.getint('connections', 'query_server_port', 4111)
        self.report_server_host = self.config.get('connections', 'report_server_host', 'localhost')
        self.report_server_port = self.config.getint('connections', 'report_server_port', 4112)
        
        # ネットワーク設定
        self.udp_buffer_size = self.config.getint('network', 'udp_buffer_size', 4096)
        
        # weather cache は query_client で統一管理
        # エリアキャッシュはlocation_clientで統一管理
        
        
        # サーバー設定情報のデバッグ出力を削除
        
        # クライアントの初期化（改良版・キャッシュ統合）
        try:
            # location_clientでエリアキャッシュを統一管理（TTLを設定から取得）
            area_cache_ttl_minutes = self.config.getint('cache', 'expiration_time_area', 604800) // 60
            area_cache_enabled = self.config.getboolean('cache', 'enable_area_cache', True)
            self.location_client = LocationClient(
                host=self.location_resolver_host,
                port=self.location_resolver_port,
                debug=self.debug,
                cache_ttl_minutes=area_cache_ttl_minutes,
                cache_enabled=area_cache_enabled
            )
        except Exception as e:
            self.logger.error(f"ロケーションクライアントの初期化に失敗しました: {self.location_resolver_host}:{self.location_resolver_port} - {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise RuntimeError(f"ロケーションクライアント初期化エラー: {str(e)}")

        try:
            # query_clientでweatherキャッシュも統一管理（TTLを設定から取得）
            weather_cache_ttl_minutes = self.config.getint('cache', 'expiration_time_weather', 600) // 60
            weather_cache_enabled = self.config.getboolean('cache', 'enable_weather_cache', True)
            self.query_client = QueryClient(
                host=self.query_generator_host,
                port=self.query_generator_port,
                debug=self.debug,
                cache_ttl_minutes=weather_cache_ttl_minutes,
                cache_enabled=weather_cache_enabled
            )
        except Exception as e:
            self.logger.error(f"クエリクライアントの初期化に失敗しました: {self.query_generator_host}:{self.query_generator_port} - {str(e)}")
            self.logger.debug(traceback.format_exc())
            raise RuntimeError(f"クエリクライアント初期化エラー: {str(e)}")
        
        # 認証設定を環境変数から読み込む
        self.auth_enabled = os.getenv('WEATHER_SERVER_AUTH_ENABLED', 'false').lower() == 'true'
        
        # パケットタイプ別のパスフレーズを設定
        self.passphrases = {
            'weather_server': os.getenv('WEATHER_SERVER_PASSPHRASE', 'secure'),
            'location_server': os.getenv('LOCATION_SERVER_PASSPHRASE', 'secure'),
            'query_server': os.getenv('QUERY_SERVER_PASSPHRASE', 'secure'),
            'report_server': os.getenv('REPORT_SERVER_PASSPHRASE', 'secure')
        }
        
        # デバッグロガーの初期化
        self.logger = create_debug_logger(f"{self.server_name}", self.debug)
        
    
    def _get_passphrase_for_packet_type(self, packet_type, addr):
        """
        パケットタイプと送信元アドレスによって適切なパスフレーズを選択
        
        Args:
            packet_type: パケットタイプ
            addr: 送信元アドレス
            
        Returns:
            使用するパスフレーズ
        """
        if packet_type in [0, 2, 4]:
            # クライアントからのリクエスト → weatherサーバーのパスフレーズを使用
            return self.passphrases['weather_server']
        elif packet_type == 1:
            # Location Serverからのレスポンス
            return self.passphrases['location_server']
        elif packet_type == 3:
            # Query Serverからのレスポンス
            return self.passphrases['query_server']
        elif packet_type == 5:
            # Report Serverからのレスポンス
            return self.passphrases['report_server']
        elif packet_type == 7:
            # エラーレスポンス → 送信元ポートから判断
            if addr[1] == self.location_resolver_port:
                return self.passphrases['location_server']
            elif addr[1] == self.query_generator_port:
                return self.passphrases['query_server']
            elif addr[1] == self.report_server_port:
                return self.passphrases['report_server']
            else:
                # 不明な場合はweatherサーバーのパスフレーズを使用
                return self.passphrases['weather_server']
        else:
            # デフォルトはweatherサーバーのパスフレーズ
            return self.passphrases['weather_server']
    
    def _verify_packet_authentication(self, data, packet_id, timestamp, packet_type, addr):
        """
        パケットの認証を検証
        
        Args:
            data: パケットデータ
            packet_id: パケットID
            timestamp: タイムスタンプ
            packet_type: パケットタイプ
            addr: 送信元アドレス
            
        Returns:
            認証が成功した場合はTrue
        """
        try:
            # パケットタイプに応じたパスフレーズを取得
            passphrase = self._get_passphrase_for_packet_type(packet_type, addr)
            
            
            # パケット内の認証ハッシュを取得（拡張フィールドから）
            # 注意: 実際の実装では、パケットから認証ハッシュを取得する必要があります
            # ここでは、認証が実装されていることを示すサンプルコードです
            
            return True  # 暫定的に常に認証成功とする
            
        except Exception as e:
            return False
    
    def _get_server_type_for_packet(self, packet_type, addr):
        """デバッグ用：パケットタイプから送信元サーバータイプを取得"""
        if packet_type in [0, 2, 4]:
            return "クライアント→ウェザーサーバー"
        elif packet_type == 1:
            return "ロケーションサーバー→ウェザーサーバー"
        elif packet_type == 3:
            return "クエリサーバー→ウェザーサーバー"
        elif packet_type == 5:
            return "レポートサーバー→ウェザーサーバー"
        elif packet_type == 7:
            if addr[1] == self.location_resolver_port:
                return "ロケーションサーバー→ウェザーサーバー（エラー）"
            elif addr[1] == self.query_generator_port:
                return "クエリサーバー→ウェザーサーバー（エラー）"
            elif addr[1] == self.report_server_port:
                return "レポートサーバー→ウェザーサーバー（エラー）"
            else:
                return "不明なサーバー→ウェザーサーバー（エラー）"
        else:
            return "不明"
        
    def handle_request(self, data, addr):
        """
        リクエストを処理（プロキシとして転送）
        
        Args:
            data: 受信したバイナリデータ
            addr: 送信元アドレス
        """
        timing_info = {}
        start_time = time.time()
        
        try:
            # リクエストカウントを増加（スレッドセーフ）
            try:
                with self.lock:
                    self.request_count += 1
            except Exception as e:
                error_msg = f"リクエストカウントの更新に失敗しました - {str(e)}"
                self.logger.debug(traceback.format_exc())
                raise RuntimeError(f"755: レート制限超過: {str(e)}")
            
            # リクエストをパース（専用パケットクラス使用）
            try:
                request, parse_time = self._measure_time(self.parse_request, data)
                timing_info['parse'] = parse_time
                # リクエストパース成功のデバッグ出力を削除
            except Exception as e:
                self.logger.error(f"530: [{self.server_name}] リクエストのパース中にエラーが発生しました: {e}")
                self.logger.debug(traceback.format_exc())
                # ErrorResponseを作成して返す（パースエラー時はpacket_id=0とする）
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=0,  # パースエラー時はpacket_id=0
                    error_code=530,
                    timestamp=int(datetime.now().timestamp())
                )
                # パースエラー時は送信先が不明なため転送できない
                self.logger.debug(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
                return
            
            # デバッグ出力（改良版）
            self._debug_print_request(data, request)
            
            # 認証チェック（有効な場合のみ）
            if self.auth_enabled:
                auth_result = self._verify_packet_authentication(
                    data, request.packet_id, request.timestamp, request.type, addr
                )
                if not auth_result:
                    
                    # 認証失敗のエラーレスポンスを作成
                    error_response = ErrorResponse(
                        version=self.version,
                        packet_id=request.packet_id,
                        error_code=401,  # 認証失敗
                        timestamp=int(datetime.now().timestamp())
                    )
                    dest = None
                    if (
                        hasattr(request, "ex_field")
                        and request.ex_field
                        and request.ex_field.contains("source")
                    ):
                        candidate = request.ex_field.source
                        if isinstance(candidate, tuple) and len(candidate) == 2:
                            dest = candidate
                    
                    # レスポンス型パケット（Type 1,3,5,7）の場合は、元の送信者に戻す
                    if request.type in [1, 3, 5, 7] and not dest:
                        dest = addr
                    
                    if dest:
                        error_response.ex_field.source = dest
                        self.sock.sendto(error_response.to_bytes(), dest)
                    
                    with self.lock:
                        self.error_count += 1
                    return
            
            # リクエストの妥当性をチェック
            is_valid, error_code, error_msg = self.validate_request(request)
            if not is_valid:
                # ErrorResponseを作成して返す
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=request.packet_id,
                    error_code=error_code,
                    timestamp=int(datetime.now().timestamp())
                )
                dest = None
                if (
                    hasattr(request, "ex_field")
                    and request.ex_field
                    and request.ex_field.contains("source")
                ):
                    candidate = request.ex_field.source
                    if isinstance(candidate, tuple) and len(candidate) == 2:
                        dest = candidate

                if dest:
                    error_response.ex_field.source = dest
                    self.sock.sendto(error_response.to_bytes(), dest)
                if dest:
                    self.logger.debug(f"[{threading.current_thread().name}] Error response sent to {dest}")
                else:
                    self.logger.debug(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
                self.logger.debug(f"{error_code}: [{threading.current_thread().name}] {addr} からの不正なリクエスト: {error_msg}")
                with self.lock:
                    self.error_count += 1
                return
            
            # パケットタイプによる分岐処理（専用クラス対応）
            # パケットタイプ処理中のデバッグ出力を削除
                
            if request.type == 0:
                # Type 0: 座標解決リクエスト
                self._handle_location_request(request, addr)
            elif request.type == 1:
                # Type 1: 座標解決レスポンス
                self._handle_location_response(data, addr)
            elif request.type == 2:
                # Type 2: 気象データリクエスト
                self._handle_query_request(request, addr)
            elif request.type == 3:
                # Type 3: 気象データレスポンス
                self._handle_query_response(data, addr)
            elif request.type == 4:
                # Type 4: データレポートリクエスト
                self._handle_report_request(request, addr)
            elif request.type == 5:
                # Type 5: データレポートレスポンス
                self._handle_report_response(data, addr)
            elif request.type == 7:  # エラーパケット処理を追加
                self._handle_error_packet(request, addr)
            else:
                self.logger.debug(f"405: 不正なパケットタイプ: {request.type}")
                # ErrorResponseを作成して返す
                error_response = ErrorResponse(
                    version=self.version,
                    packet_id=request.packet_id,
                    error_code= 405,
                    timestamp=int(datetime.now().timestamp())
                )
                dest = None
                if (
                    hasattr(request, "ex_field")
                    and request.ex_field
                    and request.ex_field.contains('source')
                ):
                    candidate = request.ex_field.source
                    if isinstance(candidate, tuple) and len(candidate) == 2:
                        dest = candidate

                if dest:
                    error_response.ex_field.source = dest
                    self.sock.sendto(error_response.to_bytes(), dest)
                    self.logger.debug(f"[{threading.current_thread().name}] Error response sent to {dest}")
                else:
                    self.logger.debug(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
                return
                    
            # タイミング情報を出力
            timing_info['total'] = time.time() - start_time
            # タイミング情報のデバッグ出力を削除
                
        except Exception as e:
            with self.lock:
                self.error_count += 1
            self.logger.error(f"530: [{self.server_name}:{threading.current_thread().name}] {addr} からのリクエスト処理中にエラーが発生しました: {e}")
            self.logger.debug(traceback.format_exc())
            # ErrorResponseを作成して返す（requestが未定義の場合の処理を追加）
            packet_id = getattr(request, 'packet_id', 0)  # requestが未定義の場合は0
            error_response = ErrorResponse(
                version=self.version,
                packet_id=packet_id,
                error_code=530,
                timestamp=int(datetime.now().timestamp())
            )

            dest = None
            if (
                'request' in locals()
                and hasattr(request, 'ex_field')
                and request.ex_field
                and request.ex_field.contains('source')
            ):
                candidate = request.ex_field.source
                if isinstance(candidate, tuple) and len(candidate) == 2:
                    dest = candidate

            if dest:
                error_response.ex_field.source = dest
                self.sock.sendto(error_response.to_bytes(), dest)
                self.logger.debug(f"[{threading.current_thread().name}] Error response sent to {dest}")
            else:
                self.logger.debug(f"[{threading.current_thread().name}] sourceが無いためエラーパケットを送信しません")
            return
    


if __name__ == "__main__":
    # 設定ファイルから読み込んで起動
    server = WeatherServer()
    server.run()
