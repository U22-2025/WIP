"""
レポートサーバー - IoT機器データ収集専用サーバー実装
IoT機器からのType 4（レポートリクエスト）を受信してType 5（レポートレスポンス）を返す
"""

import time
import sys
import os
from datetime import datetime
from pathlib import Path
import traceback

# モジュールとして使用される場合
from WIPServerPy.servers.base_server import BaseServer
from WIPCommonPy.packet import ReportRequest, ReportResponse
from WIPCommonPy.utils.config_loader import ConfigLoader
from WIPCommonPy.packet.debug.debug_logger import PacketDebugLogger
from WIPCommonPy.utils.log_config import UnifiedLogFormatter


# JSON_DIR references removed
class ReportServer(BaseServer):
    """レポートサーバーのメインクラス（IoT機器データ収集専用）"""

    def __init__(self, host=None, port=None, debug=None, max_workers=None):
        """
        初期化

        Args:
            host: サーバーホスト（Noneの場合は設定ファイルから取得）
            port: サーバーポート（Noneの場合は設定ファイルから取得）
            debug: デバッグモードフラグ（Noneの場合は設定ファイルから取得）
            max_workers: スレッドプールのワーカー数（Noneの場合は設定ファイルから取得）
        """
        # 設定ファイルを読み込む
        config_path = Path(__file__).parent / "config.ini"
        try:
            self.config = ConfigLoader(config_path)
        except Exception as e:
            error_msg = (
                f"設定ファイルの読み込みに失敗しました: {config_path} - {str(e)}"
            )
            if debug:
                traceback.print_exc()
            raise RuntimeError(f"設定ファイル読み込みエラー: {str(e)}")

        # サーバー設定を取得（引数優先、なければ設定ファイル、なければデフォルト）
        if host is None:
            host = self.config.get("server", "host", "0.0.0.0")
        if port is None:
            port = self.config.getint("server", "port", 9999)
        if debug is None:
            debug_str = self.config.get("server", "debug", "false")
            debug = debug_str.lower() == "true"
        if max_workers is None:
            max_workers = self.config.getint("server", "max_workers", None)

        # 基底クラスの初期化
        super().__init__(host, port, debug, max_workers)

        # サーバー名を設定
        self.server_name = "ReportServer"

        # 認証設定を初期化
        self._init_auth_config()

        # プロトコルバージョンを設定から取得（4ビット値に制限）
        version = self.config.getint("system", "protocol_version", 1)
        self.version = version & 0x0F  # 4ビットにマスク

        # ネットワーク設定
        self.udp_buffer_size = self.config.getint("network", "udp_buffer_size", 4096)

        # データ検証設定
        self.enable_data_validation = self.config.getboolean(
            "validation", "enable_data_validation", True
        )
        self.enable_alert_processing = self.config.getboolean(
            "processing", "enable_alert_processing", True
        )
        self.enable_disaster_processing = self.config.getboolean(
            "processing", "enable_disaster_processing", True
        )
        # ファイルログ機能は削除
        # DB保存の有効化設定
        self.enable_database = self.config.getboolean(
            "database", "enable_database", False
        )
        # 互換: 古い設定ファイルでは [storage].enable_database を使っている場合がある
        if not self.enable_database:
            self.enable_database = self.config.getboolean(
                "storage", "enable_database", False
            )
        # 環境変数での強制有効化/無効化 (REPORT_SERVER_ENABLE_DATABASE)
        env_db = os.getenv("REPORT_SERVER_ENABLE_DATABASE")
        if env_db is not None:
            self.enable_database = str(env_db).lower() == "true"
        if self.debug:
            print(f"[{self.server_name}] DB保存有効: {self.enable_database}")

        # レポートサイズ制限
        self.max_report_size = self.config.getint("validation", "max_report_size", 4096)

        # ログファイル設定は削除

        # 統計情報
        self.report_count = 0
        self.success_count = 0

        # ログファイル初期化は削除

        # 統一デバッグロガーの初期化
        self.packet_debug_logger = PacketDebugLogger("ReportServer")

        # 転送（レポートクライアントとして送信）設定
        self._init_forward_config()

    def _init_forward_config(self):
        """レポートクライアントとしての転送設定を読み込み"""
        try:
            # Config優先、未指定は環境変数/デフォルトへ
            self.forward_enabled = self.config.getboolean(
                "forwarding", "enable_client_forward", False
            )
            self.forward_host = self.config.get(
                "forwarding", "forward_host", ""
            )
            self.forward_port = self.config.getint(
                "forwarding", "forward_port", 0
            )
            self.forward_async = self.config.getboolean(
                "forwarding", "forward_async", True
            )

            # バリデーション軽微実施
            if self.forward_enabled:
                if not self.forward_host or not self.forward_port:
                    print(
                        f"[{self.server_name}] Forwarding enabled but destination is not set"
                    )
                    self.forward_enabled = False
        except Exception:
            # 失敗時は無効化（安全側）
            self.forward_enabled = False
            self.forward_host = ""
            self.forward_port = 0
            self.forward_async = True

    def _forward_report_as_client(self, sensor_data):
        """受信したセンサーデータをレポートクライアントとして転送"""
        try:
            # 遅延インポートで依存を局所化
            from WIPCommonPy.clients.report_client import ReportClient

            if not sensor_data:
                return

            area_code = sensor_data.get("area_code")
            if not area_code:
                if self.debug:
                    print(f"[{self.server_name}] Forward skipped: no area_code")
                return

            client = ReportClient(
                host=self.forward_host, port=int(self.forward_port), debug=self.debug
            )
            try:
                client.set_sensor_data(
                    area_code=area_code,
                    weather_code=sensor_data.get("weather_code"),
                    temperature=sensor_data.get("temperature"),
                    precipitation_prob=sensor_data.get("precipitation_prob"),
                    alert=sensor_data.get("alert"),
                    disaster=sensor_data.get("disaster"),
                )
                # 送信（内部でACK待ち）。非同期実行なら呼び出し元はブロックしない
                client.send_report_data()
            finally:
                client.close()
        except Exception as e:
            if self.debug:
                print(f"[{self.server_name}] Forwarding error: {e}")

    def _init_auth_config(self):
        """認証設定を環境変数から読み込み（ReportServer固有）"""
        # ReportServer自身の認証設定
        auth_enabled = (
            os.getenv("REPORT_SERVER_AUTH_ENABLED", "false").lower() == "true"
        )
        auth_passphrase = os.getenv("REPORT_SERVER_PASSPHRASE", "")
        request_auth_enabled = (
            os.getenv("REPORT_SERVER_REQUEST_AUTH_ENABLED", "false").lower() == "true"
        )

        self.auth_enabled = auth_enabled
        self.auth_passphrase = auth_passphrase
        self.request_auth_enabled = request_auth_enabled

    def _get_response_auth_config(self):
        """レスポンス認証設定を取得"""
        return (
            os.getenv("REPORT_SERVER_RESPONSE_AUTH_ENABLED", "false").lower() == "true"
        )

    def validate_request(self, request):
        """
        リクエストの妥当性をチェック（BaseServerパターン）

        Args:
            request: リクエストオブジェクト

        Returns:
            tuple: (is_valid, error_code, error_message)
        """
        # データサイズチェック
        if hasattr(request, "_original_data"):
            data_size = len(request._original_data)
            if data_size > self.max_report_size:
                return (
                    False,
                    413,
                    f"レポートサイズが制限を超えています: {data_size} > {self.max_report_size}",
                )

        # バージョンチェック
        if request.version != self.version:
            return (
                False,
                406,
                f"バージョンが不正です (expected: {self.version}, got: {request.version})",
            )

        # 認証チェック（基底クラスの共通メソッドを使用）
        auth_valid, auth_error_code, auth_error_msg = self.validate_auth(request)
        if not auth_valid:
            return False, auth_error_code, auth_error_msg

        # タイプチェック（Type 4のみ有効）
        if request.type != 4:
            return False, 405, f"サポートされていないパケットタイプ: {request.type}"

        # エリアコードチェック
        if not request.area_code or request.area_code == "000000":
            return False, 402, "エリアコードが未設定"

        # センサーデータの検証
        if self.enable_data_validation:
            sensor_data = self._extract_sensor_data(request)
            validation_result = self._validate_sensor_data(sensor_data)
            if not validation_result["valid"]:
                return (
                    False,
                    422,
                    f"センサーデータの検証に失敗: {validation_result['message']}",
                )

        # 専用クラスのバリデーション
        if hasattr(request, "is_valid") and callable(getattr(request, "is_valid")):
            if not request.is_valid():
                return False, 400, "リクエストのバリデーションに失敗"

        return True, None, None

    def _extract_sensor_data(self, request):
        """リクエストからセンサーデータを抽出"""
        sensor_data = {
            "area_code": request.area_code,
            "timestamp": request.timestamp,
            "data_types": [],
        }

        # デバッグ出力でリクエストの詳細を確認（最適化版）
        if self.debug:
            flags = [
                f"weather:{getattr(request, 'weather_flag', 'N')}",
                f"temp:{getattr(request, 'temperature_flag', 'N')}",
                f"pop:{getattr(request, 'pop_flag', 'N')}",
                f"alert:{getattr(request, 'alert_flag', 'N')}",
                f"disaster:{getattr(request, 'disaster_flag', 'N')}",
            ]
            print(f"  [デバッグ] フラグ: {' '.join(flags)}")

        # 固定長フィールドからセンサーデータを抽出
        try:
            # 天気コード
            if (
                hasattr(request, "weather_flag")
                and request.weather_flag
                and hasattr(request, "weather_code")
            ):
                weather_code = request.weather_code
                if weather_code is not None and weather_code != 0:
                    sensor_data["weather_code"] = weather_code

            # 気温（内部表現から摂氏に変換）
            if (
                hasattr(request, "temperature_flag")
                and request.temperature_flag
                and hasattr(request, "temperature")
            ):
                temperature_raw = request.temperature
                if temperature_raw is not None:
                    temperature_celsius = (
                        temperature_raw - 100
                    )  # 内部表現から摂氏に変換
                    sensor_data["temperature"] = temperature_celsius

            # 降水確率
            if (
                hasattr(request, "pop_flag")
                and request.pop_flag
                and hasattr(request, "pop")
            ):
                pop_value = request.pop
                if pop_value is not None and pop_value != 0:
                    sensor_data["precipitation_prob"] = pop_value

            if self.debug:
                fields = []
                if "weather_code" in sensor_data:
                    fields.append(f"weather:{sensor_data['weather_code']}")
                if "temperature" in sensor_data:
                    fields.append(f"temp:{sensor_data['temperature']}℃")
                if "precipitation_prob" in sensor_data:
                    fields.append(f"pop:{sensor_data['precipitation_prob']}%")
                print(f"  [デバッグ] 固定長: {' '.join(fields) if fields else 'なし'}")

        except Exception as e:
            if self.debug:
                print(f"  [デバッグ] 固定長フィールド処理エラー: {e}")

        # 拡張フィールドから警報・災害情報を抽出
        if hasattr(request, "ex_field") and request.ex_field:
            try:
                ex_dict = (
                    request.ex_field.to_dict()
                    if hasattr(request.ex_field, "to_dict")
                    else {}
                )

                if self.debug:
                    ex_keys = list(ex_dict.keys()) if ex_dict else []
                    print(f"  [デバッグ] 拡張フィールド: {ex_keys}")

                # 警報情報
                if (
                    hasattr(request, "alert_flag")
                    and request.alert_flag
                    and "alert" in ex_dict
                ):
                    sensor_data["alert"] = ex_dict["alert"]

                # 災害情報
                if (
                    hasattr(request, "disaster_flag")
                    and request.disaster_flag
                    and "disaster" in ex_dict
                ):
                    sensor_data["disaster"] = ex_dict["disaster"]

                # 送信元情報
                if "source" in ex_dict:
                    sensor_data["source"] = ex_dict["source"]

            except Exception as e:
                if self.debug:
                    print(f"  [デバッグ] 拡張フィールド処理エラー: {e}")

        return sensor_data

    def _validate_sensor_data(self, sensor_data):
        """センサーデータの検証"""
        try:
            # エリアコードの検証
            area_code = sensor_data.get("area_code")
            if not area_code or area_code == "000000":
                return {"valid": False, "message": "無効なエリアコード"}

            # 気温の範囲チェック
            if "temperature" in sensor_data:
                temp = sensor_data["temperature"]
                if temp < -50 or temp > 60:
                    return {"valid": False, "message": f"気温が範囲外: {temp}℃"}

            # 降水確率の範囲チェック
            if "precipitation_prob" in sensor_data:
                pop = sensor_data["precipitation_prob"]
                if pop < 0 or pop > 100:
                    return {"valid": False, "message": f"降水確率が範囲外: {pop}%"}

            # タイムスタンプの妥当性チェック
            timestamp = sensor_data.get("timestamp", 0)
            current_time = int(datetime.now().timestamp())
            time_diff = abs(current_time - timestamp)
            if time_diff > 3600:  # 1時間以上の差
                return {
                    "valid": False,
                    "message": f"タイムスタンプが古すぎます: {time_diff}秒の差",
                }

            return {"valid": True, "message": "OK"}

        except Exception as e:
            return {"valid": False, "message": f"検証エラー: {str(e)}"}

    def _process_sensor_data(self, sensor_data, request):
        """センサーデータの処理"""
        processed_data = sensor_data.copy()

        # 警報処理
        if self.enable_alert_processing and "alert" in sensor_data:
            processed_data["alert_processed"] = True
            if self.debug:
                print(f"  警報データを処理しました: {sensor_data['alert']}")

        # 災害情報処理
        if self.enable_disaster_processing and "disaster" in sensor_data:
            processed_data["disaster_processed"] = True
            if self.debug:
                print(f"  災害情報を処理しました: {sensor_data['disaster']}")

        # 処理時刻を追加
        processed_data["processed_at"] = datetime.now().isoformat()

        return processed_data

    # _setup_log_file method removed

    # _log_report_data method removed

    def _save_to_database(self, request, sensor_data, source_addr=None):
        """Redisに直接保存（QueryServer参照用のDB）。"""
        try:
            # 遅延インポートで依存を局所化
            from WIPServerPy.data.redis_manager import WeatherRedisManager

            # キープレフィックス（テスト検証用）を環境変数/設定から取得
            # 優先順位: REPORT_DB_KEY_PREFIX > [database].key_prefix > REDIS_KEY_PREFIX
            key_prefix = (
                os.getenv("REPORT_DB_KEY_PREFIX")
                or self.config.get("database", "key_prefix", None)
                or os.getenv("REDIS_KEY_PREFIX")
                or ""
            )

            rm = WeatherRedisManager(debug=self.debug, key_prefix=key_prefix)

            # エリアコードはRequestから直接正規化して取得（内部値優先）
            def _normalize_area_code(val):
                try:
                    return f"{int(val):06d}"
                except Exception:
                    return str(val).zfill(6)

            # 内部整数 (_area_code) を最優先で使用
            area_internal = getattr(request, "_area_code", None)
            if area_internal is not None:
                area_code = _normalize_area_code(area_internal)
            else:
                area_code = _normalize_area_code(getattr(request, "area_code", None))
            if not area_code:
                return

            # 既存データを取得してマージ
            existing = rm.get_weather_data(area_code)
            if existing is None:
                # 新規キーの場合は7要素の空配列で初期化
                existing = rm._create_default_weather_data()
                existing["area_name"] = ""

            new_data = existing.copy()

            # dayインデックスを取得（リクエストからdayフィールドを取得）
            day_index = getattr(request, 'day', 0)
            if day_index < 0 or day_index >= 7:
                day_index = 0  # 範囲外の場合は0日目に格納

            # 7要素配列の指定された位置に格納
            if "weather_code" in sensor_data:
                if not isinstance(new_data["weather"], list):
                    new_data["weather"] = [None] * 7
                new_data["weather"][day_index] = sensor_data["weather_code"]
            if "temperature" in sensor_data:
                if not isinstance(new_data["temperature"], list):
                    new_data["temperature"] = [None] * 7
                new_data["temperature"][day_index] = sensor_data["temperature"]
            if "precipitation_prob" in sensor_data:
                if not isinstance(new_data["precipitation_prob"], list):
                    new_data["precipitation_prob"] = [None] * 7
                new_data["precipitation_prob"][day_index] = sensor_data["precipitation_prob"]

            # 警報・災害は配列をマージ（重複除去）
            if "alert" in sensor_data:
                alert_data = sensor_data.get("alert")
                if isinstance(alert_data, str):
                    # 文字列の場合はカンマ区切りでリストに変換
                    alerts = [item.strip() for item in alert_data.split(",") if item.strip()]
                elif isinstance(alert_data, list):
                    alerts = alert_data
                else:
                    alerts = []
                
                # 重複除去
                alerts = list(dict.fromkeys(alerts))
                if alerts:
                    new_data["warnings"] = alerts
            if "disaster" in sensor_data:
                disaster_data = sensor_data.get("disaster")
                if isinstance(disaster_data, str):
                    # 文字列の場合はカンマ区切りでリストに変換
                    disasters = [item.strip() for item in disaster_data.split(",") if item.strip()]
                elif isinstance(disaster_data, list):
                    disasters = disaster_data
                else:
                    disasters = []
                
                # 重複除去
                disasters = list(dict.fromkeys(disasters))
                if disasters:
                    new_data["disaster"] = disasters

            rm.update_weather_data(area_code, new_data)
            
            # タイムスタンプを更新（レポートクライアント経由）
            current_time = datetime.now().isoformat()
            rm.update_timestamp(area_code, current_time, "report_client")
            
            if self.debug:
                ac_prop = getattr(request, "area_code", None)
                print(
                    f"  [{self.server_name}] DB保存: key_prefix='{key_prefix}' area='{area_code}' (prop={ac_prop})"
                )
                print(f"  [{self.server_name}] タイムスタンプ更新: {area_code} - {current_time}")
        except Exception as e:
            if self.debug:
                print(f"  [{self.server_name}] DB保存失敗: {e}")

    def create_response(self, request):
        """
        レスポンスを作成（BaseServerパターン - Type 4 → Type 5）

        Args:
            request: ReportRequestオブジェクト

        Returns:
            レスポンスのバイナリデータ
        """
        start_time = time.time()
        timing_info = {}

        try:
            # レポートカウント増加
            with self.lock:
                self.report_count += 1

            # 常にリクエスト受信をログ出力
            print(f"\n[{self.server_name}] ===== REPORT REQUEST RECEIVED =====")
            print(f"  パケットID: {request.packet_id}")
            print(f"  エリアコード: {request.area_code}")
            print(f"  タイムスタンプ: {time.ctime(request.timestamp)}")
            print(f"  レポート番号: {self.report_count}")

            # センサーデータの抽出（時間計測）
            extract_start = time.time()
            sensor_data = self._extract_sensor_data(request)
            timing_info["extract"] = time.time() - extract_start
            print(f"  センサーデータタイプ: {sensor_data.get('data_types', [])}")

            # データ処理（時間計測）
            process_start = time.time()
            processed_data = self._process_sensor_data(sensor_data, request)
            timing_info["process"] = time.time() - process_start

            # ログファイル記録は削除

            # データベース保存（オプション）
            if self.enable_database:
                db_start = time.time()
                self._save_to_database(request, sensor_data, None)
                timing_info["database"] = time.time() - db_start

            # 受信データのクライアント転送（オプション）
            if getattr(self, "forward_enabled", False):
                if self.forward_async:
                    # スレッドプールで非同期転送（ACKはバックグラウンドで待機）
                    try:
                        self.thread_pool.submit(self._forward_report_as_client, sensor_data)
                        if self.debug:
                            print(
                                f"[{self.server_name}] Forward submitted to {self.forward_host}:{self.forward_port}"
                            )
                    except Exception as e:
                        if self.debug:
                            print(f"[{self.server_name}] Forward submit failed: {e}")
                else:
                    # 同期転送（必要な場合のみ）
                    self._forward_report_as_client(sensor_data)

            # ACKレスポンス（Type 5）を作成（時間計測）
            response_start = time.time()
            response = ReportResponse.create_ack_response(
                request=request, version=self.version
            )

            # 認証フラグ設定（認証が有効でレスポンス認証が有効な場合）
            if self.auth_enabled and self._get_response_auth_config():
                response.enable_auth(self.auth_passphrase)
                response.set_auth_flags()
                print(f"[{self.server_name}] Response Auth: ✓")
            else:
                print(f"[{self.server_name}] Response Auth: disabled")

            timing_info["response"] = time.time() - response_start

            # 成功カウント
            with self.lock:
                self.success_count += 1

            # 総処理時間
            timing_info["total"] = time.time() - start_time

            print(f"  ✓ ACKレスポンス作成完了 ({timing_info['response']*1000:.1f}ms)")
            print(f"  ✓ 成功率: {(self.success_count/self.report_count)*100:.1f}%")

            # 処理時間の詳細を出力
            print(f"  📊 処理時間詳細:")
            print(f"    - データ抽出: {timing_info['extract']*1000:.1f}ms")
            print(f"    - データ処理: {timing_info['process']*1000:.1f}ms")
            # ログ記録表示は削除
            if "database" in timing_info:
                print(f"    - DB保存: {timing_info['database']*1000:.1f}ms")
            print(f"    - レスポンス作成: {timing_info['response']*1000:.1f}ms")
            print(f"    - 合計: {timing_info['total']*1000:.1f}ms")

            # 遅延警告（20ms以上の場合）
            if timing_info["total"] > 0.02:
                print(
                    f"  ⚠️  遅延検出: 総処理時間が{timing_info['total']*1000:.1f}msです"
                )
                # ログ記録関連の警告は削除
                if timing_info["extract"] > 0.005:
                    print(
                        f"     - データ抽出が遅い: {timing_info['extract']*1000:.1f}ms"
                    )

            print(f"  ===== RESPONSE SENT =====\n")

            # 統一されたデバッグ出力を追加
            debug_data = {
                "area_code": request.area_code,
                "timestamp": request.timestamp,
                "weather_code": sensor_data.get("weather_code", "N/A"),
                "temperature": sensor_data.get("temperature", "N/A"),
                "precipitation_prob": sensor_data.get("precipitation_prob", "N/A"),
                "alert": sensor_data.get("alert", []),
                "disaster": sensor_data.get("disaster", []),
            }
            self.packet_debug_logger.log_unified_packet_received(
                "IoT report processing", timing_info["total"], debug_data
            )

            return response.to_bytes()

        except Exception as e:
            error_msg = f"レスポンス作成中にエラーが発生しました: {e}"
            print(f"❌ [{self.server_name}] {error_msg}")
            if self.debug:
                traceback.print_exc()
            raise

    def parse_request(self, data):
        """
        リクエストデータをパース（レポートパケット専用）

        Args:
            data: 受信したバイナリデータ

        Returns:
            ReportRequestインスタンス
        """
        # パケットサイズの事前チェック
        if len(data) < 16:
            from WIPCommonPy.packet.core.exceptions import BitFieldError
            raise BitFieldError(f"パケットサイズが不足しています。最小16バイト必要ですが、{len(data)}バイトしか受信していません。")
        
        # まず基本的なパケットを解析してタイプを確認
        from WIPCommonPy.packet import Request

        try:
            temp_request = Request.from_bytes(data)
            packet_type = temp_request.type
        except Exception as e:
            if self.debug:
                print(f"  [Debug] パケット解析エラー: {e}")
            raise

        # Type 4のみサポート
        if packet_type == 4:
            return ReportRequest.from_bytes(data)
        else:
            raise ValueError(f"サポートされていないパケットタイプ: {packet_type}")

    def _debug_print_request(self, data, parsed, addr=None):
        """リクエストのデバッグ情報を出力（統一フォーマット）"""
        if not self.debug:
            return

        details = {
            "Version": getattr(parsed, "version", "N/A"),
            "Type": getattr(parsed, "type", "N/A"),
            "Area Code": getattr(parsed, "area_code", "N/A"),
            "Packet ID": getattr(parsed, "packet_id", "N/A"),
            "Timestamp": time.ctime(getattr(parsed, "timestamp", 0)),
            "Weather": getattr(parsed, "weather_flag", False),
            "Temperature": getattr(parsed, "temperature_flag", False),
            "POP": getattr(parsed, "pop_flag", False),
            "Alert": getattr(parsed, "alert_flag", False),
            "Disaster": getattr(parsed, "disaster_flag", False),
        }

        sensor_data = self._extract_sensor_data(parsed)
        details["Sensor Data"] = sensor_data

        log = UnifiedLogFormatter.format_communication_log(
            server_name=self.server_name,
            direction="recv from",
            remote_addr=addr[0] if addr else "unknown",
            remote_port=addr[1] if addr else 0,
            packet_size=len(data),
            packet_details=details,
        )
        print(log)

    def get_statistics(self):
        """サーバー統計情報を取得"""
        with self.lock:
            return {
                "server_name": self.server_name,
                "total_requests": self.request_count,
                "total_reports": self.report_count,
                "successful_reports": self.success_count,
                "errors": self.error_count,
                "success_rate": (
                    (self.success_count / self.report_count * 100)
                    if self.report_count > 0
                    else 0
                ),
                "uptime": (
                    time.time() - self.start_time if hasattr(self, "start_time") else 0
                ),
            }

    def _cleanup(self):
        """派生クラス固有のクリーンアップ処理"""
        if self.debug:
            print(f"[{self.server_name}] クリーンアップ完了")


