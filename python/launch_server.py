import threading
import argparse
from WIP_Server import QueryServer, LocationServer, WeatherServer, ReportServer

def main():
    parser = argparse.ArgumentParser(description='WIPサーバー起動スクリプト')
    parser.add_argument('--server', choices=['query', 'location', 'weather', 'report'],
                       help='起動するサーバーを指定 (query, location, weather, report)')
    parser.add_argument('--query', action='store_true', help='Queryサーバーを起動')
    parser.add_argument('--location', action='store_true', help='Locationサーバーを起動')
    parser.add_argument('--weather', action='store_true', help='Weatherサーバーを起動')
    parser.add_argument('--report', action='store_true', help='Reportサーバーを起動')
    parser.add_argument('--debug', action='store_true', help='デバッグモードで起動')
    parser.add_argument('--noupdate', action='store_true', help='Queryサーバーの起動時自動更新をスキップ')
    
    args = parser.parse_args()
    
    # 起動するサーバーを決定
    servers_to_start = []
    
    if args.server:
        # --server オプションが指定された場合
        if args.server == 'query':
            servers_to_start.append('query')
        elif args.server == 'location':
            servers_to_start.append('location')
        elif args.server == 'weather':
            servers_to_start.append('weather')
        elif args.server == 'report':
            servers_to_start.append('report')
    else:
        # 個別のフラグをチェック
        if args.query:
            servers_to_start.append('query')
        if args.location:
            servers_to_start.append('location')
        if args.weather:
            servers_to_start.append('weather')
        if args.report:
            servers_to_start.append('report')
    
    # 何も指定されていない場合は全てのサーバーを起動
    if not servers_to_start:
        servers_to_start = ['query', 'location', 'weather', 'report']
        print("引数が指定されていないため、全てのサーバーを起動します。")
    
    print(f"起動するサーバー: {', '.join(servers_to_start)}")
    
    # サーバーインスタンスとスレッドを格納するリスト
    servers = {}
    threads = []
    
    # デバッグモードの表示
    if args.debug:
        print("デバッグモードが有効です。")
    
    # 選択されたサーバーを起動
    if 'query' in servers_to_start:
        debug_msg = " (デバッグモード)" if args.debug else ""
        print(f"Query Serverを起動しています...{debug_msg}")
        if args.noupdate:
            print("  ※起動時自動更新をスキップします")
        servers['query'] = QueryServer(debug=args.debug, noupdate=args.noupdate)
        query_thread = threading.Thread(target=servers['query'].run, name='QueryServer')
        threads.append(query_thread)
        query_thread.start()
    
    if 'location' in servers_to_start:
        debug_msg = " (デバッグモード)" if args.debug else ""
        print(f"Location Serverを起動しています...{debug_msg}")
        servers['location'] = LocationServer(debug=args.debug)
        location_thread = threading.Thread(target=servers['location'].run, name='LocationServer')
        threads.append(location_thread)
        location_thread.start()
    
    if 'weather' in servers_to_start:
        debug_msg = " (デバッグモード)" if args.debug else ""
        print(f"Weather Serverを起動しています...{debug_msg}")
        servers['weather'] = WeatherServer(debug=args.debug)
        weather_thread = threading.Thread(target=servers['weather'].run, name='WeatherServer')
        threads.append(weather_thread)
        weather_thread.start()
    
    if 'report' in servers_to_start:
        debug_msg = " (デバッグモード)" if args.debug else ""
        print(f"Report Serverを起動しています...{debug_msg}")
        servers['report'] = ReportServer(debug=args.debug)
        report_thread = threading.Thread(target=servers['report'].run, name='ReportServer')
        threads.append(report_thread)
        report_thread.start()
    
    print(f"{len(threads)}個のサーバーが起動しました。")
    print("サーバーを停止するには Ctrl+C を押してください。")
    
    # 全てのスレッドが終了するまで待機
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\nサーバーを停止しています...")

if __name__ == "__main__":
    main()
