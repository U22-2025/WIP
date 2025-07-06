"""
WIPプロトコル認証ユーティリティ

クライアント認証機能のための認証ハッシュ計算とバリデーション機能を提供します。
"""

import hashlib
from typing import Optional

# 使用可能なハッシュアルゴリズム
SUPPORTED_HASH_ALGORITHMS = {
    'md5': hashlib.md5,
    'sha256': hashlib.sha256,
    'sha1': hashlib.sha1,
    'sha512': hashlib.sha512
}

# デフォルトハッシュアルゴリズム
DEFAULT_HASH_ALGORITHM = 'sha512'


class AuthenticationError(Exception):
    """認証関連のエラー"""
    pass


class WIPAuth:
    """
    WIPプロトコルの認証機能
    
    リプレイアタック対策を含む軽量な認証機能により、
    不正なデータの送信・インジェクションを防ぐ。
    """
    
    @staticmethod
    def calculate_auth_hash(packet_id: int, timestamp: int, passphrase: str, algorithm: str = DEFAULT_HASH_ALGORITHM) -> bytes:
        """
        認証ハッシュを計算
        
        Args:
            packet_id: パケットID (12bit)
            timestamp: UNIX時間 (64bit)
            passphrase: 予め共有されたパスフレーズ
            algorithm: ハッシュアルゴリズム ('md5', 'sha256', 'sha1', 'sha512')
            
        Returns:
            認証ハッシュ値（可変長）
            
        Raises:
            ValueError: パラメータが不正な場合
        """
        # パラメータのバリデーション
        if not (0 <= packet_id <= 0xFFF):  # 12bit範囲チェック
            raise ValueError(f"パケットIDが範囲外です: {packet_id} (0-4095の範囲である必要があります)")
        
        if not (0 <= timestamp <= 0xFFFFFFFFFFFFFFFF):  # 64bit範囲チェック
            raise ValueError(f"タイムスタンプが範囲外です: {timestamp}")
        
        if not isinstance(passphrase, str) or not passphrase:
            raise ValueError("パスフレーズは空でない文字列である必要があります")
        
        # アルゴリズムの検証
        if algorithm not in SUPPORTED_HASH_ALGORITHMS:
            raise ValueError(f"サポートされていないハッシュアルゴリズム: {algorithm}. 利用可能: {list(SUPPORTED_HASH_ALGORITHMS.keys())}")
        
        try:
            # パケットIDとタイムスタンプをバイト列に変換 (リトルエンディアン)
            packet_id_bytes = packet_id.to_bytes(2, byteorder='little')  # 12bitを2バイトに
            timestamp_bytes = timestamp.to_bytes(8, byteorder='little')  # 64bitを8バイトに
            passphrase_bytes = passphrase.encode('utf-8')
            
            # 結合してハッシュ化
            combined = packet_id_bytes + timestamp_bytes + passphrase_bytes
            hash_func = SUPPORTED_HASH_ALGORITHMS[algorithm]
            return hash_func(combined).digest()
            
        except Exception as e:
            raise ValueError(f"認証ハッシュの計算中にエラーが発生しました: {e}")
    
    @staticmethod
    def verify_auth_hash(
        packet_id: int,
        timestamp: int,
        passphrase: str,
        received_hash: bytes,
        algorithm: str = DEFAULT_HASH_ALGORITHM
    ) -> bool:
        """
        認証ハッシュを検証
        
        Args:
            packet_id: パケットID (12bit)
            timestamp: UNIX時間 (64bit)
            passphrase: 予め共有されたパスフレーズ
            received_hash: 受信した認証ハッシュ
            algorithm: ハッシュアルゴリズム ('md5', 'sha256', 'sha1', 'sha512')
            
        Returns:
            認証成功の場合True、失敗の場合False
        """
        try:
            if not isinstance(received_hash, bytes):
                return False
                
            if len(received_hash) == 0:
                return False
                
            # 期待されるハッシュ値を計算
            expected_hash = WIPAuth.calculate_auth_hash(packet_id, timestamp, passphrase, algorithm)
            
            # 定数時間での比較（タイミング攻撃対策）
            return WIPAuth._secure_compare(expected_hash, received_hash)
            
        except Exception:
            return False
    
    @staticmethod
    def _secure_compare(a: bytes, b: bytes) -> bool:
        """
        定数時間でのバイト列比較（タイミング攻撃対策）
        
        Args:
            a: 比較対象1
            b: 比較対象2
            
        Returns:
            一致する場合True
        """
        if len(a) != len(b):
            return False
        
        result = 0
        for x, y in zip(a, b):
            result |= x ^ y
        
        return result == 0


