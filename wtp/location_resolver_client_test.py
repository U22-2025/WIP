import socket
import struct
import ipaddress
import time
import random
from packet_format import *
from packet_id_12bit import PacketIDGenerator12Bit
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

PIDG = PacketIDGenerator12Bit()

class LocationResolverClient:
    def __init__(self, host='localhost', port=4109, debug=False):
        """Initialize the location resolver client"""
        self.server_host = host
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.debug = debug

    def _hex_dump(self, data):
        """Create a hex dump of binary data"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"

    def _debug_print_request(self, data):
        """Print debug information for request packet"""
        if not self.debug:
            return

        print("\n=== SENDING REQUEST PACKET ===")
        print(f"Total Length: {len(data.to_bytes())} bytes")
        print("\nCoordinates:")
        print(f"Latitude: {data.latitude}")
        print(f"Longitude: {data.longitude}")
        print("\nRaw Packet:")
        print(self._hex_dump(data.to_bytes()))
        print("===========================\n")

    def _debug_print_response(self, data, region_code, weather_server_ip=None):
        """Print debug information for response packet"""
        if not self.debug:
            return

        print("\n=== RECEIVED RESPONSE PACKET ===")
        print(f"Total Length: {len(data)} bytes")
        print(f"Region Code: {region_code}")
        # print(f"Weather Server IP: {weather_server_ip}")
        print("\nRaw Packet:")
        print(self._hex_dump(data))
        print("============================\n")

    

    def get_location_info(self, latitude, longitude):
        # """Send coordinates and get location information"""
        # try:
            start_time = time.time()

            # Create request packet
            request_start = time.time()
            request = ResolverRequest(version=1, packet_ID=PIDG.next_id(), type=0, weather_flag=0, timestamp=int(datetime.now().timestamp()), longitude=longitude, latitude=latitude, ex_field=0)
            request_time = time.time() - request_start
            self._debug_print_request(request)

            # Send request and receive response
            network_start = time.time()
            self.sock.sendto(request.to_bytes(), (self.server_host, self.server_port))
            if self.debug:
                print(f"Sent request to {self.server_host}:{self.server_port}")

            data, addr = self.sock.recvfrom(1024)
            network_time = time.time() - network_start
            if self.debug:
                print(f"Received response from {addr}")

            # Parse response
            parse_start = time.time()
            response = ResolverResponse.from_bytes(data)
            parse_time = time.time() - parse_start
            self._debug_print_response(
                data,
                response.area_code
            )

            total_time = time.time() - start_time

            if self.debug:
                print("\n=== TIMING INFORMATION ===")
                print(f"Request creation time: {request_time*1000:.2f}ms")
                print(f"Request send time: {(network_start - request_start)*1000:.2f}ms")
                print(f"Network round-trip time: {network_time*1000:.2f}ms")
                print(f"Response parsing time: {parse_time*1000:.2f}ms")
                print(f"Total processing time: {total_time*1000:.2f}ms")
                print("========================\n")

            return response, total_time

        # except Exception as e:
        #     print(f"Error communicating with location resolver: {e}")
        #     return None, 0

    def close(self):
        """Close the socket"""
        self.sock.close()

def generate_random_japan_coordinates():
    """Generate random coordinates within Japan's main islands"""
    # Define regions for Japan's main islands
    regions = [
        # Honshu (本州) - divided into multiple parts for better coverage
        {'lat': (34.5, 37.5), 'lon': (134.0, 137.0)},  # 中部
        {'lat': (36.0, 38.5), 'lon': (137.0, 140.0)},  # 関東
        {'lat': (38.5, 40.5), 'lon': (140.0, 141.5)},  # 東北南部
        {'lat': (40.5, 41.5), 'lon': (141.0, 142.0)},  # 東北北部
        
        # Hokkaido (北海道)
        {'lat': (41.5, 45.0), 'lon': (141.5, 145.5)},
        
        # Kyushu (九州)
        {'lat': (31.5, 33.5), 'lon': (130.0, 132.0)},
        
        # Shikoku (四国)
        {'lat': (32.5, 34.5), 'lon': (132.5, 134.5)},
    ]
    
    # Randomly select a region
    region = random.choice(regions)
    
    # Generate coordinates within the selected region
    latitude = random.uniform(region['lat'][0], region['lat'][1])
    longitude = random.uniform(region['lon'][0], region['lon'][1])
    
    return latitude, longitude

