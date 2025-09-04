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
import re
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

    def _normalize_alert_text(self, text: Any) -> str:
        """警報テキストの正規化（括弧とその中身を除去、空白整形）"""
        if not isinstance(text, str):
            return ""
        # 全角/半角の括弧とその中身を削除
        cleaned = re.sub(r"[（(][^）)]*[）)]", "", text)
        # 余分な空白を1つにまとめてトリム
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

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
            "wind": [None] * 7,
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

    def clear_alert_disaster_data(self, clear_alerts: bool = True, clear_disasters: bool = True) -> Dict[str, int]:
        """
        全エリアの警報・災害データを初期化（空配列にリセット）
        
        Args:
            clear_alerts: 警報データ（warnings）をクリアするかどうか
            clear_disasters: 災害データ（disaster）をクリアするかどうか
            
        Returns:
            更新結果 {'cleared_areas': クリアしたエリア数, 'errors': エラー数}
        """
        if not self.redis_client:
            return {"cleared_areas": 0, "errors": 0}
        
        cleared_count = 0
        error_count = 0
        
        try:
            # weather:* パターンのキーを取得
            prefix = getattr(self, "key_prefix", "") or ""
            pattern = f"{prefix}weather:*"
            keys = self.redis_client.keys(pattern)
            
            if self.debug:
                print(f"初期化対象: {len(keys)}個のエリアデータ")
            
            for key in keys:
                try:
                    # 既存データを取得
                    existing_data = self.redis_client.json().get(key, ".")
                    if existing_data is None:
                        # Fallback: 通常キーの場合
                        raw = self.redis_client.get(key)
                        if raw:
                            existing_data = json.loads(raw)
                        else:
                            continue
                    
                    modified = False
                    if clear_alerts and "warnings" in existing_data:
                        existing_data["warnings"] = []
                        modified = True
                    
                    if clear_disasters and "disaster" in existing_data:
                        existing_data["disaster"] = []
                        modified = True
                    
                    if modified:
                        # データを更新
                        self.redis_client.json().set(key, ".", existing_data)
                        cleared_count += 1
                        if self.debug:
                            area_code = key.replace(f"{prefix}weather:", "")
                            print(f"初期化完了: {area_code}")
                            
                except Exception as e:
                    if self.debug:
                        print(f"エリア初期化エラー ({key}): {e}")
                    error_count += 1
                    
        except Exception as e:
            if self.debug:
                print(f"初期化処理エラー: {e}")
            error_count += 1
        
        if self.debug:
            print(f"初期化完了: {cleared_count}エリア, エラー: {error_count}件")
        
        return {"cleared_areas": cleared_count, "errors": error_count}

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

                # 警報データを置換する（新規データのみを使用し、重複排除 + 再正規化）
                raw_alerts = alert_info.get("alert_info", [])
                if not isinstance(raw_alerts, list):
                    # 想定外の型の場合はリスト化
                    raw_alerts = [raw_alerts] if raw_alerts else []

                # 正規化（括弧と中身を除去、空白整形）
                normalized_alerts = [self._normalize_alert_text(a) for a in raw_alerts]
                # 空要素を除去
                normalized_alerts = [a for a in normalized_alerts if a]

                # 重複排除（順序保持）
                unique_alerts = list(dict.fromkeys(normalized_alerts))
                new_data["warnings"] = unique_alerts

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

                # 災害情報を置換する（新規データのみを使用）
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

    def bulk_update_weather_data(self, weather_data: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
        """気象データを一括更新（警報・災害情報フィールドを除く部分更新）"""
        if not self.redis_client:
            return {"updated": 0, "errors": 0}

        updated_count = 0
        error_count = 0

        try:
            # 既存データをまとめて取得
            pipe = self.redis_client.pipeline()
            for area_code in weather_data.keys():
                pipe.json().get(self._get_weather_key(area_code), ".")
            existing_results = pipe.execute()

            update_pipe = self.redis_client.pipeline()

            def _merge_weekly(existing_list, new_list):
                base = list(existing_list or [None] * 7)
                if len(base) < 7:
                    base.extend([None] * (7 - len(base)))
                else:
                    base = base[:7]
                for idx, val in enumerate(new_list):
                    if idx < 7 and val is not None:  # 新しい値がNoneでない場合のみ上書き
                        base[idx] = val
                return base

            for (area_code, data), existing_data in zip(weather_data.items(), existing_results):
                weather_key = self._get_weather_key(area_code)
                if existing_data:
                    # 既存データをベースに上書き
                    weather_list = _merge_weekly(existing_data.get("weather"), data.get("weather", []))
                    temp_list = _merge_weekly(existing_data.get("temperature"), data.get("temperature", []))
                    precip_list = _merge_weekly(
                        existing_data.get("precipitation_prob", existing_data.get("precipitationProbability")),
                        data.get("precipitation_prob", data.get("precipitationProbability", [])),
                    )
                    update_pipe.json().set(
                        weather_key, ".area_name", data.get("area_name", existing_data.get("area_name", ""))
                    )
                    update_pipe.json().set(weather_key, ".weather", weather_list)
                    update_pipe.json().set(weather_key, ".temperature", temp_list)
                    update_pipe.json().set(weather_key, ".precipitation_prob", precip_list)
                    # 風データの処理を追加
                    wind_list = _merge_weekly(existing_data.get("wind"), data.get("wind", []))
                    update_pipe.json().set(weather_key, ".wind", wind_list)
                    update_pipe.json().set(
                        weather_key, ".parent_code", data.get("parent_code", existing_data.get("parent_code"))
                    )
                    if self.debug:
                        print(f"部分更新: {weather_key}")
                else:
                    # 新規作成: デフォルトデータに埋め込み
                    base = self._create_default_weather_data()
                    base["weather"] = _merge_weekly(base["weather"], data.get("weather", []))
                    base["temperature"] = _merge_weekly(base["temperature"], data.get("temperature", []))
                    base["precipitation_prob"] = _merge_weekly(
                        base["precipitation_prob"],
                        data.get("precipitation_prob", data.get("precipitationProbability", [])),
                    )
                    if "area_name" in data:
                        base["area_name"] = data.get("area_name")
                    if "parent_code" in data:
                        base["parent_code"] = data.get("parent_code")
                    if "warnings" in data:
                        base["warnings"] = data.get("warnings") or []
                    if "disaster" in data:
                        base["disaster"] = data.get("disaster") or []
                    if "maritime_alert" in data:
                        base["maritime_alert"] = data.get("maritime_alert") or []
                    if "wind" in data:
                        base["wind"] = _merge_weekly(base["wind"], data.get("wind", []))
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

    def update_maritime_alerts(self, maritime_alert_data: Union[str, Dict[str, Any]]) -> Dict[str, int]:
        """
        海上警報・注意報情報を更新
        Args:
            maritime_alert_data: 海上警報・注意報データ（JSON文字列またはdict）
        Returns:
            更新結果 {'updated': 更新数, 'created': 新規作成数, 'errors': エラー数}
        """
        if not self.redis_client:
            return {"updated": 0, "created": 0, "errors": 0}

        # データの型チェック・変換
        if isinstance(maritime_alert_data, str):
            try:
                import json
                maritime_alert_data = json.loads(maritime_alert_data)
            except json.JSONDecodeError as e:
                if self.debug:
                    print(f"JSON parse error in maritime alerts: {e}")
                return {"updated": 0, "created": 0, "errors": 1}

        updated_count = 0
        created_count = 0
        error_count = 0

        for area_code, maritime_info in maritime_alert_data.items():
            try:
                # タイムスタンプ情報は別処理
                if area_code == "maritime_alert_pulldatetime":
                    self.update_weather_data(area_code, maritime_info)
                    continue

                # 既存の気象データを取得、なければデフォルトデータを作成
                existing_data = self.get_weather_data(area_code)

                if existing_data:
                    new_data = existing_data
                    updated_count += 1
                else:
                    new_data = self._create_default_weather_data()
                    created_count += 1

                # 海上警報・注意報情報を既存のwarningsフィールドに統合
                existing_warnings = new_data.get("warnings", [])
                maritime_alerts = maritime_info.get("maritime_alert", [])
                new_data["warnings"] = existing_warnings + maritime_alerts

                if self.update_weather_data(area_code, new_data):
                    if self.debug:
                        maritime_count = len(maritime_info.get("maritime_alert", []))
                        if existing_data:
                            print(
                                f"海上警報更新: {area_code} - {maritime_count}件"
                            )
                        else:
                            print(
                                f"海上警報新規: {area_code} - {maritime_count}件"
                            )
                else:
                    if self.debug:
                        print(f"海上警報更新失敗: {area_code}")
                    error_count += 1
            except Exception as e:
                if self.debug:
                    print(f"海上警報処理エラー ({area_code}): {e}")
                error_count += 1

        return {
            "updated": updated_count,
            "created": created_count,
            "errors": error_count,
        }

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
