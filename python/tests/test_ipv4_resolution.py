import socket
import pytest

from common.utils.network import resolve_ipv4
from common.clients.location_client import LocationClient
from common.clients.weather_client import WeatherClient
from common.clients.query_client import QueryClient
from common.clients.report_client import ReportClient


def test_resolve_ipv4_localhost():
    assert resolve_ipv4("localhost") == "127.0.0.1"


@pytest.mark.parametrize(
    "client_cls, attr",
    [
        (WeatherClient, "host"),
        (ReportClient, "host"),
        (LocationClient, "server_host"),
        (QueryClient, "host"),
    ],
)
def test_clients_send_with_ipv4(client_cls, attr):
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind(("127.0.0.1", 0))
    port = server.getsockname()[1]

    kwargs = {"host": "localhost", "port": port, "debug": False}
    if client_cls is LocationClient:
        kwargs["cache_enabled"] = False
    client = client_cls(**kwargs)

    host = getattr(client, attr)
    assert host == "127.0.0.1"

    sock = getattr(client, "sock", None) or socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.sendto(b"ping", (host, port))
    except OSError as e:
        pytest.fail(f"send failed: {e}")
    finally:
        server.close()
        if client_cls is QueryClient:
            sock.close()
        if hasattr(client, "close"):
            try:
                client.close()
            except Exception:
                pass
