import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# コマンドライン引数解析
use_coordinates = "--coord" in sys.argv
use_proxy = "--proxy" in sys.argv

import time
from common.clients.utils.packet_id_generator import PacketIDGenerator12Bit

if use_proxy:
    # Weather Server経由（プロキシモード）
    from common.clients.weather_client import WeatherClient
    from common.packet import LocationRequest, QueryRequest
    PIDG = PacketIDGenerator12Bit()
else:
    # 直接通信
    from common.clients.location_client import LocationClient
    from common.clients.query_client import QueryClient
    from common.packet import LocationRequest, QueryRequest
    PIDG = PacketIDGenerator12Bit()

"""メイン関数 - 直接通信 vs プロキシ経由の比較テスト"""
if use_proxy:
    print("Weather Client Example - Via Weather Server (Proxy Mode)")
else:
    print("Weather Client Example - Direct Communication")
print("=" * 60)

if use_coordinates:
    if use_proxy:
        # === Weather Server経由での座標リクエスト ===
        print("\n1. Coordinate-based request via Weather Server (Proxy)")
        print("-" * 50)
        
        client = WeatherClient(debug=True)
        
        # LocationRequestを作成して実行
        request = LocationRequest.create_coordinate_lookup(
            latitude=35.6895,
            longitude=139.6917,
            packet_id=PIDG.next_id(),
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=True,
            disaster=True,
            version=1
        )
        
        result = client._execute_location_request(request)
        
        if result:
            print("\n✓ Request successful via Weather Server!")
            print("=== Received packet content ===")
            for key, value in result.items():
                print(f"  {key}: {value}")
            print("==============================")
        else:
            print("\n✗ Request failed")
            
    else:
        # === 直接通信での座標リクエスト ===
        print("\n1. Direct coordinate-based request (LocationClient + QueryClient)")
        print("-" * 65)
        
        # Step 1: LocationClientで座標からエリアコードを取得
        location_client = LocationClient(debug=True, cache_ttl_minutes=60)  # キャッシュ有効期限を60分に設定
        
        location_request = LocationRequest.create_coordinate_lookup(
            latitude=35.6895,
            longitude=139.6917,
            packet_id=PIDG.next_id(),
            version=1
        )
        
        print("Step 1: Getting area code from coordinates...")
        cache_stats = location_client.get_cache_stats()
        print(f"Cache stats before request: {cache_stats}")
        print(f"Using persistent cache file: {cache_stats.get('cache_file', 'N/A')}")
        
        # キャッシュ情報も取得
        area_code_with_cache_info = location_client.get_area_code_simple(
            latitude=35.6895,
            longitude=139.6917,
            use_cache=True,
            return_cache_info=True
        )
        
        if area_code_with_cache_info:
            if isinstance(area_code_with_cache_info, tuple):
                area_code, cache_hit = area_code_with_cache_info
                print(f"Area code: {area_code} (Cache {'HIT' if cache_hit else 'MISS'})")
            else:
                area_code = area_code_with_cache_info
                print(f"Area code: {area_code}")
        
        # 従来のメソッドも実行してレスポンスを取得
        location_response, raw_data = location_client.get_location_data(
            latitude=35.6895,
            longitude=139.6917,
            use_cache=True
        )
        
        print(f"Cache stats after request: {location_client.get_cache_stats()}")
        
        if location_response and location_response.is_valid():
            area_code = location_response.get_area_code()
            cache_hit = getattr(location_response, 'cache_hit', False)
            print(f"✓ Area code obtained: {area_code} (Cache {'HIT' if cache_hit else 'MISS'})")
            
            # キャッシュテスト：同じ座標を再度取得
            print("\n--- Cache Test: Getting same coordinates again ---")
            location_response2, raw_data2 = location_client.get_location_data(
                latitude=35.6895,
                longitude=139.6917,
                use_cache=True
            )
            
            if location_response2 and location_response2.is_valid():
                area_code2 = location_response2.get_area_code()
                cache_hit2 = getattr(location_response2, 'cache_hit', False)
                print(f"✓ Second request - Area code: {area_code2} (Cache {'HIT' if cache_hit2 else 'MISS'})")
            else:
                print("\n✗ Second request failed")
            
            # Step 2: QueryClientで天気データを取得
            print("\nStep 2: Getting weather data...")
            query_client = QueryClient(debug=True)
            
            weather_result = query_client.get_weather_data(
                area_code=area_code,
                weather=True,
                temperature=True,
                precipitation_prob=True,
                alert=True,
                disaster=True
            )
            
            if weather_result:
                print("\n✓ Direct request successful!")
                print("=== Received weather data ===")
                # 座標情報を追加
                weather_result['latitude'] = 35.6895
                weather_result['longitude'] = 139.6917
                for key, value in weather_result.items():
                    print(f"  {key}: {value}")
                print("==============================")
            else:
                print("\n✗ Weather data request failed")
        else:
            print("\n✗ Failed to get area code from coordinates")
         
else:
    # エリアコード指定の場合
    if use_proxy:
        # === Weather Server経由でのエリアコードリクエスト ===
        print("\n1. Area code request via Weather Server (Proxy)")
        print("-" * 45)
        
        client = WeatherClient(debug=True)
        result = client.get_weather_data(
            area_code=460010,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=True,
            disaster=True
        )
        
        if result:
            print("\n✓ Success via Weather Server!")
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
        else:
            print("\n✗ Failed to get weather data via Weather Server")
            
    else:
        # === 直接QueryClientでのエリアコードリクエスト ===
        print("\n1. Direct area code request (QueryClient)")
        print("-" * 40)
        
        query_client = QueryClient(debug=True)
        result = query_client.get_weather_data(
            area_code=460010,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=True,
            disaster=True
        )

        if result:
            print("\n✓ Direct request successful!")
            print("=== Received weather data ===")
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
            print("==============================")
        else:
            print("\n✗ Failed to get weather data")

# === 使用方法の表示 ===
# print("\n" + "=" * 60)
# print("Usage:")
# print("  python client.py                     # エリアコード指定（直接QueryServer）")
# print("  python client.py --coord             # 座標指定（直接LocationServer+QueryServer）")
# print("  python client.py --proxy             # エリアコード指定（WeatherServer経由）")
# print("  python client.py --coord --proxy     # 座標指定（WeatherServer経由）")
# print("=" * 60)
