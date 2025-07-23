import logging
import sys
sys.path.append('src')
from WIPServerPy.servers.weather_server.weather_server import WeatherServer
from WIPCommonPy.packet import Request
from WIPCommonPy.utils.auth import WIPAuth


def _make_server():
    server = WeatherServer.__new__(WeatherServer)
    server.passphrases = {
        "weather_server": "pass",
        "location_server": "pass2",
        "query_server": "pass3",
        "report_server": "pass4",
    }
    server.location_resolver_port = 4109
    server.query_generator_port = 4111
    server.report_server_port = 4112
    server.logger = logging.getLogger("test")
    server.debug = False
    return server


def _create_packet(packet_id, timestamp, passphrase):
    req = Request(
        version=1,
        packet_id=packet_id,
        type=0,
        timestamp=timestamp,
        area_code="000001",
        ex_flag=1,
        ex_field={}
    )
    auth_hash = WIPAuth.calculate_auth_hash(packet_id, timestamp, passphrase)
    req.ex_field.auth_hash = auth_hash.hex()
    return req.to_bytes()


def test_verify_packet_authentication_success():
    srv = _make_server()
    pkt_id = 10
    ts = 123456
    data = _create_packet(pkt_id, ts, srv.passphrases["weather_server"])
    assert srv._verify_packet_authentication(data, pkt_id, ts, 0, ("127.0.0.1", 10000))


def test_verify_packet_authentication_failure():
    srv = _make_server()
    pkt_id = 11
    ts = 789012
    # use wrong passphrase when creating packet
    data = _create_packet(pkt_id, ts, "wrong")
    assert not srv._verify_packet_authentication(data, pkt_id, ts, 0, ("127.0.0.1", 10000))
