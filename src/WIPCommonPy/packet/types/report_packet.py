"""
レポートパケット - IoT機器データ収集専用
IoT機器からサーバーへのセンサーデータプッシュ配信で使用
"""

from typing import Optional, Dict, Any, Union, List
from datetime import datetime
from ..models.response import Response
import threading
import random


class PacketIDGenerator12Bit:
    """12ビットパケットIDジェネレーター（循環インポート回避のため内部実装）"""

    def __init__(self):
        self._lock = threading.Lock()
        self._current = random.randint(0, 4095)  # 0 - 4095
        self._max_id = 4096  # 2^12

    def next_id(self) -> int:
        with self._lock:
            pid = self._current
            self._current = (self._current + 1) % self._max_id
            return pid


class ReportRequest(Response):
    """
    データレポートリクエスト（IoT機器からのプッシュ配信専用）

    IoT機器からサーバーへセンサーデータを送信するためのパケット。
    Type 4を使用し、プロトコルフォーマットはType 3に準拠します。
    """

    # パケットIDジェネレーター（クラスレベルで共有）
    _packet_id_generator = PacketIDGenerator12Bit()

    @classmethod
    def create_sensor_data_report(
        cls,
        area_code: Union[str, int],
        *,
        weather_code: Optional[int] = None,
        temperature: Optional[float] = None,
        precipitation_prob: Optional[int] = None,
        alert: Optional[List[str]] = None,
        disaster: Optional[List[str]] = None,
        version: int = 1,
    ) -> "ReportRequest":
        """
        センサーデータレポートリクエストを作成（Type 4）

        Args:
            area_code: エリアコード（文字列または数値）
            weather_code: 天気コード（センサーによる現在の天気観測値）
            temperature: 気温（摂氏、実際の温度値）
            precipitation_prob: 降水確率（パーセント、0-100）
            alert: 警報情報
            disaster: 災害情報
            version: プロトコルバージョン

        Returns:
            ReportRequestインスタンス

        Note:
            パケットIDはPacketIDGenerator12Bitによって自動生成されます。

        Examples:
            >>> # IoT機器でのセンサーデータ送信例
            >>> request = ReportRequest.create_sensor_data_report(
            ...     area_code="011000",
            ...     temperature=25.5,
            ...     weather_code=100,
            ...     precipitation_prob=30
            ... )
        """
        # パケットIDを自動生成
        packet_id = cls._packet_id_generator.next_id()
        # エリアコードを6桁の文字列に正規化
        if isinstance(area_code, int):
            area_code_str = f"{area_code:06d}"
        else:
            area_code_str = str(area_code).zfill(6)

        # 拡張フィールドの準備（警報・災害情報のみ）
        ex_field = {}

        # 警報・災害情報
        if alert:
            ex_field["alert"] = alert
        if disaster:
            ex_field["disaster"] = disaster

        # フラグの設定（データが提供されている場合のみ有効にする）
        weather_flag = 1 if weather_code is not None else 0
        temperature_flag = 1 if temperature is not None else 0
        pop_flag = 1 if precipitation_prob is not None else 0
        alert_flag = 1 if alert else 0
        disaster_flag = 1 if disaster else 0

        # 固定長フィールドの値を設定
        weather_code_value = weather_code if weather_code is not None else 0
        # 気温は摂氏から内部表現（+100）に変換
        temperature_value = (
            int(temperature) + 100 if temperature is not None else 100
        )  # 0℃相当
        pop_value = precipitation_prob if precipitation_prob is not None else 0

        return cls(
            version=version,
            packet_id=packet_id,
            type=4,  # データレポートリクエスト
            weather_flag=weather_flag,
            temperature_flag=temperature_flag,
            pop_flag=pop_flag,
            alert_flag=alert_flag,
            disaster_flag=disaster_flag,
            ex_flag=1 if ex_field else 0,
            day=0,  # リアルタイムデータ
            timestamp=int(datetime.now().timestamp()),
            area_code=area_code_str,
            # 固定長フィールドに値を設定
            weather_code=weather_code_value,
            temperature=temperature_value,
            pop=pop_value,
            ex_field=ex_field if ex_field else None,
        )

    def get_source_info(self) -> Optional[tuple[str, int]]:
        """
        送信元情報を取得

        Returns:
            送信元情報 (ip, port) のタプルまたはNone
        """
        if hasattr(self, "ex_field") and self.ex_field:
            ex_dict = self.ex_field.to_dict()
            return ex_dict.get("source")
        return None


