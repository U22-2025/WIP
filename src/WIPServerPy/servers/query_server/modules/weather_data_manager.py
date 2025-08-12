"""
気象データ管理クラス
Redisキャッシュを管理
"""

import json
import redis
from WIPServerPy.servers.query_server.modules.weather_constants import RedisConstants, CacheConstants
from WIPServerPy.data import redis_manager
import dateutil.parser


class WeatherDataManager:
    """気象データマネージャー"""

    def __init__(self, config):
        """
        初期化

        Args:
            config: 設定辞書（redis_host, redis_port, redis_db, debug, max_workers, version）
        """
        self.config = config
        self.debug = config.get("debug", False)
        self.version = config.get("version", 1)
        self.cache_enabled = config.get("cache_enabled", True)

        # Redis設定
        self.redis_host = config.get("redis_host", "localhost")
        self.redis_port = config.get("redis_port", 6379)
        self.redis_db = config.get("redis_db", 0)

        # 初期化
        self._init_redis()

    def _init_redis(self):
        """Redis接続を初期化"""
        if not self.cache_enabled:
            self.redis_pool = None
            return
        try:
            # Redis接続プールを作成
            pool_config = {
                "host": self.redis_host,
                "port": self.redis_port,
                "db": self.redis_db,
                "max_connections": self.config.get("max_workers", 10)
                * RedisConstants.CONNECTION_POOL_MULTIPLIER,
                "retry_on_timeout": True,
                "socket_timeout": RedisConstants.DEFAULT_TIMEOUT,
                "socket_connect_timeout": RedisConstants.DEFAULT_TIMEOUT,
            }

            self.redis_pool = redis.ConnectionPool(**pool_config)

            # テスト接続
            r = redis.Redis(connection_pool=self.redis_pool)
            r.ping()

            if self.debug:
                print(
                    f"Successfully connected to Redis at {self.redis_host}:{self.redis_port}/{self.redis_db}"
                )

        except (redis.ConnectionError, redis.TimeoutError) as e:
            print(f"Warning: Could not connect to Redis: {e}")
            print("Continuing without Redis cache...")
            self.redis_pool = None

    def get_weather_data(
        self,
        area_code,
        weather_flag=False,
        temperature_flag=False,
        pop_flag=False,
        alert_flag=False,
        disaster_flag=False,
        day=0,
    ):
        """
        気象データを取得（Redisから直接）

        Args:
            area_code: 地域コード
            各種フラグ: 取得するデータの種類
            day: 日数（0=今日、1=明日、2=明後日）

        Returns:
            dict: 気象データ
        """
        rm = redis_manager.WeatherRedisManager()

        if not self.cache_enabled or not self.redis_pool:
            return None

        try:
            weather_data = rm.get_weather_data(area_code)
            if not weather_data:
                None

            # 必要なデータを抽出
            result = {}

            # 天気コード
            if weather_flag and "weather" in weather_data:
                weather_codes = weather_data["weather"]
                if isinstance(weather_codes, list) and len(weather_codes) > day:
                    result["weather"] = weather_codes[day]
                else:
                    result["weather"] = weather_codes

            # 気温
            if temperature_flag and "temperature" in weather_data:
                temperatures = weather_data["temperature"]
                if isinstance(temperatures, list) and len(temperatures) > day:
                    result["temperature"] = temperatures[day]
                else:
                    result["temperature"] = temperatures

            # 降水確率
            if pop_flag and "precipitation_prob" in weather_data:
                precipitation_prob = weather_data["precipitation_prob"]
                if (
                    isinstance(precipitation_prob, list)
                    and len(precipitation_prob) > day
                ):
                    result["precipitation_prob"] = precipitation_prob[day]
                else:
                    result["precipitation_prob"] = precipitation_prob

            # 警報
            if alert_flag and "warnings" in weather_data:
                result["warnings"] = weather_data["warnings"]

            # 災害情報（存在する場合のみ取得）
            if disaster_flag and (
                "disaster" in weather_data or "disaster_info" in weather_data
            ):
                disaster_data = weather_data.get("disaster") or weather_data.get(
                    "disaster_info"
                )
                if disaster_data:
                    result["disaster"] = disaster_data
            return result

        except Exception as e:
            if self.debug:
                print(f"Error retrieving weather data: {e}")
                import traceback

                traceback.print_exc()
            return None


    def save_weather_data(
        self,
        area_code,
        data,
        weather_flag=False,
        temperature_flag=False,
        pop_flag=False,
        alert_flag=False,
        disaster_flag=False,
        day=0,
    ):
        """
        気象データをRedisキャッシュに保存

        Args:
            area_code: 地域コード
            data: 保存するデータ
            各種フラグ: データの種類
            day: 日数（0=今日、1=明日、2=明後日）
        """
        # キャッシュキーを生成
        cache_key = self._generate_cache_key(
            area_code,
            weather_flag,
            temperature_flag,
            pop_flag,
            alert_flag,
            disaster_flag,
            day,
        )

        # キャッシュに保存
        if self.cache_enabled and self.redis_pool and data:
            self._save_to_cache(cache_key, data)

    def _generate_cache_key(
        self,
        area_code,
        weather_flag,
        temperature_flag,
        pop_flag,
        alert_flag,
        disaster_flag,
        day,
    ):
        """キャッシュキーを生成"""
        flags = []
        if weather_flag:
            flags.append("w")
        if temperature_flag:
            flags.append("t")
        if pop_flag:
            flags.append("p")
        if alert_flag:
            flags.append("a")
        if disaster_flag:
            flags.append("d")

        flags_str = "".join(flags) or "none"
        return f"{CacheConstants.KEY_PREFIX}{area_code}:{flags_str}:d{day}"

    def _get_from_cache(self, key):
        """Redisキャッシュからデータを取得"""
        if not self.cache_enabled:
            return None
        try:
            r = redis.Redis(connection_pool=self.redis_pool)
            data = r.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            if self.debug:
                print(f"Cache retrieval error: {e}")
        return None

    def _save_to_cache(self, key, data):
        """Redisキャッシュにデータを保存"""
        if not self.cache_enabled:
            return
        try:
            r = redis.Redis(connection_pool=self.redis_pool)
            r.setex(
                key, CacheConstants.DEFAULT_TTL, json.dumps(data, ensure_ascii=False)
            )
            if self.debug:
                print(f"Saved to cache: {key}")
        except Exception as e:
            if self.debug:
                print(f"Cache save error: {e}")

    def close(self):
        """リソースをクリーンアップ"""
        if self.redis_pool:
            self.redis_pool.disconnect()
            if self.debug:
                print("Redis connection pool closed")
