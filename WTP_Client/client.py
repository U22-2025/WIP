"""
WTP Client - Weather Server通信用のシンプルなクライアント

NTPモジュールのような設計で、Weather Serverとの通信を簡潔に扱う
インスタンスが座標とエリアコードの状態を管理し、効率的な通信を提供
"""

import sys
import os
import time
from dotenv import load_dotenv
# commonパッケージのパスを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.clients.weather_client import WeatherClient
load_dotenv()

class Client:
    """WTP Client - Weather Server通信用のシンプルなクライアント（状態管理型）"""
    
    def __init__(self, server_ip=os.getenv('WEATHER_SERVER_HOST'), server_port=int(os.getenv('WEATHER_SERVER_PORT')), debug=False, 
                 latitude=None, longitude=None, area_code=None):
        """
        初期化
        
        Args:
            server_ip (str): Weather ServerのIPアドレス（デフォルト: 'localhost'）
            server_port (int): Weather Serverのポート番号（デフォルト: 4110）
            debug (bool): デバッグモードの有効/無効（デフォルト: False）
            latitude (float, optional): 初期緯度
            longitude (float, optional): 初期経度
            area_code (str, optional): 初期エリアコード
        """
        self.server_ip = server_ip
        self.server_port = server_port
        self.debug = debug
        
        # 状態管理用の内部変数
        self._latitude = latitude
        self._longitude = longitude
        self._area_code = area_code
        self._coordinates_changed = True  # 座標変更フラグ
        
        # 内部でWeatherClientを使用
        self._weather_client = WeatherClient(
            host=self.server_ip,
            port=self.server_port,
            debug=self.debug
        )
        
        if self.debug:
            print(f"WTP Client initialized - Server: {self.server_ip}:{self.server_port}")
            print(f"Initial state - Latitude: {self._latitude}, Longitude: {self._longitude}, Area Code: {self._area_code}")
    
    @property
    def latitude(self):
        """緯度を取得"""
        return self._latitude
    
    @latitude.setter
    def latitude(self, value):
        """緯度を設定（座標変更フラグをセット）"""
        if value != self._latitude:
            self._latitude = value
            self._coordinates_changed = True
            if self.debug:
                print(f"Latitude updated: {value}")
    
    @property
    def longitude(self):
        """経度を取得"""
        return self._longitude
    
    @longitude.setter
    def longitude(self, value):
        """経度を設定（座標変更フラグをセット）"""
        if value != self._longitude:
            self._longitude = value
            self._coordinates_changed = True
            if self.debug:
                print(f"Longitude updated: {value}")
    
    @property
    def area_code(self):
        """エリアコードを取得"""
        return self._area_code
    
    @area_code.setter
    def area_code(self, value):
        """エリアコードを設定（手動設定）"""
        if value != self._area_code:
            self._area_code = value
            self._coordinates_changed = False  # 手動設定なので座標変更フラグをクリア
            if self.debug:
                print(f"Area code manually updated: {value}")
    
    def set_coordinates(self, latitude, longitude):
        """
        座標を設定
        
        Args:
            latitude (float): 緯度
            longitude (float): 経度
        """
        self._latitude = latitude
        self._longitude = longitude
        self._coordinates_changed = True
        
        if self.debug:
            print(f"Coordinates updated: ({latitude}, {longitude})")
    
    def get_weather(self, weather=True, temperature=True, precipitation_prob=True, 
                   alerts=False, disaster=False, day=0):
        """
        現在の状態（座標またはエリアコード）から天気情報を取得
        
        Args:
            weather (bool): 天気データを取得するか（デフォルト: True）
            temperature (bool): 気温データを取得するか（デフォルト: True）
            precipitation_prob (bool): 降水確率データを取得するか（デフォルト: True）
            alerts (bool): 警報データを取得するか（デフォルト: False）
            disaster (bool): 災害情報データを取得するか（デフォルト: False）
            day (int): 予報日（0: 今日, 1: 明日, ...）（デフォルト: 0）
            
        Returns:
            dict: 天気情報
            None: 取得失敗時
        """
        # 座標が変更されている場合は座標からエリアコード解決
        if self._coordinates_changed and self._latitude is not None and self._longitude is not None:
            if self.debug:
                print("Coordinates changed, resolving area code first...")
            return self._weather_client.get_weather_by_coordinates(
                latitude=self._latitude,
                longitude=self._longitude,
                weather=weather,
                temperature=temperature,
                precipitation_prob=precipitation_prob,
                alerts=alerts,
                disaster=disaster,
                day=day
            )
        
        # エリアコードが利用可能な場合はエリアコードから取得（効率的）
        if self._area_code is not None:
            if self.debug:
                print(f"Using area code for weather request: {self._area_code}")
            return self._weather_client.get_weather_by_area_code(
                area_code=self._area_code,
                weather=weather,
                temperature=temperature,
                precipitation_prob=precipitation_prob,
                alerts=alerts,
                disaster=disaster,
                day=day
            )
        
        # 座標のみ利用可能な場合は座標から取得
        elif self._latitude is not None and self._longitude is not None:
            if self.debug:
                print(f"Using coordinates for weather request: ({self._latitude}, {self._longitude})")
            return self._weather_client.get_weather_by_coordinates(
                latitude=self._latitude,
                longitude=self._longitude,
                weather=weather,
                temperature=temperature,
                precipitation_prob=precipitation_prob,
                alerts=alerts,
                disaster=disaster,
                day=day
            )
        
        # 座標もエリアコードも設定されていない場合
        else:
            if self.debug:
                print("Error: No coordinates or area code available")
            return None
    
    def get_weather_by_coordinates(self, latitude, longitude, **kwargs):
        """
        指定した座標から天気情報を取得（状態を変更せずに一時的に使用）
        
        Args:
            latitude (float): 緯度
            longitude (float): 経度
            **kwargs: その他のオプション
            
        Returns:
            dict: 天気情報
            None: 取得失敗時
        """
        return self._weather_client.get_weather_by_coordinates(
            latitude=latitude,
            longitude=longitude,
            **kwargs
        )
    
    def get_weather_by_area_code(self, area_code, **kwargs):
        """
        指定したエリアコードから天気情報を取得（状態を変更せずに一時的に使用）
        
        Args:
            area_code (str or int): エリアコード
            **kwargs: その他のオプション
            
        Returns:
            dict: 天気情報
            None: 取得失敗時
        """
        return self._weather_client.get_weather_by_area_code(
            area_code=area_code,
            **kwargs
        )
    
    def get_state(self):
        """
        現在の状態を取得
        
        Returns:
            dict: 現在の状態（latitude, longitude, area_code, coordinates_changed）
        """
        return {
            'latitude': self._latitude,
            'longitude': self._longitude,
            'area_code': self._area_code,
            'coordinates_changed': self._coordinates_changed,
            'server_ip': self.server_ip,
            'server_port': self.server_port
        }
    
    def set_server(self, server_ip, server_port=None):
        """
        Weather Serverの接続情報を変更
        
        Args:
            server_ip (str): 新しいIPアドレス
            server_port (int, optional): 新しいポート番号（指定なしの場合は変更しない）
        """
        self.server_ip = server_ip
        if server_port is not None:
            self.server_port = server_port
            
        # WeatherClientを再初期化
        self._weather_client.close()
        self._weather_client = WeatherClient(
            host=self.server_ip,
            port=self.server_port,
            debug=self.debug
        )
        
        if self.debug:
            print(f"Server updated - New server: {self.server_ip}:{self.server_port}")
    
    def close(self):
        """
        クライアントを終了し、リソースを解放
        """
        self._weather_client.close()
        if self.debug:
            print("WTP Client closed")


