"""
天気パケット - エンドユーザー向けAPI
weather_clientで使用される、使いやすいファクトリーメソッドを提供
"""
from typing import Optional, Dict, Any, Union
from datetime import datetime
from .request import Request
from .response import Response


class WeatherRequest(Request):
    """
    天気情報リクエスト（エンドユーザー向け）
    
    座標やエリアコードから天気情報を要求するための
    使いやすいファクトリーメソッドを提供します。
    """
    
    @classmethod
    def create_by_coordinates(
        cls, 
        latitude: float, 
        longitude: float,
        *,
        packet_id: int,
        weather: bool = True,
        temperature: bool = True,
        precipitation_prob: bool = True,
        alert: bool = False,
        disaster: bool = False,
        day: int = 0,
        version: int = 1
    ) -> 'WeatherRequest':
        """
        座標から天気情報を要求するリクエストを作成（Type 0）
        
        Args:
            latitude: 緯度
            longitude: 経度
            packet_id: パケットID
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation_prob: 降水確率データを取得するか
            alert: 警報データを取得するか
            disaster: 災害情報データを取得するか
            day: 予報日（0: 今日, 1: 明日, ...）
            version: プロトコルバージョン
            
        Returns:
            WeatherRequestインスタンス
            
        Examples:
            >>> request = WeatherRequest.create_by_coordinates(
            ...     latitude=35.6895,
            ...     longitude=139.6917,
            ...     packet_id=123,
            ...     weather=True,
            ...     temperature=True
            ... )
        """
        return cls(
            version=version,
            packet_id=packet_id,
            type=0,  # 座標解決リクエスト
            weather_flag=1 if weather else 0,
            temperature_flag=1 if temperature else 0,
            pop_flag=1 if precipitation_prob else 0,
            alert_flag=1 if alert else 0,
            disaster_flag=1 if disaster else 0,
            ex_flag=1,  # 拡張フィールドを使用
            day=day,
            timestamp=int(datetime.now().timestamp()),
            ex_field={
                "latitude": latitude,
                "longitude": longitude
            }
        )
    
    @classmethod
    def create_by_area_code(
        cls,
        area_code: Union[str, int],
        *,
        packet_id: int,
        weather: bool = True,
        temperature: bool = True,
        precipitation_prob: bool = True,
        alert: bool = False,
        disaster: bool = False,
        day: int = 0,
        version: int = 1
    ) -> 'WeatherRequest':
        """
        エリアコードから天気情報を要求するリクエストを作成（Type 2）
        
        Args:
            area_code: エリアコード（文字列または数値、例: "011000" または 11000）
            packet_id: パケットID
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation_prob: 降水確率データを取得するか
            alert: 警報データを取得するか
            disaster: 災害情報データを取得するか
            day: 予報日（0: 今日, 1: 明日, ...）
            version: プロトコルバージョン
            
        Returns:
            WeatherRequestインスタンス
            
        Examples:
            >>> request = WeatherRequest.create_by_area_code(
            ...     area_code="011000",
            ...     packet_id=456,
            ...     weather=True,
            ...     temperature=True,
            ...     alert=True
            ... )
        """
        # エリアコードを6桁の文字列に正規化
        if isinstance(area_code, int):
            area_code_str = f"{area_code:06d}"
        else:
            area_code_str = str(area_code).zfill(6)
        
        return cls(
            version=version,
            packet_id=packet_id,
            type=2,  # 気象データリクエスト
            weather_flag=1 if weather else 0,
            temperature_flag=1 if temperature else 0,
            pop_flag=1 if precipitation_prob else 0,
            alert_flag=1 if alert else 0,
            disaster_flag=1 if disaster else 0,
            ex_flag=0,  # Type 2では基本的に拡張フィールド不要
            day=day,
            timestamp=int(datetime.now().timestamp()),
            area_code=area_code_str
        )
    
    def get_request_summary(self) -> Dict[str, Any]:
        """
        リクエストの要約情報を取得
        
        Returns:
            リクエストの要約辞書
        """
        summary = {
            'type': 'coordinate_lookup' if self.type == 0 else 'area_code_lookup',
            'packet_id': self.packet_id,
            'day': self.day,
            'requested_data': []
        }
        
        if self.weather_flag:
            summary['requested_data'].append('weather')
        if self.temperature_flag:
            summary['requested_data'].append('temperature')
        if self.pop_flag:
            summary['requested_data'].append('precipitation_prob')
        if self.alert_flag:
            summary['requested_data'].append('alert')
        if self.disaster_flag:
            summary['requested_data'].append('disaster')
        
        if self.type == 0 and self.ex_field:
            summary['latitude'] = self.ex_field.latitude
            summary['longitude'] = self.ex_field.longitude
        elif self.type == 2:
            summary['area_code'] = self.area_code
        
        return summary
    

