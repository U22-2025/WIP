import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 環境変数を.envファイルから読み込み
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using system environment variables only.")

# コマンドライン引数解析
use_coordinates = "--coord" in sys.argv
use_proxy = "--proxy" in sys.argv
debug_enabled = "--debug" in sys.argv
use_report = "--report" in sys.argv

import time
from common.clients.utils.packet_id_generator import PacketIDGenerator12Bit

if use_proxy:
    # Weather Server経由（プロキシモード）
    from common.clients.weather_client import WeatherClient
    from common.packet import LocationRequest
    PIDG = PacketIDGenerator12Bit()
else:
    # 直接通信
    from common.clients.location_client import LocationClient
    from common.clients.query_client import QueryClient
    from common.packet import LocationRequest
    PIDG = PacketIDGenerator12Bit()

# レポート機能のインポート
if use_report:
    from common.clients.report_client import ReportClient

"""メイン関数 - 直接通信 vs プロキシ経由の比較テスト"""
if use_proxy:
    print("Weather Client Example - Via Weather Server (Proxy Mode)")
else:
    print("Weather Client Example - Direct Communication")
    
if use_report:
    print("Report mode enabled - Data will be sent to Report Server")
print("=" * 60)

# --report指定時は、ダミーデータでレポートサーバーに送信
if use_report:
    print("\n=== Report Mode: Sending dummy data to Report Server ===")
    print("-" * 55)
    
    # ダミーデータを作成
    dummy_data = {
        'area_code': 460010,  # 名古屋
        'weather_code': 100,  # 晴れ
        'temperature': 25.0,  # 25℃
        'precipitation_prob': 30,  # 30%
        'alert': ["大雨注意報"],
        'disaster': ["河川氾濫情報"]
    }
    
    print("Using dummy sensor data:")
    for key, value in dummy_data.items():
        print(f"  {key}: {value}")
    
    print("\nSending report to Report Server...")
    # --proxyがない場合は直接reportサーバへ送信
    if use_proxy:
        # プロキシ経由（weatherサーバ経由）
        weather_host = os.getenv('WEATHER_SERVER_HOST', 'localhost')
        weather_port = int(os.getenv('WEATHER_SERVER_PORT', '4110'))
        report_client = ReportClient(host=weather_host, port=weather_port, debug=debug_enabled)
        print(f"Using proxy mode - sending via Weather Server ({weather_host}:{weather_port})")
    else:
        # 直接reportサーバへ送信
        report_host = os.getenv('REPORT_SERVER_HOST', 'localhost')
        report_port = int(os.getenv('REPORT_SERVER_PORT', '4112'))
        report_client = ReportClient(host=report_host, port=report_port, debug=debug_enabled)
        print(f"Using direct mode - sending directly to Report Server ({report_host}:{report_port})")
    
    try:
        report_client.set_sensor_data(
            area_code=dummy_data['area_code'],
            weather_code=dummy_data['weather_code'],
            temperature=dummy_data['temperature'],
            precipitation_prob=dummy_data['precipitation_prob'],
            alert=dummy_data['alert'],
            disaster=dummy_data['disaster']
        )
        
        start_time = time.time()
        report_result = report_client.send_report_data()
        elapsed_time = time.time() - start_time
        
        if report_result:
            print(f"\nOK Report sent successfully! (Execution time: {elapsed_time:.3f}s)")
            print("=== Report Response ===")
            for key, value in report_result.items():
                print(f"  {key}: {value}")
            print("=======================")
        else:
            print("\n✗ Failed to send report to Report Server")
            
    except Exception as e:
        print(f"\n✗ Error sending report: {e}")
        if debug_enabled:
            import traceback
            traceback.print_exc()
    finally:
        report_client.close()
        
    print("\n" + "=" * 60)
    print("Report mode completed")
    # レポートモードの場合は、他の処理を実行せずに終了
    exit(0)

