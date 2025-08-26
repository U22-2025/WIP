"""
クエリパケット - サーバー間通信専用
weather_server ← → query_server間の通信で使用
"""

from typing import Optional, Dict, Any, Union, List
from datetime import datetime
from WIPCommonPy.packet.models.request import Request
from WIPCommonPy.packet.models.response import Response


class QueryRequest(Request):
    """
    気象データクエリリクエスト（サーバー間通信専用）

    エリアコードから気象データを取得するための内部通信用パケット。
    主にweather_serverからquery_serverへの通信で使用されます。
    """

    @classmethod
    def create_query_request(
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
        source: Optional[tuple[str, int]] = None,
        version: int = 1,
    ) -> "QueryRequest":
        """
        気象データ取得リクエストを作成（Type 2）

        Args:
            area_code: エリアコード（文字列または数値）
            packet_id: パケットID
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation_prob: 降水確率データを取得するか
            alert: 警報データを取得するか
            disaster: 災害情報データを取得するか
            day: 予報日
            source: 送信元情報 (ip, port) のタプル
            version: プロトコルバージョン

        Returns:
            QueryRequestインスタンス

        Examples:
            >>> # クライアントでの使用例
            >>> request = QueryRequest.create_weather_data_request(
            ...     area_code="011000",
            ...     packet_id=123,
            ...     weather=True,
            ...     temperature=True,
            ...     source=("192.168.1.100", 12345)
            ... )
        """
        # エリアコードを6桁の文字列に正規化
        if isinstance(area_code, int):
            area_code_str = f"{area_code:06d}"
        else:
            area_code_str = str(area_code).zfill(6)

        # 拡張フィールドの準備
        ex_field = {}
        if source:
            ex_field["source"] = source

        return cls(
            version=version,
            packet_id=packet_id,
            type=2,  # 気象データリクエスト
            weather_flag=1 if weather else 0,
            temperature_flag=1 if temperature else 0,
            pop_flag=1 if precipitation_prob else 0,
            alert_flag=1 if alert else 0,
            disaster_flag=1 if disaster else 0,
            ex_flag=1 if ex_field else 0,
            day=day,
            timestamp=int(datetime.now().timestamp()),
            area_code=area_code_str,
            ex_field=ex_field if ex_field else None,
        )

    @classmethod
    def from_location_response(
        cls, location_response: Response, source: Optional[tuple[str, int]] = None
    ) -> "QueryRequest":
        """
        LocationResponseからQueryRequestを作成

        Args:
            location_response: LocationResponse（Type 1）
            source: 追加する送信元情報 (ip, port) のタプル

        Returns:
            QueryRequestインスタンス
        """
        # source情報を取得（引数優先）
        final_source = source or location_response.get_source_info()

        return cls.create_query_request(
            area_code=location_response.area_code,
            packet_id=location_response.packet_id,
            weather=bool(location_response.weather_flag),
            temperature=bool(location_response.temperature_flag),
            precipitation_prob=bool(location_response.pop_flag),
            alert=bool(location_response.alert_flag),
            disaster=bool(location_response.disaster_flag),
            day=location_response.day,
            source=final_source,
            version=location_response.version,
        )

    def get_source_info(self) -> Optional[tuple[str, int]]:
        """
        送信元情報を取得

        Returns:
            送信元情報 (ip, port) のタプルまたはNone
        """
        if hasattr(self, "ex_field") and self.ex_field:
            return self.ex_field.source
        return None

    def get_requested_data_types(self) -> List[str]:
        """
        要求されたデータタイプのリストを取得

        Returns:
            データタイプのリスト
        """
        types = []
        if self.weather_flag:
            types.append("weather")
        if self.temperature_flag:
            types.append("temperature")
        if self.pop_flag:
            types.append("precipitation_prob")
        if self.alert_flag:
            types.append("alert")
        if self.disaster_flag:
            types.append("disaster")
        return types


