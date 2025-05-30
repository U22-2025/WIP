from WTP_Client import WeatherClient
import time

"""メイン関数 - 使用例"""
print("Weather Client Example")
print("=" * 50)

client = WeatherClient(debug=True)


# 例1: 座標から天気情報を取得
print("\n1. Getting weather by coordinates (Tokyo)")
print("-" * 30)

result = client.get_weather_by_coordinates(
    latitude=35.6895,
    longitude=139.6917,
    weather=True,
    temperature=True,
    precipitation=True
)

if result:
    print("\n✓ Success!")
    print(f"Area Code: {result['area_code']}")
    print(f"Timestamp: {time.ctime(result['timestamp'])}")
    if 'weather_code' in result:
        print(f"Weather Code: {result['weather_code']}")
    if 'temperature' in result:
        print(f"Temperature: {result['temperature']}°C")
    if 'precipitation' in result:
        print(f"Precipitation: {result['precipitation']}%")
else:
    print("\n✗ Failed to get weather data")