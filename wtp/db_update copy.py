import redis
from redis.commands.json.path import Path
from redis.client import Pipeline
import time
import requests
import json
import concurrent.futures
import threading
db_list = [
    {
        "host": "localhost",
        "port": 6379,
        "db": 0
    }
]

area_codes = [
    '011000', 
    '012000', 
    '013000', 
    # '014030', 
    '014100', 
    '015000', 
    '016000', 
    '017000', 
    '020000', 
    '030000', 
    '040000', 
    '050000', 
    '060000', 
    '070000', 
    '080000', 
    '090000', 
    '100000', 
    '110000', 
    '120000', 
    '130000', 
    '140000', 
    '150000', 
    '160000', 
    '170000', 
    '180000', 
    '190000', 
    '200000', 
    '210000', 
    '220000', 
    '230000', 
    '240000', 
    '250000', 
    '260000', 
    '270000', 
    '280000', 
    '290000', 
    '300000', 
    '310000', 
    '320000', 
    '330000', 
    '340000', 
    '350000', 
    '360000', 
    '370000', 
    '380000', 
    '390000', 
    '400000', 
    '410000', 
    '420000', 
    '430000', 
    '440000', 
    '450000', 
    # '460040', 
    '460100', 
    '471000', 
    '472000', 
    '473000', 
    '474000'
]
def get_area_codes():
    url = "https://www.jma.go.jp/bosai/common/const/area.json"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data["offices"].keys()

def get_data(area_codes: list, debug = False):
    
    
    output = {}
    output_lock = threading.Lock()
    
    if debug:
        print(f"処理開始: {len(area_codes)}個のエリアコードを処理します")
        start_time = time.time()
    
    def fetch_and_process_area(area_code):
        area_output = {}
        
        if debug:
            area_start_time = time.time()
            print(f"エリアコード {area_code} の処理を開始します")
        
        try:
            URL = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
            response = requests.get(URL)
            response.raise_for_status()
            data = response.json()
            
            if debug:
                print(f"エリアコード {area_code} のデータ取得完了: {len(data)}件")
            
            weather_areas = data[0]["timeSeries"][0]["areas"]
            pop_areas = data[0]["timeSeries"][1]["areas"]
            updated_at = data[0]["reportDatetime"]
            
            week_days = 7
            time_defines = data[0]["timeSeries"][0]["timeDefines"]
            date_to_indices = {}
            for idx, t in enumerate(time_defines):
                date = t[:10]
                if date not in date_to_indices:
                    date_to_indices[date] = []
                date_to_indices[date].append(idx)
            
            if debug:
                print(f"エリアコード {area_code} の日付マッピング: {date_to_indices}")
            
            selected_indices = []
            removed_indices = []
            for date, indices in date_to_indices.items():
                if len(indices) == 1:
                    selected_indices.append(indices[0])
                else:
                    min_diff = float('inf')
                    sel_idx = indices[0]
                    for idx in indices:
                        hour = int(time_defines[idx][11:13])
                        diff = abs(hour - 12)
                        if diff < min_diff:
                            min_diff = diff
                            sel_idx = idx
                    selected_indices.append(sel_idx)
                    for idx in indices:
                        if idx != sel_idx:
                            removed_indices.append(idx)
            
            if debug:
                print(f"エリアコード {area_code} の選択インデックス: {selected_indices}")
                print(f"エリアコード {area_code} の除外インデックス: {removed_indices}")
            
            for area in weather_areas:
                parent_code = area_code[:2]+'0000'
                area_name = area["area"].get("name", "")
                code = area["area"].get("code")
                weather_codes = area.get("weatherCodes", [])
                weather_codes = [code_ for i, code_ in enumerate(weather_codes) if i not in removed_indices]
                
                if debug:
                    print(f"エリア {area_name}({code}) の天気コード: {weather_codes}")
                
                pop = []
                for p in pop_areas:
                    if p.get("area", {}).get("code") == code:
                        pop = p.get("pops", [])
                        pop = [v for i, v in enumerate(pop) if i not in removed_indices]
                        break
                
                temps = []
                temp_avg = None
                temps_max = []
                if len(data) > 1:
                    temp_avg_areas = data[1].get("tempAverage", {}).get("areas", [])
                    for avg_area in temp_avg_areas:
                        try:
                            min_val_str = avg_area.get("min", "")
                            max_val_str = avg_area.get("max", "")
                            if min_val_str != "" and max_val_str != "":
                                min_val = int(float(min_val_str))
                                max_val = int(float(max_val_str))
                                temp_avg = int((min_val + max_val) / 2)
                            else:
                                temp_avg = ""
                        except Exception as e:
                            if debug:
                                print(f"気温平均値の計算エラー: {e}")
                            temp_avg = ""
                        break
                    
                    if "timeSeries" in data[1] and len(data[1]["timeSeries"]) > 1:
                        temps_max_areas = data[1]["timeSeries"][1].get("areas", [])
                        for tmax_area in temps_max_areas:
                            temps_max = tmax_area.get("tempsMax", [])
                            break
                
                temps = []
                if temp_avg is not None and temp_avg != "":
                    temps.append(str(temp_avg))
                else:
                    temps.append("")
                temps += temps_max[-6:] if temps_max else [""] * 6
                temps = temps[:7]
                
                if debug:
                    print(f"エリア {area_name}({code}) の気温データ: {temps}")
                
                if len(weather_codes) < week_days or len(pop) < week_days:
                    if len(data) > 1 and "timeSeries" in data[1]:
                        ts = data[1]["timeSeries"]
                        for sub_area in ts[0]["areas"]:
                            if sub_area["area"]["code"][:2] == code[:2]:
                                if len(weather_codes) < week_days:
                                    add_codes = sub_area.get("weatherCodes", [])
                                    weather_codes += add_codes[len(weather_codes):week_days]
                                if len(pop) < week_days:
                                    add_pops = sub_area.get("pops", [])
                                    pop += add_pops[len(pop):week_days]
                                break
                
                area_output[code] = {
                    "updated_at": updated_at,
                    "parent_code": parent_code,
                    "area_name": area_name,
                    "weather": weather_codes,
                    "temperature": temps,
                    "precipitation": pop,
                    "warnings": [],
                    "disaster_info": []
                }
            
            # スレッドセーフに結果をマージ
            with output_lock:
                output.update(area_output)
                if debug:
                    print(f"エリアコード {area_code} のデータをマージしました")
            
            if debug:
                area_end_time = time.time()
                print(f"エリアコード {area_code} の処理完了: 所要時間 {area_end_time - area_start_time:.2f}秒")
                
        except Exception as e:
            print(f"エラー ({area_code}): {e}")
            if debug:
                import traceback
                print(traceback.format_exc())
    
    # 並列処理の実行
    with concurrent.futures.ThreadPoolExecutor() as executor:
        if debug:
            print(f"ThreadPoolExecutor を使用して並列処理を開始します")
        executor.map(fetch_and_process_area, area_codes)
    
    if debug:
        end_time = time.time()
        print(f"全処理完了: 合計所要時間 {end_time - start_time:.2f}秒")
        print(f"取得したエリア数: {len(output)}")
    
    return output

