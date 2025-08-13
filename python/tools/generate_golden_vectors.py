import os
from pathlib import Path
from datetime import datetime

from WIPCommonPy.packet.types.location_packet import LocationRequest, LocationResponse
from WIPCommonPy.packet.types.query_packet import QueryRequest, QueryResponse


def write_bin(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main():
    out_dir = Path("dist/golden")
    now_ts = int(datetime.now().timestamp())

    # 1) QueryRequest by area code
    qr = QueryRequest.create_query_request(
        area_code="130010",
        packet_id=0x123,
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=False,
        disaster=False,
        day=0,
    )
    # stabilize timestamp
    qr.timestamp = now_ts
    data = qr.to_bytes()
    write_bin(out_dir / "query_req_area_130010.bin", data)

    # 2) LocationRequest by coordinates (Tokyo)
    lr = LocationRequest.create_coordinate_lookup(
        latitude=35.6895,
        longitude=139.6917,
        packet_id=0x234,
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=False,
        disaster=False,
        day=0,
    )
    lr.timestamp = now_ts
    write_bin(out_dir / "location_req_tokyo.bin", lr.to_bytes())

    # 3) QueryResponse example
    qr2 = QueryRequest.create_query_request(
        area_code="130010",
        packet_id=0x345,
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=True,
        disaster=True,
        day=0,
    )
    qr2.timestamp = now_ts
    resp = QueryResponse.create_query_response(
        request=qr2,
        weather_data={
            "weather": 100,
            "temperature": 25,
            "precipitation_prob": 30,
            "alert": ["大雨警報"],
            "disaster": ["土砂災害警戒"],
        },
    )
    write_bin(out_dir / "query_resp_example.bin", resp.to_bytes())

    print(f"Golden vectors generated in {out_dir}")


if __name__ == "__main__":
    main()

