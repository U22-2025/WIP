from flask import Flask, render_template, request, jsonify, send_from_directory
import sys, os
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from WIP_Client import Client

app = Flask(__name__)
client = Client(host='localhost', port=4110, debug=True)

# ジオコーダーの初期化
geolocator = Nominatim(user_agent="wip_map_app")

def get_address_from_coordinates(lat, lng):
    """座標から住所を取得する関数"""
    try:
        # タイムアウトとリトライ機能付きで住所を取得
        location = geolocator.reverse(f"{lat}, {lng}", timeout=10, language='ja')
        
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
def index():
    return render_template('map.html')  # 上のHTMLを templates/map.html に保存

# JSONファイル配置ディレクトリ
JSON_DIR = Path(__file__).resolve().parents[2] / 'wip' / 'json'

# 天気コードJSONを提供するルート
@app.route('/weather_code.json')
def weather_code():
    return send_from_directory(JSON_DIR, 'weather_code.json')

# エラーコードJSONを提供するルート
@app.route('/error_code.json')
def error_code_json():
    return send_from_directory(JSON_DIR, 'error_code.json')

@app.route('/click', methods=['POST'])
def click():
    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    
    # 座標を設定
    client.set_coordinates(lat, lng)
    
    # 天気情報を取得
    weather_result = client.get_weather()

    if not weather_result:
        return jsonify({'status': 'error', 'message': '天気情報の取得に失敗しました'}), 500

    if isinstance(weather_result, dict) and 'error_code' in weather_result:
        return jsonify({
            'status': 'error',
            'error_code': weather_result['error_code'],
            'message': 'エラーパケットを受信しました'
        }), 500

    # レスポンスを構築
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
def get_address():
    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    
    if lat is None or lng is None:
        return jsonify({'status': 'error', 'message': '緯度と経度が必要です'}), 400
    
    address_info = get_address_from_coordinates(lat, lng)
    
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

def _add_date_info(weather_data, days_offset=0):
    """天気データに日付情報を追加するヘルパー関数"""
    date = datetime.now() + timedelta(days=days_offset)
    weather_data['date'] = date.strftime('%Y-%m-%d')
    weather_data['day_of_week'] = date.strftime('%A')
    return weather_data

def _create_fallback_weather_data(area_code, days_offset=0):
    """エラー時のダミーデータを作成するヘルパー関数"""
    date = datetime.now() + timedelta(days=days_offset)
    return {
        'date': date.strftime('%Y-%m-%d'),
        'day_of_week': date.strftime('%A'),
        'weather_code': '100',
        'temperature': '--',
        'precipitation_prob': '--',
        'area_code': area_code
    }

def _get_today_weather(lat, lng):
    """今日の天気データを取得するヘルパー関数"""
    client.set_coordinates(lat, lng)
    today_weather = client.get_weather(day=0)
    
    if not today_weather or isinstance(today_weather, dict) and 'error_code' in today_weather:
        raise ValueError('今日の天気データの取得に失敗しました')
    
    if 'area_code' not in today_weather:
        raise ValueError('エリアコードが見つかりませんでした')
    
    return today_weather

def _get_weekly_weather_parallel(area_code):
    """並列で週間天気予報を取得するヘルパー関数"""
    weekly_data = [None] * 6  # 1-6日目用
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_to_day = {
            executor.submit(client.get_weather_by_area_code, area_code=area_code, day=day): day
            for day in range(1, 7)
        }
        
        for future in as_completed(future_to_day):
            day = future_to_day[future]
            try:
                result = future.result()
                if result and not ('error_code' in result):
                    weekly_data[day-1] = _add_date_info(result, day)
                else:
                    weekly_data[day-1] = _create_fallback_weather_data(area_code, day)
            except Exception:
                weekly_data[day-1] = _create_fallback_weather_data(area_code, day)
    
    return weekly_data

# 週間予報を取得するエンドポイント
@app.route('/weekly_forecast', methods=['POST'])
def weekly_forecast():
    from datetime import datetime, timedelta
    
    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    
    if lat is None or lng is None:
        return jsonify({'status': 'error', 'message': '緯度と経度が必要です'}), 400
    
    try:
        # 今日の天気データを取得
        today_weather = _get_today_weather(lat, lng)
        area_code = today_weather['area_code']
        today_weather = _add_date_info(today_weather)
        
        # 週間予報を並列で取得
        weekly_data = [today_weather] + _get_weekly_weather_parallel(area_code)
        
        return jsonify({
            'status': 'ok',
            'coordinates': {'lat': lat, 'lng': lng},
            'area_code': area_code,
            'weekly_forecast': {data['day']: data for data in weekly_data}
        })
        
    except ValueError as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        print(f"Error in weekly_forecast: {e}")
        return jsonify({'status': 'error', 'message': '週間予報の取得に失敗しました'}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True)