def main():
    """使用例"""
    print("WTP Client Example (State Management)")
    print("=" * 50)
    
    # 1. 状態管理型の使用例
    print("\n1. State management example")
    print("-" * 30)
    
    client = Client(debug=True)
    
    try:
        # 座標を設定（自動的にエリアコード解決される）
        client.set_coordinates(latitude=35.6895, longitude=139.6917)
        
        # 状態から天気情報を取得（エリアコードが使用される）
        result = client.get_weather()
        
        if result:
            print("✓ Success!")
            print(f"Area Code: {result['area_code']}")
            print(f"Timestamp: {time.ctime(result['timestamp'])}")
            if 'weather_code' in result:
                print(f"Weather Code: {result['weather_code']}")
            if 'temperature' in result:
                print(f"Temperature: {result['temperature']}°C")
            if 'precipitation_prob' in result:
                print(f"precipitation_prob: {result['precipitation_prob']}%")
        else:
            print("✗ Failed to get weather data")
        
        # 状態確認
        state = client.get_state()
        print(f"\nCurrent state: {state}")
        
    finally:
        client.close()
    
    # 2. エリアコード手動設定例
    print("\n\n2. Manual area code setting example")
    print("-" * 30)
    
    client = Client(debug=True)
    
    try:
        # エリアコードを手動設定
        client.area_code = "011000"  # 札幌
        
        # 状態から天気情報を取得
        result = client.get_weather()
        
        if result:
            print("✓ Success!")
            print(f"Area Code: {result['area_code']}")
            if 'weather_code' in result:
                print(f"Weather Code: {result['weather_code']}")
            if 'temperature' in result:
                print(f"Temperature: {result['temperature']}°C")
            if 'precipitation_prob' in result:
                print(f"precipitation_prob: {result['precipitation_prob']}%")
        else:
            print("✗ Failed to get weather data")
            
    finally:
        client.close()
    
    print("\n" + "="*50)
    print("Example completed")


if __name__ == "__main__":
    main()
