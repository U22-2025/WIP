import sys
import os
import time
tempfile = __import__('tempfile')

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../srv')))

from WIPCommonPy.utils.file_cache import PersistentCache


def test_persistent_cache_set_get_expire():
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, 'c.json')
        cache = PersistentCache(cache_file=f, ttl_hours=0.00028)
        cache.set('k', 'v')
        assert cache.get('k') == 'v'
        time.sleep(1.1)
        assert cache.get('k') is None


def test_persistent_cache_clear():
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, 'c.json')
        cache = PersistentCache(cache_file=f)
        cache.set('k1', 'v1')
        assert cache.size() == 1
        cache.clear()
        assert cache.size() == 0
