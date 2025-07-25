from WIPCommonPy.utils.network import resolve_ipv4


def test_resolve_ipv4_localhost():
    ip = resolve_ipv4("localhost")
    assert ip.startswith("127.")


def test_resolve_ipv4_unknown():
    host = "invalid.host.invalid"
    assert resolve_ipv4(host) == host
