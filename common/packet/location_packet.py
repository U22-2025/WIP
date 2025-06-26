"""
位置パケット - サーバー間通信専用
weather_server ← → location_server間の通信で使用
"""
from typing import Optional, Dict, Any, Union
from datetime import datetime
from .request import Request
from .response import Response


class LocationRequest(Request):
    """
    位置解決リクエスト（サーバー間通信専用）
    
    座標からエリアコードを解決するための内部通信用パケット。
    主にweather_serverからlocation_serverへの通信で使用されます。
    """
    
    @classmethod
    def create_coordinate_lookup(
        cls,
        latitude: float,
        longitude: float,
        *,
        packet_id: int,
        source: Optional[str] = None,
        preserve_flags: Optional[Dict[str, int]] = None,
        day: int = 0,
        version: int = 1
    ) -> 'LocationRequest':
        """
        座標からエリアコードを検索するリクエストを作成（Type 0）
        
        Args:
            latitude: 緯度
            longitude: 経度
            packet_id: パケットID
            source: 送信元情報（プロキシルーティング用）
            preserve_flags: 元のリクエストのフラグを保持
            day: 予報日
            version: プロトコルバージョン
            
        Returns:
            LocationRequestインスタンス
            
        Examples:
            >>> # プロキシサーバーでの使用例
            >>> request = LocationRequest.create_coordinate_lookup(
            ...     latitude=35.6895,
            ...     longitude=139.6917,
            ...     packet_id=123,
            ...     source=("192.168.1.100", 12345),
            ...     preserve_flags={
            ...         'weather_flag': 1,
            ...         'temperature_flag': 1,
            ...         'pop_flag': 1
            ...     }
            ... )
        """
        # 拡張フィールドを準備
        ex_field = {
            "latitude": latitude,
            "longitude": longitude
        }
        
        # source情報があれば追加
        if source:
            ex_field["source"] = source
        
        # フラグを設定（preserve_flagsがある場合はそれを使用、なければデフォルト）
        flags = preserve_flags or {}
        
        return cls(
            version=version,
            packet_id=packet_id,
            type=0,  # 座標解決リクエスト
            weather_flag=flags.get('weather_flag', 0),
            temperature_flag=flags.get('temperature_flag', 0),
            pop_flag=flags.get('pop_flag', 0),
            alert_flag=flags.get('alert_flag', 0),
            disaster_flag=flags.get('disaster_flag', 0),
            ex_flag=1,  # 拡張フィールドを使用
            day=day,
            timestamp=int(datetime.now().timestamp()),
            ex_field=ex_field
        )
    
    @classmethod
    def from_weather_request(
        cls,
        weather_request: Request,
        source: Optional[str] = None
    ) -> 'LocationRequest':
        """
        WeatherRequestからLocationRequestを作成
        
        Args:
            weather_request: 元のWeatherRequest（Type 0）
            source: 追加する送信元情報
            
        Returns:
            LocationRequestインスタンス
        """
        # 元のリクエストの拡張フィールドを取得
        latitude = weather_request.ex_field.get('latitude') if weather_request.ex_field else None
        longitude = weather_request.ex_field.get('longitude') if weather_request.ex_field else None
        
        if latitude is None or longitude is None:
            raise ValueError("Weather request must contain latitude and longitude")
        
        # フラグを保持
        preserve_flags = {
            'weather_flag': weather_request.weather_flag,
            'temperature_flag': weather_request.temperature_flag,
            'pop_flag': weather_request.pop_flag,
            'alert_flag': weather_request.alert_flag,
            'disaster_flag': weather_request.disaster_flag
        }
        
        return cls.create_coordinate_lookup(
            latitude=latitude,
            longitude=longitude,
            packet_id=weather_request.packet_id,
            source=source,
            preserve_flags=preserve_flags,
            day=weather_request.day,
            version=weather_request.version
        )
    
    def get_coordinates(self) -> Optional[tuple[float, float]]:
        """
        座標を取得
        
        Returns:
            (latitude, longitude) のタプルまたはNone
        """
        if self.ex_field:
            lat = self.ex_field.get('latitude')
            lon = self.ex_field.get('longitude')
            if lat is not None and lon is not None:
                return (lat, lon)
        return None
    
    def get_source_info(self) -> Optional[str]:
        """
        送信元情報を取得
        
        Returns:
            送信元情報またはNone
        """
        if self.ex_field:
            return self.ex_field.get('source')
        return None


