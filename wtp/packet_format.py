"""
パケットフォーマット処理クラス
このモジュールは、特定のバイナリパケットフォーマットの処理を行うクラスを提供します。

このモジュールは後方互換性のために維持されています。
新しいコードでは wtp.packet パッケージを直接使用してください。
"""
from .packet.exceptions import BitFieldError
from .packet.format import Format
from .packet.request import Request
from .packet.response import Response

__all__ = ['BitFieldError', 'Format', 'Request', 'Response']

# 使用例
if __name__ == "__main__":
    from datetime import datetime
    
    # テストデータ
    latitude = 35.6895
    longitude = 139.6917
    
    # リクエストパケットのテスト
    req = Request(
        version=1,
        packet_id=1,
        type=0,
        weather_flag=0,
        timestamp=int(datetime.now().timestamp()),
        ex_flag=1,
        ex_field={
            'alert': ["津波警報"],
            'disaster': ["土砂崩れ"],
            'latitude': latitude,
            'longitude': longitude,
            'source_ip': "127.0.0.1"
        }
    )
    print(f"リクエスト: {req.__dict__}")
    print(f"バイト列: {req.to_bytes()}")
    
    # バイト列からの復元テスト
    req1 = Request.from_bytes(req.to_bytes())
    print(f"復元したリクエスト: {req1.__dict__}")

    # レスポンスパケットのテスト
    res = Response(
        version=1,
        packet_id=1,
        type=1,
        weather_flag=0,
        timestamp=int(datetime.now().timestamp()),
        ex_flag=1,
        ex_field={
            'alert': ["津波警報"],
            'disaster': ["土砂崩れ"],
            'latitude': latitude,
            'longitude': longitude,
            'source_ip': "127.0.0.1"
        }
    )
    print(f"レスポンス: {res.__dict__}")
    print(f"バイト列: {res.to_bytes()}")
    
    # バイト列からの復元テスト
    res1 = Response.from_bytes(res.to_bytes())
    print(f"復元したレスポンス: {res1.__dict__}")
