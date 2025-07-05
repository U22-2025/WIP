"""
Query Client - 改良版（専用パケットクラス使用）
Query Serverとの通信を行うクライアント（サーバー間通信用）
"""

import socket
import struct
import time
import threading
import concurrent.futures
import os
import logging
from datetime import datetime, timedelta
from ..packet import QueryRequest, QueryResponse
from .utils.packet_id_generator import PacketIDGenerator12Bit
from ..utils.cache import Cache
import traceback
PIDG = PacketIDGenerator12Bit()


class QueryClient:
    """Query Serverと通信するクライアント（専用パケットクラス使用）"""
    
    def close(self):
        """クライアントのリソースを解放する"""
        # 現在の実装ではメソッドごとにsocketを作成・クローズしているため、
        # このメソッドは空実装とする
        pass
    
    def __init__(self, host=None, port=None, debug=False, cache_ttl_minutes=10,
                 auth_enabled=False, auth_passphrase=None):
        if host is None:
            host = os.getenv('QUERY_SERVER_HOST', 'localhost')
        if port is None:
            port = int(os.getenv('QUERY_SERVER_PORT', '4111'))
        """
        初期化
        
        Args:
            host: Query Serverのホスト
            port: Query Serverのポート
            debug: デバッグモード
            cache_ttl_minutes: キャッシュの有効期限（分）
            auth_enabled: 認証を有効にするか
            auth_passphrase: 認証用パスフレーズ
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.auth_enabled = auth_enabled
        self.auth_passphrase = auth_passphrase
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.VERSION = 1
        
        # キャッシュの初期化
        self.cache = Cache(default_ttl=timedelta(minutes=cache_ttl_minutes))
        self.logger.debug(f"Query client cache initialized with TTL: {cache_ttl_minutes} minutes")
        if self.auth_enabled:
            self.logger.debug(f"Query client authentication enabled")
        
    def _hex_dump(self, data):
        """バイナリデータのhexダンプを作成"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"
        
    def _debug_print_request(self, request, area_code):
        """リクエストのデバッグ情報を出力（改良版）"""

        self.logger.debug("\n=== SENDING QUERY REQUEST PACKET ===")
        self.logger.debug(f"Total Length: {len(request.to_bytes())} bytes")
        self.logger.debug(f"Area Code: {area_code}")
        
        # 専用クラスのメソッドを使用
        if hasattr(request, 'get_requested_data_types'):
            requested_data = request.get_requested_data_types()
            self.logger.debug(f"Requested Data: {requested_data}")
            
        if hasattr(request, 'get_source_info'):
            source = request.get_source_info()
            self.logger.debug(f"Source: {source}")
        
        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(request.to_bytes()))
        self.logger.debug("============================\n")
        
    def _debug_print_response(self, response):
        """レスポンスのデバッグ情報を出力（改良版）"""
            
        self.logger.debug("\n=== RECEIVED QUERY RESPONSE PACKET ===")
        self.logger.debug(f"Total Length: {len(response.to_bytes())} bytes")
        
        # 専用クラスのメソッドを使用
        if hasattr(response, 'get_response_summary'):
            summary = response.get_response_summary()
            self.logger.debug(f"\nResponse Summary: {summary}")
            
        if hasattr(response, 'is_success'):
            self.logger.debug(f"Success: {response.is_success()}")
            
        # 気象データの詳細
        if hasattr(response, 'get_weather_code'):
            weather_code = response.get_weather_code()
            if weather_code is not None:
                self.logger.debug(f"Weather Code: {weather_code}")
                
        if hasattr(response, 'get_temperature'):
            temp = response.get_temperature()
            if temp is not None:
                self.logger.debug(f"Temperature: {temp}℃")
                
        if hasattr(response, 'get_precipitation_prob'):
            pop = response.get_precipitation_prob()
            if pop is not None:
                self.logger.debug(f"Precipitation: {pop}%")
                
        if hasattr(response, 'get_alert'):
            alert = response.get_alert()
            if alert:
                self.logger.debug(f"Alert: {alert}")
                
        if hasattr(response, 'get_disaster_info'):
            disaster = response.get_disaster_info()
            if disaster:
                self.logger.debug(f"Disaster Info: {disaster}")
        
        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(response.to_bytes()))
        self.logger.debug("==============================\n")

    def _get_cache_key(self, area_code, weather, temperature, precipitation_prob, alert, disaster, day=0):
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
        result = cached_data.copy()
        result['area_code'] = area_code
        # キャッシュからの場合のみsourceを'cache'として設定
        result['source'] = 'cache'
        
        # キャッシュされた気温はパケット形式（+100）なので実際の気温に変換
        if 'temperature' in result and result['temperature'] is not None:
            result['temperature'] = result['temperature'] - 100
            
        return result

    def get_weather_data(self, area_code, weather=False, temperature=False,
                        precipitation_prob=False, alert=False, disaster=False,
                        source=None, timeout=5.0, use_cache=True, day=0, force_refresh=False):
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
                cache_key = self._get_cache_key(area_code, weather, temperature, precipitation_prob, alert, disaster, day)
                print(f"[QueryClient] DEBUG: キャッシュチェック開始")
                print(f"[QueryClient] DEBUG: 生成されたキャッシュキー: {cache_key}")
                print(f"[QueryClient] DEBUG: use_cache={use_cache}, force_refresh={force_refresh}")
                print(f"[QueryClient] DEBUG: 現在のキャッシュサイズ: {self.cache.size()}")
                
                cached_data = self.cache.get(cache_key)
                
                if cached_data:
                    print(f"[QueryClient] DEBUG: *** キャッシュヒット *** {cache_key}")
                    print(f"[QueryClient] DEBUG: キャッシュされたデータ: {cached_data}")
                    self.logger.debug(f"Cache hit for query: {cache_key}")
                    cached_response = self._create_cached_response(cached_data, area_code)
                    cache_time = datetime.now() - start_time
                    cached_response['timing'] = {
                        'request_creation': 0,
                        'network_roundtrip': 0,
                        'response_parsing': 0,
                        'total_time': cache_time.total_seconds() * 1000
                    }
                    print(f"[QueryClient] DEBUG: キャッシュレスポンス生成完了: {cached_response}")
                    return cached_response
                else:
                    print(f"[QueryClient] DEBUG: *** キャッシュミス *** {cache_key}")
                    print(f"[QueryClient] DEBUG: サーバーにリクエストを送信します")
                    self.logger.debug(f"Cache miss for query: {cache_key}")
            else:
                print(f"[QueryClient] DEBUG: キャッシュ使用無効 (use_cache={use_cache}, force_refresh={force_refresh})")
            
            # 専用クラスでリクエスト作成（大幅に簡潔になった）
            request_start = datetime.now()
            request = QueryRequest.create_query_request(
                area_code=area_code,
                packet_id=PIDG.next_id(),
                weather=weather,
                temperature=temperature,
                precipitation_prob=precipitation_prob,
                alert=alert,
                disaster=disaster,
                source=source,
                day=day,
                version=self.VERSION
            )
            
            # 認証が有効な場合は認証情報を追加
            if self.auth_enabled and self.auth_passphrase:
                print(f"[QueryClient] DEBUG: 認証を有効化中...")
                print(f"[QueryClient] DEBUG: パスフレーズ: '{self.auth_passphrase}'")
                request.enable_auth(self.auth_passphrase)
                request.add_auth_to_extended_field()
                print(f"[QueryClient] DEBUG: 認証ハッシュが追加されました")
            
            request_time = datetime.now() - request_start
            
            self._debug_print_request(request, area_code)
            
            # リクエスト送信
            network_start = datetime.now()
            sock.sendto(request.to_bytes(), (self.host, self.port))
            
            # レスポンス受信（専用クラス使用）
            response_data, server_addr = sock.recvfrom(1024)
            network_time = datetime.now() - network_start
            
            # レスポンス解析（専用クラス使用）
            parse_start = datetime.now()
            
            # まず基本パケットでタイプを確認
            from ..packet import Request
            temp_packet = Request.from_bytes(response_data)
            packet_type = temp_packet.type
            
            print(f"[QueryClient] DEBUG: 受信パケットタイプ: {packet_type}")
            
            # タイプに応じて適切なクラスでパース
            if packet_type == 7:
                # エラーパケットの場合
                from ..packet import ErrorResponse
                response = ErrorResponse.from_bytes(response_data)
                parse_time = datetime.now() - parse_start
                
                print(f"[QueryClient] DEBUG: エラーパケットを受信: エラーコード={getattr(response, 'error_code', 'unknown')}")
                self._debug_print_response(response)
                
                # エラーレスポンスの場合は失敗として処理
                self.logger.error(f"サーバーからエラーレスポンスを受信: エラーコード {getattr(response, 'error_code', 'unknown')}")
                return {'error': 'Server returned error response', 'error_code': getattr(response, 'error_code', 'unknown'), 'response_type': response.type}
            else:
                # 通常のQueryResponseとしてパース
                response = QueryResponse.from_bytes(response_data)
                parse_time = datetime.now() - parse_start
                
                print(f"[QueryClient] DEBUG: QueryResponseを受信: success={response.is_success()}")
                self._debug_print_response(response)
            
            # 専用クラスのメソッドで結果を簡単に取得
            if hasattr(response, 'is_success') and response.is_success():
                result = response.get_weather_data()
                
                # レスポンスが有効で、キャッシュ使用が有効な場合はキャッシュに保存
                if use_cache and result:
                    cache_key = self._get_cache_key(area_code, weather, temperature, precipitation_prob, alert, disaster, day)
                    print(f"[QueryClient] DEBUG: *** キャッシュ保存開始 ***")
                    print(f"[QueryClient] DEBUG: 保存キー: {cache_key}")
                    print(f"[QueryClient] DEBUG: 元のレスポンスデータ: {result}")
                    
                    # タイミング情報を除いてキャッシュに保存
                    cache_data = {k: v for k, v in result.items() if k != 'timing'}
                    
                    # 気温はパケット形式（+100）でキャッシュに保存（設計の一貫性のため）
                    if 'temperature' in cache_data and cache_data['temperature'] is not None:
                        cache_data['temperature'] = cache_data['temperature'] + 100
                        print(f"[QueryClient] DEBUG: 気温をパケット形式に変換: {cache_data['temperature']-100}℃ -> {cache_data['temperature']}")
                    
                    print(f"[QueryClient] DEBUG: 保存するキャッシュデータ: {cache_data}")
                    self.cache.set(cache_key, cache_data)
                    print(f"[QueryClient] DEBUG: キャッシュ保存完了 (新しいサイズ: {self.cache.size()})")
                    self.logger.debug(f"Cached query result for: {cache_key} (temperature stored in packet format)")
                else:
                    print(f"[QueryClient] DEBUG: キャッシュ保存スキップ (use_cache={use_cache}, result={bool(result)})")
                
                # タイミング情報を追加
                total_time = datetime.now() - start_time
                result['timing'] = {
                    'request_creation': request_time.total_seconds() * 1000,
                    'network_roundtrip': network_time.total_seconds() * 1000,
                    'response_parsing': parse_time.total_seconds() * 1000,
                    'total_time': total_time.total_seconds() * 1000
                }
                
                if self.debug:
                    self.logger.debug("\n=== TIMING INFORMATION ===")
                    self.logger.debug(f"Request creation time: {request_time.total_seconds()*1000:.2f}ms")
                    self.logger.debug(f"Network round-trip time: {network_time.total_seconds()*1000:.2f}ms")
                    self.logger.debug(f"Response parsing time: {parse_time.total_seconds()*1000:.2f}ms")
                    self.logger.debug(f"Total operation time: {total_time.total_seconds()*1000:.2f}ms")
                    self.logger.debug("========================\n")
                
                return result
            else:
                # サーバーからエラーレスポンスが返ってきた場合の適切な処理
                if hasattr(response, 'type') and response.type == 7:
                    # エラーパケット（type=7）の場合
                    error_code = getattr(response, 'error_code', 'unknown')
                    self.logger.error(f"サーバーからエラーレスポンスを受信: エラーコード {error_code}")
                else:
                    # その他の失敗レスポンスの場合
                    self.logger.error(f"クエリリクエストが失敗しました: レスポンスタイプ {response.type}")
                
                return {'error': 'Query request failed', 'response_type': response.type}
            
        except socket.timeout:
            self.logger.error("421: クライアントエラー: クエリサーバ接続タイムアウト")
            return {'error': 'Request timeout', 'timeout': timeout}
        except Exception as e:
            if self.debug:
                self.logger.exception("Traceback:")
            self.logger.error(f"クエリリクエスト処理中にエラーが発生: {e}")
            return {'error': f'Request processing error: {str(e)}'}
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
            "cache_ttl_minutes": self.cache.default_ttl.total_seconds() / 60
        }
    
    def clear_cache(self):
        """
        キャッシュをクリア
        """
        self.cache.clear()
        self.logger.debug("Query client cache cleared")

    def get_weather_simple(self, area_code, include_all=False, timeout=5.0, use_cache=True):
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
            use_cache=use_cache
        )

    def test_concurrent_requests(self, area_codes, num_threads=10, requests_per_thread=5):
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
                        include_all=(i % 2 == 0)  # 交互に全データ取得
                    )
                    
                    if 'error' not in result:
                        thread_results.append({
                            'thread_id': thread_id,
                            'request_id': i,
                            'area_code': area_code,
                            'timing': result.get('timing', {}),
                            'success': True,
                            'has_weather': 'weather_code' in result,
                            'has_temperature': 'temperature' in result,
                            'has_precipitation_prob': 'precipitation_prob' in result
                        })
                    else:
                        thread_errors.append({
                            'thread_id': thread_id,
                            'request_id': i,
                            'area_code': area_code,
                            'error': result['error']
                        })
                        
                except Exception as e:
                    thread_errors.append({
                        'thread_id': thread_id,
                        'request_id': i,
                        'area_code': area_code,
                        'error': str(e)
                    })
            
            return thread_results, thread_errors
        
        self.logger.info(f"Starting concurrent test: {num_threads} threads, {requests_per_thread} requests each")
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
            avg_response_time = sum(r['timing'].get('total_time', 0) for r in results) / successful_requests
            min_response_time = min(r['timing'].get('total_time', 0) for r in results)
            max_response_time = max(r['timing'].get('total_time', 0) for r in results)
        else:
            avg_response_time = min_response_time = max_response_time = 0
        
        return {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'success_rate': (successful_requests / total_requests * 100) if total_requests > 0 else 0,
            'total_test_time': total_time.total_seconds(),
            'requests_per_second': total_requests / total_time.total_seconds() if total_time.total_seconds() > 0 else 0,
            'avg_response_time_ms': avg_response_time,
            'min_response_time_ms': min_response_time,
            'max_response_time_ms': max_response_time,
            'errors': errors
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
        source=("127.0.0.1", 9999)
    )
    
    if 'error' not in result:
        logger.info("✓ Request successful!")
        logger.info(f"Area Code: {result.get('area_code')}")
        logger.info(f"Weather Code: {result.get('weather_code')}")
        logger.info(f"Temperature: {result.get('temperature')}°C")
        logger.info(f"precipitation_prob: {result.get('precipitation_prob')}%")
        if result.get('alert'):
            logger.info(f"Alert: {result.get('alert')}")
        if result.get('disaster'):
            logger.info(f"Disaster Info: {result.get('disaster')}")
    else:
        logger.error(f"✗ Request failed: {result['error']}")
    
    # 簡便メソッドのテスト
    logger.info("\n2. Simple Method Test")
    logger.info("-" * 30)
    
    simple_result = client.get_weather_simple(
        area_code="130010",  # 東京
        include_all=True
    )
    
    if 'error' not in simple_result:
        logger.info("✓ Simple request successful!")
        logger.info(f"Area Code: {simple_result.get('area_code')}")
        logger.info(f"Weather Code: {simple_result.get('weather_code')}")
        logger.info(f"Temperature: {simple_result.get('temperature')}°C")
        logger.info(f"precipitation_prob: {simple_result.get('precipitation_prob')}%")
    else:
        logger.error(f"✗ Simple request failed: {simple_result['error']}")
    
    # 並列リクエストのテスト
    logger.info("\n3. Concurrent Request Test")
    logger.info("-" * 30)
    
    test_area_codes = ["011000", "012000", "013000", "014100", "015000"]  # 北海道の各地域
    
    test_result = client.test_concurrent_requests(
        area_codes=test_area_codes,
        num_threads=5,
        requests_per_thread=3
    )
    
    logger.info(f"Total Requests: {test_result['total_requests']}")
    logger.info(f"Successful: {test_result['successful_requests']}")
    logger.info(f"Failed: {test_result['failed_requests']}")
    logger.info(f"Success Rate: {test_result['success_rate']:.1f}%")
    logger.info(f"Requests/Second: {test_result['requests_per_second']:.1f}")
    logger.info(f"Avg Response Time: {test_result['avg_response_time_ms']:.2f}ms")
    logger.info(f"Min Response Time: {test_result['min_response_time_ms']:.2f}ms")
    logger.info(f"Max Response Time: {test_result['max_response_time_ms']:.2f}ms")
    
    if test_result['errors']:
        logger.info(f"\nErrors ({len(test_result['errors'])}):")
        for error in test_result['errors'][:5]:  # 最初の5個のエラーのみ表示
            logger.info(f"  Thread {error['thread_id']}, Request {error['request_id']}: {error['error']}")
    
    logger.info("\n" + "="*70)
    logger.info("Enhanced Query Client Example completed")
    logger.info("✓ Using specialized packet classes for improved usability")
    logger.info("✓ Simplified API with better error handling")
    logger.info("✓ Automatic data conversion and validation")


if __name__ == "__main__":
    main()
