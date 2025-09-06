"""
レスポンス構築クラス
リクエストに基づいてレスポンスパケットを構築
"""

import time
import sys
import os
from datetime import datetime
import json

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
        # 要件: フラグ有無に関わらず、常にlandmarksを拡張フィールドへ格納する。
        # そのため、ex_flag/alert_flag/disaster_flagに依存せず毎回実行する。
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
            source = getattr(request.ex_field, "source", None)
            if source:
                response.ex_field.source = source

        # 警報情報
        if request.alert_flag and weather_data and "warnings" in weather_data:
            response.ex_field.alert = weather_data["warnings"]

        # 災害情報
        if request.disaster_flag and weather_data and "disaster" in weather_data:
            response.ex_field.disaster = weather_data["disaster"]
        
        # landmarkデータ（外部JSONから読み込み、ex_fieldにのみ格納）
        try:
            if self.debug:
                print(f"Loading landmarks for area: {request.area_code}")
            landmarks = self._load_landmarks_for_area(request.area_code)
            total = len(landmarks) if landmarks else 0
            if self.debug:
                print(f"Found {total} landmarks")

            # ページング指定（ex_field）を取得
            req_offset = 0
            req_limit = None
            try:
                if hasattr(request, 'ex_field') and request.ex_field:
                    ex = request.ex_field.to_dict()
                    if ex.get('landmarks_offset') is not None:
                        req_offset = max(0, int(ex['landmarks_offset']))
                    if ex.get('landmarks_limit') is not None:
                        req_limit = max(1, int(ex['landmarks_limit']))
            except Exception:
                pass

            # 既定の件数制限は設けない（残件数すべてを対象）。
            # 実際の送信サイズは後段の予算(budget)で安全に絞り込む。
            if req_limit is None:
                req_limit = max(0, total - req_offset)

            # 範囲を切り出し
            start = min(req_offset, total)
            end = min(start + req_limit, total)
            page_items = landmarks[start:end] if landmarks else []

            # 送信バジェット（UDPバッファ - 固定オーバーヘッド）
            # ExtendedField 1要素の上限は1023バイトなので、それ以下にも制限
            try:
                import os
                udp_buf = int(os.getenv('UDP_BUFFER_SIZE', '4096'))
            except Exception:
                udp_buf = 4096
            MAX_EXTENDED_SIZE = 1023
            # 固定フィールド等のオーバーヘッドに余裕を持たせる
            # ここでは安全側に 1024 バイトを確保
            budget = max(256, min(MAX_EXTENDED_SIZE, udp_buf - 1024))

            # JSONバイト長が予算を超える場合は二分探索で件数を減らす
            def fit_page(items):
                lo, hi = 0, len(items)
                best = []
                while lo <= hi:
                    mid = (lo + hi) // 2
                    cand = items[:mid]
                    s = json.dumps(cand, ensure_ascii=False)
                    if len(s.encode('utf-8')) <= budget:
                        best = cand
                        lo = mid + 1
                    else:
                        hi = mid - 1
                return best

            safe_items = fit_page(page_items)
            landmarks_json = json.dumps(safe_items, ensure_ascii=False) if safe_items else "[]"

            # ex_field に設定（合計件数・オフセット・リミットも返す）
            response.ex_field.landmarks = landmarks_json
            response.ex_field.landmarks_total = total
            response.ex_field.landmarks_offset = start
            response.ex_field.landmarks_limit = len(safe_items)
            if self.debug:
                print(
                    f"Set landmarks chunk: offset={start}, size={len(safe_items)}, total={total}, bytes={len(landmarks_json.encode('utf-8'))}, budget={budget}"
                )
        except Exception:
            if self.debug:
                print("Failed to embed landmarks into ex_field (pagination)")

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

        # ランドマーク
        if weather_data and "landmarks" in weather_data:
            response.ex_field.set("landmarks", json.dumps(weather_data["landmarks"]))

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