class QueryResponse(Response):
    """
    気象データクエリレスポンス（サーバー間通信専用）

    query_serverからの応答（Type 3）を処理します。
    主に気象データの取得結果を含みます。
    """

    @classmethod
    def create_query_response(
        cls,
        request: QueryRequest,
        weather_data: Optional[Dict[str, Any]] = None,
        version: int = 1,
    ) -> "QueryResponse":
        """
        気象データのレスポンスを作成（Type 3）

        Args:
            request: 元のQueryRequest
            weather_data: 気象データの辞書
            version: プロトコルバージョン

        Returns:
            QueryResponseインスタンス

        Examples:
            >>> weather_data = {
            ...     'weather': 100,
            ...     'temperature': 25,
            ...     'precipitation_prob': 30,
            ...     'alert': ['大雨警報'],
            ...     'disaster': ['土砂災害警戒']
            ... }
            >>> response = QueryResponse.create_weather_data_response(
            ...     request=query_request,
            ...     weather_data=weather_data
            ... )
        """
        # 拡張フィールドの準備
        ex_field = {}
        source = request.get_source_info()
        if source:
            ex_field["source"] = source

        # 気象データを設定（デフォルト値で初期化）
        weather_code = 0
        temperature = 100  # 0℃ (実際の温度 + 100)
        pop = 0

        if weather_data:
            # 天気コード
            if request.weather_flag and "weather" in weather_data:
                weather_value = weather_data["weather"]
                if isinstance(weather_value, list):
                    weather_code = int(weather_value[0]) if weather_value else 0
                else:
                    weather_code = int(weather_value) if weather_value else 0

            # 気温
            if request.temperature_flag and "temperature" in weather_data:
                temp_data = weather_data["temperature"]
                if isinstance(temp_data, list):
                    actual_temp = int(temp_data[0]) if temp_data else 25
                else:
                    actual_temp = int(temp_data) if temp_data else 25
                temperature = actual_temp + 100  # パケットフォーマット変換

            # 降水確率
            if request.pop_flag and "precipitation_prob" in weather_data:
                pop_value = weather_data["precipitation_prob"]
                if isinstance(pop_value, list):
                    pop = int(pop_value[0]) if pop_value else 0
                else:
                    pop = int(pop_value) if pop_value else 0

            # 警報・災害情報を拡張フィールドに追加
            if request.alert_flag and "alert" in weather_data:
                ex_field["alert"] = weather_data["alert"]

            if request.disaster_flag and "disaster" in weather_data:
                ex_field["disaster"] = weather_data["disaster"]

        return cls(
            version=version,
            packet_id=request.packet_id,
            type=3,  # 気象データレスポンス
            weather_flag=request.weather_flag,
            temperature_flag=request.temperature_flag,
            pop_flag=request.pop_flag,
            alert_flag=request.alert_flag,
            disaster_flag=request.disaster_flag,
            ex_flag=1 if ex_field else 0,
            day=request.day,
            timestamp=int(datetime.now().timestamp()),
            area_code=request.area_code,
            weather_code=weather_code,
            temperature=temperature,
            pop=pop,
            ex_field=ex_field if ex_field else None,
        )

    def get_source_info(self) -> Optional[tuple[str, int]]:
        """
        送信元情報を取得（プロキシルーティング用）

        Returns:
            送信元情報 (ip, port) のタプルまたはNone
        """
        if hasattr(self, "ex_field") and self.ex_field:
            return self.ex_field.source
        return None

    def get_temperature(self) -> Optional[int]:
        """
        気温を摂氏で取得

        Returns:
            気温（摂氏）またはNone
        """
        if self.temperature_flag and hasattr(self, "temperature"):
            return self.temperature - 100
        return None

    def get_weather_code(self) -> Optional[int]:
        """
        天気コードを取得

        Returns:
            天気コードまたはNone
        """
        if self.weather_flag and hasattr(self, "weather_code"):
            return self.weather_code
        return None

    def get_precipitation_prob(self) -> Optional[int]:
        """
        降水確率を取得

        Returns:
            降水確率（パーセント）またはNone
        """
        if self.pop_flag and hasattr(self, "pop"):
            return self.pop
        return None

    # 後方互換性のためのエイリアス
    def get_precipitation(self) -> Optional[int]:
        """降水確率を取得（後方互換性のため）"""
        return self.get_precipitation_prob()

    def get_alert(self) -> List[str]:
        """
        警報情報を取得

        Returns:
            警報情報のリスト
        """
        if self.alert_flag and hasattr(self, "ex_field") and self.ex_field:
            alert = self.ex_field.alert if hasattr(self.ex_field, "alert") else []
            return alert if isinstance(alert, list) else [alert] if alert else []
        return []

    def get_disaster_info(self) -> List[str]:
        """
        災害情報を取得

        Returns:
            災害情報のリスト
        """
        if self.disaster_flag and hasattr(self, "ex_field") and self.ex_field:
            disaster = (
                self.ex_field.disaster if hasattr(self.ex_field, "disaster") else []
            )
            return (
                disaster
                if isinstance(disaster, list)
                else [disaster] if disaster else []
            )
        return []

    def get_weather_data(self) -> Dict[str, Any]:
        """
        全ての気象データを取得

        Returns:
            気象データの辞書
        """
        data = {
            "area_code": self.area_code,
            "timestamp": self.timestamp,
            "day": self.day,
        }

        # 基本データ
        if self.weather_flag:
            data["weather_code"] = self.get_weather_code()

        if self.temperature_flag:
            data["temperature"] = self.get_temperature()

        if self.pop_flag:
            data["precipitation_prob"] = self.get_precipitation()

        # 拡張データ
        alert = self.get_alert()
        if alert:
            data["alert"] = alert

        disaster_info = self.get_disaster_info()
        if disaster_info:
            data["disaster"] = disaster_info

        return data

    def is_success(self) -> bool:
        """
        レスポンスが成功かどうかを判定

        Returns:
            成功の場合True
        """
        # エリアコードが有効かチェック
        if not self.area_code or self.area_code == "000000":
            return False

        # タイプが3かチェック
        if self.type != 3:
            return False

        # 要求されたデータが少なくとも1つ含まれているかチェック
        has_data = False
        if self.weather_flag and self.get_weather_code() is not None:
            has_data = True
        if self.temperature_flag and self.get_temperature() is not None:
            has_data = True
        if self.pop_flag and self.get_precipitation() is not None:
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
            "type": "query_response",
            "success": self.is_success(),
            "area_code": self.area_code,
            "packet_id": self.packet_id,
            "source": self.get_source_info(),
            "data": self.get_weather_data(),
        }
