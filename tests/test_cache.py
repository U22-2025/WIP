import time
from datetime import timedelta
from WIPCommonPy.utils.cache import Cache


def test_cache_set_get_and_expiry():
    cache = Cache(default_ttl=timedelta(seconds=1))
    cache.set('foo', 'bar')
    assert cache.get('foo') == 'bar'
    time.sleep(1.1)
    assert cache.get('foo') is None


def test_cache_delete_and_clear():
    cache = Cache()
    cache.set('a', 1)
    cache.set('b', 2)
    assert cache.size() == 2
    cache.delete('a')
    assert cache.get('a') is None
    assert cache.size() == 1
    cache.clear()
    assert cache.size() == 0
