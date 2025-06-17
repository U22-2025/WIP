"""
設定管理クラス
環境変数とデフォルト値を統合管理
"""

import os
from dotenv import load_dotenv
from .weather_constants import NetworkConstants, RedisConstants, ThreadConstants


class ConfigManager:
    """設定管理クラス"""
    
    def __init__(self):
        """設定を初期化"""
        # 環境変数を読み込む
        load_dotenv()
        self._load_config()
    
    def _load_config(self):
        """設定値を環境変数またはデフォルト値から読み込み"""
        
        # サーバー設定
        self.server_host = os.getenv('WIP_HOST', NetworkConstants.DEFAULT_HOST)
        self.server_port = int(os.getenv('QUERY_GENERATOR_PORT', NetworkConstants.DEFAULT_PORT))
        
        # Redis設定
        self.redis_host = os.getenv('REDIS_HOST', RedisConstants.DEFAULT_HOST)
        self.redis_port = int(os.getenv('REDIS_PORT', RedisConstants.DEFAULT_PORT))
        self.redis_db = int(os.getenv('REDIS_DB', RedisConstants.DEFAULT_DB))
        
        # スレッド設定
        self.max_workers = int(os.getenv('WIP_MAX_WORKERS', ThreadConstants.DEFAULT_MAX_WORKERS))
        
        # ネットワーク設定
        self.udp_buffer_size = int(os.getenv('UDP_BUFFER_SIZE', NetworkConstants.UDP_BUFFER_SIZE))
        self.socket_timeout = NetworkConstants.SOCKET_TIMEOUT
        self.socket_connect_timeout = NetworkConstants.SOCKET_CONNECT_TIMEOUT
        
        # デバッグ設定
        self.debug = os.getenv('WIP_DEBUG', 'false').lower() == 'true'
        
        # バージョン
        self.version = int(os.getenv('PROTOCOL_VERSION', '1'))
    
    def get_redis_pool_config(self):
        """Redis接続プール設定を取得"""
        return {
            'host': self.redis_host,
            'port': self.redis_port,
            'db': self.redis_db,
            'max_connections': self.max_workers * RedisConstants.CONNECTION_POOL_MULTIPLIER,
            'retry_on_timeout': True,
            'socket_timeout': self.socket_timeout,
            'socket_connect_timeout': self.socket_connect_timeout
        }
    
    def validate_config(self):
        """設定値の妥当性をチェック"""
        errors = []
        
        if self.server_port < 1 or self.server_port > 65535:
            errors.append(f"Invalid server port: {self.server_port}")
        
        if self.redis_port < 1 or self.redis_port > 65535:
            errors.append(f"Invalid Redis port: {self.redis_port}")
        
        if self.max_workers < 1:
            errors.append(f"Invalid max_workers: {self.max_workers}")
        
        if errors:
            raise ValueError("Configuration validation failed: " + "; ".join(errors))
        
        return True
    
    def __str__(self):
        """設定内容を文字列で表示"""
        return (
            f"ConfigManager(\n"
            f"  server: {self.server_host}:{self.server_port}\n"
            f"  redis: {self.redis_host}:{self.redis_port}/{self.redis_db}\n"
            f"  workers: {self.max_workers}\n"
            f"  debug: {self.debug}\n"
            f")"
        )