if use_coordinates:
    if use_proxy:
        # === Weather Server経由での座標リクエスト ===
        print("\n1. Coordinate-based request via Weather Server (Proxy)")
        print("-" * 50)
        
        start_time = time.time()
        client = WeatherClient(debug=debug_enabled)
        
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
            elapsed_time = time.time() - start_time
            print(f"\nOK Request successful via Weather Server! (Execution time: {elapsed_time:.3f}s)")
            print("=== Received packet content ===")
            for key, value in result.items():
                print(f"  {key}: {value}")
            print("==============================")
            
            # レポート送信処理
            if use_report:
                print("\n--- Sending data to Report Server ---")
                # プロキシ経由でのレポート送信
                weather_host = os.getenv('WEATHER_SERVER_HOST', 'localhost')
                weather_port = int(os.getenv('WEATHER_SERVER_PORT', '4110'))
                report_client = ReportClient(host=weather_host, port=weather_port, debug=debug_enabled)
                try:
                    report_client.set_sensor_data(
                        area_code=result.get('area_code'),
                        weather_code=result.get('weather_code'),
                        temperature=result.get('temperature'),
                        precipitation_prob=result.get('precipitation_prob'),
                        alert=result.get('alert'),
                        disaster=result.get('disaster')
                    )
                    report_result = report_client.send_report_data()
                    if report_result:
                        print(f"OK Report sent successfully! Response: {report_result}")
                    else:
                        print("✗ Failed to send report to Report Server")
                finally:
                    report_client.close()
        else:
            print("\n✗ Request failed")
            
    else:
        # === 直接通信での座標リクエスト ===
        print("\n1. Direct coordinate-based request (LocationClient + QueryClient)")
        print("-" * 65)
        
        start_time = time.time()
        # Step 1: LocationClientで座標からエリアコードを取得
        location_client = LocationClient(debug=debug_enabled, cache_ttl_minutes=60)  # キャッシュ有効期限を60分に設定
        
        location_request = LocationRequest.create_coordinate_lookup(
            latitude=35.6895,
            longitude=139.6917,
            packet_id=PIDG.next_id(),
            version=1
        )
        
        print("Step 1: Getting area code from coordinates...")
        cache_stats = location_client.get_cache_stats()
        print(f"Cache stats before request: {cache_stats}")
        
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
            print(f"OK Area code obtained: {area_code} (Cache {'HIT' if cache_hit else 'MISS'})")
            
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
                print(f"OK Second request - Area code: {area_code2} (Cache {'HIT' if cache_hit2 else 'MISS'})")
            else:
                print("\n✗ Second request failed")
            
            # Step 2: QueryClientで天気データを取得
            print("\nStep 2: Getting weather data...")
            query_client = QueryClient(debug=debug_enabled)
            
            weather_result = query_client.get_weather_data(
                area_code=area_code,
                weather=True,
                temperature=True,
                precipitation_prob=True,
                alert=True,
                disaster=True
            )
            
            if weather_result:
                elapsed_time = time.time() - start_time
                print(f"\nOK Direct request successful! (Execution time: {elapsed_time:.3f}s)")
                print("=== Received weather data ===")
                # 座標情報を追加
                weather_result['latitude'] = 35.6895
                weather_result['longitude'] = 139.6917
                for key, value in weather_result.items():
                    print(f"  {key}: {value}")
                print("==============================")
                
                # レポート送信処理
                if use_report:
                    print("\n--- Sending data to Report Server ---")
                    # 直接通信でのレポート送信
                    report_host = os.getenv('REPORT_SERVER_HOST', 'localhost')
                    report_port = int(os.getenv('REPORT_SERVER_PORT', '4112'))
                    report_client = ReportClient(host=report_host, port=report_port, debug=debug_enabled)
                    try:
                        report_client.set_sensor_data(
                            area_code=weather_result.get('area_code'),
                            weather_code=weather_result.get('weather_code'),
                            temperature=weather_result.get('temperature'),
                            precipitation_prob=weather_result.get('precipitation_prob'),
                            alert=weather_result.get('alert'),
                            disaster=weather_result.get('disaster')
                        )
                        report_result = report_client.send_report_data()
                        if report_result:
                            print(f"OK Report sent successfully! Response: {report_result}")
                        else:
                            print("✗ Failed to send report to Report Server")
                    finally:
                        report_client.close()
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
        
        start_time = time.time()
        client = WeatherClient(debug=debug_enabled)
        result = client.get_weather_data(
            area_code=460010,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=True,
            disaster=True
        )
        
        if result:
            elapsed_time = (time.time() - start_time)*1000
            print(f"\nOK Success via Weather Server! (Execution time: {elapsed_time:.3f}ms)")
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
                
            # レポート送信処理
            if use_report:
                print("\n--- Sending data to Report Server ---")
                # プロキシ経由でのレポート送信
                weather_host = os.getenv('WEATHER_SERVER_HOST', 'localhost')
                weather_port = int(os.getenv('WEATHER_SERVER_PORT', '4110'))
                report_client = ReportClient(host=weather_host, port=weather_port, debug=debug_enabled)
                try:
                    report_client.set_sensor_data(
                        area_code=result.get('area_code'),
                        weather_code=result.get('weather_code'),
                        temperature=result.get('temperature'),
                        precipitation_prob=result.get('precipitation_prob'),
                        alert=result.get('alert'),
                        disaster=result.get('disaster')
                    )
                    report_result = report_client.send_report_data()
                    if report_result:
                        print(f"OK Report sent successfully! Response: {report_result}")
                    else:
                        print("✗ Failed to send report to Report Server")
                finally:
                    report_client.close()
        else:
            print("\n✗ Failed to get weather data via Weather Server")
            
    else:
        # === 直接QueryClientでのエリアコードリクエスト ===
        print("\n1. Direct area code request (QueryClient)")
        print("-" * 40)
        
        start_time = time.time()
        query_client = QueryClient(debug=debug_enabled)
        result = query_client.get_weather_data(
            area_code=460010,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=True,
            disaster=True
        )

        if result:
            elapsed_time = time.time() - start_time
            print(f"\nOK Direct request successful! (Execution time: {elapsed_time:.3f}s)")
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
            
            # レポート送信処理
            if use_report:
                print("\n--- Sending data to Report Server ---")
                # 直接通信でのレポート送信
                report_host = os.getenv('REPORT_SERVER_HOST', 'localhost')
                report_port = int(os.getenv('REPORT_SERVER_PORT', '4112'))
                report_client = ReportClient(host=report_host, port=report_port, debug=debug_enabled)
                try:
                    report_client.set_sensor_data(
                        area_code=result.get('area_code'),
                        weather_code=result.get('weather_code'),
                        temperature=result.get('temperature'),
                        precipitation_prob=result.get('precipitation_prob'),
                        alert=result.get('alert'),
                        disaster=result.get('disaster')
                    )
                    report_result = report_client.send_report_data()
                    if report_result:
                        print(f"OK Report sent successfully! Response: {report_result}")
                    else:
                        print("✗ Failed to send report to Report Server")
                finally:
                    report_client.close()
        else:
            print("\n✗ Failed to get weather data")
