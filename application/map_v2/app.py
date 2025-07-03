from flask import Flask, render_template, request, jsonify, send_from_directory
import sys, os
import json
from pathlib import Path
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

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

# 週間予報を取得するエンドポイント
@app.route('/weekly_forecast', methods=['POST'])
def weekly_forecast():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import datetime, timedelta
    
    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    
    if lat is None or lng is None:
        return jsonify({'status': 'error', 'message': '緯度と経度が必要です'}), 400
    
    # day=0（今日）を座標から取得してエリアコードを取得
    client.set_coordinates(lat, lng)

    try:
        today_weather = client.get_weather(day=0)
        if not today_weather:
            return jsonify({'status': 'error', 'message': '今日の天気データの取得に失敗しました'}), 500

        if isinstance(today_weather, dict) and 'error_code' in today_weather:
            return jsonify({
                'status': 'error',
                'error_code': today_weather['error_code'],
                'message': 'エラーパケットを受信しました'
            }), 500

        if 'area_code' not in today_weather:
            return jsonify({'status': 'error', 'message': '今日の天気データまたはエリアコードの取得に失敗しました'}), 500
        
        area_code = today_weather['area_code']
        
        # 今日のデータに日付情報を追加
        today_date = datetime.now()
        today_weather['date'] = today_date.strftime('%Y-%m-%d')
        today_weather['day_of_week'] = today_date.strftime('%A')
        today_weather['day_number'] = 0
        
    except Exception as e:
        print(f"Error getting today's weather: {e}")
        return jsonify({'status': 'error', 'message': f'今日の天気データの取得に失敗しました: {str(e)}'}), 500
    
    def get_daily_weather_by_area_code(day):
        """エリアコードを使って指定された日の天気データを取得する関数（day=1~6用）"""
        try:
            weather_result = client.get_weather_by_area_code(area_code=area_code, day=day)
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
                    'area_code': area_code
                }
        except Exception as e:
            print(f"Error getting weather for day {day} with area code {area_code}: {e}")
            # エラーの場合はダミーデータを返す
            date = datetime.now() + timedelta(days=day)
            return {
                'date': date.strftime('%Y-%m-%d'),
                'day_of_week': date.strftime('%A'),
                'day_number': day,
                'weather_code': '100',
                'temperature': '--',
                'precipitation_prob': '--',
                'area_code': area_code
            }
    
    # 明日以降（day=1~6）を並列でエリアコードから取得
    weekly_data = [today_weather] + [None] * 6  # 今日のデータ + 6日分のNone
    
    with ThreadPoolExecutor(max_workers=6) as executor:
        # day=1~6について並列でタスクを送信
        future_to_day = {executor.submit(get_daily_weather_by_area_code, day): day for day in range(1, 7)}
        
        # 結果を取得して正しい順序でリストに格納
        for future in as_completed(future_to_day):
            day = future_to_day[future]
            try:
                result = future.result()
                weekly_data[day] = result
            except Exception as exc:
                print(f'Day {day} generated an exception: {exc}')
                # エラーの場合はダミーデータを作成
                date = datetime.now() + timedelta(days=day)
                weekly_data[day] = {
                    'date': date.strftime('%Y-%m-%d'),
                    'day_of_week': date.strftime('%A'),
                    'day_number': day,
                    'weather_code': '100',
                    'temperature': '--',
                    'precipitation_prob': '--',
                    'area_code': area_code
                }
    
    forecast_dict = {data['day_number']: data for data in weekly_data}

    return jsonify({
        'status': 'ok',
        'coordinates': {'lat': lat, 'lng': lng},
        'area_code': area_code,
        'weekly_forecast': forecast_dict
    })

# 災害情報を取得するエンドポイント
@app.route('/disaster_info', methods=['POST'])
def disaster_info():
    data = request.get_json()
    area_code = data.get('area_code')

    if not area_code:
        return jsonify({'status': 'error', 'message': 'area_code required'}), 400

    try:
        with open(JSON_DIR / 'disaster_data.json', 'r', encoding='utf-8') as f:
            disaster_data = json.load(f)
        info = disaster_data.get(str(area_code), {}).get('disaster', [])
        return jsonify({'status': 'ok', 'area_code': area_code, 'disaster': info})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True)
