import socket
import threading
import time

import pytest

from common.clients.query_client import QueryClient
from common.packet.types.query_packet import QueryRequest, QueryResponse


def start_mock_server(host, port, stop_event, received):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    data, addr = sock.recvfrom(1024)
    received.append(QueryRequest.from_bytes(data))
    response = QueryResponse.create_query_response(
        received[0],
        weather_data={"weather": 100, "temperature": 20, "precipitation_prob": 50}
    )
    sock.sendto(response.to_bytes(), addr)
    stop_event.set()
    sock.close()


def test_query_client_basic(tmp_path):
    host = '127.0.0.1'
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, 0))
        port = s.getsockname()[1]

    stop_event = threading.Event()
    received = []
    server = threading.Thread(target=start_mock_server, args=(host, port, stop_event, received))
    server.start()
    time.sleep(0.1)

    client = QueryClient(host=host, port=port, debug=False, cache_ttl_minutes=1)
    result = client.get_weather_data(
        area_code="123456",
        weather=True,
        temperature=True,
        precipitation_prob=True,
        timeout=1.0,
        use_cache=False,
    )

    stop_event.wait(1)
    server.join()

    assert received
    req = received[0]
    assert req.area_code == "123456"
    assert result["area_code"] == "123456"
    assert result["weather_code"] == 100
    assert result["temperature"] == 20
    assert result["precipitation_prob"] == 50
