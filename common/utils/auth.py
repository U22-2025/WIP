"""
WIPプロトコル認証ユーティリティ

クライアント認証機能のための認証ハッシュ計算とバリデーション機能を提供します。
"""

import hashlib
from typing import Optional


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
    def calculate_auth_hash(packet_id: int, timestamp: int, passphrase: str) -> bytes:
        """
        認証ハッシュを計算
        
        Args:
            packet_id: パケットID (12bit)
            timestamp: UNIX時間 (64bit)
            passphrase: 予め共有されたパスフレーズ
            
        Returns:
            16バイトのMD5ハッシュ値
            
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
        
        try:
            # パケットIDとタイムスタンプをバイト列に変換 (リトルエンディアン)
            packet_id_bytes = packet_id.to_bytes(2, byteorder='little')  # 12bitを2バイトに
            timestamp_bytes = timestamp.to_bytes(8, byteorder='little')  # 64bitを8バイトに
            passphrase_bytes = passphrase.encode('utf-8')
            
            # 結合してハッシュ化
            combined = packet_id_bytes + timestamp_bytes + passphrase_bytes
            return hashlib.md5(combined).digest()  # 16バイトのハッシュ値
            
        except Exception as e:
            raise ValueError(f"認証ハッシュの計算中にエラーが発生しました: {e}")
    
    @staticmethod
    def verify_auth_hash(
        packet_id: int, 
        timestamp: int, 
        passphrase: str, 
        received_hash: bytes
    ) -> bool:
        """
        認証ハッシュを検証
        
        Args:
            packet_id: パケットID (12bit)
            timestamp: UNIX時間 (64bit)
            passphrase: 予め共有されたパスフレーズ
            received_hash: 受信した認証ハッシュ
            
        Returns:
            認証成功の場合True、失敗の場合False
        """
        try:
            if not isinstance(received_hash, bytes):
                return False
                
            if len(received_hash) != 16:
                return False
                
            # 期待されるハッシュ値を計算
            expected_hash = WIPAuth.calculate_auth_hash(packet_id, timestamp, passphrase)
            
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
        target_packet_types: Optional[set] = None
    ):
        """
        認証設定の初期化
        
        Args:
            enabled: 認証機能の有効/無効
            passphrase: パスフレーズ
            target_packet_types: 認証対象のパケットタイプ（デフォルト: {4, 5}）
        """
        self.enabled = enabled
        self.passphrase = passphrase
        self.target_packet_types = target_packet_types or {4, 5}  # デフォルトはタイプ4,5
    
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


# 認証失敗時のエラーコード定数
class AuthErrorCode:
    """認証エラーコード定数"""
    AUTH_REQUIRED = 0x01      # 認証が必要
    INVALID_HASH = 0x02       # 認証ハッシュが不正
    MISSING_AUTH_FIELD = 0x03 # 認証フィールドが見つからない
    PASSPHRASE_MISMATCH = 0x04 # パスフレーズが一致しない