"""永続キャッシュ - ファイルベースのキャッシュシステム"""

import json
import time
from pathlib import Path
from typing import Optional


class PersistentCache:
    """ファイルベースの永続キャッシュ"""

    def __init__(self, cache_file: str = "WIP_Client/coordinate_cache.json", ttl_hours: int = 24, enabled: bool = True):
        self.enabled = enabled
        self.cache_file = Path(cache_file)
        self.ttl_seconds = ttl_hours * 3600
        self._cache = {}
        if self.enabled:
            self._load_cache()
    
    def _load_cache(self):
        """キャッシュファイルから読み込み"""
        if not self.enabled or not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                current_time = time.time()
                
                # 有効期限内のエントリのみ保持
                self._cache = {
                    key: value for key, value in data.items()
                    if 'timestamp' in value and 'area_code' in value
                    and current_time - value['timestamp'] < self.ttl_seconds
                }
        except (json.JSONDecodeError, KeyError, IOError):
            self._cache = {}
    
    def _save_cache(self):
        """キャッシュファイルに保存"""
        if not self.enabled:
            return
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except IOError:
            pass  # 保存に失敗しても継続
    
    def get(self, key: str) -> Optional[str]:
        """キャッシュから値を取得"""
        if not self.enabled:
            return None
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry['timestamp'] < self.ttl_seconds:
                return entry['area_code']
            else:
                # 期限切れエントリを削除
                del self._cache[key]
                self._save_cache()
        return None
    
    def set(self, key: str, area_code: str):
        """キャッシュに値を設定"""
        if not self.enabled:
            return
        self._cache[key] = {
            'area_code': area_code,
            'timestamp': time.time()
        }
        self._save_cache()
    
    def clear(self):
        """キャッシュをクリア"""
        if not self.enabled:
            return
        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
    
    def size(self) -> int:
        """キャッシュサイズを取得"""
        if not self.enabled:
            return 0
        return len(self._cache)
