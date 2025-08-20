import json
import os
import subprocess
from pathlib import Path

from WIPCommonPy.packet.models.request import Request
from WIPCommonPy.packet.types.query_packet import QueryResponse, QueryRequest


def run(cmd, check=True):
    print("$", " ".join(cmd))
    res = subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.stdout.decode(), res.stderr.decode(), res.returncode


def decode_with_python(path: Path):
    data = path.read_bytes()
    req = Request.from_bytes(data)
    return {
        "version": req.version,
        "packet_id": req.packet_id,
        "type": req.type,
        "area_code": req.area_code,
        "weather_flag": req.weather_flag,
        "temperature_flag": req.temperature_flag,
        "pop_flag": req.pop_flag,
        "alert_flag": req.alert_flag,
        "disaster_flag": req.disaster_flag,
        "ex_flag": req.ex_flag,
    }

def main():
    # Detect C++ tools
    bin_dir = Path(os.environ.get("WIP_CPP_BIN_DIR", "cpp/build"))
    gen = bin_dir / ("wip_packet_gen.exe" if os.name == "nt" else "wip_packet_gen")
    dec = bin_dir / ("wip_packet_decode.exe" if os.name == "nt" else "wip_packet_decode")
    if not gen.exists() or not dec.exists():
        print("C++ tools not found. Please build cpp tools and set WIP_CPP_BIN_DIR.")
        print("Expected:", gen, dec)
        return 2

    out_dir = Path("dist/interop")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) C++ -> Python (request generation)
    req1 = out_dir / "cpp_query_req.bin"
    run([str(gen), "--type", "query", "--area", "130010", "--packet-id", "0x123", "--timestamp", "1731000000", "--out", str(req1)])
    py_decoded = decode_with_python(req1)
    assert py_decoded["type"] == 2, py_decoded
    assert py_decoded["area_code"] == "130010", py_decoded

    req2 = out_dir / "cpp_location_req.bin"
    run([str(gen), "--type", "location", "--coords", "35.6895", "139.6917", "--packet-id", "0x234", "--timestamp", "1731000001", "--out", str(req2)])
    py_decoded2 = decode_with_python(req2)
    assert py_decoded2["type"] == 0, py_decoded2
    assert py_decoded2["ex_flag"] == 1, py_decoded2

    # ネガティブ: チェックサム破損時は Python 側が拒否
    tampered = req1.read_bytes()
    tampered = bytearray(tampered)
    tampered[0] ^= 0x01  # 先頭ビットを反転
    (out_dir / "cpp_query_req_tampered.bin").write_bytes(tampered)
    try:
        Request.from_bytes(bytes(tampered))
        raise AssertionError("Expected checksum verification failure")
    except Exception:
        pass

    # 2) Python -> C++ (response generation)
    qr = QueryRequest.create_query_request(
        area_code="130010",
        packet_id=0x345,
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=True,
        disaster=True,
        day=0,
    )
    resp = QueryResponse.create_query_response(
        request=qr,
        weather_data={
            "weather": 100,
            "temperature": 25,
            "precipitation_prob": 30,
            "alert": ["大雨警報"],
            "disaster": ["土砂災害警戒"],
        },
    )
    resp_path = out_dir / "py_query_resp.bin"
    resp_path.write_bytes(resp.to_bytes())
    out, _, rc = run([str(dec), str(resp_path)])
    assert rc == 0
    j = json.loads(out)
    assert j["type"] == "WeatherResponse", j
    assert j["area_code"] == "130010", j
    assert j["response"]["weather_code"] == 100, j
    assert j["response"]["precipitation_prob"] == 30, j
    # 拡張フィールド（alert/disaster）が含まれること（type_id 1,2）
    types = {int(item.get("type_id", -1)) for item in j.get("extensions", [])}
    assert 1 in types and 2 in types, j

    print("Interop tests passed (no socket)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
