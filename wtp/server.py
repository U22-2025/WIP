import socket
import struct
import time
import requests
import json
import schedule
from datetime import datetime
import threading

class WeatherServer:
    URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/150000.json"
    OUTPUT_FILE = r"C:\Users\pijon\Downloads\test.json"
    last_report_time = None  # グローバル変数として宣言


    def __init__(self, host='localhost', port=4110, debug=False):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))
        self.debug = debug
        
        # Protocol constants
        self.VERSION = 1  # 4 bits
        self.REQUEST_TYPE = 0
        self.RESPONSE_TYPE = 1
        
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
        
    def parse_request(self, data):
        """Parse incoming request data"""
        # 1byte: version(4) + type(1) + time(3)
        first_byte = data[0]
        version = (first_byte >> 4) & 0x0F
        req_type = (first_byte >> 3) & 0x01
        day = first_byte & 0x07
        
        # 1byte: flags(5) + ip_version(3)
        second_byte = data[1]
        flags_value = (second_byte >> 3) & 0x1F
        ip_version = second_byte & 0x07

        # フラグをビットごとに分割
        flags = {
            'weather': (flags_value >> 4) & 0x01,
            'temperature': (flags_value >> 3) & 0x01,
            'precipitation': (flags_value >> 2) & 0x01,
            'alert': (flags_value >> 1) & 0x01,
            'disaster': flags_value & 0x01,
        }

        # 2byte: packet_id
        packet_id = struct.unpack('!H', data[2:4])[0]

        # 16byte: region (latitude 8byte + longitude 8byte)
        latitude = struct.unpack('!Q', data[4:12])[0] / 1e7 # 1e7 is used to convert to degrees
        longitude = struct.unpack('!Q', data[12:20])[0] / 1e7 

        # 8byte: timestamp
        timestamp = struct.unpack('!Q', data[20:28])[0]

        # 2byte: weather code
        weather_code = struct.unpack('!H', data[28:30])[0]

        # 3byte: temperature (current, max, min)
        temp_bytes = data[30:33]
        temperature = {
            'current': struct.unpack('b', temp_bytes[0:1])[0],
            'max': struct.unpack('b', temp_bytes[1:2])[0],
            'min': struct.unpack('b', temp_bytes[2:3])[0]
        }

        # 1byte: precipitation(5bit) + reserved(3bit)
        prec_and_reserved = data[33]
        precipitation = (prec_and_reserved >> 3) & 0x1F
        reserved = prec_and_reserved & 0x07
        
        # 拡張フィールドはdata[34:]以降

        return {
            'version': version,
            'type': req_type,
            'day': day,
            'flags': flags,
            'ip_version': ip_version,
            'packet_id': packet_id,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': timestamp,
            'weather_code': weather_code,
            'temperature': temperature,
            'precipitation': precipitation,
            'reserved': reserved,
            'extension': data[34:]
        }

    def create_response(self, request):

        # flagsを5ビットにまとめる
        flags = request['flags']
        flags_value = (
        ((flags.get('weather', 0) & 0x01) << 4) |
        ((flags.get('temperature', 0) & 0x01) << 3) |
        ((flags.get('precipitation', 0) & 0x01) << 2) |
        ((flags.get('alert', 0) & 0x01) << 1) |
        (flags.get('disaster', 0) & 0x01)
        )

        # 1byte: version(4) + type(1) + time(3)
        first_byte = ((self.VERSION & 0x0F) << 4) | ((self.RESPONSE_TYPE & 0x01) << 3) | (request['day'] & 0x07)
        # 1byte: flags(5) + ip_version(3)
        second_byte = ((flags_value & 0x1F) << 3) | (request['ip_version'] & 0x07)
        # 2byte: packet_id
        packet_id = struct.pack('!H', request['packet_id'])
        # 8byte: latitude, 8byte: longitude
        latitude = struct.pack('!Q', request['latitude'])
        longitude = struct.pack('!Q', request['longitude'])
        # 8byte: current timestamp
        timestamp = struct.pack('!Q', int(time.time()))
        # 2byte: weather code (例: 晴れ=1)
        weather_code = struct.pack('!H', 1)
        # 3byte: temperature (例: 25, 30, 20)
        temp_bytes = struct.pack('bbb', 25, 30, 20)
        # 1byte: precipitation(5bit=6=30%) + reserved(3bit=0)
        precipitation = (6 << 3) | 0
        prec_byte = struct.pack('B', precipitation)
        # 拡張フィールドなし

        return bytes([first_byte, second_byte]) + packet_id + latitude + longitude + timestamp + weather_code + temp_bytes + prec_byte
        
    def run(self):
        """Start the weather server"""
        print(f"Weather server running on {self.host}:{self.port}")
        
        while True:
            try:
                start_time = time.time()
                data, addr = self.sock.recvfrom(1024)
                print(f"Received request from {addr}")
                
                # Measure request parsing time
                parse_start = time.time()
                request = self.parse_request(data)

                # パケット内の不正な情報をチェック
                #check_request(request)

                parse_time = time.time() - parse_start
                self._debug_print_request(data, request)
                
                # Measure response creation time
                response_start = time.time()
                response = self.create_response(request)
                response_time = time.time() - response_start
                self._debug_print_response(response, request)
                
                # Send response and calculate total time
                self.sock.sendto(response, addr)
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
    
    def check_request(request : dict):
        
        if ( request.version != 1 & request.type != 0 ):
            print("バージョンまたはタイプが不正です")
            return False
        if  all(v == 0 for v in request['flags'].values()) :
            print("全てのフラグが0です")
            return False
        return True