def create_performance_plots(df):
    """Create performance visualization plots"""
    # Set style and font
    plt.style.use('default')
    plt.rcParams['figure.figsize'] = (16, 12)
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['axes.titlepad'] = 15
    
    # Convert times to milliseconds for better readability
    df['processing_time_ms'] = df['processing_time'] * 1000
    
    # Create a figure with subplots
    fig = plt.figure(figsize=(16, 12))
    
    # 1. Histogram with Box Plot
    ax1 = plt.subplot(2, 2, 1)
    plt.hist(df['processing_time_ms'], bins=30, color='skyblue', alpha=0.7, density=True)
    plt.title('Processing Time Distribution', pad=20)
    plt.xlabel('Processing Time (ms)')
    plt.ylabel('Density')
    
    # Add box plot on top of histogram
    ax2 = ax1.twinx()
    ax2.boxplot(df['processing_time_ms'], vert=False, widths=0.7,
                patch_artist=True, 
                boxprops=dict(facecolor="lightgreen", alpha=0.5),
                medianprops=dict(color="red", linewidth=1.5))
    ax2.set_ylim(0.5, 1.5)  # Adjust box plot height
    ax2.set_yticks([])  # Hide y-axis for box plot
    
    # 2. Time series plot
    plt.subplot(2, 2, 2)
    plt.plot(df.index, df['processing_time_ms'], alpha=0.6, color='mediumseagreen', linewidth=1, marker='.', markersize=3)
    plt.title('Processing Time Trend', pad=20)
    plt.xlabel('Request Number')
    plt.ylabel('Processing Time (ms)')
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # 3. CDF plot
    plt.subplot(2, 2, 3)
    sorted_times = np.sort(df['processing_time_ms'])
    cumulative = np.arange(1, len(sorted_times) + 1) / len(sorted_times)
    plt.plot(sorted_times, cumulative, color='coral', linewidth=2, marker='.', markersize=3)
    plt.title('Cumulative Distribution Function (CDF)', pad=20)
    plt.xlabel('Processing Time (ms)')
    plt.ylabel('Cumulative Probability')
    plt.grid(True, alpha=0.3, linestyle='--')
    
    # Add statistics text
    stats_text = (
        f"Performance Statistics:\n\n"
        f"Mean: {df['processing_time_ms'].mean():.2f} ms\n"
        f"Median: {df['processing_time_ms'].median():.2f} ms\n"
        f"Std Dev: {df['processing_time_ms'].std():.2f} ms\n"
        f"Min: {df['processing_time_ms'].min():.2f} ms\n"
        f"Max: {df['processing_time_ms'].max():.2f} ms\n"
        f"90th percentile: {df['processing_time_ms'].quantile(0.90):.2f} ms\n"
        f"95th percentile: {df['processing_time_ms'].quantile(0.95):.2f} ms\n"
        f"99th percentile: {df['processing_time_ms'].quantile(0.99):.2f} ms\n"
        f"Total requests: {len(df)}\n"
        f"Success rate: 100%"
    )
    plt.subplot(2, 2, 4)
    plt.text(0.1, 0.5, stats_text, va='center', family='monospace')
    plt.axis('off')
    
    # Add overall title with more padding
    plt.suptitle('Location Resolver Performance Analysis', y=1.05)
    
    # Adjust layout and save
    plt.tight_layout()
    plt.savefig('performance_analysis.png', dpi=300, bbox_inches='tight')
    print("\nPerformance analysis plots have been saved to 'performance_analysis.png'")

