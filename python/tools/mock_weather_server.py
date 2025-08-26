#!/usr/bin/env python3
"""
Minimal WIP mock weather server for connectivity testing.

Listens on UDP/4110, returns a WeatherResponse packet with
fixed area_code and simple weather fields. Matches the C++
client's codec/checksum rules.
"""
from __future__ import annotations
import socket
import struct
import time
from typing import Tuple


PORT = 4110
HOST = "0.0.0.0"


def compute_checksum(header16: bytes) -> int:
    # Same as C++: sum of 16 header bytes, masked to 12 bits
    assert len(header16) == 16
    return sum(header16) & 0x0FFF


def build_header(
    *,
    version: int,
    packet_id: int,
    ptype: int,
    flags_byte: int,
    day: int,
    timestamp: int,
    area_code: int,
) -> bytes:
    # 1-2: Version(4) + PacketID(12)
    first = ((version & 0x0F) << 12) | (packet_id & 0x0FFF)

    # 3-4: Type(3) + Flags(8) + Day(3) + Reserved(2)
    second = ((ptype & 0x7) << 13) | ((flags_byte & 0xFF) << 5) | ((day & 0x7) << 2) | 0

    # 5-12: Timestamp (64-bit BE)
    ts = timestamp & 0xFFFFFFFFFFFFFFFF

    # 13-16: AreaCode(20) + Checksum(12) [checksum initially 0]
    last = (area_code & 0xFFFFF) << 12

    # Pack big-endian with checksum=0 first
    hb = bytearray(16)
    hb[0:2] = struct.pack(">H", first)
    hb[2:4] = struct.pack(">H", second)
    hb[4:12] = struct.pack(">Q", ts)
    hb[12:16] = struct.pack(">I", last)

    # Compute and set checksum lower 12 bits
    cs = compute_checksum(bytes(hb))
    last |= (cs & 0x0FFF)
    hb[12:16] = struct.pack(">I", last)
    return bytes(hb)


def build_response(
    req: bytes,
    area_code: int = 130010,
    weather_code: int = 100,
    temperature_c: int = 22,
    precip_prob: int = 10,
) -> bytes:
    # Parse packet_id from request (first 2 bytes)
    if len(req) < 16:
        pkt_id = 0
        day = 0
    else:
        first = struct.unpack(">H", req[0:2])[0]
        pkt_id = first & 0x0FFF
        second = struct.unpack(">H", req[2:4])[0]
        day = (second >> 2) & 0x7

    version = 1
    ptype = 3  # WeatherResponse
    flags = 0
    ts = int(time.time())
    header = build_header(
        version=version,
        packet_id=pkt_id,
        ptype=ptype,
        flags_byte=flags,
        day=day,
        timestamp=ts,
        area_code=area_code,
    )

    # Response fields: weather_code(2 BE), temperature(int8), precipitation_prob(uint8)
    wc = weather_code & 0xFFFF
    t8 = int(temperature_c) & 0xFF  # client treats as raw 2's complement
    pp = precip_prob & 0xFF
    resp = struct.pack(">Hbb", wc, t8 if t8 < 128 else t8 - 256, pp)

    return header + resp


def run_server(host: str = HOST, port: int = PORT) -> None:
    print(f"[mock-weather] Listening on {host}:{port} (UDP)")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((host, port))
        while True:
            data, addr = s.recvfrom(2048)
            print(f"[mock-weather] received {len(data)} bytes from {addr}")
            resp = build_response(data)
            s.sendto(resp, addr)
            print(f"[mock-weather] sent response {len(resp)} bytes to {addr}")


if __name__ == "__main__":
    run_server()