class WeatherResponse(Response):
    """
    天気情報レスポンス（エンドユーザー向け）
    
    QueryServerから返される気象データ（Type 3）を
    使いやすい形で処理するためのメソッドを提供します。
    """
    
    def get_temperature_celsius(self) -> Optional[int]:
        """
        気温を摂氏で取得
        
        Returns:
            気温（摂氏）またはNone
            
        Examples:
            >>> response = WeatherResponse.from_bytes(data)
            >>> temp = response.get_temperature_celsius()
            >>> print(f"気温: {temp}℃")
        """
        if self.temperature_flag and hasattr(self, 'temperature'):
            return self.temperature - 100
        return None
    
    def get_weather_code(self) -> Optional[int]:
        """
        天気コードを取得
        
        Returns:
            天気コードまたはNone
        """
        if self.weather_flag and hasattr(self, 'weather_code'):
            return self.weather_code
        return None
    
    
    def get_precipitation_prob(self) -> Optional[int]:
        """
        降水確率を取得
        
        Returns:
            降水確率（パーセント）またはNone
        """
        if self.pop_flag and hasattr(self, 'pop'):
            return self.pop
        return None
    
    def get_alert(self) -> Optional[str]:
        """
        警報情報を取得
        
        Returns:
            警報情報（文字列）またはNone
        """
        if self.alert_flag and hasattr(self, 'ex_field') and self.ex_field:
            alert = self.ex_field.alert
            return str(alert) if alert is not None else None
        return None
    
    def get_disaster_info(self) -> Optional[str]:
        """
        災害情報を取得
        
        Returns:
            災害情報（文字列）またはNone
        """
        if self.disaster_flag and hasattr(self, 'ex_field') and self.ex_field:
            disaster = self.ex_field.disaster
            return str(disaster) if disaster is not None else None
        return None
    
    def get_weather_data(self) -> Dict[str, Any]:
        """
        全ての天気データを整形して取得
        
        Returns:
            天気データの辞書
             
        Examples:
            >>> response = WeatherResponse.from_bytes(data)
            >>> data = response.get_weather_data()
            >>> print(f"気温: {data.get('temperature')}℃")
            >>> print(f"天気: {data.get('weather_code')}")
        """
        data = {
            'area_code': self.area_code,
            'timestamp': self.timestamp,
            'day': self.day
        }
        
        # 基本データ
        if self.weather_flag:
            data['weather_code'] = self.get_weather_code()
        
        if self.temperature_flag:
            data['temperature'] = self.get_temperature_celsius()
        
        if self.pop_flag:
            data['precipitation_prob'] = self.get_precipitation_prob()
        
        # 拡張データ
        alert = self.get_alert()
        if alert:
            data['alert'] = alert
        
        disaster = self.get_disaster_info()
        if disaster:
            data['disaster'] = disaster

        # 座標データを追加 (Noneの場合はフィールドを追加しない)
        coordinates = self.get_coordinates()
        if coordinates:
            lat, long = coordinates
            data['latitude'] = lat
            data['longitude'] = long
        
        return data
    
    def is_success(self) -> bool:
        """
        レスポンスが成功かどうかを判定
        
        Returns:
            成功の場合True
        """
        # 基本的な妥当性チェック
        if not self.area_code or self.area_code == "000000":
            return False
        
        # 要求されたデータが少なくとも1つ含まれているかチェック
        has_data = False
        if self.weather_flag and self.get_weather_code() is not None:
            has_data = True
        if self.temperature_flag and self.get_temperature_celsius() is not None:
            has_data = True
        if self.pop_flag and self.get_precipitation_prob() is not None:
            has_data = True
        if self.alert_flag and self.get_alert():
            has_data = True
        if self.disaster_flag and self.get_disaster_info():
            has_data = True
        
        return has_data
    
    def get_response_summary(self) -> Dict[str, Any]:
        """
        レスポンスの要約情報を取得
        
        Returns:
            レスポンスの要約辞書
        """
        return {
            'success': self.is_success(),
            'area_code': self.area_code,
            'packet_id': self.packet_id,
            'data': self.get_weather_data()
        }
    
    @classmethod
    def from_query_response(cls, query_response) -> 'WeatherResponse':
        """
        QueryResponseからWeatherResponseに変換
        
        Args:
            query_response: QueryResponseインスタンス
            
        Returns:
            WeatherResponseインスタンス
            
        Examples:
            >>> query_resp = QueryResponse.from_bytes(data)
            >>> weather_resp = WeatherResponse.from_query_response(query_resp)
        """
        # QueryResponseのバイト列を取得してWeatherResponseで再パース
        query_bytes = query_response.to_bytes()
        return cls.from_bytes(query_bytes)
