"""
専用パケットクラスの動作テスト
"""
import time
from .weather_packet import WeatherRequest, WeatherResponse
from .location_packet import LocationRequest, LocationResponse
from .query_packet import QueryRequest, QueryResponse


def test_weather_packet():
    """WeatherRequestとWeatherResponseのテスト"""
    print("=== Weather Packet Test ===")
    
    # 座標からの天気リクエスト
    weather_req = WeatherRequest.create_by_coordinates(
        latitude=35.6895,
        longitude=139.6917,
        packet_id=123,
        weather=True,
        temperature=True,
        precipitation_prob=True
    )
    
    print(f"Weather Request (by coordinates):")
    print(f"  Type: {weather_req.type}")
    print(f"  Flags: weather={weather_req.weather_flag}, temp={weather_req.temperature_flag}")
    print(f"  Coordinates: {weather_req.ex_field.latitude}, {weather_req.ex_field.longitude}")
    print(f"  Summary: {weather_req.get_request_summary()}")
    
    # エリアコードからの天気リクエスト
    weather_req2 = WeatherRequest.create_by_area_code(
        area_code="011000",
        packet_id=456,
        weather=True,
        temperature=True,
        alert=True
    )
    
    print(f"\nWeather Request (by area code):")
    print(f"  Type: {weather_req2.type}")
    print(f"  Area Code: {weather_req2.area_code}")
    print(f"  Summary: {weather_req2.get_request_summary()}")
    
    # バイト列変換テスト
    data = weather_req.to_bytes()
    print(f"\nByte conversion test: {len(data)} bytes")
    
    # 復元テスト
    restored = WeatherRequest.from_bytes(data)
    print(f"Restored type: {restored.type}")
    print(f"Restored coordinates: {restored.ex_field.latitude}, {restored.ex_field.longitude}")


def test_location_packet():
    """LocationRequestとLocationResponseのテスト"""
    print("\n=== Location Packet Test ===")
    
    # 座標解決リクエスト
    location_req = LocationRequest.create_coordinate_lookup(
        latitude=35.6895,
        longitude=139.6917,
        packet_id=789,
        source="192.168.1.100:12345",
        preserve_flags={
            'weather_flag': 1,
            'temperature_flag': 1,
            'pop_flag': 1
        }
    )
    
    print(f"Location Request:")
    print(f"  Type: {location_req.type}")
    print(f"  Coordinates: {location_req.get_coordinates()}")
    print(f"  Source: {location_req.get_source_info()}")
    
    # レスポンス作成
    location_resp = LocationResponse.create_area_code_response(
        request=location_req,
        area_code="130010"  # 東京都
    )
    
    print(f"\nLocation Response:")
    print(f"  Type: {location_resp.type}")
    print(f"  Area Code: {location_resp.get_area_code()}")
    print(f"  Source: {location_resp.get_source_info()}")
    print(f"  Valid: {location_resp.is_valid()}")
    print(f"  Summary: {location_resp.get_response_summary()}")
    
    # Type 2リクエストへの変換
    weather_req = location_resp.to_weather_request()
    print(f"\nConverted to Weather Request:")
    print(f"  Type: {weather_req.type}")
    print(f"  Area Code: {weather_req.area_code}")


def test_query_packet():
    """QueryRequestとQueryResponseのテスト"""
    print("\n=== Query Packet Test ===")
    
    # 気象データリクエスト
    query_req = QueryRequest.create_weather_data_request(
        area_code="011000",
        packet_id=999,
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=True,
        source="192.168.1.100:12345"
    )
    
    print(f"Query Request:")
    print(f"  Type: {query_req.type}")
    print(f"  Area Code: {query_req.area_code}")
    print(f"  Source: {query_req.get_source_info()}")
    print(f"  Requested data: {query_req.get_requested_data_types()}")
    
    # レスポンス作成（気象データ付き）
    weather_data = {
        'weather': 100,
        'temperature': 25,
        'precipitation_prob': 30,
        'warnings': ['大雨警報', '洪水注意報'],
        'disaster': ['土砂災害警戒']
    }
    
    query_resp = QueryResponse.create_weather_data_response(
        request=query_req,
        weather_data=weather_data
    )
    
    print(f"\nQuery Response:")
    print(f"  Type: {query_resp.type}")
    print(f"  Weather Code: {query_resp.get_weather_code()}")
    print(f"  Temperature: {query_resp.get_temperature_celsius()}℃")
    print(f"  precipitation_prob: {query_resp.get_precipitation()}%")
    print(f"  Alerts: {query_resp.get_alert()}")
    print(f"  Disaster Info: {query_resp.get_disaster_info()}")
    print(f"  Success: {query_resp.is_success()}")
    print(f"  Summary: {query_resp.get_response_summary()}")


def test_interoperability():
    """パケット間の相互運用性テスト"""
    print("\n=== Interoperability Test ===")
    
    # WeatherRequest → LocationRequest
    weather_req = WeatherRequest.create_by_coordinates(
        latitude=35.6895,
        longitude=139.6917,
        packet_id=111,
        weather=True,
        temperature=True
    )
    
    location_req = LocationRequest.from_weather_request(
        weather_req,
        source="127.0.0.1:12345"
    )
    
    print(f"WeatherRequest → LocationRequest conversion:")
    print(f"  Coordinates preserved: {location_req.get_coordinates()}")
    print(f"  Source added: {location_req.get_source_info()}")
    
    # LocationResponse → QueryRequest
    location_resp = LocationResponse.create_area_code_response(
        request=location_req,
        area_code="130010"
    )
    
    query_req = QueryRequest.from_location_response(
        location_resp,
        source="127.0.0.1:23456"
    )
    
    print(f"\nLocationResponse → QueryRequest conversion:")
    print(f"  Area code preserved: {query_req.area_code}")
    print(f"  Source preserved: {query_req.get_source_info()}")
    print(f"  Flags preserved: {query_req.get_requested_data_types()}")


def main():
    """メインテスト関数"""
    print("Specialized Packet Classes Test")
    print("=" * 50)
    
    test_weather_packet()
    test_location_packet()
    test_query_packet()
    test_interoperability()
    
    print("\n" + "=" * 50)
    print("All tests completed successfully!")


if __name__ == "__main__":
    main()
