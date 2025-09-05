"""
Query Client - 改良版（専用パケットクラス使用）
Query Serverとの通信を行うクライアント（サーバー間通信用）
"""

import socket
import concurrent.futures
import os
import logging
import asyncio
from datetime import datetime, timedelta
from WIPCommonPy.packet import QueryRequest, QueryResponse
from WIPCommonPy.packet.debug import create_debug_logger
from WIPCommonPy.clients.utils.packet_id_generator import PacketIDGenerator12Bit
from WIPCommonPy.clients.utils import receive_with_id, receive_with_id_async, safe_sock_sendto
from WIPCommonPy.utils.cache import Cache
from WIPCommonPy.utils.network import resolve_ipv4

PIDG = PacketIDGenerator12Bit()


class QueryClient:
    """Query Serverと通信するクライアント（専用パケットクラス使用）"""

    def close(self):
        """クライアントのリソースを解放する"""
        # 現在の実装ではメソッドごとにsocketを作成・クローズしているため、
        # このメソッドは空実装とする
        pass

    def __init__(
        self,
        host=None,
        port=None,
        debug=False,
        cache_ttl_minutes=10,
        cache_enabled=True,
    ):
        if host is None:
            host = os.getenv("QUERY_GENERATOR_HOST", "wip.ncc.onl")
        if port is None:
            port = int(os.getenv("QUERY_GENERATOR_PORT", "4111"))
        """
        初期化
        
        Args:
            host: Query Serverのホスト
            port: Query Serverのポート
            debug: デバッグモード
            cache_ttl_minutes: キャッシュの有効期限（分）
        """
        self.host = resolve_ipv4(host)
        self.port = port
        self.debug = debug
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.debug_logger = create_debug_logger(__name__, debug)
        self.VERSION = 1

        # 認証設定を初期化
        self._init_auth_config()

        # キャッシュの初期化
        self.cache = Cache(
            default_ttl=timedelta(minutes=cache_ttl_minutes), enabled=cache_enabled
        )
        self.cache_enabled = cache_enabled
        self.logger.debug(
            f"Query client cache initialized with TTL: {cache_ttl_minutes} minutes (enabled={cache_enabled})"
        )

    def _init_auth_config(self):
        """認証設定を環境変数から読み込み"""
        # QueryServer向けのリクエスト認証設定
        auth_enabled = (
            os.getenv("QUERY_GENERATOR_REQUEST_AUTH_ENABLED", "false").lower() == "true"
        )
        auth_passphrase = os.getenv("QUERY_SERVER_PASSPHRASE", "")

        self.auth_enabled = auth_enabled
        self.auth_passphrase = auth_passphrase

    def _get_response_auth_config(self):
        """レスポンス認証設定を取得"""
        return (
            os.getenv("QUERY_SERVER_RESPONSE_AUTH_ENABLED", "false").lower() == "true"
        )
    
    def _verify_response_auth(self, response):
        """
        レスポンス認証を検証
        
        Args:
            response: QueryResponse オブジェクト
            
        Returns:
            bool: 認証が成功した場合True、失敗またはスキップした場合False
        """
        # レスポンス認証が無効な場合は常にTrue
        if not self._get_response_auth_config():
            return True
            
        # レスポンスのresponse_authフラグをチェック
        # フラグが0の場合は認証検証をスキップ
        if not hasattr(response, 'response_auth') or response.response_auth != 1:
            self.logger.debug("Response authentication skipped - response_auth flag not set")
            return True
            
        # パスフレーズが設定されていない場合は失敗
        if not self.auth_passphrase:
            self.logger.warning("Response authentication enabled but passphrase not set")
            return False
            
        # レスポンスパケットのタイムスタンプとパケットIDを使って再計算
        from WIPCommonPy.utils.auth import WIPAuth
        
        try:
            # レスポンスパケットの認証ハッシュを拡張フィールドから取得
            if not hasattr(response, "ex_field") or not response.ex_field:
                self.logger.warning("Response authentication required but no extended field found")
                return False
                
            if not response.ex_field.contains("auth_hash"):
                self.logger.warning("Response authentication required but no auth_hash found")
                return False
                
            auth_hash_str = response.ex_field.auth_hash
            if not auth_hash_str:
                self.logger.warning("Response authentication required but no auth_hash found")
                return False
                
            # hex文字列をバイト列に変換
            received_hash = bytes.fromhex(auth_hash_str)
            
            # レスポンスパケットのタイムスタンプとパケットIDで認証ハッシュを再計算
            is_valid = WIPAuth.verify_auth_hash(
                packet_id=response.packet_id,
                timestamp=response.timestamp,
                passphrase=self.auth_passphrase,
                received_hash=received_hash
            )
            
            if not is_valid:
                self.logger.error("Response authentication verification failed")
                return False
                
            self.logger.debug("Response authentication verification successful")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during response authentication verification: {e}")
            return False

    def _get_cache_key(
        self,
        area_code,
        weather,
        temperature,
        precipitation_prob,
        alert,
        disaster,
        day=0,
    ):
        """
        クエリ条件からキャッシュキーを生成

        Args:
            area_code: エリアコード
            weather: 天気データフラグ
            temperature: 気温データフラグ
            precipitation_prob: 降水確率データフラグ
            alert: 警報データフラグ
            disaster: 災害データフラグ
            day: 日数

        Returns:
            str: キャッシュキー
        """
        # 各フラグを文字列化してキーに含める
        flags = f"w{int(weather)}t{int(temperature)}p{int(precipitation_prob)}a{int(alert)}d{int(disaster)}"
        return f"query:{area_code}:{flags}:d{day}"

    def _create_cached_response(self, cached_data, area_code):
        """
        キャッシュされたデータから簡易的なQueryResponseを作成

        Args:
            cached_data: キャッシュされたデータ
            area_code: エリアコード

        Returns:
            dict: 簡易的なレスポンスデータ
        """
        # キャッシュからの場合はsourceを'cache'として返す
        result = cached_data.copy()
        result["source"] = "cache"
        result["area_code"] = area_code

        # キャッシュされた気温はパケット形式（+100）なので実際の気温に変換
        if "temperature" in result and result["temperature"] is not None:
            result["temperature"] = result["temperature"] - 100

        return result

    def get_weather_data(
        self,
        area_code,
        weather=False,
        temperature=False,
        precipitation_prob=False,
        wind=False,
        alert=False,
        disaster=False,
        source=None,
        timeout=5.0,
        use_cache=True,
        day=0,
        force_refresh=False,
    ):
        """
        指定されたエリアの気象データを取得する（改良版・キャッシュ対応）

        Args:
            area_code: エリアコード
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation_prob: 降水確率データを取得するか
            alert: 警報データを取得するか
            disaster: 災害情報データを取得するか
            source: 送信元情報 (ip, port) のタプル
            timeout: タイムアウト時間（秒）
            use_cache: キャッシュを使用するかどうか
            day: 予報日
            force_refresh: キャッシュを無視して強制的に再取得するか

        Returns:
            dict: 取得した気象データ
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)

        try:
            start_time = datetime.now()

            # キャッシュチェック
            if use_cache and not force_refresh:
                cache_key = self._get_cache_key(
                    area_code,
                    weather,
                    temperature,
                    precipitation_prob,
                    alert,
                    disaster,
                    day,
                )
                cached_data = self.cache.get(cache_key)

                if cached_data:
                    cached_response = self._create_cached_response(
                        cached_data, area_code
                    )
                    cache_time = datetime.now() - start_time
                    cached_response["timing"] = {
                        "request_creation": 0,
                        "network_roundtrip": 0,
                        "response_parsing": 0,
                        "total_time": cache_time.total_seconds() * 1000,
                    }
                    cached_response["cache_hit"] = True
                    return cached_response
            # 専用クラスでリクエスト作成（大幅に簡潔になった）
            request_start = datetime.now()
            request = QueryRequest.create_query_request(
                area_code=area_code,
                packet_id=PIDG.next_id(),
                weather=weather,
                temperature=temperature,
                precipitation_prob=precipitation_prob,
                wind=wind,
                alert=alert,
                disaster=disaster,
                source=source,
                day=day,
                version=self.VERSION,
            )

            # 認証設定を適用（認証が有効な場合）
            if self.auth_enabled and self.auth_passphrase:
                request.enable_auth(self.auth_passphrase)
                request.set_auth_flags()

            # レスポンス認証フラグの設定
            if self._get_response_auth_config():
                request.response_auth = 1

            request_time = datetime.now() - request_start

            self.debug_logger.log_request(request, "QUERY REQUEST")

            # リクエスト送信
            packet_bytes = request.to_bytes()
            network_start = datetime.now()
            sock.sendto(packet_bytes, (self.host, self.port))

            # レスポンス受信（専用クラス使用）
            response_data, server_addr = receive_with_id(
                sock, request.packet_id, timeout
            )
            network_time = datetime.now() - network_start

            # レスポンス解析（専用クラス使用）
            parse_start = datetime.now()
            response = QueryResponse.from_bytes(response_data)
            parse_time = datetime.now() - parse_start

            self.debug_logger.log_response(response, "QUERY RESPONSE")

            # レスポンス認証検証
            if response and not self._verify_response_auth(response):
                self.logger.error("Response authentication verification failed")
                return None

            # 専用クラスのメソッドで結果を簡単に取得
            if response.is_success():
                result = response.get_weather_data()

                # レスポンスが有効で、キャッシュ使用が有効な場合はキャッシュに保存
                if use_cache and result:
                    cache_key = self._get_cache_key(
                        area_code,
                        weather,
                        temperature,
                        precipitation_prob,
                        alert,
                        disaster,
                        day,
                    )
                    # タイミング情報を除いてキャッシュに保存
                    cache_data = {k: v for k, v in result.items() if k != "timing"}

                    # 気温はパケット形式（+100）でキャッシュに保存（設計の一貫性のため）
                    if (
                        "temperature" in cache_data
                        and cache_data["temperature"] is not None
                    ):
                        cache_data["temperature"] = cache_data["temperature"] + 100

                    self.cache.set(cache_key, cache_data)

                # タイミング情報を追加
                total_time = datetime.now() - start_time
                result["timing"] = {
                    "request_creation": request_time.total_seconds() * 1000,
                    "network_roundtrip": network_time.total_seconds() * 1000,
                    "response_parsing": parse_time.total_seconds() * 1000,
                    "total_time": total_time.total_seconds() * 1000,
                }
                result["cache_hit"] = False

                # 統一フォーマットでの成功ログ出力
                execution_time = total_time.total_seconds()
                self.debug_logger.log_unified_packet_received(
                    "Direct request", execution_time, result
                )

                return result
            else:
                self.logger.error("420: クライアントエラー: クエリサーバが見つからない")
                return {"error": "Query request failed", "response_type": response.type}

        except socket.timeout:
            self.logger.error("421: クライアントエラー: クエリサーバ接続タイムアウト")
            return {"error": "Request timeout", "timeout": timeout}
        except Exception as e:
            if self.debug:
                self.logger.exception("Traceback:")
            self.logger.error(
                f"420: クライアントエラー: クエリサーバが見つからない: {e}"
            )
            return {"420": str(e)}
        finally:
            sock.close()

    async def get_weather_data_async(
        self,
        area_code,
        weather=False,
        temperature=False,
        precipitation_prob=False,
        wind=False,
        alert=False,
        disaster=False,
        source=None,
        timeout=5.0,
        use_cache=True,
        day=0,
        force_refresh=False,
        raw_packet: bool = False,
    ):
        """
        非同期版 get_weather_data

        Args:
            area_code: エリアコード
            raw_packet: True の場合は QueryResponse をそのまま返す
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)

        try:
            start_time = datetime.now()

            if use_cache and not force_refresh and not raw_packet:
                cache_key = self._get_cache_key(
                    area_code,
                    weather,
                    temperature,
                    precipitation_prob,
                    alert,
                    disaster,
                    day,
                )
                cached_data = self.cache.get(cache_key)

                if cached_data:
                    cached_response = self._create_cached_response(
                        cached_data, area_code
                    )
                    cache_time = datetime.now() - start_time
                    cached_response["timing"] = {
                        "request_creation": 0,
                        "network_roundtrip": 0,
                        "response_parsing": 0,
                        "total_time": cache_time.total_seconds() * 1000,
                    }
                    cached_response["cache_hit"] = True
                    return cached_response

            request_start = datetime.now()
            request = QueryRequest.create_query_request(
                area_code=area_code,
                packet_id=PIDG.next_id(),
                weather=weather,
                temperature=temperature,
                precipitation_prob=precipitation_prob,
                wind=wind,
                alert=alert,
                disaster=disaster,
                source=source,
                day=day,
                version=self.VERSION,
            )

            if self.auth_enabled and self.auth_passphrase:
                request.enable_auth(self.auth_passphrase)
                request.set_auth_flags()

            # レスポンス認証フラグの設定（非同期版）
            if self._get_response_auth_config():
                request.response_auth = 1

            request_time = datetime.now() - request_start

            self.debug_logger.log_request(request, "QUERY REQUEST")

            packet_bytes = request.to_bytes()
            loop = asyncio.get_running_loop()
            network_start = datetime.now()
            await safe_sock_sendto(loop, sock, packet_bytes, (self.host, self.port))

            response_data, server_addr = await receive_with_id_async(
                sock, request.packet_id, timeout
            )
            network_time = datetime.now() - network_start

            parse_start = datetime.now()
            response = QueryResponse.from_bytes(response_data)
            parse_time = datetime.now() - parse_start

            self.debug_logger.log_response(response, "QUERY RESPONSE")

            # レスポンス認証検証（非同期版）
            if response and not self._verify_response_auth(response):
                self.logger.error("Response authentication verification failed")
                return None

            if raw_packet:
                return response

            if response.is_success():
                result = response.get_weather_data()

                if use_cache and result:
                    cache_key = self._get_cache_key(
                        area_code,
                        weather,
                        temperature,
                        precipitation_prob,
                        alert,
                        disaster,
                        day,
                    )
                    cache_data = {k: v for k, v in result.items() if k != "timing"}

                    if (
                        "temperature" in cache_data
                        and cache_data["temperature"] is not None
                    ):
                        cache_data["temperature"] = cache_data["temperature"] + 100

                    self.cache.set(cache_key, cache_data)

                total_time = datetime.now() - start_time
                result["timing"] = {
                    "request_creation": request_time.total_seconds() * 1000,
                    "network_roundtrip": network_time.total_seconds() * 1000,
                    "response_parsing": parse_time.total_seconds() * 1000,
                    "total_time": total_time.total_seconds() * 1000,
                }
                result["cache_hit"] = False

                execution_time = total_time.total_seconds()
                self.debug_logger.log_unified_packet_received(
                    "Direct request", execution_time, result
                )

                return result
            else:
                self.logger.error("420: クライアントエラー: クエリサーバが見つからない")
                return response if raw_packet else {"error": "Query request failed", "response_type": response.type}

        except asyncio.TimeoutError:
            self.logger.error("421: クライアントエラー: クエリサーバ接続タイムアウト")
            return {"error": "Request timeout", "timeout": timeout}
        except Exception as e:
            if self.debug:
                self.logger.exception("Traceback:")
            self.logger.error(
                f"420: クライアントエラー: クエリサーバが見つからない: {e}"
            )
            return {"420": str(e)}
        finally:
            sock.close()

    def get_cache_stats(self):
        """
        キャッシュの統計情報を取得

        Returns:
            dict: キャッシュの統計情報
        """
        return {
            "cache_size": self.cache.size(),
            "cache_ttl_minutes": self.cache.default_ttl.total_seconds() / 60,
        }

    def clear_cache(self):
        """
        キャッシュをクリア
        """
        self.cache.clear()
        self.logger.debug("Query client cache cleared")

    def get_weather_simple(
        self, area_code, include_all=False, timeout=5.0, use_cache=True
    ):
        """
        簡便なメソッド：基本的な気象データを一括取得（統一命名規則版・キャッシュ対応）

        Args:
            area_code: エリアコード
            include_all: すべてのデータを取得するか（警報・災害情報も含む）
            timeout: タイムアウト時間（秒）
            use_cache: キャッシュを使用するかどうか

        Returns:
            dict: 取得した気象データ
        """
        return self.get_weather_data(
            area_code=area_code,
            weather=True,
            temperature=True,
            precipitation_prob=True,
            alert=include_all,
            disaster=include_all,
            timeout=timeout,
            use_cache=use_cache,
        )

    def test_concurrent_requests(
        self, area_codes, num_threads=10, requests_per_thread=5
    ):
        """
        並列リクエストのテストを実行する（改良版）

        Args:
            area_codes: テストするエリアコードのリスト
            num_threads: 並列スレッド数
            requests_per_thread: スレッドあたりのリクエスト数

        Returns:
            dict: テスト結果
        """
        results = []
        errors = []

        def worker_thread(thread_id):
            thread_results = []
            thread_errors = []

            for i in range(requests_per_thread):
                area_code = area_codes[i % len(area_codes)]
                try:
                    result = self.get_weather_simple(
                        area_code=area_code,
                        include_all=(i % 2 == 0),  # 交互に全データ取得
                    )

                    if "error" not in result:
                        thread_results.append(
                            {
                                "thread_id": thread_id,
                                "request_id": i,
                                "area_code": area_code,
                                "timing": result.get("timing", {}),
                                "success": True,
                                "has_weather": "weather_code" in result,
                                "has_temperature": "temperature" in result,
                                "has_precipitation_prob": "precipitation_prob"
                                in result,
                            }
                        )
                    else:
                        thread_errors.append(
                            {
                                "thread_id": thread_id,
                                "request_id": i,
                                "area_code": area_code,
                                "error": result["error"],
                            }
                        )

                except Exception as e:
                    thread_errors.append(
                        {
                            "thread_id": thread_id,
                            "request_id": i,
                            "area_code": area_code,
                            "error": str(e),
                        }
                    )

            return thread_results, thread_errors

        self.logger.info(
            f"Starting concurrent test: {num_threads} threads, {requests_per_thread} requests each"
        )
        start_time = datetime.now()

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(num_threads)]

            for future in concurrent.futures.as_completed(futures):
                thread_results, thread_errors = future.result()
                results.extend(thread_results)
                errors.extend(thread_errors)

        total_time = datetime.now() - start_time

        # 統計情報の計算
        successful_requests = len(results)
        failed_requests = len(errors)
        total_requests = successful_requests + failed_requests

        if successful_requests > 0:
            avg_response_time = (
                sum(r["timing"].get("total_time", 0) for r in results)
                / successful_requests
            )
            min_response_time = min(r["timing"].get("total_time", 0) for r in results)
            max_response_time = max(r["timing"].get("total_time", 0) for r in results)
        else:
            avg_response_time = min_response_time = max_response_time = 0

        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": (
                (successful_requests / total_requests * 100)
                if total_requests > 0
                else 0
            ),
            "total_test_time": total_time.total_seconds(),
            "requests_per_second": (
                total_requests / total_time.total_seconds()
                if total_time.total_seconds() > 0
                else 0
            ),
            "avg_response_time_ms": avg_response_time,
            "min_response_time_ms": min_response_time,
            "max_response_time_ms": max_response_time,
            "errors": errors,
        }

    # 後方互換性のためのエイリアスメソッド
    def get_weather_data_simple(self, area_code, include_all=False, timeout=5.0):
        """後方互換性のため - get_weather_simple()を使用してください"""
        return self.get_weather_simple(area_code, include_all, timeout)


