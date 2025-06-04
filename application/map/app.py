from flask import Flask, render_template, request, jsonify, send_from_directory
import sys, os
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from WTP_Client import Client

app = Flask(__name__)
client = Client(debug=True)

# ジオコーダーの初期化
geolocator = Nominatim(user_agent="wtp_map_app")

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

# 天気コードJSONを提供するルート
@app.route('/weather_code.json')
def weather_code():
    return send_from_directory('templates', 'weather_code.json')

@app.route('/click', methods=['POST'])
def click():
    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    
    # 座標を設定
    client.set_coordinates(lat, lng)
    
    # 天気情報を取得
    weather_result = client.get_weather()
    
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
    
    # 座標を設定
    client.set_coordinates(lat, lng)
    
    def get_daily_weather(day):
        """指定された日の天気データを取得する関数"""
        try:
            weather_result = client.get_weather(day=day)
            if weather_result:
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
    
    # 並列で一週間分の天気データを取得
    weekly_data = [None] * 7  # 結果を格納するリストを初期化
    
    with ThreadPoolExecutor(max_workers=7) as executor:
        # 全ての日について並列でタスクを送信
        future_to_day = {executor.submit(get_daily_weather, day): day for day in range(7)}
        
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
                    'area_code': 'unknown'
                }
    
    return jsonify({
        'status': 'ok',
        'coordinates': {'lat': lat, 'lng': lng},
        'weekly_forecast': weekly_data
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True)