def load_last_report_time():
    global last_report_time
    try:
        with open(WeatherServer.OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            last_report_time = data.get("データ報告時刻")
    except Exception:
        last_report_time = None

def fetch_and_save_weather():
    global last_report_time
    print("関数が呼び出されました。")
    try:
        response = requests.get(WeatherServer.URL)
        response.raise_for_status()
        data = response.json()

        report_time = data[0]["reportDatetime"]
        # 既に保存済みの時刻と同じなら中断
        if last_report_time == report_time:
            print("データ報告時刻が同じなので書き込みをスキップします。")
            return

        weather_areas = data[0]["timeSeries"][0]["areas"]
        pop_areas = data[0]["timeSeries"][1]["areas"]
        temp_areas = data[0]["timeSeries"][2]["areas"]

        # 1週間分の日付数
        week_days = 7

        # timeDefinesから日付ごとに12:00に近いindexを選択
        time_defines = data[0]["timeSeries"][0]["timeDefines"]
        date_to_indices = {}
        for idx, t in enumerate(time_defines):
            date = t[:10]
            if date not in date_to_indices:
                # 日付が初めて出てきた場合、空のリストを作成
                # 日付をキーとして、indexをリストに追加していく
                date_to_indices[date] = [] 
            date_to_indices[date].append(idx)

        # 12:00に近いindexを選ぶ
        selected_indices = []
        removed_indices = []
        for date, indices in date_to_indices.items():
            if len(indices) == 1:
                selected_indices.append(indices[0])
            else:
                # 12:00に近いindexを選択
                min_diff = float('inf')
                sel_idx = indices[0]
                for idx in indices:
                    hour = int(time_defines[idx][11:13])
                    diff = abs(hour - 12)
                    if diff < min_diff:
                        min_diff = diff
                        sel_idx = idx
                selected_indices.append(sel_idx)
                # 除外するindexを保存
                for idx in indices:
                    if idx != sel_idx:
                        removed_indices.append(idx)

        output = {
            "データ報告時刻": report_time,
        }

        for area in weather_areas:
            area_name = area["area"].get("name", "")
            area_code = area["area"].get("code")
            weather_codes = area.get("weatherCodes", [])

            # 除外indexを取り除く
            weather_codes = [code for i, code in enumerate(weather_codes) if i not in removed_indices]

            # 降水確率をarea_codeで紐付けて取得
            pop = []
            for p in pop_areas:
                if p.get("area", {}).get("code") == area_code:
                    pop = p.get("pops", [])
                    # 除外indexを取り除く
                    pop = [v for i, v in enumerate(pop) if i not in removed_indices]
                    break

            # 気温データの補完処理
            temps = []
            # tempAverageからmin/maxの平均値を取得
            temp_avg = None
            temps_max = []
            if len(data) > 1:
                # tempAverage
                temp_avg_areas = data[1].get("tempAverage", {}).get("areas", [])
                for avg_area in temp_avg_areas:
                    try:
                        min_val_str = avg_area.get("min", "")
                        max_val_str = avg_area.get("max", "")
                        if min_val_str != "" and max_val_str != "":
                            min_val = float(min_val_str)
                            max_val = float(max_val_str)
                            temp_avg = int((min_val + max_val) / 2)
                        else:
                            temp_avg = ""
                    except Exception:
                        temp_avg = ""
                    break

                # tempsMax
                if "timeSeries" in data[1] and len(data[1]["timeSeries"]) > 1:
                    temps_max_areas = data[1]["timeSeries"][1].get("areas", [])
                    for tmax_area in temps_max_areas:
                        temps_max = tmax_area.get("tempsMax", [])
                        break

            # temps配列の作成
            temps = []
            if temp_avg is not None and temp_avg != "":
                temps.append(str(temp_avg))
            else:
                temps.append("")
            # tempsMaxの後ろ6つを追加
            temps += temps_max[-6:] if temps_max else [""] * 6
            temps = temps[:7]  # 念のため7つに制限

            # 不足分を補完
            # 例: 3日分しかなければ、4日目以降をdata[1]から補完
            if len(weather_codes) < week_days or len(pop) < week_days:
                # data[1]のtimeSeries[0]から該当エリアのデータを探す
                if len(data) > 1 and "timeSeries" in data[1]:
                    ts = data[1]["timeSeries"]
                    for sub_area in ts[0]["areas"]:
                        
                        # area内のcodeと地域コードの先頭2文字が一致するかを確認
                        if sub_area["area"]["code"][:2] == area_code[:2]: 
                            # weatherCodes補完
                            if len(weather_codes) < week_days:
                                add_codes = sub_area.get("weatherCodes", [])
                                weather_codes += add_codes[len(weather_codes):week_days]
                            # pops補完
                            if len(pop) < week_days:
                                add_pops = sub_area.get("pops", [])
                                pop += add_pops[len(pop):week_days]
                            break

            output[area_code] = {
                "地方名": area_name,
                "天気": weather_codes,
                "気温": temps,
                "降水確率": pop,
                "注意報・警報": [],
                "災害情報": []
            }

        # JSONファイルに保存
        with open(WeatherServer.OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"[{datetime.now()}] 天気データを保存しました。")

    except Exception as e:
        print(f"エラー: {e}")
        
load_last_report_time()
if __name__ == "__main__":
    server = WeatherServer(debug=True)
    
    threading.Thread(target=server.run, daemon=True).start()
    schedule.every(10).minutes.do(fetch_and_save_weather)
    fetch_and_save_weather()
    while True:
        schedule.run_pending()
        time.sleep(3600)

