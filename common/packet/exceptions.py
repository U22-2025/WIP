"""
パケットフォーマット処理に関連する例外クラス
"""

class ErrorPacketException(Exception):
    """エラーパケット処理に関する基底例外クラス"""
    pass


class InvalidErrorCodeException(ErrorPacketException):
    """無効なエラーコードが指定された場合の例外"""
    pass


class ErrorPacketSerializationException(ErrorPacketException):
    """エラーパケットのシリアライズ/デシリアライズに失敗した場合の例外"""
    pass


class BitFieldError(Exception):
    """ビットフィールド操作に関連するエラー"""
    pass
