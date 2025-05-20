import requests
import time
import threading
import random
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def generate_random_coordinates():
    """世界の主要都市付近のランダムな座標を生成"""
    regions = [
        {'lat': (35.0, 36.0), 'lon': (139.0, 140.0)},  # 東京付近
        {'lat': (40.0, 41.0), 'lon': (-74.0, -73.0)},  # ニューヨーク付近
        {'lat': (51.0, 52.0), 'lon': (-0.5, 0.5)},     # ロンドン付近
        {'lat': (48.0, 49.0), 'lon': (2.0, 3.0)},      # パリ付近
        {'lat': (39.0, 40.0), 'lon': (116.0, 117.0)},  # 北京付近
    ]
    region = random.choice(regions)
    latitude = random.uniform(region['lat'][0], region['lat'][1])
    longitude = random.uniform(region['lon'][0], region['lon'][1])
    return latitude, longitude

def create_api_performance_plots(df, num_threads, total_time, api_name):
    """APIパフォーマンス分析用のグラフを作成"""
    plt.style.use('default')
    plt.rcParams['figure.figsize'] = (16, 14)
    plt.rcParams['axes.grid'] = True
    
    fig = plt.figure(figsize=(16, 14))
    
    # 1. レスポンスタイム分布
    plt.subplot(3, 2, 1)
    plt.hist(df['processing_time']*1000, bins=20, color='skyblue', alpha=0.7)
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
    plt.scatter(range(len(df)), df['processing_time']*1000, alpha=0.5, s=30)
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
    
    # 5. 座標分布またはリクエスト分布
    plt.subplot(3, 2, 5)
    if 'latitude' in df.columns and 'longitude' in df.columns:
        plt.scatter(df['longitude'], df['latitude'], alpha=0.5, c=df['processing_time']*1000, cmap='viridis')
        plt.colorbar(label='Response Time (ms)')
        plt.title('Geographic Distribution of Response Times')
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
    else:
        # 座標がない場合は別の可視化を表示
        plt.hist(df['processing_time']*1000, bins=30, color='lightgreen', alpha=0.7)
        plt.title('Detailed Response Time Distribution')
        plt.xlabel('Response Time (ms)')
        plt.ylabel('Frequency')
    
    # 6. 統計情報
    plt.subplot(3, 2, 6)
    stats_text = (
        f"API Performance Statistics:\n\n"
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
    
    plt.suptitle(f'{api_name} API Performance Analysis', y=1.02, fontsize=16)
    plt.tight_layout()
    
    # APIドメインに基づいてファイル名を設定
    filename = f"{api_name.lower().replace('.', '_')}_performance_analysis.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"\nAPI performance analysis plots have been saved to '{filename}'")

def concurrent_api_test_open_meteo(num_requests=100, num_threads=5):
    """Open-Meteo APIの同時実行パフォーマンステスト"""
    results = []
    results_lock = threading.Lock()
    
    def worker(thread_id):
        thread_results = []
        for i in range(num_requests // num_threads):
            latitude, longitude = generate_random_coordinates()
            url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
            
            start_time = time.time()
            try:
                response = requests.get(url)
                success = response.status_code == 200
                if success:
                    response.json()
            except Exception as e:
                print(f"Error in thread {thread_id}: {e}")
                success = False
            end_time = time.time()
            
            thread_results.append({
                'thread_id': thread_id,
                'request_number': i + 1,
                'latitude': latitude,
                'longitude': longitude,
                'processing_time': end_time - start_time,
                'success': success
            })
            
            if (i + 1) % 5 == 0:
                print(f"Thread {thread_id}: Completed {i + 1}/{num_requests // num_threads} requests")
            time.sleep(0.1)
        
        with results_lock:
            results.extend(thread_results)
    
    run_concurrent_test("Open-Meteo", worker, results, num_requests, num_threads)

def concurrent_api_test_wttr(num_requests=100, num_threads=5):
    """wttr.in APIの同時実行パフォーマンステスト"""
    results = []
    results_lock = threading.Lock()
    
    def worker(thread_id):
        thread_results = []
        for i in range(num_requests // num_threads):
            url = "https://wttr.in/Tokyo?format=j1"
            
            start_time = time.time()
            try:
                response = requests.get(url)
                success = response.status_code == 200
                if success:
                    response.json()
            except Exception as e:
                print(f"Error in thread {thread_id}: {e}")
                success = False
            end_time = time.time()
            
            thread_results.append({
                'thread_id': thread_id,
                'request_number': i + 1,
                'processing_time': end_time - start_time,
                'success': success
            })
            
            if (i + 1) % 5 == 0:
                print(f"Thread {thread_id}: Completed {i + 1}/{num_requests // num_threads} requests")
            time.sleep(0.1)
        
        with results_lock:
            results.extend(thread_results)
    
    run_concurrent_test("wttr.in", worker, results, num_requests, num_threads)

def concurrent_api_test_met_no(num_requests=100, num_threads=5):
    """met.no APIの同時実行パフォーマンステスト"""
    results = []
    results_lock = threading.Lock()
    
    def worker(thread_id):
        thread_results = []
        headers = {
            'User-Agent': 'WTPWeatherApp/1.0 (szk27@outlook.jp)'  # met.noはUser-Agentが必須
        }
        for i in range(num_requests // num_threads):
            url = "https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=35.68&lon=139.76"
            
            start_time = time.time()
            try:
                response = requests.get(url, headers=headers)
                success = response.status_code == 200
                if success:
                    response.json()
            except Exception as e:
                print(f"Error in thread {thread_id}: {e}")
                success = False
            end_time = time.time()
            
            thread_results.append({
                'thread_id': thread_id,
                'request_number': i + 1,
                'processing_time': end_time - start_time,
                'success': success
            })
            
            if (i + 1) % 5 == 0:
                print(f"Thread {thread_id}: Completed {i + 1}/{num_requests // num_threads} requests")
            time.sleep(0.1)
        
        with results_lock:
            results.extend(thread_results)
    
    run_concurrent_test("met.no", worker, results, num_requests, num_threads)

def run_concurrent_test(api_name, worker_func, results, num_requests, num_threads):
    """共通の同時実行テストロジック"""
    print(f"\nStarting concurrent {api_name} API test with {num_threads} threads...")
    print(f"Total requests: {num_requests} ({num_requests // num_threads} requests per thread)")
    
    total_start_time = time.time()
    
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker_func, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    total_time = time.time() - total_start_time
    
    df = pd.DataFrame(results)
    successful_df = df[df['success']]
    
    print(f"\n{api_name} API Performance Test Results:")
    print(f"Total execution time: {total_time:.2f} seconds")
    print(f"Requests per second: {len(df) / total_time:.2f}")
    print(f"Average response time: {successful_df['processing_time'].mean()*1000:.2f}ms")
    print(f"Minimum response time: {successful_df['processing_time'].min()*1000:.2f}ms")
    print(f"Maximum response time: {successful_df['processing_time'].max()*1000:.2f}ms")
    print(f"95th percentile: {successful_df['processing_time'].quantile(0.95)*1000:.2f}ms")
    print(f"Success rate: {len(successful_df)}/{len(df)} ({len(successful_df)/len(df)*100:.2f}%)")
    
    create_api_performance_plots(successful_df, num_threads, total_time, api_name)

if __name__ == "__main__":
    # 外部APIなので少なめのリクエスト数とスレッド数で実行
    num_requests = 50  # 各APIに対して50リクエスト
    num_threads = 5    # 5スレッドで並行実行
    
    # 各APIのテストを実行
    concurrent_api_test_open_meteo(num_requests, num_threads)
    concurrent_api_test_wttr(num_requests, num_threads)
    concurrent_api_test_met_no(num_requests, num_threads)
