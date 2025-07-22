"""
共通パケットデバッグログユーティリティ
統一されたデバッグ出力フォーマットを提供
"""

import logging
import time
from typing import Any, Optional, Dict


class PacketDebugLogger:
    """パケットデバッグログの共通ユーティリティクラス"""
    
    def __init__(self, logger_name: str, debug_enabled: bool = False):
        """
        初期化
        
        Args:
            logger_name: ロガー名
            debug_enabled: デバッグモードの有効/無効
        """
        self.logger = logging.getLogger(logger_name)
        self.debug_enabled = debug_enabled
        self.logger.setLevel(logging.DEBUG if debug_enabled else logging.INFO)
        
        # DEBUG: 接頭辞を削除するため、シンプルなフォーマッターを設定
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')  # メッセージのみ表示
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.propagate = False  # 親ロガーへの伝播を防止
    
    def log_request(self, packet: Any, operation_type: str = "REQUEST") -> None:
        """
        リクエストパケットの重要な情報のみをログ出力（簡潔版）
        
        Args:
            packet: パケットオブジェクト
            operation_type: 操作タイプ（表示用）
        """
        if not self.debug_enabled:
            return
        
        # 基本情報のみ1行で表示
        packet_type_name = self._get_packet_type_name(packet.type) if hasattr(packet, 'type') else "Unknown"
        packet_id = packet.packet_id if hasattr(packet, 'packet_id') else "N/A"
        area_code = packet.area_code if hasattr(packet, 'area_code') else "N/A"
        
        # フラグ情報（簡潔に）
        flags = self._extract_request_flags(packet)
        flags_str = ', '.join(flags) if flags else "None"
        
        self.logger.debug(f"{operation_type}: {packet_type_name} | ID:{packet_id} | Area:{area_code} | Data:{flags_str}")
    
    def log_response(self, packet: Any, operation_type: str = "RESPONSE") -> None:
        """
        レスポンスパケットの重要な情報のみをログ出力（簡潔版）
        
        Args:
            packet: パケットオブジェクト
            operation_type: 操作タイプ（表示用）
        """
        if not self.debug_enabled:
            return
        
        # 基本情報のみ1行で表示
        packet_type_name = self._get_packet_type_name(packet.type) if hasattr(packet, 'type') else "Unknown"
        
        # 成功/失敗状態
        status = "Unknown"
        if hasattr(packet, 'is_success'):
            status = "Success" if packet.is_success() else "Failed"
        elif hasattr(packet, 'is_valid'):
            status = "Valid" if packet.is_valid() else "Invalid"
        elif hasattr(packet, 'error_code'):
            status = f"Error:{packet.error_code}"
        
        # 応答内容の要約
        summary = ""
        if hasattr(packet, 'get_response_summary'):
            summary = packet.get_response_summary()
        elif hasattr(packet, 'get_weather_data'):
            weather_data = packet.get_weather_data()
            if weather_data:
                summary = self._format_weather_data(weather_data)
        
        # 複数行で表示
        self.logger.debug(f"{operation_type}: {packet_type_name}")
        packet_id = packet.packet_id if hasattr(packet, 'packet_id') else "N/A"
        self.logger.debug(f"  Packet ID: {packet_id}")
        self.logger.debug(f"  Status: {status}")
        
        # 応答内容の詳細
        if hasattr(packet, 'get_response_summary'):
            summary = packet.get_response_summary()
            if summary:
                self._log_summary(summary)
        elif hasattr(packet, 'get_weather_data'):
            weather_data = packet.get_weather_data()
            if weather_data:
                self.logger.debug(f"  Weather Data:")
                if 'area_code' in weather_data:
                    self.logger.debug(f"    Area Code: {weather_data['area_code']}\n")
                if 'weather_code' in weather_data:
                    self.logger.debug(f"    Weather Code: {weather_data['weather_code']}\n")
                if 'temperature' in weather_data:
                    self.logger.debug(f"    Temperature: {weather_data['temperature']}°C\n")
                if 'precipitation_prob' in weather_data:
                    self.logger.debug(f"    Precipitation: {weather_data['precipitation_prob']}%\n")
                if 'alert' in weather_data and weather_data['alert']:
                    self.logger.debug(f"    Alert: {weather_data['alert']}\n")
                if 'disaster' in weather_data and weather_data['disaster']:
                    self.logger.debug(f"    Disaster: {weather_data['disaster']}\n")
        elif summary:
            self._log_summary(summary)
    
    def log_error(self, error_msg: str, error_code: Optional[str] = None) -> None:
        """
        エラー情報をログ出力
        
        Args:
            error_msg: エラーメッセージ
            error_code: エラーコード（オプション）
        """
        if error_code:
            self.logger.error(f"[{error_code}] {error_msg}")
        else:
            self.logger.error(error_msg)
    
    def debug(self, message: str) -> None:
        """
        デバッグメッセージをログ出力
        
        Args:
            message: デバッグメッセージ
        """
        if self.debug_enabled:
            self.logger.debug(message)
    
    def info(self, message: str) -> None:
        """
        情報メッセージをログ出力
        
        Args:
            message: 情報メッセージ
        """
        self.logger.info(message)
    
    def warning(self, message: str) -> None:
        """
        警告メッセージをログ出力
        
        Args:
            message: 警告メッセージ
        """
        self.logger.warning(message)
    
    def error(self, message: str) -> None:
        """
        エラーメッセージをログ出力
        
        Args:
            message: エラーメッセージ
        """
        self.logger.error(message)
    
    def log_success_result(self, result: dict, operation_type: str = "OPERATION", execution_time: float = None) -> None:
        """
        成功時の結果内容を統一フォーマットでログ出力（非デバッグモードでも表示）
        
        Args:
            result: 結果データの辞書
            operation_type: 操作タイプ（表示用）
            execution_time: 実行時間（秒）
        """
        # 成功時の結果は常に表示（デバッグモードに関係なく）
        self.logger.info("----------------------------------------")
        
        # 実行時間の表示
        if execution_time is not None:
            self.logger.info(f"✓ {operation_type} successful! (Execution time: {execution_time:.3f}s)")
        else:
            self.logger.info(f"✓ {operation_type} successful!")
        
        self.logger.info("=== Received weather data ===")
        
        # エリアコード
        if 'area_code' in result and result['area_code']:
            self.logger.info(f"Area Code: {result['area_code']}")
        
        # タイムスタンプ
        if 'timestamp' in result and result['timestamp']:
            self.logger.info(f"Timestamp: {time.ctime(result['timestamp'])}")
        
        # 気象データ
        if 'weather_code' in result and result['weather_code'] is not None:
            self.logger.info(f"Weather Code: {result['weather_code']}")
        
        if 'temperature' in result and result['temperature'] is not None:
            self.logger.info(f"Temperature: {result['temperature']}°C")
        
        if 'precipitation_prob' in result and result['precipitation_prob'] is not None:
            self.logger.info(f"precipitation_prob: {result['precipitation_prob']}%")
        
        # 警報・災害情報
        if 'alert' in result and result['alert']:
            self.logger.info(f"alert: {result['alert']}")
        
        if 'disaster' in result and result['disaster']:
            self.logger.info(f"disaster: {result['disaster']}")
        
        # キャッシュ情報
        if 'cache_hit' in result and result['cache_hit']:
            self.logger.info("Source: Cache")
        
        # タイミング情報（簡略版）
        if 'timing' in result:
            timing = result['timing']
            if 'total_time' in timing:
                self.logger.info(f"Response Time: {timing['total_time']:.3f}s")
        
        self.logger.info("==============================")
    
    def log_unified_packet_received(self, operation_type: str, execution_time: float, data: Dict[str, Any]) -> None:
        """
        統一フォーマットでパケット受信成功時のログを出力
        
        Args:
            operation_type: 操作タイプ（例：Direct request）
            execution_time: 実行時間（秒）
            data: 受信データの辞書
        """
        self.logger.info("----------------------------------------")
        self.logger.info("")
        self.logger.info(f"✓ {operation_type} successful! (Execution time: {execution_time:.3f}s)")
        self.logger.info("=== Received weather data ===")
        
        # エリアコード
        if 'area_code' in data and data['area_code']:
            self.logger.info(f"Area Code: {data['area_code']}")
        
        # タイムスタンプ
        if 'timestamp' in data and data['timestamp']:
            self.logger.info(f"Timestamp: {time.ctime(data['timestamp'])}")
        
        # 気象データ
        if 'weather_code' in data and data['weather_code'] is not None:
            self.logger.info(f"Weather Code: {data['weather_code']}")
        
        if 'temperature' in data and data['temperature'] is not None:
            self.logger.info(f"Temperature: {data['temperature']}°C")
        
        if 'precipitation_prob' in data and data['precipitation_prob'] is not None:
            self.logger.info(f"precipitation_prob: {data['precipitation_prob']}%")
        
        # 警報・災害情報
        if 'alert' in data and data['alert']:
            self.logger.info(f"alert: {data['alert']}")
        
        if 'disaster' in data and data['disaster']:
            self.logger.info(f"disaster: {data['disaster']}")
        
        self.logger.info("==============================")
    
    def _get_packet_type_name(self, packet_type: int) -> str:
        """パケットタイプ番号から名前を取得"""
        type_names = {
            0: "Location Request",
            1: "Location Response", 
            2: "Query Request",
            3: "Query Response",
            4: "Report Request",
            5: "Report Response",
            7: "Error Response"
        }
        return type_names.get(packet_type, f"Unknown({packet_type})")
    
    def _extract_request_flags(self, packet: Any) -> list:
        """リクエストパケットからフラグ情報を抽出"""
        flags = []
        
        flag_mappings = [
            ('weather_flag', 'Weather'),
            ('temperature_flag', 'Temperature'),
            ('pop_flag', 'Precipitation'),
            ('alert_flag', 'Alert'),
            ('disaster_flag', 'Disaster')
        ]
        
        for attr_name, display_name in flag_mappings:
            if hasattr(packet, attr_name) and getattr(packet, attr_name):
                flags.append(display_name)
        
        return flags
    
    def _format_weather_data(self, weather_data: dict) -> str:
        """気象データを簡潔にフォーマット"""
        parts = []
        
        if 'weather_code' in weather_data and weather_data['weather_code'] is not None:
            parts.append(f"Weather: {weather_data['weather_code']}")
        
        if 'temperature' in weather_data and weather_data['temperature'] is not None:
            parts.append(f"Temp: {weather_data['temperature']}°C")
        
        if 'precipitation_prob' in weather_data and weather_data['precipitation_prob'] is not None:
            parts.append(f"Precip: {weather_data['precipitation_prob']}%")
        
        if 'alert' in weather_data and weather_data['alert']:
            parts.append("Alert: Yes")
        
        if 'disaster' in weather_data and weather_data['disaster']:
            parts.append("Disaster: Yes")
        
        return ", ".join(parts) if parts else "No data"
    
    def _log_summary(self, summary: Any) -> None:
        """
        サマリー情報を適切にフォーマットして表示
        
        Args:
            summary: サマリー情報（辞書、文字列、その他）
        """
        if isinstance(summary, dict):
            # 辞書の場合：各キーとバリューのペアを改行して表示
            self.logger.debug("  Summary:")
            for key, value in summary.items():
                self.logger.debug(f"    {key}: {value}")
        else:
            # その他の場合：そのまま表示
            self.logger.debug(f"  Summary: {summary}")


def create_debug_logger(logger_name: str, debug_enabled: bool = False) -> PacketDebugLogger:
    """
    パケットデバッグロガーを作成する便利関数
    
    Args:
        logger_name: ロガー名
        debug_enabled: デバッグモードの有効/無効
        
    Returns:
        PacketDebugLogger: デバッグロガーインスタンス
    """
    return PacketDebugLogger(logger_name, debug_enabled)