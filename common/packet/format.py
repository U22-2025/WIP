"""
パケットフォーマットの基本実装クラス
共通ヘッダー部分の構造を定義し、ビット操作のユーティリティを提供します
"""
from .format_extended import FormatExtended


class Format(FormatExtended):
    """
    パケットフォーマットの基本実装クラス

    このクラスは、パケットフォーマットの基本的な実装を提供します。
    Request/Response クラスの代わりに直接使用でき、
    共通ヘッダーと拡張フィールドの両方をサポートします。
    
    主な用途:
    1. 汎用的なパケット処理
       - 特殊な処理が不要な場合の基本的なパケット処理
       - プロトタイピングやテスト用途
       
    2. カスタムパケットの基底クラス
       - 新しいパケットタイプを実装する際の基底クラスとして使用
       - 共通機能を継承しつつ、独自の拡張が可能
    
    ビットフィールド構造:
    - version:          1-4bit   (4ビット)
    - packet_id:        5-16bit  (12ビット)
    - type:             17-19bit (3ビット)
    - weather_flag:     20bit    (1ビット)
    - temperature_flag: 21bit    (1ビット)
    - pop_flag:        22bit    (1ビット)
    - alert_flag:       23bit    (1ビット)
    - disaster_flag:    24bit    (1ビット)
    - ex_flag:          25bit    (1ビット)
    - day:              26-28bit (3ビット)
    - reserved:         29-32bit (4ビット)
    - timestamp:        33-96bit (64ビット)
    - area_code:        97-116bit (20ビット)
    - checksum:         117-128bit (12ビット)
    
    拡張フィールド (ex_flag=1の場合):
    - ex_field: 129- (可変長)
        - alert: 警報情報 (文字列のリスト)
        - disaster: 災害情報 (文字列のリスト)
        - latitude: 緯度 (数値)
        - longitude: 経度 (数値)
        - source: 送信元情報 (ip, port) のタプル
    
    Example:
        # 基本的な使用方法
        packet = Format(
            version=1,
            packet_id=1,
            type=0,
            weather_flag=1,
            timestamp=int(datetime.now().timestamp())
        )
        
        # 拡張フィールドを使用する場合
        packet = Format(
            version=1,
            packet_id=1,
            type=0,
            ex_flag=1,
            timestamp=int(datetime.now().timestamp()),
            ex_field={
                'alert': ["津波警報"],
                'disaster': ["土砂崩れ"],
                'latitude': 35.6895,
                'longitude': 139.6917,
                'source': ("127.0.0.1", 8080)
            }
        )
        
        # バイト列への変換
        data = packet.to_bytes()
        
        # バイト列からの復元
        restored = Format.from_bytes(data)
    """

    def __init__(self, *args, **kwargs) -> None:
        """特別な処理は行わず親クラスの初期化のみを実行"""
        super().__init__(*args, **kwargs)
