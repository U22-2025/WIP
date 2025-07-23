import os
import time
from tempfile import TemporaryDirectory
from WIPCommonPy.utils.file_cache import PersistentCache


def test_persistent_cache_set_get_and_expiry():
    with TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'cache.json')
        cache = PersistentCache(cache_file=file_path, ttl_hours=0.00027)  # ~1s
        cache.set('key', '123')
        assert cache.get('key') == '123'
        time.sleep(1.1)
        assert cache.get('key') is None
        # file should exist
        assert os.path.exists(file_path)


def test_persistent_cache_clear():
    with TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, 'cache.json')
        cache = PersistentCache(cache_file=file_path)
        cache.set('k', 'v')
        assert cache.size() == 1
        cache.clear()
        assert cache.size() == 0
        assert not os.path.exists(file_path)


def test_persistent_cache_disabled(tmp_path):
    file_path = tmp_path / 'cache.json'
    cache = PersistentCache(cache_file=str(file_path), enabled=False)
    cache.set('k', 'v')
    assert cache.get('k') is None
    assert cache.size() == 0
    cache.clear()
    assert not file_path.exists()