class ReportResponse(Response):
    """
    データレポートレスポンス（IoT機器へのACK専用）

    サーバーからIoT機器への応答（Type 5）を処理します。
    プロトコルフォーマットはType 3に準拠し、通常はデータを含める必要はありません。
    """

    @classmethod
    def create_ack_response(
        cls, request: ReportRequest, *, version: int = 1
    ) -> "ReportResponse":
        """
        ACKレスポンスを作成（Type 5）

        Args:
            request: 元のReportRequest
            version: プロトコルバージョン

        Returns:
            ReportResponseインスタンス

        Examples:
            >>> # 成功レスポンス
            >>> response = ReportResponse.create_ack_response(
            ...     request=report_request
            ... )
        """
        # 拡張フィールドの準備
        ex_field = {}

        # 送信元情報を保持（ルーティング用・改良版）
        source = request.get_source_info()
        if source:
            ex_field["source"] = source
        else:
            # requestに直接source情報がない場合、拡張フィールドを直接チェック
            if hasattr(request, "ex_field") and request.ex_field:
                try:
                    if hasattr(request.ex_field, "to_dict"):
                        ex_dict = request.ex_field.to_dict()
                        if "source" in ex_dict:
                            ex_field["source"] = ex_dict["source"]
                    elif hasattr(request.ex_field, "source"):
                        ex_field["source"] = request.ex_field.source
                except Exception as e:
                    print(f"警告: 拡張フィールドからのsource抽出に失敗: {e}")

        # レスポンスデータ（通常は空だが、フラグは元のリクエストを反映）
        weather_code = 0
        temperature = 0  # 0℃相当（デフォルト値）
        pop = 0

        return cls(
            version=version,
            packet_id=request.packet_id,
            type=5,  # データレポートレスポンス
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

    @classmethod
    def create_data_response(
        cls, request: ReportRequest, sensor_data: Dict[str, Any], *, version: int = 1
    ) -> "ReportResponse":
        """
        データ付きレスポンスを作成（Type 5）

        Args:
            request: 元のReportRequest
            sensor_data: サーバーで処理されたセンサーデータ
            version: プロトコルバージョン

        Returns:
            ReportResponseインスタンス
        """
        # 拡張フィールドの準備
        ex_field = {}
        source = request.get_source_info()
        if source:
            ex_field["source"] = source

        # センサーデータを設定
        weather_code = 0
        temperature = 100  # 0℃相当
        pop = 0

        if sensor_data:
            # 天気コード
            if request.weather_flag and "weather_code" in sensor_data:
                weather_code = int(sensor_data["weather_code"])

            # 気温（摂氏から内部表現に変換）
            if request.temperature_flag and "temperature" in sensor_data:
                temp_celsius = float(sensor_data["temperature"])
                temperature = int(temp_celsius) + 100  # パケットフォーマット変換

            # 降水確率
            if request.pop_flag and "precipitation_prob" in sensor_data:
                pop = int(sensor_data["precipitation_prob"])

            # 警報・災害情報を拡張フィールドに追加
            if request.alert_flag and "alert" in sensor_data:
                ex_field["alert"] = sensor_data["alert"]

            if request.disaster_flag and "disaster" in sensor_data:
                ex_field["disaster"] = sensor_data["disaster"]

        return cls(
            version=version,
            packet_id=request.packet_id,
            type=5,  # データレポートレスポンス
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
        送信元情報を取得（ルーティング用）

        Returns:
            送信元情報 (ip, port) のタプルまたはNone
        """
        if hasattr(self, "ex_field") and self.ex_field:
            ex_dict = self.ex_field.to_dict()
            return ex_dict.get("source")
        return None

    def is_success(self) -> bool:
        """
        レスポンスが成功かどうかを判定

        Returns:
            成功の場合True（Type 5であればエラーパケットとは別なので常に成功）
        """
        # Type 5かチェック
        return self.type == 5

    def get_response_summary(self) -> Dict[str, Any]:
        """
        レスポンスの要約情報を取得

        Returns:
            レスポンスの要約辞書
        """
        return {
            "type": "report_response",
            "success": self.is_success(),
            "area_code": self.area_code,
            "packet_id": self.packet_id,
            "source": self.get_source_info(),
        }
