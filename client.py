import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# コマンドライン引数解析
use_coordinates = "--coord" in sys.argv

from WIP_Client import Client
import time

"""メイン関数 - 使用例"""
print("Weather Client Example")
print("=" * 50)

# 例1: 座標から天気情報を取得
print("\n1. Getting weather by coordinates (Tokyo)")
print("-" * 30)

if use_coordinates:
    client = Client(debug=True)
    client.set_coordinates(35.6895, 139.6917)
else:
    client = Client(area_code=460020, debug=True)

result = client.get_weather(alert=True, disaster=True)

if result:
    print("\n✓ Success!")
    if 'area_code' in result:
        print(f"Area Code: {result['area_code']}")
    if 'error_code' in result:
        print(f"Error Code: {result['error_code']}")
    if 'timestamp' in result:
        print(f"Timestamp: {time.ctime(result['timestamp'])}")
    if 'weather_code' in result:
        print(f"Weather Code: {result['weather_code']}")
    if 'temperature' in result:
        print(f"Temperature: {result['temperature']}°C")
    if 'precipitation_prob' in result:
        print(f"precipitation_prob: {result['precipitation_prob']}%")
    if 'alert' in result:
        print(f"alert: {result['alert']}")
    if 'disaster' in result:
        print(f"disaster: {result['disaster']}")
    if 'latitude' in result and 'longitude' in result:
        print(f"latitude: {result['latitude']}")
        print(f"longitude: {result['longitude']}")
    
else:
    print("\n✗ Failed to get weather data")
