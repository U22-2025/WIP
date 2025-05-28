import socket
import struct
import time
import requests
import json
import schedule
from datetime import datetime
import threading
import csv
import location_resolver

from packet import response_fixed

class WeatherServer:
    json_data = None
    OUTPUT_FILE = r"wtp\resources\test.json" # 取得したデータの保存用ファイルを指定
    last_report_time = None  # グローバル変数として宣言

    def __init__(self, host='localhost', port=4110, debug=False):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.debug = debug
        
        # Protocol constants
        self.VERSION = 1  # 4 bits
        self.REQUEST_TYPE = 2
        self.RESPONSE_TYPE = 3
        
    def _hex_dump(self, data):
        """Create a hex dump of binary data"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
        
    def _debug_print_request(self, data, parsed):
        """Print debug information for request packet"""
        if not self.debug:
            return
            
        print("\n=== RECEIVED REQUEST PACKET ===")
        print(f"Total Length: {len(data)} bytes")
        print("\nHeader:")
        print(f"Version: {parsed['version']}")
        print(f"Type: REQUEST ({parsed['type']})")
        print(f"Region ID: {parsed['region_id']}")
        print(f"Timestamp: {time.ctime(parsed['timestamp'])}")
        print("\nFlags:")
        for flag, value in parsed['flags'].items():
            print(f"{flag}: {value}")
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("===========================\n")
        
    def _debug_print_response(self, response, request):
        """Print debug information for response packet"""
        if not self.debug:
            return
            
        print("\n=== SENDING RESPONSE PACKET ===")
        print(f"Total Length: {len(response)} bytes")
        print("\nHeader:")
        print(f"Version: {self.VERSION}")
        print(f"Type: RESPONSE ({self.RESPONSE_TYPE})")
        print(f"Region ID: {request['region_id']}")
        print(f"Timestamp: {time.ctime(int(time.time()))}")
        print("\nRaw Packet:")
        print(self._hex_dump(response))
        print("============================\n")

    def determine_packet_type(data_bytes):
        # バイト列をビット列（整数）に変換
        bitstr = int.from_bytes(data_bytes, byteorder='big')
        
        # 17-19ビット目を抽出（0から数えて16-18ビット目）
        # FormatBaseクラスのFIELD_POSITIONの'type'の値を使用
        type_position = 16  # 0から数えた場合の位置
        type_length = 3     # 長さ
        
        # ビットマスクを作成して抽出
        mask = ((1 << type_length) - 1) << type_position
        packet_type = (bitstr & mask) >> type_position
        
        return packet_type
        
        
    def run(self):
        """Start the weather server"""
        print(f"Weather server running on {self.host}:{self.port}")
        
        while True:
            try:
                start_time = time.time()
                data, addr = self.sock.recvfrom(1024)
                print(f"Received request from {addr}")
                
                type = self.determine_packet_type(data) # 1:request / 2:response
                # Measure request parsing time
                parse_start = time.time()
                
                # 受信パケットがresponseだった場合、
                # 送信元アドレスを書き換えて転送し、終了
                if type == 2:
                    response = response_fixed.Response.from_bytes(data)
                    response.timestamp = int(time.time())

                    addr = response.ex_field['source']
                    self.sock.sendto(response, addr)
                    return

                # 以下、リクエストパケット
                request = self.parse_request(data)
                request.timestamp = int(time.time())
                request.ex_field['source'] = addr

                # region_idが指定されていない場合
                if request.area_code == 0 :
                    addr = ["localhost",4109] 
                    self.sock.sendto(request, addr) # location_resolverに転送する
                    return
                
                # 以下、redisDBを持つサーバへ問い合わせる処理
                query_resolve_host = 'localhost'
                query_resolve_port = 4110
                addr[0] = query_resolve_host
                addr[1] = query_resolve_port
                self.sock.sendto(request,addr)

                parse_time = time.time() - parse_start
                self._debug_print_request(data, request)
                
                # Measure response creation time
                response_start = time.time()
                response_time = time.time() - response_start
                self._debug_print_response(response, request)
                
                total_time = time.time() - start_time
                
                if self.debug:
                    print("\n=== TIMING INFORMATION ===")
                    print(f"Request parsing time: {parse_time*1000:.2f}ms")
                    print(f"Response creation time: {response_time*1000:.2f}ms")
                    print(f"Total processing time: {total_time*1000:.2f}ms")
                    print("========================\n")
                
                print(f"Sent response to {addr}")
                
            except Exception as e:
                print(f"Error processing request: {e}")
                continue
    
def load_last_report_time():
    global last_report_time
    try:
        with open(WeatherServer.OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            last_report_time = data.get("データ報告時刻")
    except Exception:
        last_report_time = None


def get_pref_codes_from_csv(csv_path):
    codes = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            # 1列目に都道府県コードがある場合
            if row and row[0]:
                codes.append(row[0])
    return codes


# 複数のエリアコードを指定して、天気データをまとめて取得する。
def all_fetches_done():
    # CSVファイルで、扱う地域の地域コードをまとめておき、
    # それを読み込んで配列化。引数として渡し、天気データを取得する。
    # codes = get_pref_codes_from_csv(r"wtp\resources\prefecture.csv")  # CSVファイル名を指定
    fetch_and_save_weather("010000")


def fetch_and_save_weather(area_code):
    global last_report_time
    global json_data
    print("関数が呼び出されました。") # debug
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

        # with open(WeatherServer.OUTPUT_FILE, "w", encoding="utf-8") as f:
        #     json.dump(output, f, ensure_ascii=False, indent=2)

        # 変数に保持
        global json_data
        json_data = output

        print(f"[{datetime.now()}] 天気データを保存しました。")

    except Exception as e:
        print(f"エラー: {e}")
        

if __name__ == "__main__":
    server = WeatherServer(debug=True)
    load_last_report_time()

    threading.Thread(target=server.run, daemon=True).start()
    schedule.every(10).minutes.do(all_fetches_done)
    all_fetches_done()
    while True:
        schedule.run_pending()
        time.sleep(30)

