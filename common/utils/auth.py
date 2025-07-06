"""
WIPプロジェクト用認証モジュール
パケット認証とAPIキー管理を提供
"""

import hashlib
import hmac
from typing import Optional, Tuple
import os
from datetime import datetime, timedelta

class WIPAuth:
    """WIPプロジェクト用認証クラス"""
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        認証クラスの初期化
        
        Args:
            secret_key: 認証用シークレットキー（Noneの場合は環境変数から取得）
        """
        self.secret_key = secret_key or os.getenv('WIP_SECRET_KEY')
        if not self.secret_key:
            raise ValueError("認証用シークレットキーが設定されていません")
            
        self.token_expiry = timedelta(hours=1)  # トークンの有効期限
    
    def generate_packet_signature(self, packet_data: bytes) -> str:
        """
        パケットデータの署名を生成
        
        Args:
            packet_data: 署名対象のバイト列
            
        Returns:
            生成された署名（HMAC-SHA256）
        """
        return hmac.new(
            self.secret_key.encode(),
            packet_data,
            hashlib.sha256
        ).hexdigest()
    
    def verify_packet_signature(self, packet_data: bytes, signature: str) -> bool:
        """
        パケット署名を検証
        
        Args:
            packet_data: 検証対象のバイト列
            signature: 比較する署名
            
        Returns:
            署名が有効な場合はTrue
        """
        expected_sig = self.generate_packet_signature(packet_data)
        return hmac.compare_digest(expected_sig, signature)
    
    def generate_api_token(self, client_id: str) -> Tuple[str, datetime]:
        """
        APIトークンを生成
        
        Args:
            client_id: クライアント識別子
            
        Returns:
            (トークン, 有効期限)のタプル
        """
        expiry = datetime.now() + self.token_expiry
        token_data = f"{client_id}:{expiry.timestamp()}"
        token = hmac.new(
            self.secret_key.encode(),
            token_data.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{token}:{expiry.timestamp()}", expiry
    
    def verify_api_token(self, token: str, client_id: str) -> bool:
        """
        APIトークンを検証
        
        Args:
            token: 検証対象のトークン
            client_id: クライアント識別子
            
        Returns:
            トークンが有効な場合はTrue
        """
        try:
            token_part, expiry_ts = token.rsplit(':', 1)
            expiry = datetime.fromtimestamp(float(expiry_ts))
            
            if datetime.now() > expiry:
                return False
                
            expected_token, _ = self.generate_api_token(client_id)
            expected_token_part = expected_token.split(':', 1)[0]
            
            return hmac.compare_digest(token_part, expected_token_part)
        except (ValueError, IndexError):
            return False

# デフォルト認証インスタンス（シングルトンパターン）
_default_auth = None

def get_default_auth() -> WIPAuth:
    """デフォルト認証インスタンスを取得"""
    global _default_auth
    if _default_auth is None:
        _default_auth = WIPAuth()
    return _default_auth