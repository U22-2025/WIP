from .response import Response
from .extended_field import ExtendedField
from datetime import datetime

class ErrorResponse(Response):
    def __init__(self, version=1, packet_id=None, type=7, error_code=None, timestamp=datetime.now().timestamp()):
        """
        エラーレスポンスの初期化
        
        Args:
            version: プロトコルバージョン
            packet_id: パケットID
            type: パケットタイプ (7=エラー)
            error_code: エラーコード
            timestamp: タイムスタンプ
        """
        super().__init__(
            version=version,
            packet_id=packet_id,
            type=type,
            timestamp=timestamp
        )
        self.error_code = error_code
        
    @property
    def error_code(self):
        return self.weather_code
        
    @error_code.setter
    def error_code(self, value):
        self.weather_code = value
        
    def deserialize(self, data):
        """
        バイト列からエラーレスポンスをデシリアライズ
        
        Args:
            data: デシリアライズするバイト列
            
        Returns:
            デシリアライズしたバイト数
        """
        # 基本フィールドをデシリアライズ
        base_len = super().deserialize(data)
        # ex_fieldをデシリアライズ
        ex_data = data[base_len:]
        self.ex_field.deserialize(ex_data)
        return base_len + len(ex_data)
        
    def to_bytes(self):
        """
        エラーレスポンスをバイト列にシリアライズ
        
        Returns:
            シリアライズされたバイト列
        """
        return super().to_bytes()