"""
気象データ管理クラス
Redisからの気象データ取得を担当
"""

import redis
import threading
from .weather_constants import RedisConstants, WeatherConstants


class WeatherDataManager:
    """気象データ管理クラス"""
    
    def __init__(self, config_manager):
        """
        初期化
        
        Args:
            config_manager: 設定管理オブジェクト
        """
        self.config = config_manager
        self.debug = config_manager.debug
        
        # Redis接続プールの初期化
        self.redis_pool = redis.ConnectionPool(**config_manager.get_redis_pool_config())
        
        # スレッドローカルストレージ
        self._thread_local = threading.local()
        
        if self.debug:
            print(f"WeatherDataManager initialized with Redis pool")
    
    def get_redis_client(self):
        """
        スレッドローカルなRedis接続を取得
        
        Returns:
            redis.Redis: Redis接続オブジェクト
        """
        if not hasattr(self._thread_local, 'redis_client'):
            self._thread_local.redis_client = redis.Redis(connection_pool=self.redis_pool)
        return self._thread_local.redis_client
    
    def _normalize_area_code(self, area_code):
        """
        エリアコードを6桁の文字列に正規化
        
        Args:
            area_code: エリアコード（int or str）
            
        Returns:
            str: 正規化されたエリアコード
        """
        if isinstance(area_code, int):
            return f"{area_code:06d}"
        return str(area_code).zfill(6)
    
    def _build_redis_queries(self, area_code, weather_flag, temperature_flag, 
                           pops_flag, alert_flag, disaster_flag, day):
        """
        Redisクエリを構築
        
        Returns:
            tuple: (pipe, queries_added)
        """
        r = self.get_redis_client()
        pipe = r.pipeline()
        
        area_code_str = self._normalize_area_code(area_code)
        weather_key = f"{RedisConstants.WEATHER_KEY_PREFIX}{area_code_str}"
        
        queries_added = []
        
        if weather_flag == WeatherConstants.FLAG_ENABLED:
            pipe.json().get(weather_key, f".weather[{day}]")
            queries_added.append("weather")
            
        if temperature_flag == WeatherConstants.FLAG_ENABLED:
            pipe.json().get(weather_key, f".temperature[{day}]")
            queries_added.append("temperature")
            
        if pops_flag == WeatherConstants.FLAG_ENABLED:
            pipe.json().get(weather_key, f".precipitation[{day}]")
            queries_added.append("precipitation")
            
        if alert_flag == WeatherConstants.FLAG_ENABLED:
            pipe.json().get(weather_key, f".warnings")
            queries_added.append("warnings")
            
        if disaster_flag == WeatherConstants.FLAG_ENABLED:
            pipe.json().get(weather_key, f".disaster_info")
            queries_added.append("disaster_info")
        
        return pipe, queries_added
    
    def _process_query_results(self, results, queries_added):
        """
        クエリ結果を処理
        
        Args:
            results: Redisクエリ結果
            queries_added: 実行されたクエリのリスト
            
        Returns:
            dict: 処理された気象データ
        """
        data = {}
        for i, query_type in enumerate(queries_added):
            data[query_type] = results[i] if results[i] is not None else []
        return data
    
    def get_weather_data(self, area_code, weather_flag, temperature_flag, 
                        pops_flag, alert_flag, disaster_flag, day):
        """
        Redisから気象データを取得
        
        Args:
            area_code: エリアコード
            weather_flag: 天気データ取得フラグ
            temperature_flag: 気温データ取得フラグ
            pops_flag: 降水確率データ取得フラグ
            alert_flag: 警報データ取得フラグ
            disaster_flag: 災害情報データ取得フラグ
            day: 日数
            
        Returns:
            dict: 取得した気象データ
        """
        try:
            # クエリを構築
            pipe, queries_added = self._build_redis_queries(
                area_code, weather_flag, temperature_flag, 
                pops_flag, alert_flag, disaster_flag, day
            )
            
            # クエリが追加されていない場合は空の辞書を返す
            if not queries_added:
                if self.debug:
                    print("No flags enabled, returning empty data")
                return {}
            
            # パイプラインを一括実行
            results = pipe.execute()
            
            # 結果を処理
            data = self._process_query_results(results, queries_added)
            
            if self.debug:
                print(f"Retrieved weather data for area {area_code}: {data}")
                
            return data
            
        except redis.RedisError as e:
            print(f"Redis error in get_weather_data: {e}")
            return {}
        except Exception as e:
            print(f"Error in get_weather_data: {e}")
            return {}
    
    def validate_area_code(self, area_code):
        """
        エリアコードの妥当性をチェック
        
        Args:
            area_code: チェックするエリアコード
            
        Returns:
            bool: 妥当性
        """
        try:
            if isinstance(area_code, int):
                return 0 <= area_code <= 999999
            elif isinstance(area_code, str):
                return area_code.isdigit() and len(area_code) <= 6
            return False
        except:
            return False
