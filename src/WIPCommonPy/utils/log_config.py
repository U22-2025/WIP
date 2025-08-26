"""
共通ログ設定ユーティリティ
プロジェクト全体で統一されたログ設定を提供
log-task.md仕様に基づく統一ログフォーマット
"""

import logging
import sys
import time
from typing import Optional, Dict, Any


class UnifiedLogFormatter:
    """統一ログフォーマッター - log-task.md仕様準拠"""

    @staticmethod
    def format_communication_log(
        server_name: str,
        direction: str,  # "recv from" or "sent to"
        remote_addr: str,
        remote_port: int,
        packet_size: int,
        auth_status: Optional[str] = None,  # "認証成功" or "認証失敗"
        processing_time_ms: Optional[float] = None,
        packet_details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        統一通信ログフォーマット

        Args:
            server_name: サーバ/クライアント名
            direction: "recv from" or "sent to"
            remote_addr: 相手先アドレス
            remote_port: 相手先ポート
            packet_size: パケットサイズ（バイト）
            auth_status: 認証状態（認証有効時のみ）
            processing_time_ms: 処理時間（送信時のみ）
            packet_details: パケット詳細（デバッグモード時）

        Returns:
            フォーマットされたログメッセージ
        """
        # 基本ヘッダー
        header = f"{server_name}:{direction} {remote_addr}:{remote_port}"

        # 認証情報（有効時）
        auth_info = f"\n{auth_status}" if auth_status else ""

        # パケット情報
        packet_direction = "受信" if "recv" in direction else "送信"
        packet_info = f"\n{packet_direction} パケットバイト数: {packet_size}"

        # 詳細情報（デバッグモード）
        details = ""
        if packet_details:
            details = "\n========"
            for field_name, field_value in packet_details.items():
                details += f"\n{field_name}: {field_value}"

        # 処理時間（送信時）
        timing_info = (
            f"\n処理時間: {processing_time_ms:.2f}ms"
            if processing_time_ms is not None
            else ""
        )

        return f"***\n{header}{auth_info}{packet_info}{details}{timing_info}\n***"


class LoggerConfig:
    """統一されたロガー設定クラス"""

    DEFAULT_FORMAT = "%(message)s"  # 統一フォーマットを使用するため、シンプルに
    DEBUG_FORMAT = "%(message)s"

    @staticmethod
    def setup_logger(
        name: str,
        debug: bool = False,
        level: Optional[int] = None,
        handler_type: str = "console",
    ) -> logging.Logger:
        """
        統一されたロガーを設定

        Args:
            name: ロガー名
            debug: デバッグモード
            level: ログレベル（指定しない場合は自動設定）
            handler_type: ハンドラータイプ（'console', 'file'）

        Returns:
            設定されたロガー
        """
        logger = logging.getLogger(name)

        # ハンドラーの重複追加を防ぐ
        if logger.handlers:
            return logger

        # レベル設定
        if level is None:
            level = logging.DEBUG if debug else logging.INFO
        logger.setLevel(level)

        # ハンドラー作成
        if handler_type == "console":
            handler = logging.StreamHandler(sys.stdout)
        else:
            raise ValueError(f"Unsupported handler type: {handler_type}")

        # フォーマッター設定
        formatter = logging.Formatter(
            LoggerConfig.DEBUG_FORMAT if debug else LoggerConfig.DEFAULT_FORMAT
        )
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        return logger

    @staticmethod
    def setup_debug_helper_logger(
        name: str, debug_enabled: bool = False
    ) -> logging.Logger:
        """
        DebugHelper用の専用ロガーを設定

        Args:
            name: ロガー名
            debug_enabled: デバッグモードの有効/無効

        Returns:
            設定されたロガー
        """
        return LoggerConfig.setup_logger(
            name=f"DebugHelper.{name}",
            debug=debug_enabled,
            level=logging.DEBUG if debug_enabled else logging.WARNING,
        )

    @staticmethod
    def setup_server_logger(server_name: str, debug: bool = False) -> logging.Logger:
        """
        サーバー用ロガーを設定

        Args:
            server_name: サーバー名
            debug: デバッグモード

        Returns:
            設定されたロガー
        """
        return LoggerConfig.setup_logger(name=f"Server.{server_name}", debug=debug)

    @staticmethod
    def setup_client_logger(
        client_name: str = "WIPClient", debug: bool = False
    ) -> logging.Logger:
        """
        クライアント用ロガーを設定

        Args:
            client_name: クライアント名
            debug: デバッグモード

        Returns:
            設定されたロガー
        """
        return LoggerConfig.setup_logger(name=f"Client.{client_name}", debug=debug)


class PerformanceTimer:
    """パフォーマンス測定クラス - 統一ログ対応"""

    def __init__(self):
        self.start_time = None
        self.timings = {}

    def start(self):
        """測定開始"""
        self.start_time = time.time()
        return self.start_time

    def mark(self, label: str) -> float:
        """
        特定ポイントの時間を記録

        Args:
            label: ラベル名

        Returns:
            経過時間（ミリ秒）
        """
        if self.start_time is None:
            self.start()

        current_time = time.time()
        elapsed_ms = (current_time - self.start_time) * 1000
        self.timings[label] = elapsed_ms
        return elapsed_ms

    def get_elapsed_ms(self) -> float:
        """
        開始からの経過時間を取得（ミリ秒）

        Returns:
            経過時間（ミリ秒）
        """
        if self.start_time is None:
            return 0.0
        return (time.time() - self.start_time) * 1000

    def reset(self):
        """測定データをリセット"""
        self.start_time = None
        self.timings.clear()
