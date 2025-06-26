"""
Query Client - 改良版（専用パケットクラス使用）
Query Serverとの通信を行うクライアント（サーバー間通信用）
"""

import socket
import struct
import time
import threading
import concurrent.futures
import os
from datetime import datetime
from ..packet import QueryRequest, QueryResponse
from .utils.packet_id_generator import PacketIDGenerator12Bit

PIDG = PacketIDGenerator12Bit()


class QueryClient:
    """Query Serverと通信するクライアント（専用パケットクラス使用）"""
    
    def close(self):
        """クライアントのリソースを解放する"""
        # 現在の実装ではメソッドごとにsocketを作成・クローズしているため、
        # このメソッドは空実装とする
        pass
    
    def __init__(self, host=os.getenv('QUERY_GENERATOR_HOST'), port=int(os.getenv('QUERY_GENERATOR_PORT')), debug=False):
        """
        初期化
        
        Args:
            host: Query Serverのホスト
            port: Query Serverのポート
            debug: デバッグモード
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.VERSION = 1
        
    def _hex_dump(self, data):
        """バイナリデータのhexダンプを作成"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
        
    def _debug_print_request(self, request, area_code):
        """リクエストのデバッグ情報を出力（改良版）"""
        if not self.debug:
            return
            
        print("\n=== SENDING QUERY REQUEST PACKET ===")
        print(f"Total Length: {len(request.to_bytes())} bytes")
        print(f"Area Code: {area_code}")
        
        # 専用クラスのメソッドを使用
        if hasattr(request, 'get_requested_data_types'):
            requested_data = request.get_requested_data_types()
            print(f"Requested Data: {requested_data}")
            
        if hasattr(request, 'get_source_info'):
            source = request.get_source_info()
            print(f"Source: {source}")
        
        print("\nRaw Packet:")
        print(self._hex_dump(request.to_bytes()))
        print("============================\n")
        
    def _debug_print_response(self, response):
        """レスポンスのデバッグ情報を出力（改良版）"""
        if not self.debug:
            return
            
        print("\n=== RECEIVED QUERY RESPONSE PACKET ===")
        print(f"Total Length: {len(response.to_bytes())} bytes")
        
        # 専用クラスのメソッドを使用
        if hasattr(response, 'get_response_summary'):
            summary = response.get_response_summary()
            print(f"\nResponse Summary: {summary}")
            
        if hasattr(response, 'is_success'):
            print(f"Success: {response.is_success()}")
            
        # 気象データの詳細
        if hasattr(response, 'get_weather_code'):
            weather_code = response.get_weather_code()
            if weather_code is not None:
                print(f"Weather Code: {weather_code}")
                
        if hasattr(response, 'get_temperature_celsius'):
            temp = response.get_temperature_celsius()
            if temp is not None:
                print(f"Temperature: {temp}℃")
                
        if hasattr(response, 'get_precipitation_prob'):
            pop = response.get_precipitation_prob()
            if pop is not None:
                print(f"Precipitation: {pop}%")
                
        if hasattr(response, 'get_alert'):
            alert = response.get_alert()
            if alert:
                print(f"Alert: {alert}")
                
        if hasattr(response, 'get_disaster_info'):
            disaster = response.get_disaster_info()
            if disaster:
                print(f"Disaster Info: {disaster}")
        
        print("\nRaw Packet:")
        print(self._hex_dump(response.to_bytes()))
        print("==============================\n")

    def get_weather_data(self, area_code, weather=False, temperature=False, 
                        precipitation_prob=False, alert=False, disaster=False,
                        source=None, timeout=5.0):
        """
        指定されたエリアの気象データを取得する（改良版）
        
        Args:
            area_code: エリアコード
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation_prob: 降水確率データを取得するか
            alert: 警報データを取得するか
            disaster: 災害情報データを取得するか
            source: 送信元情報（プロキシルーティング用）
            timeout: タイムアウト時間（秒）
            
        Returns:
            dict: 取得した気象データ
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        try:
            start_time = time.time()
            
            # 専用クラスでリクエスト作成（大幅に簡潔になった）
            request_start = time.time()
            request = QueryRequest.create_weather_data_request(
                area_code=area_code,
                packet_id=PIDG.next_id(),
                weather=weather,
                temperature=temperature,
                precipitation_prob=precipitation_prob,
                alert=alert,
                disaster=disaster,
                source=source,
                version=self.VERSION
            )
            request_time = time.time() - request_start
            
            self._debug_print_request(request, area_code)
            
            # リクエスト送信
            network_start = time.time()
            sock.sendto(request.to_bytes(), (self.host, self.port))
            
            # レスポンス受信（専用クラス使用）
            response_data, server_addr = sock.recvfrom(1024)
            network_time = datetime.now() - network_start
            
            # レスポンス解析（専用クラス使用）
            parse_start = time.time()
            response = QueryResponse.from_bytes(response_data)
            parse_time = time.time() - parse_start
            
            self._debug_print_response(response)
            
            # 専用クラスのメソッドで結果を簡単に取得
            if response.is_success():
                result = response.get_weather_data()
                
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
            else:
                return {'error': 'Query request failed', 'response_type': response.type}
            
        except socket.timeout:
            return {'error': 'Request timeout', 'timeout': timeout}
        except Exception as e:
            if self.debug:
                import traceback
                traceback.print_exc()
            return {'error': str(e)}
        finally:
            sock.close()

    def get_weather_data_simple(self, area_code, include_all=False, timeout=5.0):
        """
        簡便なメソッド：基本的な気象データを一括取得
        
        Args:
            area_code: エリアコード
            include_all: すべてのデータを取得するか（警報・災害情報も含む）
            timeout: タイムアウト時間（秒）
            
        Returns:
            dict: 取得した気象データ
        """
        return self.get_weather_data(
            area_code=area_code,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=include_all,
            disaster=include_all,
            timeout=timeout
        )

    def test_concurrent_requests(self, area_codes, num_threads=10, requests_per_thread=5):
        """
        並列リクエストのテストを実行する（改良版）
        
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
                    result = self.get_weather_data_simple(
                        area_code=area_code,
                        include_all=(i % 2 == 0)  # 交互に全データ取得
                    )
                    
                    if 'error' not in result:
                        thread_results.append({
                            'thread_id': thread_id,
                            'request_id': i,
                            'area_code': area_code,
                            'timing': result.get('timing', {}),
                            'success': True,
                            'has_weather': 'weather_code' in result,
                            'has_temperature': 'temperature' in result,
                            'has_precipitation_prob': 'precipitation_prob' in result
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
    """メイン関数 - 使用例（専用パケットクラス版）"""
    print("Query Client Example (Enhanced with Specialized Packet Classes)")
    print("=" * 70)
    
    client = QueryClient(debug=True)
    
    # 単一リクエストのテスト
    print("\n1. Single Request Test")
    print("-" * 30)
    
    result = client.get_weather_data(
        area_code="011000",  # 札幌
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=True,
        disaster=True,
        source="query_client_test"
    )
    
    if 'error' not in result:
        print("✓ Request successful!")
        print(f"Area Code: {result.get('area_code')}")
        print(f"Weather Code: {result.get('weather_code')}")
        print(f"Temperature: {result.get('temperature')}°C")
        print(f"precipitation_prob: {result.get('precipitation_prob')}%")
        if result.get('alert'):
            print(f"Alert: {result.get('alert')}")
        if result.get('disaster'):
            print(f"Disaster Info: {result.get('disaster')}")
    else:
        print(f"✗ Request failed: {result['error']}")
    
    # 簡便メソッドのテスト
    print("\n2. Simple Method Test")
    print("-" * 30)
    
    simple_result = client.get_weather_data_simple(
        area_code="130010",  # 東京
        include_all=True
    )
    
    if 'error' not in simple_result:
        print("✓ Simple request successful!")
        print(f"Area Code: {simple_result.get('area_code')}")
        print(f"Weather Code: {simple_result.get('weather_code')}")
        print(f"Temperature: {simple_result.get('temperature')}°C")
        print(f"precipitation_prob: {simple_result.get('precipitation_prob')}%")
    else:
        print(f"✗ Simple request failed: {simple_result['error']}")
    
    # 並列リクエストのテスト
    print("\n3. Concurrent Request Test")
    print("-" * 30)
    
    test_area_codes = ["011000", "012000", "013000", "014100", "015000"]  # 北海道の各地域
    
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
    
    print("\n" + "="*70)
    print("Enhanced Query Client Example completed")
    print("✓ Using specialized packet classes for improved usability")
    print("✓ Simplified API with better error handling")
    print("✓ Automatic data conversion and validation")


if __name__ == "__main__":
    main()
