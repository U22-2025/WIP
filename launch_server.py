import threading
from WTP_Server import QueryServer, LocationServer, WeatherServer

if __name__ == "__main__":
    # 3つのサーバをそれぞれ別スレッドで起動
    query_server = QueryServer()
    location_server = LocationServer()
    weather_server = WeatherServer()
    
    # 各サーバを別スレッドで実行
    query_thread = threading.Thread(target=query_server.run)
    location_thread = threading.Thread(target=location_server.run)
    weather_thread = threading.Thread(target=weather_server.run)
    
    # スレッドの開始
    query_thread.start()
    location_thread.start()
    weather_thread.start()
    
    # メインスレッドが終了しないようにする
    query_thread.join()
    location_thread.join()
    weather_thread.join()
