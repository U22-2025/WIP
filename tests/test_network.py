from WIPCommonPy.utils.network import resolve_ipv4


def test_resolve_ipv4_localhost():
    ip = resolve_ipv4('localhost')
    assert ip.startswith('127.')
