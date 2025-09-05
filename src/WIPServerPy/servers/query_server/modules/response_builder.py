"""
レスポンス構築クラス
リクエストに基づいてレスポンスパケットを構築
"""

import time
import sys
import os
import datetime

# プロジェクトルートをパスに追加
sys.path.insert(
    0,
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
    ),
)

from WIPCommonPy.packet import Response
import json
from WIPServerPy.data.redis_manager import WeatherRedisManager, RedisConfig


class ResponseBuilder:
    """レスポンスビルダー"""

    def __init__(self, config):
        """
        初期化

        Args:
            config: 設定辞書（debug, version, redis_host, redis_port, redis_db, redis_prefix）
        """
        self.debug = config.get("debug", False)
        self.version = config.get("version", 1)

        # Redis設定を保持
        self._redis_config = RedisConfig(
            host=config.get("redis_host", "localhost"),
            port=config.get("redis_port", 6379),
            db=config.get("redis_db", 0),
        )
        self._redis_key_prefix = config.get("redis_prefix")

        try:
            self._redis_manager = WeatherRedisManager(
                config=self._redis_config,
                debug=self.debug,
                key_prefix=self._redis_key_prefix,
            )
        except Exception:
            self._redis_manager = None
            if self.debug:
                print("Failed to initialize WeatherRedisManager for landmarks")

    def build_response(self, request, weather_data):
        """
        レスポンスを構築

        Args:
            request: リクエストオブジェクト
            weather_data: 気象データ辞書

        Returns:
            Response: レスポンスオブジェクト
        """
        # 基本レスポンスを作成
        response = Response(
            version=self.version,
            packet_id=request.packet_id,
            type=3,  # Type 3 for weather data response
            area_code=request.area_code,
            day=request.day,
            timestamp=int(datetime.now().timestamp()),
            weather_flag=request.weather_flag,
            temperature_flag=request.temperature_flag,
            pop_flag=request.pop_flag,
            alert_flag=request.alert_flag,
            disaster_flag=request.disaster_flag,
            ex_flag=0,  # デフォルトは0
        )

        # 気象データを設定
        if weather_data:
            self._set_weather_data(response, request, weather_data)

        # 拡張フィールドを設定
        if request.ex_flag or request.alert_flag or request.disaster_flag:
            self._set_extended_fields(response, request, weather_data)

        return response

    def _set_weather_data(self, response, request, weather_data):
        """基本気象データを設定"""
        if request.weather_flag and "weather" in weather_data:
            weather_value = weather_data["weather"]
            # リストの場合は最初の要素を使用
            if isinstance(weather_value, list):
                response.weather_code = int(weather_value[0]) if weather_value else 0
            else:
                response.weather_code = int(weather_value) if weather_value else 0

        if request.temperature_flag and "temperature" in weather_data:
            temp_data = weather_data["temperature"]
            # リストの場合は最初の要素を使用
            if isinstance(temp_data, list):
                actual_temp = int(temp_data[0]) if temp_data else 25
            else:
                actual_temp = int(temp_data) if temp_data else 25
            # パケットフォーマットに合わせて変換（実際の温度 + 100）
            response.temperature = actual_temp + 100

        if request.pop_flag and "precipitation_prob" in weather_data:
            pop_value = weather_data["precipitation_prob"]
            # リストの場合は最初の要素を使用
            if isinstance(pop_value, list):
                response.pop = int(pop_value[0]) if pop_value else 0
            else:
                response.pop = int(pop_value) if pop_value else 0

    def _set_extended_fields(self, response, request, weather_data):
        """拡張フィールドを設定"""
        response.ex_flag = 1

        # sourceを引き継ぐ
        if hasattr(request, "ex_field") and request.ex_field:
            source = request.ex_field.get("source")
            if source:
                response.ex_field.set("source", source)

        # 警報情報
        if request.alert_flag and weather_data and "warnings" in weather_data:
            response.ex_field.set("alert", weather_data["warnings"])

        # 災害情報
        if request.disaster_flag and weather_data and "disaster" in weather_data:
            response.ex_field.set("disaster", weather_data["disaster"])
        
        # landmarkデータ（外部JSONから読み込み、ex_fieldにのみ格納）
        try:
            landmarks = self._load_landmarks_for_area(request.area_code)
            if landmarks:
                # まず件数上限を適用
                max_landmarks_count = 50
                if len(landmarks) > max_landmarks_count:
                    landmarks = landmarks[:max_landmarks_count]

                # ExtendedField の1要素あたりの最大サイズは1023バイト
                MAX_EXTENDED_SIZE = 1023

                # 文字列サイズが超える場合に件数を段階的に減らす
                lo, hi = 1, len(landmarks)
                best = []
                while lo <= hi:
                    mid = (lo + hi) // 2
                    cand = landmarks[:mid]
                    s = json.dumps(cand, ensure_ascii=False)
                    if len(s.encode('utf-8')) <= MAX_EXTENDED_SIZE:
                        best = cand
                        lo = mid + 1
                    else:
                        hi = mid - 1

                if best:
                    response.ex_field.set("landmarks", json.dumps(best, ensure_ascii=False))
        except Exception:
            # サイレントにスキップ（デバッグ時のみ標準出力）
            if self.debug:
                print("Failed to embed landmarks into ex_field")

    def _load_landmarks_for_area(self, area_code):
        """Redisからランドマークを取得"""
        if not self._redis_manager:
            if self.debug:
                print("Redis manager not initialized")
            return []

        try:
            data = self._redis_manager.get_weather_data(area_code)
        except Exception as e:
            if self.debug:
                print(
                    f"Error loading landmarks for area {area_code}: {e}. Trying to reconnect..."
                )
            try:
                self._redis_manager = WeatherRedisManager(
                    config=self._redis_config,
                    debug=self.debug,
                    key_prefix=self._redis_key_prefix,
                )
                data = self._redis_manager.get_weather_data(area_code)
            except Exception as e2:
                if self.debug:
                    print(f"Reconnection failed: {e2}")
                return []

        if data and isinstance(data, dict):
            landmarks = data.get("landmarks")
            if isinstance(landmarks, list):
                return landmarks
        if self.debug:
            print(f"No landmarks found for area {area_code}")
        return []

    def build_error_response(self, request, error_code, error_message):
        """
        エラーレスポンスを構築

        Args:
            request: リクエストオブジェクト
            error_code: エラーコード
            error_message: エラーメッセージ

        Returns:
            Response: エラーレスポンスオブジェクト
        """
        response = Response(
            version=self.version,
            packet_id=request.packet_id,
            type=3,
            area_code=request.area_code,
            day=request.day,
            timestamp=int(datetime.now().timestamp()),
            weather_flag=0,
            temperature_flag=0,
            pop_flag=0,
            alert_flag=0,
            disaster_flag=0,
            ex_flag=1,
        )

        # エラー情報を拡張フィールドに設定
        # ExtendedFieldオブジェクトはResponseのコンストラクタで作成されるため、
        # 辞書形式でデータを設定することはできません
        # 代わりに、個別にsetメソッドを使用する必要があります
        # ただし、エラー情報は標準の拡張フィールドではないため、
        # 別の方法で処理する必要があります

        # sourceを引き継ぐ
        if hasattr(request, "ex_field") and request.ex_field:
            source = request.ex_field.get("source")
            if source:
                response.ex_field.set("source", source)

        return response
