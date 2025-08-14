#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, '/mnt/c/Users/ポッポ焼き/Desktop/WIP/src')

from WIPCommonPy.clients.weather_client import WeatherClient
from WIPCommonPy.packet import QueryRequest

def debug_packet():
    client = WeatherClient(debug=True)
    
    # Rustと同じパラメータでQueryRequestを直接作成
    request = QueryRequest.create_query_request(
        area_code=11000,
        packet_id=client.PIDG.next_id(),
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=False,
        disaster=False,
        day=0,
        version=1,
    )
    
    packet_bytes = request.to_bytes()
    print(f"Python packet ID: {request.packet_id} (0x{request.packet_id:03X})")
    print(f"Python packet bytes: {[f'{b:02X}' for b in packet_bytes]}")
    print(f"Python raw bytes: {packet_bytes}")
    
    # 実際にリクエストを実行
    result = client._execute_query_request(request)
    print("Result:", result)
    client.close()

if __name__ == "__main__":
    debug_packet()