def concurrent_performance_test(num_requests=10000, num_threads=10):
    """複数スレッドを使用した同時リクエストによるパフォーマンステスト"""
    import threading
    # スレッドごとのリクエスト数を計算
    requests_per_thread = num_requests // num_threads
    
    # 結果を格納するための共有データ構造
    results = []
    results_lock = threading.Lock()
    
    # スレッド関数
    def worker(thread_id):
        client = LocationResolverClient(debug=False)
        thread_results = []
        
        try:
            for i in range(requests_per_thread):
                latitude, longitude = generate_random_japan_coordinates()
                start_time = time.time()
                result, _ = client.get_location_info(latitude, longitude)
                end_time = time.time()
                
                thread_results.append({
                    'thread_id': thread_id,
                    'request_number': i + 1,
                    'latitude': latitude,
                    'longitude': longitude,
                    'processing_time': end_time - start_time,
                    'success': result is not None
                })
                
                # 進捗表示（スレッドごとに100リクエストごと）
                if (i + 1) % 100 == 0:
                    print(f"Thread {thread_id}: Completed {i + 1}/{requests_per_thread} requests")
        finally:
            client.close()
            
        # 結果をマージ
        with results_lock:
            results.extend(thread_results)
    
    # 全体の開始時間
    total_start_time = time.time()
    print(f"\nStarting concurrent performance test with {num_threads} threads...")
    print(f"Total requests: {num_requests} ({requests_per_thread} requests per thread)")
    
    # スレッドの作成と開始
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    # すべてのスレッドの終了を待機
    for t in threads:
        t.join()
    
    # 全体の終了時間
    total_end_time = time.time()
    total_time = total_end_time - total_start_time
    
    # 結果の分析と表示
    df = pd.DataFrame(results)
    successful_df = df[df['success']]
    
    # 統計情報の表示
    print(f"\nConcurrent Performance Test Results:")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Requests per second: {len(df) / total_time:.2f}")
    print(f"Average response time: {successful_df['processing_time'].mean()*1000:.2f}ms")
    print(f"Minimum response time: {successful_df['processing_time'].min()*1000:.2f}ms")
    print(f"Maximum response time: {successful_df['processing_time'].max()*1000:.2f}ms")
    print(f"95th percentile: {successful_df['processing_time'].quantile(0.95)*1000:.2f}ms")
    print(f"Success rate: {len(successful_df)}/{len(df)} ({len(successful_df)/len(df)*100:.2f}%)")
    
    # 拡張されたパフォーマンス分析グラフの作成
    create_concurrent_performance_plots(successful_df, num_threads, total_time)

def create_concurrent_performance_plots(df, num_threads, total_time):
    """同時実行テスト用のパフォーマンス分析グラフを作成"""
    
    # 基本的なプロット設定
    plt.style.use('default')
    plt.rcParams['figure.figsize'] = (16, 14)
    plt.rcParams['axes.grid'] = True
    
    # 図の作成
    fig = plt.figure(figsize=(16, 14))
    
    # 1. レスポンスタイム分布
    plt.subplot(3, 2, 1)
    plt.hist(df['processing_time']*1000, bins=30, color='skyblue', alpha=0.7)
    plt.title('Response Time Distribution')
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Frequency')
    
    # 2. スレッドごとのレスポンスタイム
    plt.subplot(3, 2, 2)
    sns.boxplot(x='thread_id', y='processing_time', data=df, palette='Set3')
    plt.title('Response Time by Thread')
    plt.xlabel('Thread ID')
    plt.ylabel('Response Time (s)')
    
    # 3. 時系列でのレスポンスタイム
    plt.subplot(3, 2, 3)
    plt.scatter(range(len(df)), df['processing_time']*1000, alpha=0.5, s=3)
    plt.title('Response Time Over Test Duration')
    plt.xlabel('Request Number')
    plt.ylabel('Response Time (ms)')
    
    # 4. CDF (累積分布関数)
    plt.subplot(3, 2, 4)
    sorted_times = np.sort(df['processing_time']*1000)
    cumulative = np.arange(1, len(sorted_times) + 1) / len(sorted_times)
    plt.plot(sorted_times, cumulative, linewidth=2)
    plt.title('Cumulative Distribution Function (CDF)')
    plt.xlabel('Response Time (ms)')
    plt.ylabel('Cumulative Probability')
    plt.grid(True)
    
    # 5. スレッド数とスループットの関係（理論値）
    plt.subplot(3, 2, 5)
    thread_counts = list(range(1, num_threads + 1))
    throughputs = [min(t, 10) * (len(df) / num_threads) / (total_time / num_threads) for t in thread_counts]
    plt.plot(thread_counts, throughputs, marker='o')
    plt.title('Theoretical Throughput vs Thread Count')
    plt.xlabel('Number of Threads')
    plt.ylabel('Requests per Second')
    
    # 6. 統計情報
    plt.subplot(3, 2, 6)
    stats_text = (
        f"Concurrent Performance Statistics:\n\n"
        f"Total Requests: {len(df)}\n"
        f"Number of Threads: {num_threads}\n"
        f"Total Time: {total_time:.2f} seconds\n"
        f"Throughput: {len(df)/total_time:.2f} req/sec\n\n"
        f"Response Time (ms):\n"
        f"  Mean: {df['processing_time'].mean()*1000:.2f}\n"
        f"  Median: {df['processing_time'].median()*1000:.2f}\n"
        f"  Min: {df['processing_time'].min()*1000:.2f}\n"
        f"  Max: {df['processing_time'].max()*1000:.2f}\n"
        f"  Std Dev: {df['processing_time'].std()*1000:.2f}\n"
        f"  90th %ile: {df['processing_time'].quantile(0.90)*1000:.2f}\n"
        f"  95th %ile: {df['processing_time'].quantile(0.95)*1000:.2f}\n"
        f"  99th %ile: {df['processing_time'].quantile(0.99)*1000:.2f}\n\n"
        f"Success Rate: {df['success'].mean()*100:.2f}%"
    )
    plt.text(0.1, 0.5, stats_text, va='center', family='monospace')
    plt.axis('off')
    
    # 全体タイトル
    plt.suptitle(f'Concurrent Location Resolver Performance Analysis ({num_threads} Threads)', y=1.02, fontsize=16)
    
    # レイアウト調整と保存
    plt.tight_layout()
    plt.savefig('concurrent_performance_analysis.png', dpi=300, bbox_inches='tight')
    print("\nConcurrent performance analysis plots have been saved to 'concurrent_performance_analysis.png'")