def main():
    """メイン関数 - 使用例（専用パケットクラス版）"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Query Client Example (Enhanced with Specialized Packet Classes)")
    logger.info("=" * 70)

    client = QueryClient(debug=True)

    # 単一リクエストのテスト
    logger.info("\n1. Single Request Test")
    logger.info("-" * 30)

    result = client.get_weather_data(
        area_code="011000",  # 札幌
        weather=True,
        temperature=True,
        precipitation_prob=True,
        alert=True,
        disaster=True,
        source=("127.0.0.1", 9999),
    )

    if "error" not in result:
        client.debug_logger.log_success_result(result, "SINGLE REQUEST")
    else:
        logger.error(f"✗ Request failed: {result['error']}")

    # 簡便メソッドのテスト
    logger.info("\n2. Simple Method Test")
    logger.info("-" * 30)

    simple_result = client.get_weather_simple(
        area_code="130010", include_all=True  # 東京
    )

    if "error" not in simple_result:
        client.debug_logger.log_success_result(simple_result, "SIMPLE REQUEST")
    else:
        logger.error(f"✗ Simple request failed: {simple_result['error']}")

    # 並列リクエストのテスト
    logger.info("\n3. Concurrent Request Test")
    logger.info("-" * 30)

    test_area_codes = [
        "011000",
        "012000",
        "013000",
        "014100",
        "015000",
    ]  # 北海道の各地域

    test_result = client.test_concurrent_requests(
        area_codes=test_area_codes, num_threads=5, requests_per_thread=3
    )

    logger.info(f"Total Requests: {test_result['total_requests']}")
    logger.info(f"Successful: {test_result['successful_requests']}")
    logger.info(f"Failed: {test_result['failed_requests']}")
    logger.info(f"Success Rate: {test_result['success_rate']:.1f}%")
    logger.info(f"Requests/Second: {test_result['requests_per_second']:.1f}")
    logger.info(f"Avg Response Time: {test_result['avg_response_time_ms']:.2f}ms")
    logger.info(f"Min Response Time: {test_result['min_response_time_ms']:.2f}ms")
    logger.info(f"Max Response Time: {test_result['max_response_time_ms']:.2f}ms")

    if test_result["errors"]:
        logger.info(f"\nErrors ({len(test_result['errors'])}):")
        for error in test_result["errors"][:5]:  # 最初の5個のエラーのみ表示
            logger.info(
                f"  Thread {error['thread_id']}, Request {error['request_id']}: {error['error']}"
            )

    logger.info("\n" + "=" * 70)
    logger.info("Enhanced Query Client Example completed")
    logger.info("✓ Using specialized packet classes for improved usability")
    logger.info("✓ Simplified API with better error handling")
    logger.info("✓ Automatic data conversion and validation")


