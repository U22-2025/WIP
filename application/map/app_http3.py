from quart import Quart, render_template, request, jsonify, send_from_directory
import sys, os
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from functools import lru_cache
import logging

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from WIP_Client import Client

app = Quart(__name__)

# Quartアプリケーションの設定（アプリ初期化後に設定）
app.config.update({
    'PROVIDE_AUTOMATIC_OPTIONS': True,
    'JSON_AS_ASCII': False,
    'JSON_SORT_KEYS': False
})

client = Client(debug=True)

# ジオコーダーの初期化（高速化設定）
geolocator = Nominatim(user_agent="wip_map_app_http3")

# 地理情報のキャッシュ（最大100件、1時間保持）
@lru_cache(maxsize=100)
def get_address_from_coordinates_cached(lat_str, lng_str):
    """キャッシュ付き座標から住所を取得する関数"""
    lat, lng = float(lat_str), float(lng_str)
    try:
        # タイムアウトを短縮して高速化
        location = geolocator.reverse(f"{lat}, {lng}", timeout=5, language='ja')
        
        if location:
            address = location.address
            # 住所の各要素を取得
            address_components = location.raw.get('address', {})
            
            # 日本の住所形式に合わせて整理
            prefecture = address_components.get('state', '')
            city = address_components.get('city', '')
            if not city:
                city = address_components.get('town', '')
            if not city:
                city = address_components.get('village', '')
            
            suburb = address_components.get('suburb', '')
            neighbourhood = address_components.get('neighbourhood', '')
            
            # 住所情報を構造化して返す
            return {
                'full_address': address,
                'prefecture': prefecture,
                'city': city,
                'suburb': suburb,
                'neighbourhood': neighbourhood,
                'country': address_components.get('country', ''),
                'postcode': address_components.get('postcode', ''),
                'raw_components': address_components
            }
        else:
            return None
            
    except GeocoderTimedOut:
        print("Geocoder timed out")
        return None
    except GeocoderServiceError as e:
        print(f"Geocoder service error: {e}")
        return None
    except Exception as e:
        print(f"Error getting address: {e}")
        return None

@app.route('/')
async def index():
    return await render_template('map.html')

# JSONファイル配置ディレクトリ
JSON_DIR = Path(__file__).resolve().parents[2] / 'wip' / 'json'

# 天気コードJSONを提供するルート
@app.route('/weather_code.json')
async def weather_code():
    return await send_from_directory(JSON_DIR, 'weather_code.json')

# エラーコードJSONを提供するルート
@app.route('/error_code.json')
async def error_code_json():
    return await send_from_directory(JSON_DIR, 'error_code.json')

@app.route('/click', methods=['POST'])
async def click():
    data = await request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    
    # 座標を設定
    client.set_coordinates(lat, lng)
    
    # 天気情報を取得（非同期で実行）
    loop = asyncio.get_event_loop()
    weather_result = await loop.run_in_executor(None, client.get_weather)

    if not weather_result:
        return jsonify({'status': 'error', 'message': '天気情報の取得に失敗しました'}), 500

    if isinstance(weather_result, dict) and 'error_code' in weather_result:
        return jsonify({
            'status': 'error',
            'error_code': weather_result['error_code'],
            'message': 'エラーパケットを受信しました'
        }), 500

    response_data = {
        'status': 'ok',
        'coordinates': {
            'lat': lat,
            'lng': lng
        },
        'weather': weather_result
    }

    return jsonify(response_data)

# 住所のみを取得するエンドポイント
@app.route('/get_address', methods=['POST'])
async def get_address():
    data = await request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    
    if lat is None or lng is None:
        return jsonify({'status': 'error', 'message': '緯度と経度が必要です'}), 400
    
    # 住所情報を取得（非同期で実行、キャッシュ付き）
    loop = asyncio.get_event_loop()
    address_info = await loop.run_in_executor(None, get_address_from_coordinates_cached, str(lat), str(lng))
    
    if address_info:
        return jsonify({
            'status': 'ok',
            'coordinates': {'lat': lat, 'lng': lng},
            'address': address_info
        })
    else:
        return jsonify({
            'status': 'error',
            'message': '住所の取得に失敗しました',
            'coordinates': {'lat': lat, 'lng': lng}
        }), 404

