"""
共通パケットデバッグログユーティリティ
各クライアントで重複していたデバッグログ機能を集約し、重要な情報のみを簡潔に出力
"""

import logging
import time
from typing import Any, Optional


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
    
    def log_request(self, packet: Any, operation_type: str = "REQUEST") -> None:
        """
        リクエストパケットの重要な情報のみをログ出力
        
        Args:
            packet: パケットオブジェクト
            operation_type: 操作タイプ（表示用）
        """
        if not self.debug_enabled:
            return
            
        self.logger.debug(f"\n=== {operation_type} ===")
        
        # パケットタイプに応じた情報表示
        if hasattr(packet, 'type'):
            packet_type_name = self._get_packet_type_name(packet.type)
            self.logger.debug(f"Type: {packet_type_name} ({packet.type})")
        
        if hasattr(packet, 'packet_id'):
            self.logger.debug(f"Packet ID: {packet.packet_id}")
        
        # 要求の内容を表示
        if hasattr(packet, 'get_request_summary'):
            summary = packet.get_request_summary()
            self.logger.debug(f"Request: {summary}")
        elif hasattr(packet, 'area_code'):
            self.logger.debug(f"Area Code: {packet.area_code}")
        
        # 座標情報
        if hasattr(packet, 'get_coordinates'):
            coords = packet.get_coordinates()
            if coords:
                self.logger.debug(f"Coordinates: {coords}")
        
        # フラグ情報（簡潔に）
        flags = self._extract_request_flags(packet)
        if flags:
            self.logger.debug(f"Data Requested: {', '.join(flags)}")
        
        self.logger.debug(f"Packet Size: {len(packet.to_bytes())} bytes")
        self.logger.debug("=" * 30)
    
    def log_response(self, packet: Any, operation_type: str = "RESPONSE") -> None:
        """
        レスポンスパケットの重要な情報のみをログ出力
        
        Args:
            packet: パケットオブジェクト
            operation_type: 操作タイプ（表示用）
        """
        if not self.debug_enabled:
            return
            
        self.logger.debug(f"\n=== {operation_type} ===")
        
        # パケットタイプに応じた情報表示
        if hasattr(packet, 'type'):
            packet_type_name = self._get_packet_type_name(packet.type)
            self.logger.debug(f"Type: {packet_type_name} ({packet.type})")
        
        # 成功/失敗状態
        if hasattr(packet, 'is_success'):
            success = packet.is_success()
            self.logger.debug(f"Status: {'Success' if success else 'Failed'}")
        elif hasattr(packet, 'is_valid'):
            valid = packet.is_valid()
            self.logger.debug(f"Status: {'Valid' if valid else 'Invalid'}")
        
        # 応答内容の要約
        if hasattr(packet, 'get_response_summary'):
            summary = packet.get_response_summary()
            self.logger.debug(f"Response: {summary}")
        elif hasattr(packet, 'get_weather_data'):
            weather_data = packet.get_weather_data()
            if weather_data:
                self.logger.debug(f"Weather Data: {self._format_weather_data(weather_data)}")
        
        # エリアコード
        if hasattr(packet, 'get_area_code'):
            area_code = packet.get_area_code()
            if area_code:
                self.logger.debug(f"Area Code: {area_code}")
        
        # エラー情報
        if hasattr(packet, 'error_code'):
            self.logger.debug(f"Error Code: {packet.error_code}")
        
        self.logger.debug(f"Packet Size: {len(packet.to_bytes())} bytes")
        self.logger.debug("=" * 30)
    
    def log_timing(self, operation_name: str, timing_info: dict) -> None:
        """
        タイミング情報をログ出力（重要な情報のみ）
        
        Args:
            operation_name: 操作名
            timing_info: タイミング情報の辞書
        """
        # タイミング情報ログは無効化
        pass
    
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
    
    def log_cache_operation(self, operation: str, key: str, hit: bool = False) -> None:
        """
        キャッシュ操作をログ出力
        
        Args:
            operation: 操作名（"get", "set", "miss", "hit"）
            key: キャッシュキー
            hit: キャッシュヒットかどうか
        """
        # キャッシュ操作ログは無効化
        pass
    
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
    
    def log_success_result(self, result: dict, operation_type: str = "OPERATION") -> None:
        """
        成功時の結果内容をログ出力（非デバッグモードでも表示）
        
        Args:
            result: 結果データの辞書
            operation_type: 操作タイプ（表示用）
        """
        # 成功時の結果は常に表示（デバッグモードに関係なく）
        self.logger.info(f"\n✓ {operation_type} Success!")
        
        # エリアコード
        if 'area_code' in result and result['area_code']:
            self.logger.info(f"Area Code: {result['area_code']}")
        
        # タイムスタンプ
        if 'timestamp' in result and result['timestamp']:
            import time
            self.logger.info(f"Timestamp: {time.ctime(result['timestamp'])}")
        
        # 気象データ
        if 'weather_code' in result and result['weather_code'] is not None:
            self.logger.info(f"Weather Code: {result['weather_code']}")
        
        if 'temperature' in result and result['temperature'] is not None:
            self.logger.info(f"Temperature: {result['temperature']}°C")
        
        if 'precipitation_prob' in result and result['precipitation_prob'] is not None:
            self.logger.info(f"Precipitation Probability: {result['precipitation_prob']}%")
        
        # 警報・災害情報
        if 'alert' in result and result['alert']:
            self.logger.info(f"Alert: {result['alert']}")
        
        if 'disaster' in result and result['disaster']:
            self.logger.info(f"Disaster Info: {result['disaster']}")
        
        # キャッシュ情報
        if 'cache_hit' in result and result['cache_hit']:
            self.logger.info("Source: Cache")
        
        # タイミング情報（簡略版）
        if 'timing' in result:
            timing = result['timing']
            if 'total_time' in timing:
                self.logger.info(f"Response Time: {timing['total_time']:.2f}ms")
    
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