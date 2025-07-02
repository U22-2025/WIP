"""シンプルで拡張性の高いスレッドセーフキャッシュ実装."""

import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Generic, Iterable, Optional, Tuple, TypeVar


T = TypeVar("T")


@dataclass
class _CacheEntry(Generic[T]):
    """キャッシュに格納するエントリ."""

    value: T
    expire: datetime

class Cache(Generic[T]):
    def __init__(self, default_ttl: timedelta = timedelta(minutes=30)):
        """
        汎用キャッシュクラス
        
        :param default_ttl: デフォルトの有効期限（デフォルト30分）
        """
        self._cache: Dict[str, _CacheEntry[T]] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl

    def set(self, key: str, value: T, ttl: Optional[timedelta] = None) -> None:
        """
        キャッシュにデータを設定
        
        :param key: キャッシュキー
        :param value: キャッシュ値
        :param ttl: 有効期限（Noneの場合はデフォルト値を使用）
        """
        with self._lock:
            expire = datetime.now() + (ttl or self.default_ttl)
            self._cache[key] = _CacheEntry(value=value, expire=expire)

    def get_or_set(
        self, key: str, factory: Callable[[], T], ttl: Optional[timedelta] = None
    ) -> T:
        """指定キーの値を取得し、存在しなければ生成して設定する"""
        with self._lock:
            entry = self._cache.get(key)
            if entry is not None and datetime.now() <= entry.expire:
                return entry.value
            value = factory()
            expire = datetime.now() + (ttl or self.default_ttl)
            self._cache[key] = _CacheEntry(value=value, expire=expire)
            return value

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """
        キャッシュからデータを取得
        
        :param key: キャッシュキー
        :return: キャッシュ値（有効期限切れまたは存在しない場合はNone）
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None or datetime.now() > entry.expire:
                self._cache.pop(key, None)
                return default
            return entry.value

    def cleanup(self) -> None:
        """期限切れのエントリを削除"""
        now = datetime.now()
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if now > v.expire]
            for k in expired_keys:
                del self._cache[k]

    def items(self) -> Iterable[Tuple[str, T]]:
        """有効な(キー, 値)ペアを列挙"""
        self.cleanup()
        with self._lock:
            for key, entry in self._cache.items():
                yield key, entry.value

    def __repr__(self) -> str:
        return f"Cache(size={len(self)})"

    def delete(self, key: str) -> None:
        """
        キャッシュからデータを削除
        
        :param key: キャッシュキー
        """
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        """
        キャッシュを全クリア
        """
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """
        キャッシュエントリ数を返す
        """
        with self._lock:
            return len(self._cache)

    __len__ = size

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._cache and datetime.now() <= self._cache[key].expire