def update_redis_weather_data(debug=False):
    """
    気象情報を取得してRedisに保存する関数
    
    Args:
        debug (bool): デバッグモードを有効にするかどうか
    """
    if debug:
        print("気象情報の取得を開始します")
        start_time = time.time()
    
    # 気象データを取得
    weather_data = get_data(area_codes, debug=debug)
    
    if debug:
        print(f"気象データの取得完了: {len(weather_data)}エリア")
        print("Redisへのデータ保存を開始します")
    
    # Redisクライアントの初期化
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # パイプラインを使用して一括処理
    with r.pipeline() as pipe:
        for area_code, area_info in weather_data.items():
            pipe.json().set(f"weather:{area_code}", ".", area_info)
        
        # コマンドを実行
        pipe.execute()
    
    if debug:
        end_time = time.time()
        print(f"Redisへのデータ保存完了: 所要時間 {end_time - start_time:.2f}秒")
    
    return len(weather_data)


def redis_set_data(key, data):
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.json().set(f"weather:{key}", ".", data)

def redis_get_data(key):
    r = redis.Redis(host='localhost', port=6379, db=0)
    return r.json().get(f"weather:{key}", ".")



if __name__ == "__main__":
    # redis_set_data(key, data)
    update_redis_weather_data(debug=True)
    # output = get_data(area_codes, debug=True)
    # with open("wtp/resources/test.json", "w", encoding="utf-8") as f:
    #     json.dump(output, f, ensure_ascii=False, indent=2)