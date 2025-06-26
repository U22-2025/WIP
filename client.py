import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from WIP_Client import Client
import time

"""メイン関数 - 使用例"""
print("Weather Client Example")
print("=" * 50)

# client = Client(area_code=460010, debug=True)
client = Client( debug=True)

# 例1: 座標から天気情報を取得
print("\n1. Getting weather by coordinates (Tokyo)")
print("-" * 30)
client.set_coordinates(35.6895, 139.6917)
result = client.get_weather(alert=True, disaster=True)

if result:
    print("\n✓ Success!")
    print(f"Area Code: {result['area_code']}")
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
    
else:
    print("\n✗ Failed to get weather data")
