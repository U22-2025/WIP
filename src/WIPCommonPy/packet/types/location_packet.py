"""
位置パケット - サーバー間通信専用
weather_server ← → location_server間の通信で使用
"""

from typing import Optional, Dict, Any, Union
from datetime import datetime
from ..models.request import Request
from ..models.response import Response


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
        weather: bool = True,
        temperature: bool = True,
        precipitation_prob: bool = True,
        alert: bool = False,
        disaster: bool = False,
        source: Optional[tuple[str, int]] = None,
        day: int = 0,
        version: int = 1,
    ) -> "LocationRequest":
        """
        座標からエリアコードを検索するリクエストを作成（Type 0）

        Args:
            latitude: 緯度
            longitude: 経度
            packet_id: パケットID
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation_prob: 降水確率データを取得するか
            alert: 警報データを取得するか
            disaster: 災害情報データを取得するか
            source: 送信元情報 (ip, port) のタプル
            day: 予報日
            version: プロトコルバージョン

        Returns:
            LocationRequestインスタンス

        Examples:
            >>> # クライアントでの使用例
            >>> request = LocationRequest.create_coordinate_lookup(
            ...     latitude=35.6895,
            ...     longitude=139.6917,
            ...     packet_id=123,
            ...     weather=True,
            ...     temperature=True,
            ...     precipitation_prob=True,
            ...     alert=False,
            ...     disaster=False
            ... )
        """
        # 拡張フィールドを準備
        ex_field = {"latitude": latitude, "longitude": longitude}

        # source情報があれば追加
        if source:
            ex_field["source"] = source

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
            ex_field=ex_field,
        )

    def get_coordinates(self) -> Optional[tuple[float, float]]:
        """
        拡張フィールドから緯度経度を取得する

        Returns:
            緯度経度のタプル (latitude, longitude)、存在しない場合はNone
        """
        if hasattr(self, "ex_field") and self.ex_field:
            try:
                ex_dict = self.ex_field.to_dict()
                if "latitude" in ex_dict and "longitude" in ex_dict:
                    return (float(ex_dict["latitude"]), float(ex_dict["longitude"]))
            except Exception:
                pass
        return None

    def get_source_info(self) -> Optional[tuple[str, int]]:
        """
        送信元情報を取得

        Returns:
            送信元情報 (ip, port) のタプルまたはNone
        """
        if self.ex_field:
            return self.ex_field.source
        return None


class LocationResponse(Response):
    """
    位置解決レスポンス（サーバー間通信専用）

    location_serverからの応答（Type 1）を処理します。
    主にエリアコード解決の結果を含みます。
    """

    @classmethod
    def create_area_code_response(
        cls, request: LocationRequest, area_code: Union[str, int], version: int = 1
    ) -> "LocationResponse":
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
        latitude, longitude = request.get_coordinates()
        if source:
            ex_field["source"] = source
        if latitude:
            ex_field["latitude"] = latitude
        if longitude:
            ex_field["longitude"] = longitude

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
            ex_field=ex_field if ex_field else None,
        )

    def get_area_code(self) -> str:
        """
        エリアコードを6桁の文字列として取得

        Returns:
            6桁のエリアコード文字列
        """
        return self.area_code

    def get_coordinates(self) -> Optional[tuple[float, float]]:
        """
        拡張フィールドから緯度経度を取得する

        Returns:
            緯度経度のタプル (latitude, longitude)、存在しない場合はNone
        """
        if hasattr(self, "ex_field") and self.ex_field:
            try:
                ex_dict = self.ex_field.to_dict()
                if "latitude" in ex_dict and "longitude" in ex_dict:
                    return (float(ex_dict["latitude"]), float(ex_dict["longitude"]))
            except Exception:
                pass
        return None

    def get_source_info(self) -> Optional[tuple[str, int]]:
        """
        送信元情報を取得（プロキシルーティング用）

        Returns:
            送信元情報 (ip, port) のタプルまたはNone
        """
        if hasattr(self, "ex_field") and self.ex_field:
            return self.ex_field.source
        return None

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
            "type": "location_response",
            "valid": self.is_valid(),
            "area_code": self.get_area_code(),
            "packet_id": self.packet_id,
            "source": self.get_source_info(),
            "weather_flag": bool(self.weather_flag),
            "temperature_flag": bool(self.temperature_flag),
            "pop_flag": bool(self.pop_flag),
            "alert_flag": bool(self.alert_flag),
            "disaster_flag": bool(self.disaster_flag),
            "ex_flag": bool(self.ex_flag),
        }
