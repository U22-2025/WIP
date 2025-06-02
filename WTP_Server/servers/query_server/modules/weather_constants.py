"""
気象データサーバーで使用する定数定義
"""

class WeatherConstants:
    """気象データ関連の定数"""
    
    # パケットタイプ
    REQUEST_TYPE = 2
    RESPONSE_TYPE = 3
    
    # 温度関連
    TEMPERATURE_OFFSET = 100  # 0℃を表す値
    MIN_TEMPERATURE = 0       # 最小温度値（-100℃）
    MAX_TEMPERATURE = 255     # 最大温度値（+155℃）
    DEFAULT_TEMPERATURE = 100 # デフォルト温度（0℃）
    
    # 降水確率
    MIN_PRECIPITATION = 0     # 最小降水確率
    MAX_PRECIPITATION = 100   # 最大降水確率
    DEFAULT_PRECIPITATION = 0 # デフォルト降水確率
    
    # 天気コード
    DEFAULT_WEATHER_CODE = 0  # デフォルト天気コード
    
    # 拡張フィールドフラグ
    EX_FIELD_DISABLED = 0
    EX_FIELD_ENABLED = 1
    
    # フラグ値
    FLAG_DISABLED = 0
    FLAG_ENABLED = 1


class NetworkConstants:
    """ネットワーク関連の定数"""
    
    # デフォルトサーバー設定
    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = 4111
    
    # バッファサイズ
    UDP_BUFFER_SIZE = 1024
    
    # タイムアウト設定
    SOCKET_TIMEOUT = 5
    SOCKET_CONNECT_TIMEOUT = 5


class RedisConstants:
    """Redis関連の定数"""
    
    # デフォルトRedis設定
    DEFAULT_HOST = "localhost"
    DEFAULT_PORT = "6379"
    DEFAULT_DB = 0
    
    # 接続プール設定
    CONNECTION_POOL_MULTIPLIER = 2  # ワーカー数に対する接続数の倍率
    
    # キープレフィックス
    WEATHER_KEY_PREFIX = "weather:"
    
    # タイムアウト設定
    DEFAULT_TIMEOUT = 5


class CacheConstants:
    """キャッシュ関連の定数"""
    
    # キャッシュキープレフィックス
    KEY_PREFIX = "weather:"
    
    # TTL（秒）
    DEFAULT_TTL = 3600  # 1時間


class ThreadConstants:
    """スレッド関連の定数"""
    
    # デフォルトワーカー数
    DEFAULT_MAX_WORKERS = 20
    
    # スレッド名プレフィックス
    THREAD_NAME_PREFIX = "weather-worker"


class DebugConstants:
    """デバッグ関連の定数"""
    
    # ログメッセージ
    REQUEST_SEPARATOR = "=== RECEIVED REQUEST PACKET ==="
    RESPONSE_SEPARATOR = "=== SENDING RESPONSE PACKET ==="
    TIMING_SEPARATOR = "=== TIMING INFORMATION ==="
    
    # 時間単位変換
    MS_MULTIPLIER = 1000  # 秒をミリ秒に変換
