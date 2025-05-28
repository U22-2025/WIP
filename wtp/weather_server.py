"""
天気サーバー - リファクタリング版
基底クラスを継承した実装
"""

import socket
import struct
import time
import requests
import json
import schedule
from datetime import datetime
import threading
import csv
import sys
import os

# パスを追加して直接実行にも対応
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # モジュールとして使用される場合
    from .base_server import BaseServer
    from .packet import Request, Response
except ImportError:
    # 直接実行される場合
    from base_server import BaseServer
    from packet import Request, Response


class WeatherServer(BaseServer):
    """天気サーバーのメインクラス（基底クラス継承版）"""
    
    # クラス変数
    json_data = None
    OUTPUT_FILE = r"wtp\resources\test.json"  # 取得したデータの保存用ファイルを指定
    last_report_time = None
    
    def __init__(self, host='localhost', port=4110, debug=False, max_workers=None):
        """
        初期化
        
        Args:
            host: サーバーホスト
            port: サーバーポート
            debug: デバッグモードフラグ
            max_workers: スレッドプールのワーカー数（Noneの場合はCPU数*2）
        """
        # 基底クラスの初期化（max_workersも渡す）
        super().__init__(host, port, debug, max_workers)
        
        # サーバー名を設定
        self.server_name = "WeatherServer"
        
        # Protocol constants
        self.VERSION = 1  # 4 bits
        self.REQUEST_TYPE = 0
        self.RESPONSE_TYPE = 1
        
        # 天気データ取得用の初期化
        self._init_weather_data()
    
    def _init_weather_data(self):
        """天気データの初期化"""
        self.load_last_report_time()
        # 初回データ取得
        threading.Thread(target=self.all_fetches_done, daemon=True).start()
        # 定期実行のスケジュール設定
        schedule.every(10).minutes.do(self.all_fetches_done)
    
    def parse_request(self, data):
        """
        リクエストデータをパース
        
        Args:
            data: 受信したバイナリデータ
            
        Returns:
            Request: パースされたリクエスト
        """
        return Request.from_bytes(data)
    
    def create_response(self, request):
        """
        レスポンスを作成
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            レスポンスのバイナリデータ
        """
        # レスポンスオブジェクトを作成
        response = Response(
            version=self.VERSION,
            packet_id=request.packet_id,
            type=self.RESPONSE_TYPE,
            area_code=request.area_code,
            day=request.day,
            timestamp=int(time.time()),
            weather_flag=request.weather_flag,
            temperature_flag=request.temperature_flag,
            pops_flag=request.pops_flag,
            alert_flag=request.alert_flag,
            disaster_flag=request.disaster_flag,
            ex_flag=request.ex_flag
        )
        
        # area_codeから該当エリアのデータを取得
        area_code = request.area_code
        region_info = None
        if self.json_data and str(area_code) in self.json_data:
            region_info = self.json_data[str(area_code)]
        else:
            region_info = {
                "地方名": "",
                "天気": [],
                "気温": [],
                "降水確率": [],
                "注意報・警報": [],
                "災害情報": []
            }
        
        # 必要なデータを抽出し、responseにセット
        if request.weather_flag == 1:
            weather_list = region_info.get('天気', [])
            if weather_list and len(weather_list) > request.day:
                try:
                    response.weather_code = int(weather_list[request.day])
                except (ValueError, TypeError):
                    response.weather_code = 0
            else:
                response.weather_code = 0
        
        if request.temperature_flag == 1:
            temp_list = region_info.get('気温', [])
            if temp_list:
                # 最高気温、最低気温、平均気温を設定
                try:
                    if len(temp_list) > request.day and temp_list[request.day]:
                        temp_value = int(temp_list[request.day])
                        response.temperature_max = temp_value
                        response.temperature_min = temp_value - 5  # 仮の値
                        response.temperature_avg = temp_value - 2  # 仮の値
                    else:
                        response.temperature_max = 25
                        response.temperature_min = 20
                        response.temperature_avg = 22
                except (ValueError, TypeError, IndexError):
                    response.temperature_max = 25
                    response.temperature_min = 20
                    response.temperature_avg = 22
        
        if request.pops_flag == 1:
            pops_list = region_info.get('降水確率', [])
            if pops_list and len(pops_list) > request.day:
                try:
                    response.precipitation = int(pops_list[request.day])
                except (ValueError, TypeError):
                    response.precipitation = 0
            else:
                response.precipitation = 0
        
        # 拡張フィールドの処理
        if request.ex_flag == 1 and hasattr(request, 'ex_field'):
            response.ex_field = {}
            
            if request.alert_flag == 1:
                alert_list = region_info.get('注意報・警報', [])
                if alert_list:
                    response.ex_field['alert'] = alert_list
            
            if request.disaster_flag == 1:
                disaster_list = region_info.get('災害情報', [])
                if disaster_list:
                    response.ex_field['disaster'] = disaster_list
        
        return response.to_bytes()
    
    def validate_request(self, request):
        """
        リクエストの妥当性をチェック
        
        Args:
            request: リクエストオブジェクト
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if request.version != 1 or request.type != 0:
            return False, "バージョンまたはタイプが不正です"
        
        # すべてのフラグが0かチェック
        if (request.weather_flag == 0 and 
            request.temperature_flag == 0 and 
            request.pops_flag == 0 and 
            request.alert_flag == 0 and 
            request.disaster_flag == 0):
            return False, "全てのフラグが0です"
        
        return True, None
    
    def _debug_print_request(self, data, parsed):
        """リクエストのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print("\n=== RECEIVED REQUEST PACKET ===")
        print(f"Total Length: {len(data)} bytes")
        print("\nHeader:")
        print(f"Version: {parsed.version}")
        print(f"Type: REQUEST ({parsed.type})")
        print(f"Area Code: {parsed.area_code}")
        print(f"Packet ID: {parsed.packet_id}")
        print(f"Timestamp: {time.ctime(parsed.timestamp)}")
        print(f"Day: {parsed.day}")
        print("\nFlags:")
        print(f"Weather: {parsed.weather_flag}")
        print(f"Temperature: {parsed.temperature_flag}")
        print(f"PoPs: {parsed.pops_flag}")
        print(f"Alert: {parsed.alert_flag}")
        print(f"Disaster: {parsed.disaster_flag}")
        print(f"Extended Field: {parsed.ex_flag}")
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("===========================\n")
    
    def _debug_print_response(self, response, request=None):
        """レスポンスのデバッグ情報を出力（オーバーライド）"""
        if not self.debug:
            return
            
        print("\n=== SENDING RESPONSE PACKET ===")
        print(f"Total Length: {len(response)} bytes")
        print("\nHeader:")
        print(f"Version: {self.VERSION}")
        print(f"Type: RESPONSE ({self.RESPONSE_TYPE})")
        if request:
            print(f"Area Code: {request.area_code}")
            print(f"Packet ID: {request.packet_id}")
        print(f"Timestamp: {time.ctime(int(time.time()))}")
        print("\nRaw Packet:")
        print(self._hex_dump(response))
        print("============================\n")
    
    def load_last_report_time(self):
        """最後のレポート時刻を読み込み"""
        try:
            with open(self.OUTPUT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.last_report_time = data.get("データ報告時刻")
        except Exception:
            self.last_report_time = None
    
    @staticmethod
    def get_pref_codes_from_csv(csv_path):
        """CSVファイルから都道府県コードを取得"""
        codes = []
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                # 1列目に都道府県コードがある場合
                if row and row[0]:
                    codes.append(row[0])
        return codes
    
    def all_fetches_done(self):
        """複数のエリアコードを指定して、天気データをまとめて取得"""
        # CSVファイルで、扱う地域の地域コードをまとめておき、
        # それを読み込んで配列化。引数として渡し、天気データを取得する。
        # codes = get_pref_codes_from_csv(r"wtp\resources\prefecture.csv")  # CSVファイル名を指定
        self.fetch_and_save_weather("010000")
    
    def fetch_and_save_weather(self, area_code):
        """天気データを取得して保存"""
        print("関数が呼び出されました。")  # debug
        output = {
            "updated_at": None,
        }
        
        try:
            # ここから下はデータ取得・保存処理
            URL = f"https://www.jma.go.jp/bosai/forecast/data/forecast/{area_code}.json"
            response = requests.get(URL)
            response.raise_for_status()
            data = response.json()
            
            output["updated_at"] = data[0]["reportdateTime"]
            weather_areas = data[0]["timeSeries"][0]["areas"]
            pop_areas = data[0]["timeSeries"][1]["areas"]
            
            week_days = 7
            time_defines = data[0]["timeSeries"][0]["timeDefines"]
            date_to_indices = {}
            for idx, t in enumerate(time_defines):
                date = t[:10]
                if date not in date_to_indices:
                    date_to_indices[date] = []
                date_to_indices[date].append(idx)
            
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
            
            for area in weather_areas:
                parent_code = area_code[:2]+'0000'
                area_name = area["area"].get("name", "")
                code = area["area"].get("code")
                weather_codes = area.get("weatherCodes", [])
                weather_codes = [code_ for i, code_ in enumerate(weather_codes) if i not in removed_indices]
                
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
                        except Exception:
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
                
                output[code] = {
                    "地方名": area_name,
                    "天気": weather_codes,
                    "気温": temps,
                    "降水確率": pop,
                    "注意報・警報": [],
                    "災害情報": []
                }
            
            ## redisDBに書き出す処理
            import redis
            r = redis.Redis(host='localhost', port=6379, db=0)
            r.set('weather_data', json.dumps(output))
            
            # 変数に保持
            WeatherServer.json_data = output
            
            print(f"[{datetime.now()}] 天気データを保存しました。")
            
        except Exception as e:
            print(f"エラー: {e}")
    
    def run(self):
        """サーバーを開始（オーバーライド）"""
        # 天気データ更新用スレッドを開始
        def schedule_runner():
            while True:
                schedule.run_pending()
                time.sleep(30)
        
        schedule_thread = threading.Thread(target=schedule_runner, daemon=True)
        schedule_thread.start()
        
        # 基底クラスのrun()を呼び出す
        super().run()
    
    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理（オーバーライド）"""
        # 特に追加のクリーンアップ処理はなし
        pass


if __name__ == "__main__":
    server = WeatherServer(debug=True)
    server.run()