def performance_test():
    """従来の逐次実行によるパフォーマンステスト"""
    # テストパラメータ
    num_requests = 1000  # リクエスト回数
    client = LocationResolverClient(debug=False)  # デバッグ出力は無効化
    
    # データを格納するDataFrame
    data = {
        'request_number': [],
        'latitude': [],
        'longitude': [],
        'processing_time': [],
        'success': []
    }

    try:
        print(f"Sending {num_requests} requests with random coordinates in Japan...")
        
        for i in range(num_requests):
            latitude, longitude = generate_random_japan_coordinates()
            result, total_time = client.get_location_info(latitude, longitude)
            
            # データを記録
            data['request_number'].append(i + 1)
            data['latitude'].append(latitude)
            data['longitude'].append(longitude)
            data['processing_time'].append(total_time)
            data['success'].append(result is not None)
            
            if (i + 1) % 100 == 0:  # 進捗表示を100リクエストごとに
                print(f"Completed {i + 1}/{num_requests} requests")

        # DataFrameを作成
        df = pd.DataFrame(data)
        successful_df = df[df['success']]
        
        # 統計情報の表示
        print("\nPerformance Statistics:")
        print(f"Average processing time: {successful_df['processing_time'].mean()*1000:.2f}ms")
        print(f"Minimum processing time: {successful_df['processing_time'].min()*1000:.2f}ms")
        print(f"Maximum processing time: {successful_df['processing_time'].max()*1000:.2f}ms")
        print(f"95th percentile: {successful_df['processing_time'].quantile(0.95)*1000:.2f}ms")
        print(f"Successful requests: {len(successful_df)}/{num_requests}")
        
        # グラフの作成と表示
        create_performance_plots(successful_df)

    finally:
        client.close()

def main():
    """Send a single location request with coordinates"""
    # 東京の座標を使用
    latitude = 35.6895
    longitude = 139.6917
    
    client = LocationResolverClient(debug=True)  # デバッグ出力を有効化
    try:
        result, total_time = client.get_location_info(latitude, longitude)
        if result:
            print(f"\nLocation request completed in {total_time*1000:.2f}ms")
            print(f"Region Code: {result.area_code}")
            # print(f"Weather Server IP: {result['weather_server_ip']}")
        else:
            print("Location request failed")
    finally:
        client.close()

if __name__ == "__main__":
    # サーバーのデータベース接続プール（最大10接続）を考慮して10スレッドを使用
    concurrent_performance_test(num_requests=10000, num_threads=10)
