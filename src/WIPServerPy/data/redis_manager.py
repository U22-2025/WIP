"""
Redis管理クラス

気象データ、警報・注意報、災害情報、地震情報のRedis操作を統一管理します。

主な機能:
- Redis接続管理
- 気象データの取得・更新
- 警報・注意報情報の追加
- 災害情報の追加
- 地震情報の追加
- エラーハンドリング
"""

import json
import redis
import os
from datetime import datetime
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass


@dataclass
class RedisConfig:
    """Redis設定クラス"""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    timeout: int = 1  # タイムアウトを1秒に短縮

    @classmethod
    def from_env(cls) -> "RedisConfig":
        """環境変数からRedis設定を作成"""
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
        )


class WeatherRedisManager:
    """
    気象データRedis管理クラス

    気象データ、警報・注意報、災害情報、地震情報のRedis操作を統一管理
    """

    def __init__(
        self,
        config: Optional[RedisConfig] = None,
        debug: bool = False,
        key_prefix: Optional[str] = None,
    ):
        """
        初期化

        Args:
            config: Redis設定
            debug: デバッグモード
        """
        self.config = config or RedisConfig.from_env()
        self.debug = debug
        # キープレフィックス（テスト用途などで使用）
        if key_prefix is not None:
            self.key_prefix = str(key_prefix)
        else:
            # 環境変数からの既定（REPORT_DB_KEY_PREFIXがあれば優先）
            self.key_prefix = os.getenv("REPORT_DB_KEY_PREFIX", os.getenv("REDIS_KEY_PREFIX", ""))
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
                retry_on_timeout=True,
            )

            # 接続テスト
            self.redis_client.ping()

            if self.debug:
                print(
                    f"Redis接続成功: {self.config.host}:{self.config.port}/{self.config.db}"
                )

        except (redis.ConnectionError, redis.TimeoutError) as e:
            print(f"Redis接続エラー: {e}")
            print("Redisサーバーが起動していることを確認してください")
            self.redis_client = None
            raise

    def _get_weather_key(self, area_code: str) -> str:
        """気象データキーを生成"""
        prefix = getattr(self, "key_prefix", "") or ""
        return f"{prefix}weather:{area_code}"

    def _create_default_weather_data(self) -> Dict[str, Any]:
        """デフォルト気象データ構造を作成"""
        # 週次データは要素数7・null埋め、リアルタイム系は空配列で初期化
        return {
            "weather": [None] * 7,
            "temperature": [None] * 7,
            "precipitation_prob": [None] * 7,
            "warnings": [],
            "disaster": [],
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
            if self.debug:
                print(
                    "Redisクライアントが接続されていません。気象データを取得できません。"
                )
            return None

        try:
            weather_key = self._get_weather_key(area_code)
            data = self.redis_client.json().get(weather_key, ".")
            if data is not None:
                return data
            # Fallback: 通常キーにJSON文字列として保存されている場合
            raw = self.redis_client.get(weather_key)
            if raw:
                try:
                    return json.loads(raw)
                except Exception:
                    return None
            return None

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
            if self.debug:
                print(
                    "Redisクライアントが接続されていません。気象データを更新できません。"
                )
            return False

        try:
            weather_key = self._get_weather_key(area_code)
            # precipitation_prob に正規化して保存（新旧キーの混在を解消）
            normalized = dict(data)
            if "precipitation_prob" not in normalized and "precipitationProbability" in normalized:
                normalized["precipitation_prob"] = normalized.get("precipitationProbability")
                # 旧フィールド（camelCase）は保存しない
                if "precipitationProbability" in normalized:
                    try:
                        del normalized["precipitationProbability"]
                    except Exception:
                        pass

            self.redis_client.json().set(weather_key, ".", normalized)

            if self.debug:
                print(
                    f"更新成功(JSON): {weather_key}, データ: {json.dumps(normalized, ensure_ascii=False)}"
                )

            return True

        except Exception as e:
            # Fallback: RedisJSONが無い環境では通常のStringとして保存
            try:
                weather_key = self._get_weather_key(area_code)
                self.redis_client.set(weather_key, json.dumps(normalized, ensure_ascii=False))
                if self.debug:
                    print(
                        f"更新成功(STRING): {weather_key}, データ: {json.dumps(normalized, ensure_ascii=False)}"
                    )
                return True
            except Exception as e2:
                if self.debug:
                    print(
                        f"データ更新エラー ({area_code}): {str(e2)}, データ型: {type(data)}, データ: {data}"
                    )
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
            return {"updated": 0, "created": 0, "errors": 0}

        updated_count = 0
        created_count = 0
        error_count = 0

        for area_code, alert_info in alert_data.items():
            new_data = {}
            try:
                if area_code == "alert_pulldatetime":
                    self.update_weather_data(area_code, alert_info)
                    continue

                # 新規データ作成
                # 既存の気象データを取得、なければデフォルトデータを作成
                existing_data = self.get_weather_data(area_code)
                if existing_data:
                    new_data = existing_data
                    updated_count += 1
                else:
                    new_data = self._create_default_weather_data()
                    created_count += 1

                new_data["warnings"] = alert_info.get("alert_info", [])

                if self.update_weather_data(area_code, new_data):
                    if existing_data:
                        if self.debug:
                            print(
                                f"警報更新: {area_code} - {len(new_data['warnings'])}件"
                            )
                    else:
                        created_count += 1
                        if self.debug:
                            print(
                                f"警報新規: {area_code} - {len(new_data['warnings'])}件"
                            )
                else:
                    error_count += 1

            except Exception as e:
                if self.debug:
                    print(f"警報処理エラー ({area_code}): {e}")
                error_count += 1

        return {
            "updated": updated_count,
            "created": created_count,
            "errors": error_count,
        }

    def update_disasters(self, disaster_data: Dict[str, Any]) -> Dict[str, int]:
        """
        災害情報を更新

        Args:
            disaster_data: 災害情報データ

        Returns:
            更新結果 {'updated': 更新数, 'created': 新規作成数, 'errors': エラー数}
        """
        if not self.redis_client:
            return {"updated": 0, "created": 0, "errors": 0}

        updated_count = 0
        created_count = 0
        error_count = 0

        for area_code, disaster_info in disaster_data.items():
            new_data = {}
            try:
                if area_code == "disaster_pulldatetime":
                    self.update_weather_data(area_code, disaster_info)
                    continue

                # 既存の気象データを取得、なければデフォルトデータを作成
                existing_data = self.get_weather_data(area_code)

                if existing_data:
                    new_data = existing_data
                    updated_count += 1
                else:
                    new_data = self._create_default_weather_data()
                    created_count += 1

                # 災害情報を追加
                new_data["disaster"] = disaster_info.get("disaster", [])

                if self.update_weather_data(area_code, new_data):
                    if self.debug:
                        if existing_data:
                            print(
                                f"災害更新成功: {area_code} - {len(new_data['disaster'])}件"
                            )
                        else:
                            print(
                                f"災害新規成功: {area_code} - {len(new_data['disaster'])}件"
                            )
                else:
                    if self.debug:
                        print(f"災害更新失敗: {area_code}")
                    error_count += 1
            except Exception as e:
                if self.debug:
                    print(f"災害処理エラー ({area_code}): {e}")
                error_count += 1

        return {
            "updated": updated_count,
            "created": created_count,
            "errors": error_count,
        }

    def update_earthquakes(self, earthquake_data: Dict[str, Any]) -> Dict[str, int]:
        """
        地震情報を災害情報として更新（earthquakeデータをdisasterに統合）

        Args:
            earthquake_data: 地震情報データ

        Returns:
            更新結果 {'updated': 更新数, 'created': 新規作成数, 'errors': エラー数}
        """
        if not self.redis_client:
            return {"updated": 0, "created": 0, "errors": 0}

        updated_count = 0
        created_count = 0
        error_count = 0

        for area_code, earthquake_info in earthquake_data.items():
            new_data = {}
            try:
                # 地震データ取得時刻をdisasterpulldatetimeとして処理
                if area_code == "earthquake_pulldatetime":
                    self.update_weather_data("disaster_pulldatetime", earthquake_info)
                    continue

                # 既存の気象データを取得、なければデフォルトデータを作成
                existing_data = self.get_weather_data(area_code)

                if existing_data:
                    new_data = existing_data
                    updated_count += 1
                else:
                    new_data = self._create_default_weather_data()
                    created_count += 1

                # earthquakeキーのデータをdisaster配列に統合
                earthquake_list = earthquake_info.get("earthquake", [])

                # 既存のdisaster配列を取得（なければ空配列）
                existing_disasters = new_data.get("disaster", [])

                # 重複を避けるため、地震情報のみを先に削除
                filtered_disasters = [
                    d
                    for d in existing_disasters
                    if not (isinstance(d, str) and d.startswith("地震情報"))
                ]

                # 地震情報を既存のdisaster配列に追加
                new_data["disaster"] = filtered_disasters + earthquake_list

                if self.update_weather_data(area_code, new_data):
                    if self.debug:
                        if existing_data:
                            print(
                                f"災害情報（地震）更新成功: {area_code} - {len(earthquake_list)}件"
                            )
                        else:
                            print(
                                f"災害情報（地震）新規成功: {area_code} - {len(earthquake_list)}件"
                            )
                else:
                    if self.debug:
                        print(f"災害情報（地震）更新失敗: {area_code}")
                    error_count += 1
            except Exception as e:
                if self.debug:
                    print(f"災害情報（地震）処理エラー ({area_code}): {e}")
                error_count += 1

        return {
            "updated": updated_count,
            "created": created_count,
            "errors": error_count,
        }

    def bulk_update_weather_data(
        self, weather_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        気象データを一括更新（警報・災害情報フィールドを除く部分更新）

        Args:
            weather_data: {area_code: weather_data}の辞書

        Returns:
            更新結果 {'updated': 更新数, 'errors': エラー数}
        """
        if not self.redis_client:
            return {"updated": 0, "errors": 0}

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
                    update_pipe.json().set(
                        weather_key, ".area_name", data.get("area_name", "")
                    )
                    update_pipe.json().set(
                        weather_key, ".weather", data.get("weather", [])
                    )
                    update_pipe.json().set(
                        weather_key, ".temperature", data.get("temperature", [])
                    )
                    # precipitation_prob を使用（camelCaseからフォールバック）
                    update_pipe.json().set(
                        weather_key,
                        ".precipitation_prob",
                        data.get("precipitation_prob", data.get("precipitationProbability", [])),
                    )
                    update_pipe.json().set(
                        weather_key, ".parent_code", data["parent_code"]
                    )

                    if self.debug:
                        print(f"部分更新: {weather_key}")
                else:
                    # 既存データがない場合は全体を新規作成（snake_caseで統一）
                    base = self._create_default_weather_data()
                    # 上書き（必要フィールドのみマッピング）
                    if "weather" in data:
                        base["weather"] = data.get("weather", base["weather"])
                    if "temperature" in data:
                        base["temperature"] = data.get("temperature", base["temperature"])
                    # 降水確率は precipitation_prob に正規化
                    base["precipitation_prob"] = data.get(
                        "precipitation_prob", data.get("precipitationProbability", base["precipitation_prob"])
                    )
                    # 任意フィールド（下位互換維持）
                    if "area_name" in data:
                        base["area_name"] = data.get("area_name")
                    if "parent_code" in data:
                        base["parent_code"] = data.get("parent_code")
                    if "warnings" in data:
                        base["warnings"] = data.get("warnings") or []
                    if "disaster" in data:
                        base["disaster"] = data.get("disaster") or []
                    update_pipe.json().set(weather_key, ".", base)

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

        return {"updated": updated_count, "errors": error_count}

    def update_timestamp(self, area_code: str, source_time: str, source_type: str) -> bool:
        """
        指定地域のタイムスタンプを更新
        
        Args:
            area_code: 地域コード
            source_time: データ元時刻（JMAならreportdatetime、レポートクライアントなら現在時刻）
            source_type: "jma_api" または "report_client"
        
        Returns:
            bool: 更新成功時True
        """
        try:
            # 現在のタイムスタンプデータを取得
            timestamps_key = "weather:timestamps"
            current_data = self.redis_client.json().get(timestamps_key)
            if current_data is None:
                current_data = {}
            
            # 新しいタイムスタンプデータを作成
            saved_at = datetime.now().isoformat()
            timestamp_data = {
                "saved_at": saved_at,
                "source_time": source_time,
                "source_type": source_type
            }
            
            # データを更新
            current_data[area_code] = timestamp_data
            
            # Redisに保存
            self.redis_client.json().set(timestamps_key, ".", current_data)
            
            if self.debug:
                print(f"タイムスタンプ更新: {area_code} ({source_type}) - {source_time}")
            
            return True
            
        except Exception as e:
            if self.debug:
                print(f"タイムスタンプ更新エラー ({area_code}): {e}")
            return False

    def bulk_update_timestamps(self, timestamp_data: Dict[str, Dict[str, str]]) -> int:
        """
        複数地域のタイムスタンプを一括更新
        
        Args:
            timestamp_data: {area_code: {"source_time": str, "source_type": str}} 形式
        
        Returns:
            int: 更新成功数
        """
        try:
            timestamps_key = "weather:timestamps"
            current_data = self.redis_client.json().get(timestamps_key)
            if current_data is None:
                current_data = {}
            
            saved_at = datetime.now().isoformat()
            updated_count = 0
            
            for area_code, data in timestamp_data.items():
                current_data[area_code] = {
                    "saved_at": saved_at,
                    "source_time": data["source_time"],
                    "source_type": data["source_type"]
                }
                updated_count += 1
            
            self.redis_client.json().set(timestamps_key, ".", current_data)
            
            if self.debug:
                print(f"一括タイムスタンプ更新: {updated_count}件")
            
            return updated_count
            
        except Exception as e:
            if self.debug:
                print(f"一括タイムスタンプ更新エラー: {e}")
            return 0

    def get_timestamps(self, area_codes: Optional[list] = None) -> Dict[str, Dict[str, str]]:
        """
        タイムスタンプデータを取得
        
        Args:
            area_codes: 取得対象の地域コードリスト（Noneで全取得）
        
        Returns:
            dict: タイムスタンプデータ
        """
        try:
            timestamps_key = "weather:timestamps"
            all_data = self.redis_client.json().get(timestamps_key)
            
            if all_data is None:
                return {}
            
            if area_codes is None:
                return all_data
            
            # 指定された地域コードのみ返す
            return {code: all_data.get(code, {}) for code in area_codes if code in all_data}
            
        except Exception as e:
            if self.debug:
                print(f"タイムスタンプ取得エラー: {e}")
            return {}

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
