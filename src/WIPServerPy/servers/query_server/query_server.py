"""
気象データサーバー - リファクタリング版
基底クラスを継承した実装
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime
import time
import traceback

# モジュールとして使用される場合
from WIPServerPy.servers.base_server import BaseServer
from WIPServerPy.servers.query_server.modules.weather_data_manager import WeatherDataManager, MissingDataError
from WIPServerPy.servers.query_server.modules.response_builder import ResponseBuilder
from WIPServerPy.servers.query_server.modules.debug_helper import DebugHelper
from WIPServerPy.servers.query_server.modules.weather_constants import ThreadConstants
from WIPCommonPy.packet import QueryRequest, QueryResponse
from WIPCommonPy.utils.config_loader import ConfigLoader
from WIPCommonPy.packet import ErrorResponse
from WIPCommonPy.packet.debug.debug_logger import create_debug_logger, PacketDebugLogger


class QueryServer(BaseServer):
    """気象データサーバーのメインクラス（基底クラス継承版）"""

    def __init__(
        self, host=None, port=None, debug=None, max_workers=None, noupdate=False
    ):
        """
        初期化

        Args:
            host: サーバーホスト（Noneの場合は設定ファイルから取得）
            port: サーバーポート（Noneの場合は設定ファイルから取得）
            debug: デバッグモード（Noneの場合は設定ファイルから取得）
            max_workers: ワーカー数（Noneの場合は設定ファイルから取得）
        """
        # 設定ファイルを読み込む
        config_path = Path(__file__).parent / "config.ini"
        self.config = ConfigLoader(config_path)

        # サーバー設定を取得（引数優先、なければ設定ファイル、なければデフォルト）
        if host is None:
            host = self.config.get("server", "host", "0.0.0.0")
        if port is None:
            port = self.config.getint("server", "port", 4111)
        if debug is None:
            debug_str = self.config.get("server", "debug", "false")
            debug = debug_str.lower() == "true"
        if max_workers is None:
            max_workers = self.config.getint(
                "server", "max_workers", ThreadConstants.DEFAULT_MAX_WORKERS
            )

        # 基底クラスの初期化
        super().__init__(host, port, debug, max_workers)

        # サーバー名を設定
        self.server_name = "QueryServer"

        # 認証設定を初期化
        self._init_auth_config()

        # プロトコルバージョンを設定から取得
        self.version = self.config.getint("system", "protocol_version", 1)

        # 各コンポーネントの初期化
        self._setup_components()

        # デバッグロガーの初期化
        self.logger = create_debug_logger(f"{self.server_name}", self.debug)

        # 統一デバッグロガーの初期化
        self.packet_debug_logger = PacketDebugLogger("QueryServer")




    def _init_auth_config(self):
        """認証設定を環境変数から読み込み（QueryServer固有）"""
        # QueryServer自身の認証設定
        auth_enabled = os.getenv("QUERY_SERVER_AUTH_ENABLED", "false").lower() == "true"
        auth_passphrase = os.getenv("QUERY_SERVER_PASSPHRASE", "")

        self.auth_enabled = auth_enabled
        self.auth_passphrase = auth_passphrase


    def _setup_components(self):
        """各コンポーネントを初期化"""
        # デバッグヘルパー
        self.debug_helper = DebugHelper(self.debug, logger_name=self.server_name)

        # 気象データマネージャー（設定情報を渡す）
        weather_config = {
            "redis_host": self.config.get("redis", "host", "localhost"),
            "redis_port": self.config.getint("redis", "port", 6379),
            "redis_db": self.config.getint("redis", "db", 0),
            "debug": self.debug,
            "max_workers": self.max_workers,
            "version": self.version,
            "cache_enabled": self.config.getboolean(
                "cache", "enable_redis_cache", True
            ),
        }
        self.weather_manager = WeatherDataManager(weather_config)

        # レスポンスビルダー
        response_config = {"debug": self.debug, "version": self.version}
        self.response_builder = ResponseBuilder(response_config)

    def parse_request(self, data):
        """
        リクエストデータをパース

        Args:
            data: 受信したバイナリデータ

        Returns:
            Request: パースされたリクエスト
        """
        return QueryRequest.from_bytes(data)

    def validate_request(self, request):
        """
        リクエストの妥当性をチェック

        Args:
            request: リクエストオブジェクト

        Returns:
            tuple: (is_valid, error_message)
        """
        # 認証チェック（基底クラスの共通メソッドを使用）
        auth_valid, auth_error_code, auth_error_msg = self.validate_auth(request)
        if not auth_valid:
            return False, auth_error_code, auth_error_msg

        # バージョンのチェック
        if request.version != self.version:
            return (
                False,
                "403",
                f"バージョンが不正です (expected: {self.version}, got: {request.version})",
            )

        # タイプのチェック
        if request.type != 2:
            return False, "400", f"不正なパケットタイプ: {request.type}"

        # 地域コードのチェック
        if not request.area_code or request.area_code == "000000":
            return False, "402", "エリアコードが未設定"

        # フラグのチェック（少なくとも1つは必要）
        if not any(
            [
                request.weather_flag,
                request.temperature_flag,
                request.pop_flag,
                request.alert_flag,
                request.disaster_flag,
            ]
        ):
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
        start_time = time.time()

        # リクエストのバリデーション
        is_valid, error_code, error_msg = self.validate_request(request)
        if not is_valid:
            # ErrorResponseを作成して返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code=error_code,
                timestamp=int(datetime.now().timestamp()),
            )
            self.logger.debug(
                f"{error_code}: [{self.server_name}] エラーレスポンスを生成: {error_code}"
            )
            return error_response.to_bytes()

        try:
            # デバッグ：リクエストの状態を確認

            # 気象データを取得
            weather_start = time.time()
            weather_data = self.weather_manager.get_weather_data(
                area_code=request.area_code,
                weather_flag=request.weather_flag,
                temperature_flag=request.temperature_flag,
                pop_flag=request.pop_flag,
                alert_flag=request.alert_flag,
                disaster_flag=request.disaster_flag,
                day=request.day,
            )
        except MissingDataError:
            # 指定データが未取得（null）の場合は 406 を返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code="406",
                timestamp=int(datetime.now().timestamp()),
            )
            self.logger.debug("406: 指定したデータが見つからない")
            return error_response.to_bytes()
        weather_time = time.time() - weather_start
        self.logger.debug(f"Data fetch: {weather_time:.3f}s")

            # QueryResponseクラスのcreate_query_responseメソッドを使用
            response = QueryResponse.create_query_response(
                request=request, weather_data=weather_data, version=self.version
            )

            # 座標情報がある場合は拡張フィールドに追加
            if hasattr(request, "get_coordinates"):
                coords = request.get_coordinates()
                if coords and coords[0] is not None and coords[1] is not None:
                    lat, long = coords
                    if hasattr(response, "ex_field") and response.ex_field:
                        response.ex_field.latitude = lat
                        response.ex_field.longitude = long
                        response.ex_flag = 1
                        self.logger.debug(
                            f"[{self.server_name}] 座標をレスポンスに追加しました: {lat},{long}"
                        )
        except Exception as e:
            # 内部エラー発生時は500エラーを返す
            error_response = ErrorResponse(
                version=self.version,
                packet_id=request.packet_id,
                error_code="520",
                timestamp=int(datetime.now().timestamp()),
            )
            self.logger.debug(
                f"520: [{self.server_name}] エラーレスポンスを生成: {error_code}"
            )
            return error_response.to_bytes()

        # 統一されたデバッグ出力を追加
        execution_time = time.time() - start_time
        debug_data = {
            "area_code": request.area_code,
            "timestamp": response.timestamp,
            "weather_code": response.weather_code if response.weather_flag else "N/A",
            "temperature": (
                response.temperature - 100 if response.temperature_flag else "N/A"
            ),
            "precipitation_prob": response.pop if response.pop_flag else "N/A",
            "alert": (
                response.ex_field.get("alert", [])
                if hasattr(response, "ex_field") and response.ex_field
                else []
            ),
            "disaster": (
                response.ex_field.get("disaster", [])
                if hasattr(response, "ex_field") and response.ex_field
                else []
            ),
        }
        self.packet_debug_logger.log_unified_packet_received(
            "Direct request", execution_time, debug_data
        )

        return response.to_bytes()

    def _debug_print_request(self, data, parsed, addr=None):
        """リクエストのデバッグ情報を出力（統一フォーマット）"""
        if not self.debug:
            return

        # タイマー開始
        self.debug_helper.start_timing()

        # 認証状態の確認（認証が有効な場合）
        auth_status = None
        if hasattr(self, "auth_enabled") and self.auth_enabled:
            # 認証結果を確認する処理（実装に応じて調整）
            auth_status = "認証成功"  # または "認証失敗"

        # debug_helperの統一フォーマットを使用
        self.debug_helper.print_request_debug(
            data=data,
            parsed_request=parsed,
            remote_addr=addr[0] if addr else "unknown",
            remote_port=addr[1] if addr else 0,
            auth_status=auth_status,
        )

    def _debug_print_response(self, response, addr=None, request=None):
        """レスポンスのデバッグ情報を出力（統一フォーマット）"""
        if not self.debug:
            return

        # 認証状態の確認（認証が有効な場合）
        auth_status = None
        if hasattr(self, "auth_enabled") and self.auth_enabled:
            auth_status = "認証成功"  # または "認証失敗"

        # レスポンスオブジェクトの詳細情報を取得
        response_obj = None
        try:
            response_obj = QueryResponse.from_bytes(response)
        except:
            pass

        # debug_helperの統一フォーマットを使用
        self.debug_helper.print_response_debug(
            response_data=response,
            remote_addr=addr[0] if addr else "unknown",
            remote_port=addr[1] if addr else 0,
            auth_status=auth_status,
            response_obj=response_obj,
        )

    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理（オーバーライド）"""
        # WeatherDataManagerのクリーンアップ
        if hasattr(self, "weather_manager"):
            self.weather_manager.close()






