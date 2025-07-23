"""
デバッグ支援クラス
デバッグ出力とパフォーマンス測定を担当
"""

import time
import threading
import logging
import os
from .weather_constants import DebugConstants

from WIPCommonPy.utils.log_config import LoggerConfig, UnifiedLogFormatter


class DebugHelper:
    """デバッグ支援クラス"""

    def __init__(self, debug_enabled=False, logger_name=None):
        """
        初期化

        Args:
            debug_enabled: デバッグモードの有効/無効
            logger_name: ロガー名（指定しない場合はモジュール名を使用）
        """
        self.debug_enabled = debug_enabled
        self.server_name = logger_name or "QueryServer"
        self.logger = LoggerConfig.setup_debug_helper_logger(
            name=self.server_name, debug_enabled=debug_enabled
        )
        self.timer = PerformanceTimer()

    def _hex_dump(self, data):
        """
        バイナリデータのHEXダンプを作成

        Args:
            data: バイナリデータ

        Returns:
            str: HEXダンプ文字列
        """
        hex_str = " ".join(f"{b:02x}" for b in data)
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else "." for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"

    def print_request_debug(
        self,
        data,
        parsed_request,
        remote_addr="unknown",
        remote_port=0,
        auth_status=None,
    ):
        """
        リクエストパケットのデバッグ情報を出力（統一フォーマット）

        Args:
            data: 受信したバイナリデータ
            parsed_request: パースされたリクエスト
            remote_addr: 送信元アドレス
            remote_port: 送信元ポート
            auth_status: 認証状態
        """
        if not self.debug_enabled:
            return

        # パケット詳細情報の収集
        packet_details = {
            "Version": getattr(parsed_request, "version", "N/A"),
            "Type": getattr(parsed_request, "type", "N/A"),
            "Area Code": getattr(parsed_request, "area_code", "N/A"),
            "Day": getattr(parsed_request, "day", "N/A"),
            "Weather Flag": getattr(parsed_request, "weather_flag", "N/A"),
            "Temperature Flag": getattr(parsed_request, "temperature_flag", "N/A"),
            "Precipitation Flag": getattr(parsed_request, "pop_flag", "N/A"),
            "Alert Flag": getattr(parsed_request, "alert_flag", "N/A"),
            "Disaster Flag": getattr(parsed_request, "disaster_flag", "N/A"),
        }

        if hasattr(parsed_request, "ex_field") and parsed_request.ex_field:
            packet_details["Extended Field"] = str(parsed_request.ex_field)
            if hasattr(parsed_request.ex_field, "source"):
                packet_details["Source"] = (
                    f"{parsed_request.ex_field.source[0]}:{parsed_request.ex_field.source[1]}"
                )

        log_message = UnifiedLogFormatter.format_communication_log(
            server_name=self.server_name,
            direction="recv from",
            remote_addr=remote_addr,
            remote_port=remote_port,
            packet_size=len(data),
            auth_status=auth_status,
            packet_details=packet_details,
        )

        self.logger.debug(log_message)

    def print_response_debug(
        self,
        response_data,
        remote_addr="unknown",
        remote_port=0,
        auth_status=None,
        response_obj=None,
    ):
        """
        レスポンスパケットのデバッグ情報を出力（統一フォーマット）

        Args:
            response_data: レスポンスのバイナリデータ
            remote_addr: 送信先アドレス
            remote_port: 送信先ポート
            auth_status: 認証状態
            response_obj: レスポンスオブジェクト（詳細表示用）
        """
        if not self.debug_enabled:
            return

        # 処理時間を計算
        processing_time_ms = (
            self.timer.get_elapsed_ms() if self.timer.start_time else None
        )

        # パケット詳細情報の収集
        packet_details = {}
        if response_obj:
            if hasattr(response_obj, "weather_code"):
                packet_details["Weather Code"] = response_obj.weather_code
            if hasattr(response_obj, "temperature"):
                packet_details["Temperature"] = response_obj.temperature
            if hasattr(response_obj, "pop"):
                packet_details["Precipitation Probability"] = f"{response_obj.pop}%"
            if hasattr(response_obj, "ex_field") and response_obj.ex_field:
                packet_details["Extended Field"] = str(response_obj.ex_field)
                if hasattr(response_obj.ex_field, "source"):
                    packet_details["Source"] = (
                        f"{response_obj.ex_field.source[0]}:{response_obj.ex_field.source[1]}"
                    )

        log_message = UnifiedLogFormatter.format_communication_log(
            server_name=self.server_name,
            direction="sent to",
            remote_addr=remote_addr,
            remote_port=remote_port,
            packet_size=len(response_data),
            auth_status=auth_status,
            processing_time_ms=processing_time_ms,
            packet_details=packet_details if packet_details else None,
        )

        self.logger.debug(log_message)

    def start_timing(self):
        """
        処理時間測定を開始
        """
        self.timer.start()

    def print_timing_info(self, thread_id, addr, timing_data):
        """
        処理時間情報を出力（統一フォーマット対応）

        Args:
            thread_id: スレッドID
            addr: クライアントアドレス
            timing_data: タイミングデータの辞書
        """
        if not self.debug_enabled:
            return

        timing_info = f"[{thread_id}] Processing times for {addr}:"
        for key, value in timing_data.items():
            timing_info += f"\n  {key}: {value * DebugConstants.MS_MULTIPLIER:.2f}ms"

        self.logger.debug(timing_info)

    def print_thread_info(self, message, addr=None):
        """
        スレッド情報を出力

        Args:
            message: 出力メッセージ
            addr: クライアントアドレス（オプション）
        """
        if not self.debug_enabled:
            return

        thread_id = threading.current_thread().name
        if addr:
            self.logger.debug(f"[{thread_id}] {message} from {addr}")
        else:
            self.logger.debug(f"[{thread_id}] {message}")

    def print_error(self, message, addr=None, exception=None):
        """
        エラー情報を出力

        Args:
            message: エラーメッセージ
            addr: クライアントアドレス（オプション）
            exception: 例外オブジェクト（オプション）
        """
        thread_id = threading.current_thread().name
        error_msg = f"[{thread_id}] ERROR: {message}"

        if addr:
            error_msg += f" from {addr}"

        if exception:
            error_msg += f" - {exception}"

        self.logger.error(error_msg)

    def print_info(self, message):
        """
        情報メッセージを出力

        Args:
            message: 情報メッセージ
        """
        if self.debug_enabled:
            self.logger.info(f"INFO: {message}")


class PerformanceTimer:
    """パフォーマンス測定用タイマー"""

    def __init__(self):
        self.start_time = None

    def start(self):
        """タイマーを開始"""
        self.start_time = time.time()

    def get_elapsed_ms(self):
        """経過時間をミリ秒で取得"""
        if self.start_time is None:
            return None
        return (time.time() - self.start_time) * 1000
