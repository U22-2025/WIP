import socket
import struct
import time
import threading
import concurrent.futures

# 新しい構造に合わせたimport
try:
    # モジュールとして使用される場合
    from ..packet import Request, Response
except ImportError:
    # 直接実行される場合
    from wtp.packet import Request, Response

class QueryClient:
    def __init__(self, host='localhost', port=4111, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        self.VERSION = 1
        
    def _hex_dump(self, data):
        """Create a hex dump of binary data"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
        
    def _debug_print_request(self, request_packet, area_code, flags):
        """Print debug information for request packet"""
        if not self.debug:
            return
            
        print("\n=== SENDING REQUEST PACKET ===")
        print(f"Total Length: {len(request_packet)} bytes")
        print(f"Area Code: {area_code}")
        print("\nFlags:")
        for flag_name, value in flags.items():
            print(f"  {flag_name}: {value}")
        print("\nRaw Packet:")
        print(self._hex_dump(request_packet))
        print("============================\n")
        
    def _debug_print_response(self, response_data, parsed_response):
        """Print debug information for response packet"""
        if not self.debug:
            return
            
        print("\n=== RECEIVED RESPONSE PACKET ===")
        print(f"Total Length: {len(response_data)} bytes")
        print("\nParsed Response:")
        for key, value in parsed_response.items():
            if key == 'timestamp':
                print(f"  {key}: {time.ctime(value)} ({value})")
            else:
                print(f"  {key}: {value}")
        print("\nRaw Packet:")
        print(self._hex_dump(response_data))
        print("==============================\n")

    def create_request(self, area_code, weather_flag=0, temperature_flag=0, 
                      pops_flag=0, alert_flag=0, disaster_flag=0, packet_id=None):
        """
        気象データリクエストパケットを作成する
        
        Args:
            area_code: エリアコード（文字列または数値、例: "080010" または 80010）
            weather_flag: 天気データ取得フラグ (1で取得)
            temperature_flag: 気温データ取得フラグ (1で取得)
            pops_flag: 降水確率データ取得フラグ (1で取得)
            alert_flag: 警報データ取得フラグ (1で取得)
            disaster_flag: 災害情報データ取得フラグ (1で取得)
            packet_id: パケットID (Noneの場合は自動生成)
            
        Returns:
            bytes: リクエストパケットのバイト列
        """
        if packet_id is None:
            packet_id = int(time.time()) & 0xFFF  # 12ビットに制限
        
        # エリアコードを6桁の文字列に正規化
        if isinstance(area_code, int):
            area_code_str = f"{area_code:06d}"
        else:
            area_code_str = str(area_code).zfill(6)
            
        request = Request(
            version=self.VERSION,
            packet_id=packet_id,
            type=2,  # 気象データリクエスト
            weather_flag=weather_flag,
            temperature_flag=temperature_flag,
            pops_flag=pops_flag,
            alert_flag=alert_flag,
            disaster_flag=disaster_flag,
            ex_flag=0,
            day=0,
            timestamp=int(time.time()),
            area_code=area_code_str  # 文字列として設定
        )
        
        return request.to_bytes()

    def parse_response(self, response_data):
        """
        レスポンスパケットを解析する
        
        Args:
            response_data: 受信したバイナリデータ
            
        Returns:
            dict: 解析されたレスポンスデータ
        """
        try:
            response = Response.from_bytes(response_data)
            
            result = {
                'version': response.version,
                'packet_id': response.packet_id,
                'type': response.type,
                'timestamp': response.timestamp,
                'area_code': response.area_code,
                'ex_flag': response.ex_flag
            }
            
            # 固定長拡張フィールドがある場合
            if hasattr(response, 'weather_code'):
                result['weather_code'] = response.weather_code
            if hasattr(response, 'temperature'):
                # 気温を実際の値に変換 (0-255 -> -100℃～+155℃)
                result['temperature'] = response.temperature - 100
            if hasattr(response, 'pops'):
                result['precipitation'] = response.pops
                
            # 拡張フィールドがある場合
            if response.ex_flag == 1 and hasattr(response, 'ex_field'):
                result['ex_field'] = response.ex_field
                
            return result
            
        except Exception as e:
            print(f"Error parsing response: {e}")
            return {'error': str(e), 'raw_data': self._hex_dump(response_data)}

    def get_weather_data(self, area_code, weather=False, temperature=False, 
                        precipitation=False, alerts=False, disaster=False, 
                        timeout=5.0):
        """
        指定されたエリアの気象データを取得する
        
        Args:
            area_code: エリアコード
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation: 降水確率データを取得するか
            alerts: 警報データを取得するか
            disaster: 災害情報データを取得するか
            timeout: タイムアウト時間（秒）
            
        Returns:
            dict: 取得した気象データ
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        try:
            start_time = time.time()
            
            # フラグの設定
            flags = {
                'weather_flag': 1 if weather else 0,
                'temperature_flag': 1 if temperature else 0,
                'pops_flag': 1 if precipitation else 0,
                'alert_flag': 1 if alerts else 0,
                'disaster_flag': 1 if disaster else 0
            }
            
            # リクエスト作成
            request_start = time.time()
            request_packet = self.create_request(area_code, **flags)
            request_time = time.time() - request_start
            
            self._debug_print_request(request_packet, area_code, flags)
            
            # リクエスト送信
            network_start = time.time()
            sock.sendto(request_packet, (self.host, self.port))
            
            # レスポンス受信
            response_data, server_addr = sock.recvfrom(1024)
            network_time = time.time() - network_start
            
            # レスポンス解析
            parse_start = time.time()
            result = self.parse_response(response_data)
            parse_time = time.time() - parse_start
            
            self._debug_print_response(response_data, result)
            
            # タイミング情報を追加
            total_time = time.time() - start_time
            result['timing'] = {
                'request_creation': request_time * 1000,
                'network_roundtrip': network_time * 1000,
                'response_parsing': parse_time * 1000,
                'total_time': total_time * 1000
            }
            
            if self.debug:
                print("\n=== TIMING INFORMATION ===")
                print(f"Request creation time: {request_time*1000:.2f}ms")
                print(f"Network round-trip time: {network_time*1000:.2f}ms")
                print(f"Response parsing time: {parse_time*1000:.2f}ms")
                print(f"Total operation time: {total_time*1000:.2f}ms")
                print("========================\n")
            
            return result
            
        except socket.timeout:
            return {'error': 'Request timeout', 'timeout': timeout}
        except Exception as e:
            return {'error': str(e)}
        finally:
            sock.close()

    def test_concurrent_requests(self, area_codes, num_threads=10, requests_per_thread=5):
        """
        並列リクエストのテストを実行する
        
        Args:
            area_codes: テストするエリアコードのリスト
            num_threads: 並列スレッド数
            requests_per_thread: スレッドあたりのリクエスト数
            
        Returns:
            dict: テスト結果
        """
        results = []
        errors = []
        
        def worker_thread(thread_id):
            thread_results = []
            thread_errors = []
            
            for i in range(requests_per_thread):
                area_code = area_codes[i % len(area_codes)]
                try:
                    result = self.get_weather_data(
                        area_code=area_code,
                        weather=True,
                        temperature=True,
                        precipitation=True
                    )
                    
                    if 'error' not in result:
                        thread_results.append({
                            'thread_id': thread_id,
                            'request_id': i,
                            'area_code': area_code,
                            'timing': result.get('timing', {}),
                            'success': True
                        })
                    else:
                        thread_errors.append({
                            'thread_id': thread_id,
                            'request_id': i,
                            'area_code': area_code,
                            'error': result['error']
                        })
                        
                except Exception as e:
                    thread_errors.append({
                        'thread_id': thread_id,
                        'request_id': i,
                        'area_code': area_code,
                        'error': str(e)
                    })
            
            return thread_results, thread_errors
        
        print(f"Starting concurrent test: {num_threads} threads, {requests_per_thread} requests each")
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(num_threads)]
            
            for future in concurrent.futures.as_completed(futures):
                thread_results, thread_errors = future.result()
                results.extend(thread_results)
                errors.extend(thread_errors)
        
        total_time = time.time() - start_time
        
        # 統計情報の計算
        successful_requests = len(results)
        failed_requests = len(errors)
        total_requests = successful_requests + failed_requests
        
        if successful_requests > 0:
            avg_response_time = sum(r['timing'].get('total_time', 0) for r in results) / successful_requests
            min_response_time = min(r['timing'].get('total_time', 0) for r in results)
            max_response_time = max(r['timing'].get('total_time', 0) for r in results)
        else:
            avg_response_time = min_response_time = max_response_time = 0
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'total_test_time': total_time,
            'requests_per_second': total_requests / total_time if total_time > 0 else 0,
            'avg_response_time_ms': avg_response_time,
            'min_response_time_ms': min_response_time,
            'max_response_time_ms': max_response_time,
            'errors': errors
        }