class LocationResponse(Response):
    """
    位置解決レスポンス（サーバー間通信専用）
    
    location_serverからの応答（Type 1）を処理します。
    主にエリアコード解決の結果を含みます。
    """
    
    @classmethod
    def create_area_code_response(
        cls,
        request: LocationRequest,
        area_code: Union[str, int],
        version: int = 1
    ) -> 'LocationResponse':
        """
        エリアコード解決結果のレスポンスを作成（Type 1）
        
        Args:
            request: 元のLocationRequest
            area_code: 解決されたエリアコード
            version: プロトコルバージョン
            
        Returns:
            LocationResponseインスタンス
        """
        # エリアコードを数値に変換
        if isinstance(area_code, str):
            area_code_int = int(area_code)
        else:
            area_code_int = int(area_code)
        
        # 拡張フィールドの準備（sourceのみ引き継ぐ）
        ex_field = {}
        source = request.get_source_info()
        if source:
            ex_field["source"] = source
        
        return cls(
            version=version,
            packet_id=request.packet_id,
            type=1,  # 位置解決レスポンス
            weather_flag=request.weather_flag,
            temperature_flag=request.temperature_flag,
            pop_flag=request.pop_flag,
            alert_flag=request.alert_flag,
            disaster_flag=request.disaster_flag,
            ex_flag=1 if ex_field else 0,
            day=request.day,
            timestamp=int(datetime.now().timestamp()),
            area_code=area_code_int,
            ex_field=ex_field if ex_field else None
        )
    
    def get_area_code(self) -> str:
        """
        エリアコードを6桁の文字列として取得
        
        Returns:
            6桁のエリアコード文字列
        """
        return self.area_code
    
    def get_source_info(self) -> Optional[str]:
        """
        送信元情報を取得（プロキシルーティング用）
        
        Returns:
            送信元情報またはNone
        """
        if hasattr(self, 'ex_field') and self.ex_field:
            return self.ex_field.get('source')
        return None
    
    def get_preserved_flags(self) -> Dict[str, int]:
        """
        保持されたフラグ情報を取得
        
        Returns:
            フラグ情報の辞書
        """
        return {
            'weather_flag': self.weather_flag,
            'temperature_flag': self.temperature_flag,
            'pop_flag': self.pop_flag,
            'alert_flag': self.alert_flag,
            'disaster_flag': self.disaster_flag
        }
    
    def to_weather_request(self, request_type: int = 2) -> Request:
        """
        このLocationResponseからWeatherRequest（Type 2）を生成
        
        Args:
            request_type: リクエストタイプ（通常は2）
            
        Returns:
            新しいRequestインスタンス
        """
        # 拡張フィールドの準備
        ex_field = {}
        source = self.get_source_info()
        if source:
            ex_field["source"] = source
        
        return Request(
            version=self.version,
            packet_id=self.packet_id,
            type=request_type,
            weather_flag=self.weather_flag,
            temperature_flag=self.temperature_flag,
            pop_flag=self.pop_flag,
            alert_flag=self.alert_flag,
            disaster_flag=self.disaster_flag,
            ex_flag=1 if ex_field else 0,
            day=self.day,
            timestamp=int(datetime.now().timestamp()),
            area_code=self.area_code,
            ex_field=ex_field if ex_field else None
        )
    
    def is_valid(self) -> bool:
        """
        レスポンスが有効かどうかを判定
        
        Returns:
            有効な場合True
        """
        # エリアコードが有効かチェック
        if not self.area_code or self.area_code == "000000":
            return False
        
        # タイプが1かチェック
        if self.type != 1:
            return False
        
        return True
    
    def get_response_summary(self) -> Dict[str, Any]:
        """
        レスポンスの要約情報を取得
        
        Returns:
            レスポンスの要約辞書
        """
        return {
            'type': 'location_response',
            'valid': self.is_valid(),
            'area_code': self.get_area_code(),
            'packet_id': self.packet_id,
            'source': self.get_source_info(),
            'preserved_flags': self.get_preserved_flags()
        }
