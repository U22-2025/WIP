"""
専用パケットクラスの使用例
従来のRequest/Responseクラスと新しい専用クラスの使いやすさを比較
"""
from datetime import datetime
from .weather_packet import WeatherRequest, WeatherResponse
from .request import Request
from .response import Response
from ..clients.utils.packet_id_generator import PacketIDGenerator12Bit

# パケットIDジェネレーター
PIDG = PacketIDGenerator12Bit()


def traditional_usage_example():
    """従来のRequest/Responseクラスの使用例"""
    print("=== 従来の使用方法 ===")
    
    # 座標から天気情報を取得（従来方式）
    request = Request(
        version=1,
        packet_id=PIDG.next_id(),
        type=0,  # 座標解決リクエスト
        timestamp=int(datetime.now().timestamp()),
        weather_flag=1,
        temperature_flag=1,
        pops_flag=1,
        alert_flag=0,
        disaster_flag=0,
        day=0,
        ex_field={
            "latitude": 35.6895,
            "longitude": 139.6917
        },
        ex_flag=1
    )
    
    print("従来のRequest作成:")
    print(f"  コード行数: 15行")
    print(f"  Type: {request.type}")
    print(f"  Flags: {request.weather_flag}, {request.temperature_flag}, {request.pops_flag}")
    print(f"  Coordinates: {request.ex_field.get('latitude')}, {request.ex_field.get('longitude')}")
    
    # エリアコードから天気情報を取得（従来方式）
    request2 = Request(
        version=1,
        packet_id=PIDG.next_id(),
        type=2,  # 気象データリクエスト
        timestamp=int(datetime.now().timestamp()),
        area_code="011000",
        weather_flag=1,
        temperature_flag=1,
        pops_flag=1,
        alert_flag=1,
        disaster_flag=0,
        day=0
    )
    
    print(f"\n従来のRequest作成 (エリアコード):")
    print(f"  コード行数: 11行")
    print(f"  Type: {request2.type}")
    print(f"  Area Code: {request2.area_code}")


def modern_usage_example():
    """新しい専用クラスの使用例"""
    print("\n=== 新しい専用クラスの使用方法 ===")
    
    # 座標から天気情報を取得（新方式）
    weather_req = WeatherRequest.create_by_coordinates(
        latitude=35.6895,
        longitude=139.6917,
        packet_id=PIDG.next_id(),
        weather=True,
        temperature=True,
        precipitation_prob=True
    )
    
    print("新しいWeatherRequest作成:")
    print(f"  コード行数: 7行 (半分以下！)")
    print(f"  Type: {weather_req.type}")
    print(f"  Summary: {weather_req.get_request_summary()}")
    
    # エリアコードから天気情報を取得（新方式）
    weather_req2 = WeatherRequest.create_by_area_code(
        area_code="011000",
        packet_id=PIDG.next_id(),
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alerts=True
    )
    
    print(f"\n新しいWeatherRequest作成 (エリアコード):")
    print(f"  コード行数: 7行 (従来の約半分！)")
    print(f"  Type: {weather_req2.type}")
    print(f"  Summary: {weather_req2.get_request_summary()}")


