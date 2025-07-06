import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from WIP_Client import Client
import time

print("Weather Client with Authentication Test")
print("=" * 50)

# 例1: 座標から天気情報を取得（認証付き）
print("\n1. Getting weather by area code with authentication")
print("-" * 30)

client = Client(area_code=460010, debug=True)

# 認証設定の確認
print("\n認証設定の確認:")
for server_type in ['location', 'query', 'weather', 'report']:
    auth_config = client.state.get_auth_config(server_type)
    print(f"  {server_type}: enabled={auth_config.enabled}, has_passphrase={bool(auth_config.passphrase)}")

result = client.get_weather(alert=True, disaster=True)

if result:
    print("\n✓ Success!")
    if 'area_code' in result:
        print(f"Area Code: {result['area_code']}")
    elif 'error_code' in result:
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

client.close()