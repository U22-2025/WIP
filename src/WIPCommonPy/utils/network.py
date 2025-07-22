import socket


def resolve_ipv4(host: str) -> str:
    """ホスト名をIPv4アドレスへ解決するヘルパー"""
    try:
        info = socket.getaddrinfo(host, None, family=socket.AF_INET)
        if info:
            return info[0][4][0]
    except socket.gaierror:
        pass
    return host

