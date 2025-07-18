import time
import requests
import json
import concurrent.futures
import threading
import sys
import os
import traceback
from pathlib import Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from WIP_Server.data.redis_manager import create_redis_manager, WeatherRedisManager
JSON_DIR = Path(__file__).resolve().parents[2] / "logs" / "json"
def get_data(area_codes: list, debug=False, save_to_redis=False):
    output = {"weather_reportdatetime": {}}
    output_lock = threading.Lock()
    skip_area = []  # ローカル変数として定義

    if debug:
        print(f"処理開始: {len(area_codes)}個のエリアコードを処理します")
        start_time = time.time()

    # セッション共有の設定
    session = requests.Session()

    # コネクションプールの最適化
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=20,
        pool_maxsize=50,
        max_retries=3
    )
    session.mount('https://', adapter)

    # タイムアウト設定
    timeout = 5.0

    ### ここに日付チェックを追加
    rm = WeatherRedisManager()
    
    # Redisから既存のweather_reportdatetimeを取得
    existing_report_datetimes = rm.get_weather_data("weather_reportdatetime")

    # レート制限のためのロック
    rate_limit_lock = threading.Lock()
    last_request_time = [0]  # リストにして参照渡し

    def fetch_and_process_area(area_code):
        area_output = {}

        if debug:
            area_start_time = time.time()
            print(f"エリアコード {area_code} の処理を開始します")

        try:
            # レート制限: 1秒間に1リクエスト
            with rate_limit_lock:
                current_time = time.time()
                time_since_last = current_time - last_request_time[0]
                if time_since_last < 1.0:
                    sleep_time = 1.0 - time_since_last
                    time.sleep(sleep_time)
                last_request_time[0] = time.time()

            URL = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
            # 共有セッションとタイムアウトを使用
            response = session.get(URL, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            if debug:
                print(f"エリアコード {area_code} のデータ取得完了: {len(data)}件")

            weather_areas = data[0]["timeSeries"][0]["areas"]
            pop_areas = data[0]["timeSeries"][1]["areas"]
            reporttime = data[0]["reportDatetime"]

            ### 時刻チェック
            ### redisが保持しているデータと同じreportdatetimeならスキップ
            if existing_report_datetimes is not None and area_code in existing_report_datetimes and existing_report_datetimes[area_code] == reporttime:
                if debug:
                    print(f"エリアコード {area_code} のデータは更新されていません。スキップします。")
                    skip_area.append(area_code)
                return # このエリアコードの処理をスキップ

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

            parent_code = area_code
            for area in weather_areas:
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
                                    add_pop = sub_area.get("pops", [])
                                    pop += add_pop[len(pop):week_days]
                                break
                area_data = {
                    "parent_code": parent_code,
                    "area_name": area_name,
                    "weather": weather_codes,
                    "temperature": temps,
                    "precipitation_prob": pop,
                }

                area_output[code] = area_data

            # スレッドセーフに結果をマージ
            with output_lock:
                output.update(area_output)
                output["weather_reportdatetime"][area_code] = reporttime # weather_reportdatetimeをトップレベルに追加
                if debug:
                    print(f"エリアコード {area_code} のデータをマージしました")

            if debug:
                area_end_time = time.time()
                print(f"エリアコード {area_code} の処理完了: 所要時間 {area_end_time - area_start_time:.2f}秒")

        except Exception as e:
            print(f"エラー ({area_code}): {e}")
            if debug:
                print(traceback.format_exc())

    # 並列処理の実行 - ワーカー数を明示的に設定
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        if debug:
            print(f"ThreadPoolExecutor を使用して並列処理を開始します (max_workers=20)")
        executor.map(fetch_and_process_area, area_codes)

    # 全データの処理が完了した後、一括でRedisに保存
    if save_to_redis:
        try:
            if debug:
                print("全データをRedisに一括保存します")
                redis_start_time = time.time()

            # Redis管理クラスを使用して一括保存
            redis_manager = create_redis_manager(debug=debug)
            
            # weather_reportdatetime を output から分離
            report_datetimes_data = output.pop("weather_reportdatetime", {})
            
            # エリアごとの気象データを一括保存
            result = redis_manager.bulk_update_weather_data(output)
            
            # weather_reportdatetime を個別に保存
            if report_datetimes_data:
                redis_manager.update_weather_data("weather_reportdatetime", report_datetimes_data)

            redis_manager.close()

            if debug:
                redis_end_time = time.time()
                print(f"Redisへの一括保存完了: 所要時間 {redis_end_time - redis_start_time:.2f}秒")
                print(f"更新件数: {result['updated']}, エラー件数: {result['errors']}")
        except Exception as e:
            print(f"Redisへの一括保存エラー: {e}")
            if debug:
                print(traceback.format_exc())

    if debug:
        end_time = time.time()
        print(f"全処理完了: 合計所要時間 {end_time - start_time:.2f}秒")
        print(f"取得したエリア数: {len(output)}")

    return skip_area

def update_redis_weather_data(debug=False, area_codes=None):
    """
    気象情報を取得してRedisに保存する関数

    Args:
        debug (bool): デバッグモードを有効にするかどうか
        area_codes (list, optional): 処理対象のエリアコードリスト。Noneの場合は全エリアを処理
    """
    if debug:
        print("気象情報の取得を開始します")
        start_time = time.time()

    # エリアコードが指定されていない場合は、JSONファイルから読み込む
    if area_codes is None:
        with open(JSON_DIR / "area_codes.json", "r", encoding="utf-8") as f:
            area_codes = list(json.load(f).keys())

    # 気象データを取得し、直接Redisに保存
    skip_area = get_data(area_codes, debug=debug, save_to_redis=True)

    if debug:
        end_time = time.time()
        print(f"気象データの取得と保存完了: {len(area_codes)}エリア処理、{len(skip_area)}エリアスキップ")
        print(f"合計所要時間: {end_time - start_time:.2f}秒")

    return skip_area

if __name__ == "__main__":
    # 気象データの更新を実行し、スキップされたエリアを取得
    skip_area = update_redis_weather_data(debug=True)
    
    # スキップされたエリアを表示
    if skip_area:
        print(f"\n=== スキップされたエリア ===")
        print(f"スキップされたエリア数: {len(skip_area)}")
        print(f"スキップされたエリアコード: {skip_area}")
        print("="*30)
    else:
        print(f"\n=== 全エリア更新完了 ===")
        print("スキップされたエリアはありません")
        print("="*30)
