"""
Redis管理クラス

気象データ、警報・注意報、災害情報のRedis操作を統一管理します。

主な機能:
- Redis接続管理
- 気象データの取得・更新
- 警報・注意報情報の追加
- 災害情報の追加
- エラーハンドリング
"""

import json
import redis
import os
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass


@dataclass
class RedisConfig:
    """Redis設定クラス"""
    host: str = 'localhost'
    port: int = 6379
    db: int = 0
    timeout: int = 5
    
    @classmethod
    def from_env(cls) -> 'RedisConfig':
        """環境変数からRedis設定を作成"""
        return cls(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            db=int(os.getenv('REDIS_DB', 0))
        )


class WeatherRedisManager:
    """
    気象データRedis管理クラス
    
    気象データ、警報・注意報、災害情報のRedis操作を統一管理
    """
    
    def __init__(self, config: Optional[RedisConfig] = None, debug: bool = False):
        """
        初期化
        
        Args:
            config: Redis設定
            debug: デバッグモード
        """
        self.config = config or RedisConfig.from_env()
        self.debug = debug
        self.redis_client = None
        self._connect()
    
    def _connect(self):
        """Redis接続を確立"""
        try:
            self.redis_client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                db=self.config.db,
                socket_timeout=self.config.timeout,
                socket_connect_timeout=self.config.timeout,
                retry_on_timeout=True
            )
            
            # 接続テスト
            self.redis_client.ping()
            
            if self.debug:
                print(f"Redis接続成功: {self.config.host}:{self.config.port}/{self.config.db}")
                
        except (redis.ConnectionError, redis.TimeoutError) as e:
            print(f"Redis接続エラー: {e}")
            print("Redisサーバーが起動していることを確認してください")
            self.redis_client = None
            raise
    
    def _get_weather_key(self, area_code: str) -> str:
        """気象データキーを生成"""
        return f"weather:{area_code}"
    
    def _create_default_weather_data(self) -> Dict[str, Any]:
        """デフォルト気象データ構造を作成"""
        return {
            "area_name": "",
            "weather": [],
            "temperature": [],
            "precipitation_prob": []
        }
    
    def get_weather_data(self, area_code: str) -> Optional[Dict[str, Any]]:
        """
        気象データを取得
        
        Args:
            area_code: エリアコード
            
        Returns:
            気象データ辞書、存在しない場合はNone
        """
        if not self.redis_client:
            return None
        
        try:
            weather_key = self._get_weather_key(area_code)
            data = self.redis_client.json().get(weather_key, ".")
            
            if self.debug and data:
                print(f"取得: {weather_key}")
            
            return data
            
        except Exception as e:
            if self.debug:
                print(f"データ取得エラー ({area_code}): {e}")
            return None
    
    def update_weather_data(self, area_code: str, data: Dict[str, Any]) -> bool:
        """
        気象データを更新
        
        Args:
            area_code: エリアコード
            data: 更新するデータ
            
        Returns:
            成功した場合True
        """
        if not self.redis_client:
            return False
        
        try:
            weather_key = self._get_weather_key(area_code)
            self.redis_client.json().set(weather_key, ".", data)
            
            if self.debug:
                print(f"更新: {weather_key}")
            
            return True
            
        except Exception as e:
            if self.debug:
                print(f"データ更新エラー ({area_code}): {e}")
            return False
    
    def update_alerts(self, alert_data: Union[str, Dict[str, Any]]) -> Dict[str, int]:
        """
        警報・注意報情報を更新
        
        Args:
            alert_data: 警報・注意報データ（JSON文字列またはdict）
            
        Returns:
            更新結果 {'updated': 更新数, 'created': 新規作成数, 'errors': エラー数}
        """
        if not self.redis_client:
            return {'updated': 0, 'created': 0, 'errors': 0}
        
        # データがJSON文字列の場合は辞書に変換
        if isinstance(alert_data, str):
            try:
                alert_dict = json.loads(alert_data)
            except json.JSONDecodeError as e:
                if self.debug:
                    print(f"JSONデコードエラー: {e}")
                return {'updated': 0, 'created': 0, 'errors': 1}
        else:
            alert_dict = alert_data
        
        updated_count = 0
        created_count = 0
        error_count = 0
        
        for area_code, alert_info in alert_dict.items():
            try:
                # 新規データ作成
                # 既存の気象データを取得、なければデフォルトデータを作成
                existing_data = self.get_weather_data(area_code)
                if existing_data:
                    new_data = existing_data
                    updated_count += 1
                else:
                    new_data = self._create_default_weather_data()
                    created_count += 1
                
                new_data['warnings'] = alert_info.get('alert_info', [])
                
                if self.update_weather_data(area_code, new_data):
                    created_count += 1
                    if self.debug:
                        print(f"警報新規: {area_code} - {len(new_data['warnings'])}件")
                else:
                    error_count += 1
                    
            except Exception as e:
                if self.debug:
                    print(f"警報処理エラー ({area_code}): {e}")
                error_count += 1
        
        return {'updated': updated_count, 'created': created_count, 'errors': error_count}
    
    def update_disasters(self, disaster_data: Dict[str, Any]) -> Dict[str, int]:
        """
        災害情報を更新
        
        Args:
            disaster_data: 災害情報データ
            
        Returns:
            更新結果 {'updated': 更新数, 'created': 新規作成数, 'errors': エラー数}
        """
        if not self.redis_client:
            return {'updated': 0, 'created': 0, 'errors': 0}
        
        updated_count = 0
        created_count = 0
        error_count = 0
        
        for area_code, disaster_info in disaster_data.items():
            if area_code == "disaster_pulldatetime":
                # disaster_pulldatetimeは処理対象外なのでスキップ
                continue
            try:
                # 既存の気象データを取得、なければデフォルトデータを作成
                existing_data = self.get_weather_data(area_code)
                if existing_data:
                    new_data = existing_data
                    updated_count += 1
                else:
                    new_data = self._create_default_weather_data()
                    created_count += 1
                
                new_data['disaster_info'] = disaster_info.get('disaster_info', [])
                
                if self.update_weather_data(area_code, new_data):
                    if existing_data:
                        if self.debug:
                            print(f"災害更新: {area_code} - {len(new_data['disaster_info'])}件")
                    else:
                        if self.debug:
                            print(f"災害新規: {area_code} - {len(new_data['disaster_info'])}件")
                else:
                    error_count += 1
            except Exception as e:
                if self.debug:
                    print(f"災害処理エラー ({area_code}): {e}")
                error_count += 1
        
        return {'updated': updated_count, 'created': created_count, 'errors': error_count}
    
    def bulk_update_weather_data(self, weather_data: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        """
        気象データを一括更新（警報・災害情報フィールドを除く部分更新）
        
        Args:
            weather_data: {area_code: weather_data}の辞書
            
        Returns:
            更新結果 {'updated': 更新数, 'errors': エラー数}
        """
        if not self.redis_client:
            return {'updated': 0, 'errors': 0}
        
        updated_count = 0
        error_count = 0
        
        try:
            # パイプラインを使用して一括処理
            pipe = self.redis_client.pipeline()
            
            for area_code, data in weather_data.items():
                weather_key = self._get_weather_key(area_code)
                
                # 既存データがない場合は全体を作成
                pipe.json().get(weather_key, ".")
            
            # 既存データの存在確認
            existing_results = pipe.execute()
            
            # 更新用パイプライン
            update_pipe = self.redis_client.pipeline()
            
            for i, (area_code, data) in enumerate(weather_data.items()):
                weather_key = self._get_weather_key(area_code)
                existing_data = existing_results[i]
                
                if existing_data:
                    # 既存データがある場合は気象データフィールドのみ部分更新
                    update_pipe.json().set(weather_key, ".weather_reportdatetime", data.get("weather_reportdatetime", ""))
                    update_pipe.json().set(weather_key, ".area_name", data.get("area_name", ""))
                    update_pipe.json().set(weather_key, ".weather", data.get("weather", []))
                    update_pipe.json().set(weather_key, ".temperature", data.get("temperature", []))
                    update_pipe.json().set(weather_key, ".precipitation_prob", data.get("precipitation_prob", []))
                    update_pipe.json().set(weather_key, ".parent_code", data["parent_code"])
                    
                    if self.debug:
                        print(f"部分更新: {weather_key}")
                else:
                    # 既存データがない場合は全体を新規作成
                    new_data = self._create_default_weather_data()
                    new_data.update(data)
                    update_pipe.json().set(weather_key, ".", new_data)
                    
                    if self.debug:
                        print(f"新規作成: {weather_key}")
            
            update_pipe.execute()
            updated_count = len(weather_data)
            
            if self.debug:
                print(f"一括更新完了: {updated_count}件")
                
        except Exception as e:
            if self.debug:
                print(f"一括更新エラー: {e}")
            error_count = len(weather_data)
        
        return {'updated': updated_count, 'errors': error_count}
    
    def close(self):
        """Redis接続を閉じる"""
        if self.redis_client:
            self.redis_client.close()
            if self.debug:
                print("Redis接続を閉じました")


def create_redis_manager(debug: bool = False) -> WeatherRedisManager:
    """
    Redis管理クラスのファクトリー関数
    
    Args:
        debug: デバッグモード
        
    Returns:
        WeatherRedisManagerインスタンス
    """
    config = RedisConfig.from_env()
    return WeatherRedisManager(config, debug)
