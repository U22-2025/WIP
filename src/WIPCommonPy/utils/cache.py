import threading
from datetime import datetime, timedelta

class Cache:
    def __init__(self, default_ttl: timedelta = timedelta(minutes=30), enabled: bool = True):
        """
        汎用キャッシュクラス
        
        :param default_ttl: デフォルトの有効期限（デフォルト30分）
        """
        self.enabled = enabled
        self._cache = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl

    def set(self, key: str, value: any, ttl: timedelta = None) -> None:
        """
        キャッシュにデータを設定
        
        :param key: キャッシュキー
        :param value: キャッシュ値
        :param ttl: 有効期限（Noneの場合はデフォルト値を使用）
        """
        if not self.enabled:
            return
        with self._lock:
            expire = datetime.now() + (ttl or self.default_ttl)
            self._cache[key] = (value, expire)

    def get(self, key: str) -> any:
        """
        キャッシュからデータを取得
        
        :param key: キャッシュキー
        :return: キャッシュ値（有効期限切れまたは存在しない場合はNone）
        """
        if not self.enabled:
            return None
        with self._lock:
            item = self._cache.get(key)
            if not item:
                return None

            value, expire = item
            if datetime.now() > expire:
                del self._cache[key]
                return None
            return value

    def delete(self, key: str) -> None:
        """
        キャッシュからデータを削除
        
        :param key: キャッシュキー
        """
        if not self.enabled:
            return
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        """
        キャッシュを全クリア
        """
        if not self.enabled:
            return
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """
        キャッシュエントリ数を返す
        """
        if not self.enabled:
            return 0
        with self._lock:
            return len(self._cache)
