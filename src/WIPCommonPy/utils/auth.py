"""
WIPプロジェクト用認証モジュール
パケット認証とAPIキー管理を提供
"""

import hashlib
import hmac
from typing import Optional
import os


class WIPAuth:
    """WIPプロジェクト用認証クラス"""

    def __init__(self, secret_key: Optional[str] = None):
        """
        認証クラスの初期化

        Args:
            secret_key: 認証用シークレットキー（Noneの場合は環境変数から取得）
        """
        self.secret_key = secret_key or os.getenv("WIP_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("認証用シークレットキーが設定されていません")

    @staticmethod
    def calculate_auth_hash(
        packet_id: int, timestamp: int, passphrase: str
    ) -> bytes:
        """
        認証ハッシュを計算

        Args:
            packet_id: パケットID
            timestamp: タイムスタンプ
            passphrase: パスフレーズ

        Returns:
            計算された認証ハッシュ（バイト列）
        """
        # 認証データを構築
        auth_data = f"{packet_id}:{timestamp}:{passphrase}".encode("utf-8")

        # HMAC-SHA256でハッシュを計算
        # パスフレーズをキーとして使用
        auth_hash = hmac.new(
            passphrase.encode("utf-8"), auth_data, hashlib.sha256
        ).digest()

        return auth_hash

    @staticmethod
    def verify_auth_hash(
        packet_id: int, timestamp: int, passphrase: str, received_hash: bytes
    ) -> bool:
        """
        認証ハッシュを検証

        Args:
            packet_id: パケットID
            timestamp: タイムスタンプ
            passphrase: パスフレーズ
            received_hash: 受信した認証ハッシュ

        Returns:
            認証ハッシュが有効な場合はTrue
        """
        # 期待される認証ハッシュを計算
        expected_hash = WIPAuth.calculate_auth_hash(
            packet_id, timestamp, passphrase
        )

        # 定数時間比較で検証
        return hmac.compare_digest(expected_hash, received_hash)
