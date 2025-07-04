"""
Weather Request用の設定クラス
WeatherClientで使用するリクエスト設定をまとめて管理
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class Coordinates:
    """座標情報を格納するクラス"""
    latitude: float
    longitude: float
    
    def __post_init__(self):
        """座標の妥当性チェック"""
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"緯度は-90〜90の範囲である必要があります: {self.latitude}")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"経度は-180〜180の範囲である必要があります: {self.longitude}")


@dataclass
class WeatherRequestFlags:
    """天気リクエストのフラグ設定を格納するクラス"""
    weather: bool = True
    temperature: bool = True
    precipitation_prob: bool = True
    alert: bool = False
    disaster: bool = False
    
    @classmethod
    def basic_weather(cls) -> 'WeatherRequestFlags':
        """基本的な天気情報のみを取得する設定"""
        return cls(
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=False,
            disaster=False
        )
    
    @classmethod
    def full_weather(cls) -> 'WeatherRequestFlags':
        """すべての天気情報を取得する設定"""
        return cls(
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=True,
            disaster=True
        )
    
    @classmethod
    def minimal_weather(cls) -> 'WeatherRequestFlags':
        """最小限の天気情報を取得する設定"""
        return cls(
            weather=True,
            temperature=False,
            precipitation_prob=False,
            alert=False,
            disaster=False
        )


@dataclass
class WeatherRequestConfig:
    """天気リクエストの完全な設定を格納するクラス"""
    coordinates: Coordinates
    flags: WeatherRequestFlags
    day: int = 0
    
    def __post_init__(self):
        """設定の妥当性チェック"""
        if self.day < 0:
            raise ValueError(f"dayは0以上である必要があります: {self.day}")
    
    @classmethod
    def create_basic(cls, latitude: float, longitude: float, day: int = 0) -> 'WeatherRequestConfig':
        """基本的な設定でWeatherRequestConfigを作成"""
        return cls(
            coordinates=Coordinates(latitude, longitude),
            flags=WeatherRequestFlags.basic_weather(),
            day=day
        )
    
    @classmethod
    def create_full(cls, latitude: float, longitude: float, day: int = 0) -> 'WeatherRequestConfig':
        """全ての情報を取得する設定でWeatherRequestConfigを作成"""
        return cls(
            coordinates=Coordinates(latitude, longitude),
            flags=WeatherRequestFlags.full_weather(),
            day=day
        )


@dataclass 
class AreaCodeRequestConfig:
    """エリアコードベースのリクエスト設定"""
    area_code: str
    flags: WeatherRequestFlags
    day: int = 0
    
    def __post_init__(self):
        """設定の妥当性チェック"""
        if self.day < 0:
            raise ValueError(f"dayは0以上である必要があります: {self.day}")
        if not self.area_code or len(self.area_code) != 6:
            raise ValueError(f"エリアコードは6桁である必要があります: {self.area_code}")
    
    @classmethod
    def create_basic(cls, area_code: str, day: int = 0) -> 'AreaCodeRequestConfig':
        """基本的な設定でAreaCodeRequestConfigを作成"""
        return cls(
            area_code=area_code,
            flags=WeatherRequestFlags.basic_weather(),
            day=day
        )
    
    @classmethod
    def create_full(cls, area_code: str, day: int = 0) -> 'AreaCodeRequestConfig':
        """全ての情報を取得する設定でAreaCodeRequestConfigを作成"""
        return cls(
            area_code=area_code,
            flags=WeatherRequestFlags.full_weather(),
            day=day
        )


# 便利な事前定義済み座標
class CommonLocations:
    """よく使用される場所の座標定義"""
    
    TOKYO = Coordinates(35.6895, 139.6917)
    OSAKA = Coordinates(34.6937, 135.5023)
    KYOTO = Coordinates(35.0116, 135.7681)
    YOKOHAMA = Coordinates(35.4437, 139.6380)
    NAGOYA = Coordinates(35.1815, 136.9066)
    SAPPORO = Coordinates(43.0642, 141.3469)
    FUKUOKA = Coordinates(33.5904, 130.4017)
    SENDAI = Coordinates(38.2682, 140.8694)