def main():
    """テスト用のメイン関数"""
    print("Query Client Test")
    print("=" * 50)
    
    client = QueryClient(debug=True)
    
    # 単一リクエストのテスト
    print("\n1. Single Request Test")
    print("-" * 30)
    
    result = client.get_weather_data(
        area_code=11000,  # 札幌
        weather=True,
        temperature=True,
        precipitation=True,
        alerts=True,
        disaster=True
    )
    
    if 'error' not in result:
        print("✓ Request successful!")
        print(f"Area Code: {result.get('area_code')}")
        print(f"Weather Code: {result.get('weather_code')}")
        print(f"Temperature: {result.get('temperature')}°C")
        print(f"Precipitation: {result.get('precipitation')}%")
        if result.get('ex_field'):
            print(f"Extended Field: {result.get('ex_field')}")
    else:
        print(f"✗ Request failed: {result['error']}")
    
    # 並列リクエストのテスト
    print("\n2. Concurrent Request Test")
    print("-" * 30)
    
    test_area_codes = [11000, 12000, 13000, 14100, 15000]  # 北海道の各地域
    
    test_result = client.test_concurrent_requests(
        area_codes=test_area_codes,
        num_threads=5,
        requests_per_thread=3
    )
    
    print(f"Total Requests: {test_result['total_requests']}")
    print(f"Successful: {test_result['successful_requests']}")
    print(f"Failed: {test_result['failed_requests']}")
    print(f"Success Rate: {test_result['success_rate']:.1f}%")
    print(f"Requests/Second: {test_result['requests_per_second']:.1f}")
    print(f"Avg Response Time: {test_result['avg_response_time_ms']:.2f}ms")
    print(f"Min Response Time: {test_result['min_response_time_ms']:.2f}ms")
    print(f"Max Response Time: {test_result['max_response_time_ms']:.2f}ms")
    
    if test_result['errors']:
        print(f"\nErrors ({len(test_result['errors'])}):")
        for error in test_result['errors'][:5]:  # 最初の5個のエラーのみ表示
            print(f"  Thread {error['thread_id']}, Request {error['request_id']}: {error['error']}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    main()