# 週間予報を取得するエンドポイント
@app.route('/weekly_forecast', methods=['POST'])
async def weekly_forecast():
    data = await request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    
    if lat is None or lng is None:
        return jsonify({'status': 'error', 'message': '緯度と経度が必要です'}), 400
    
    # 座標を設定
    client.set_coordinates(lat, lng)
    
    def get_daily_weather(day):
        """指定された日の天気データを取得する関数"""
        local_client = Client(host=client.config.host, port=client.config.port)
        # スレッド毎に独立したソケットを使うため、座標情報もコピー
        local_client.set_coordinates(lat, lng)
        try:
            weather_result = local_client.get_weather(day=day)
            if weather_result and not ('error_code' in weather_result):
                # 日付情報を追加
                date = datetime.now() + timedelta(days=day)
                weather_result['date'] = date.strftime('%Y-%m-%d')
                weather_result['day_of_week'] = date.strftime('%A')
                weather_result['day_number'] = day
                return weather_result
            else:
                # エラーの場合はダミーデータを返す
                date = datetime.now() + timedelta(days=day)
                return {
                    'date': date.strftime('%Y-%m-%d'),
                    'day_of_week': date.strftime('%A'),
                    'day_number': day,
                    'weather_code': '100',
                    'temperature': '--',
                    'precipitation_prob': '--',
                    'area_code': 'unknown'
                }
        except Exception as e:
            print(f"Error getting weather for day {day}: {e}")
            # エラーの場合はダミーデータを返す
            date = datetime.now() + timedelta(days=day)
            return {
                'date': date.strftime('%Y-%m-%d'),
                'day_of_week': date.strftime('%A'),
                'day_number': day,
                'weather_code': '100',
                'temperature': '--',
                'precipitation_prob': '--',
                'area_code': 'unknown'
            }
        finally:
            local_client.close()
    
    # 並列で一週間分の天気データを取得（非同期で実行）
    loop = asyncio.get_event_loop()
    
    async def get_weekly_data():
        weekly_data = [None] * 7  # 結果を格納するリストを初期化
        
        with ThreadPoolExecutor(max_workers=7) as executor:
            # 全ての日について並列でタスクを送信
            tasks = [
                loop.run_in_executor(executor, get_daily_weather, day)
                for day in range(7)
            ]
            
            # 全てのタスクの完了を待つ
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果を正しい順序でリストに格納
            for day, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f'Day {day} generated an exception: {result}')
                    # エラーの場合はダミーデータを作成
                    date = datetime.now() + timedelta(days=day)
                    weekly_data[day] = {
                        'date': date.strftime('%Y-%m-%d'),
                        'day_of_week': date.strftime('%A'),
                        'day_number': day,
                        'weather_code': '100',
                        'temperature': '--',
                        'precipitation_prob': '--',
                        'area_code': 'unknown'
                    }
                else:
                    weekly_data[day] = result
        
        return weekly_data
    
    weekly_data = await get_weekly_data()
    
    return jsonify({
        'status': 'ok',
        'coordinates': {'lat': lat, 'lng': lng},
        'weekly_forecast': weekly_data
    })

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config
    
    # Hypercornの設定（高性能化）
    config = Config()
    config.bind = ["0.0.0.0:5000"]  # すべてのインターフェースでバインド
    config.alpn_protocols = ["h3", "h2", "http/1.1"]  # HTTP/3を優先
    
    # HTTP/3高速化設定
    config.h3_max_concurrent_streams = 200  # 同時ストリーム数を増加
    config.h3_stream_timeout = 60  # タイムアウトを延長
    config.h3_max_stream_data = 1048576  # 1MB
    config.h3_max_connection_data = 10485760  # 10MB
    
    # 一般的な性能設定
    config.workers = 1  # 単一ワーカー（開発用）
    config.keep_alive_timeout = 30
    config.graceful_timeout = 30
    config.max_requests = 10000
    config.max_requests_jitter = 1000
    
    # キープアライブとバッファサイズ
    config.h11_max_incomplete_size = 65536
    config.h2_max_concurrent_streams = 100
    config.h2_max_header_list_size = 65536
    
    # SSL証明書の設定（HTTP/3には必須）
    cert_file = "cert.pem"
    key_file = "key.pem"
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        config.certfile = cert_file
        config.keyfile = key_file
        config.ssl_handshake_timeout = 30
        
        print("🚀 HTTP/3高速サーバーを起動中...")
        print(f"📡 URL: https://localhost:5000")
        print(f"🔒 SSL: 有効 (自己署名証明書)")
        print(f"⚡ プロトコル: HTTP/3 (h3) > HTTP/2 (h2) > HTTP/1.1")
        print(f"🎯 最適化: キャッシュ有効、非同期処理、並列実行")
        print(f"📊 同時ストリーム: {config.h3_max_concurrent_streams}")
        print("=" * 60)
        print("💡 ブラウザで証明書警告が出た場合:")
        print("   → 「詳細設定」→「localhost にアクセスする（安全ではありません）」")
        print("=" * 60)
    else:
        print("⚠️  SSL証明書が見つかりません。")
        print("HTTP/3を使用するには SSL証明書が必要です。")
        print("自動生成するには:")
        print("  python generate_cert.py")
        print("")
        print("HTTP/1.1モードで起動します...")
        config.bind = ["localhost:5000"]
        config.alpn_protocols = ["http/1.1"]  # HTTP/1.1のみ
    
    try:
        asyncio.run(hypercorn.asyncio.serve(app, config))
    except KeyboardInterrupt:
        print("\n🛑 サーバーを停止しました")
    except Exception as e:
        print(f"\n❌ サーバー起動エラー: {e}")