class AuthConfig:
    """
    認証設定クラス
    """
    
    def __init__(
        self,
        enabled: bool = False,
        passphrase: Optional[str] = None,
        target_packet_types: Optional[set] = None,
        hash_algorithm: str = DEFAULT_HASH_ALGORITHM
    ):
        """
        認証設定の初期化
        
        Args:
            enabled: 認証機能の有効/無効
            passphrase: パスフレーズ
            target_packet_types: 認証対象のパケットタイプ（デフォルト: {4, 5}）
            hash_algorithm: ハッシュアルゴリズム（デフォルト: 'md5'）
        """
        self.enabled = enabled
        self.passphrase = passphrase
        self.target_packet_types = target_packet_types or {4, 5}  # デフォルトはタイプ4,5
        self.hash_algorithm = hash_algorithm
    
    def is_auth_required(self, packet_type: int) -> bool:
        """
        指定されたパケットタイプで認証が必要かチェック
        
        Args:
            packet_type: パケットタイプ
            
        Returns:
            認証が必要な場合True
        """
        return self.enabled and packet_type in self.target_packet_types
    
    def validate(self) -> None:
        """
        設定の妥当性を検証
        
        Raises:
            ValueError: 設定が不正な場合
        """
        if self.enabled and not self.passphrase:
            raise ValueError("認証が有効な場合、パスフレーズが必要です")
        
        if self.enabled and not isinstance(self.passphrase, str):
            raise ValueError("パスフレーズは文字列である必要があります")
        
        if not isinstance(self.target_packet_types, set):
            raise ValueError("対象パケットタイプはsetオブジェクトである必要があります")
        
        if self.hash_algorithm not in SUPPORTED_HASH_ALGORITHMS:
            raise ValueError(f"サポートされていないハッシュアルゴリズム: {self.hash_algorithm}. 利用可能: {list(SUPPORTED_HASH_ALGORITHMS.keys())}")
    
    def calculate_auth_hash(self, packet_id: int, timestamp: int) -> bytes:
        """
        設定されたアルゴリズムで認証ハッシュを計算
        
        Args:
            packet_id: パケットID (12bit)
            timestamp: UNIX時間 (64bit)
            
        Returns:
            認証ハッシュ値
            
        Raises:
            ValueError: 認証が無効またはパスフレーズが未設定の場合
        """
        if not self.enabled or not self.passphrase:
            raise ValueError("認証が無効またはパスフレーズが未設定です")
        
        return WIPAuth.calculate_auth_hash(packet_id, timestamp, self.passphrase, self.hash_algorithm)
    
    def verify_auth_hash(self, packet_id: int, timestamp: int, received_hash: bytes) -> bool:
        """
        設定されたアルゴリズムで認証ハッシュを検証
        
        Args:
            packet_id: パケットID (12bit)
            timestamp: UNIX時間 (64bit)
            received_hash: 受信した認証ハッシュ
            
        Returns:
            認証成功の場合True、失敗の場合False
        """
        if not self.enabled or not self.passphrase:
            return False
        
        return WIPAuth.verify_auth_hash(packet_id, timestamp, self.passphrase, received_hash, self.hash_algorithm)


# 認証失敗時のエラーコード定数
class AuthErrorCode:
    """認証エラーコード定数"""
    AUTH_REQUIRED = 0x01      # 認証が必要
    INVALID_HASH = 0x02       # 認証ハッシュが不正
    MISSING_AUTH_FIELD = 0x03 # 認証フィールドが見つからない
    PASSPHRASE_MISMATCH = 0x04 # パスフレーズが一致しない