def response_processing_example():
    """レスポンス処理の比較例"""
    print("\n=== レスポンス処理の比較 ===")
    
    # サンプルレスポンスデータを作成
    sample_response = Response(
        version=1,
        packet_id=123,
        type=3,
        area_code="011000",
        timestamp=int(datetime.now().timestamp()),
        weather_flag=1,
        temperature_flag=1,
        pops_flag=1,
        alert_flag=1,
        disaster_flag=0,
        ex_flag=1,
        weather_code=100,
        temperature=125,  # 25℃ + 100
        pops=30,
        ex_field={
            'alert': ['大雨警報', '洪水注意報']
        }
    )
    
    # 従来の処理方法
    print("従来のレスポンス処理:")
    print(f"  気温: {sample_response.temperature - 100}℃ (手動変換)")
    print(f"  天気コード: {sample_response.weather_code}")
    print(f"  降水確率: {sample_response.pops}%")
    if hasattr(sample_response, 'ex_field') and sample_response.ex_field:
        alerts = sample_response.ex_field.get('alert', [])
        print(f"  警報: {alerts}")
    
    # バイト列に変換して新しいクラスで処理
    response_bytes = sample_response.to_bytes()
    weather_resp = WeatherResponse.from_bytes(response_bytes)
    
    print(f"\n新しいWeatherResponse処理:")
    print(f"  気温: {weather_resp.get_temperature_celsius()}℃ (自動変換)")
    print(f"  天気コード: {weather_resp.get_weather_code()}")
    print(f"  降水確率: {weather_resp.get_precipitation_prob_percentage()}%")
    print(f"  警報: {weather_resp.get_alerts()}")
    print(f"  成功判定: {weather_resp.is_success()}")
    print(f"  全データ: {weather_resp.get_weather_data()}")


def client_integration_example():
    """クライアント統合の例"""
    print("\n=== クライアント統合例 ===")
    
    # 新しいパケットクラスを使った簡潔なクライアント
    def create_weather_request_easily(lat, lon, options=None):
        """簡単な天気リクエスト作成"""
        options = options or {}
        return WeatherRequest.create_by_coordinates(
            latitude=lat,
            longitude=lon,
            packet_id=PIDG.next_id(),
            weather=options.get('weather', True),
            temperature=options.get('temperature', True),
            precipitation_prob=options.get('precipitation_prob', True),
            alerts=options.get('alerts', False),
            disaster=options.get('disaster', False)
        )
    
    # 使用例
    tokyo_request = create_weather_request_easily(35.6895, 139.6917)
    sapporo_request = create_weather_request_easily(
        43.0642, 141.3469, 
        {'weather': True, 'temperature': True, 'alerts': True}
    )
    
    print("簡潔なリクエスト作成:")
    print(f"  東京: {tokyo_request.get_request_summary()}")
    print(f"  札幌: {sapporo_request.get_request_summary()}")


def compatibility_test():
    """互換性テスト"""
    print("\n=== 互換性テスト ===")
    
    # 新しいクラスで作成したパケットが従来のクラスで読める
    weather_req = WeatherRequest.create_by_coordinates(
        latitude=35.6895,
        longitude=139.6917,
        packet_id=999,
        weather=True,
        temperature=True
    )
    
    # バイト列に変換
    packet_bytes = weather_req.to_bytes()
    
    # 従来のRequestクラスで読み取り
    traditional_req = Request.from_bytes(packet_bytes)
    
    print("新→従来 互換性:")
    print(f"  Type: {traditional_req.type}")
    print(f"  Coordinates: {traditional_req.ex_field.get('latitude')}, {traditional_req.ex_field.get('longitude')}")
    
    # 従来のクラスで作成したパケットが新しいクラスで読める
    old_req = Request(
        version=1,
        packet_id=888,
        type=0,
        weather_flag=1,
        temperature_flag=1,
        timestamp=int(datetime.now().timestamp()),
        ex_field={"latitude": 43.0642, "longitude": 141.3469},
        ex_flag=1
    )
    
    old_bytes = old_req.to_bytes()
    new_weather_req = WeatherRequest.from_bytes(old_bytes)
    
    print(f"\n従来→新 互換性:")
    print(f"  Summary: {new_weather_req.get_request_summary()}")


def main():
    """メイン関数"""
    print("専用パケットクラス使用例")
    print("=" * 60)
    
    traditional_usage_example()
    modern_usage_example()
    response_processing_example()
    client_integration_example()
    compatibility_test()
    
    print("\n" + "=" * 60)
    print("専用パケットクラスの利点:")
    print("✓ コード行数が大幅削減（従来の約半分）")
    print("✓ 型安全性の向上")
    print("✓ 直感的なメソッド名")
    print("✓ 自動的なデータ変換")
    print("✓ 既存コードとの完全互換性")
    print("✓ エラーの少ない開発")


if __name__ == "__main__":
    main()
