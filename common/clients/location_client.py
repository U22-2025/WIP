"""
Location Client - 改良版（専用パケットクラス使用）
Location Serverとの通信を行うクライアント（サーバー間通信用）
"""

import json
import socket
import struct
import time
from datetime import datetime, timedelta
import os
import logging
from ..packet import LocationRequest, LocationResponse
from .utils.packet_id_generator import PacketIDGenerator12Bit
from ..utils.cache import Cache
import traceback

from common.environment import get as get_env
from ..utils.file_cache import PersistentCache

PIDG = PacketIDGenerator12Bit()

class LocationClient:
    """Location Serverと通信するクライアント（専用パケットクラス使用）"""

    def __init__(self, host=None, port=None, debug=False, cache_ttl_minutes=30):
        if host is None:
            host = get_env('LOCATION_RESOLVER_HOST', 'localhost')
        if port is None:
            port = get_env('LOCATION_RESOLVER_PORT', 4111, int)
        """
        初期化
        
        Args:
            host: Location Serverのホスト
            port: Location Serverのポート
            debug: デバッグモード
            cache_ttl_minutes: キャッシュの有効期限（分）
        """
        self.server_host = host
        self.server_port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.debug = debug
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        self.VERSION = 1
        
        # 認証設定を初期化
        self._init_auth_config()
        
        # 永続キャッシュの初期化
        cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'coordinate_cache.json')
        self.cache = PersistentCache(cache_file=cache_file, ttl_hours=cache_ttl_minutes/60)
        self.logger.debug(f"Location client persistent cache initialized with TTL: {cache_ttl_minutes} minutes")
        self.logger.debug(f"Cache file location: {cache_file}")
    
    def _init_auth_config(self):
        """認証設定を環境変数から読み込み"""
        # LocationServer向けのリクエスト認証設定
        auth_enabled = get_env('LOCATION_RESOLVER_REQUEST_AUTH_ENABLED', False, bool)
        auth_passphrase = get_env('LOCATION_SERVER_PASSPHRASE', '')
        
        self.auth_enabled = auth_enabled
        self.auth_passphrase = auth_passphrase
        
        if self.debug:
            self.logger.debug(f"Location client 認証設定:")
            self.logger.debug(f"  - 認証有効: {self.auth_enabled}")
            self.logger.debug(f"  - パスフレーズ設定: {'✓' if self.auth_passphrase else '✗'}")

    def _hex_dump(self, data):
        """バイナリデータのhexダンプを作成"""
        hex_str = ' '.join(f'{b:02x}' for b in data)
        ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
        return f"Hex: {hex_str}\nASCII: {ascii_str}"

    def _debug_print_request(self, request):
        """リクエストのデバッグ情報を出力（改良版）"""
        self.logger.debug("\n=== SENDING LOCATION REQUEST PACKET ===")
        self.logger.debug(f"Total Length: {len(request.to_bytes())} bytes")
        
        # 専用クラスのメソッドを使用
        coordinates = request.get_coordinates()
        source_info = request.get_source_info()
        
        self.logger.debug("\nRequest Details:")
        self.logger.debug(f"Type: {request.type}")
        self.logger.debug(f"Packet ID: {request.packet_id}")
        self.logger.debug(f"Coordinates: {coordinates}")
        self.logger.debug(f"Source: {source_info}")
        
        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(request.to_bytes()))
        self.logger.debug("===========================\n")

    def _debug_print_response(self, response):
        """レスポンスのデバッグ情報を出力（改良版）"""

        self.logger.debug("\n=== RECEIVED LOCATION RESPONSE PACKET ===")
        self.logger.debug(f"Total Length: {len(response.to_bytes())} bytes")
        
        # 専用クラスのメソッドを使用
        if hasattr(response, 'get_response_summary'):
            summary = response.get_response_summary()
            # summaryが辞書の場合、json.dumpsで安全に表示
            if isinstance(summary, dict):
                self.logger.debug(f"\nResponse Summary: {json.dumps(summary, ensure_ascii=False, indent=2)}")
            else:
                self.logger.debug(f"\nResponse Summary: {summary}")
        
        self.logger.debug("\nResponse Details:")
        self.logger.debug(f"Type: {response.type}")
        self.logger.debug(f"Area Code: {response.get_area_code()}")
        self.logger.debug(f"Valid: {response.is_valid()}")
        self.logger.debug(f"Source: {response.get_source_info()}")
        
        self.logger.debug("\nRaw Packet:")
        self.logger.debug(self._hex_dump(response.to_bytes()))
        self.logger.debug("============================\n")

    def _get_cache_key(self, latitude, longitude):
        """
        座標からキャッシュキーを生成
        
        Args:
            latitude: 緯度
            longitude: 経度
            
        Returns:
            str: キャッシュキー
        """
        # 座標を適切な精度で丸めてキャッシュキーとする
        # 小数点以下4桁（約10m精度）で丸める
        rounded_lat = round(latitude, 4)
        rounded_lon = round(longitude, 4)
        return f"coord:{rounded_lat},{rounded_lon}"

    def get_location_data(self, latitude, longitude, source=None, use_cache=True,
                         enable_debug=None, weather=True, temperature=True,
                         precipitation_prob=True, alert=False, disaster=False,
                         day=0, validate_response=True, force_refresh=False):
        """
        座標から位置情報を取得（統一命名規則版）
        
        Args:
            latitude: 緯度
            longitude: 経度
            source: 送信元情報 (ip, port) のタプル
            use_cache: キャッシュを使用するかどうか
            enable_debug: デバッグ情報を出力するか（Noneの場合はself.debugを使用）
            weather: 天気データを取得するか
            temperature: 気温データを取得するか
            precipitation_prob: 降水確率データを取得するか
            alert: 警報データを取得するか
            disaster: 災害情報データを取得するか
            day: 予報日
            validate_response: レスポンスを厳密に検証するか
            force_refresh: キャッシュを無視して強制的に再取得するか
            
        Returns:
            tuple: (LocationResponse, 処理時間)
        """
        try:
            start_time = time.time()
            
            # デバッグフラグの決定
            debug_enabled = enable_debug if enable_debug is not None else self.debug
            
            # キャッシュチェック（タイプ0の座標解決リクエストのみ）
            if use_cache and not force_refresh:
                cache_key = self._get_cache_key(latitude, longitude)
                cached_area_code = self.cache.get(cache_key)
                
                if cached_area_code:
                    self.logger.debug(f"Cache hit for coordinates ({latitude}, {longitude}): {cached_area_code}")
                    # キャッシュから取得したエリアコードでLocationResponseを作成
                    # 実際のLocationResponseと同じ形式で返すため、簡易的なレスポンスオブジェクトを作成
                    cached_response = self._create_cached_response(cached_area_code, latitude, longitude)
                    cached_response.cache_hit = True
                    cache_time = time.time() - start_time
                    return cached_response, cache_time
                else:
                    self.logger.debug(f"Cache miss for coordinates ({latitude}, {longitude})")

            # 専用クラスでリクエスト作成（大幅に簡潔になった）
            request_start = time.time()
            request = LocationRequest.create_coordinate_lookup(
                latitude=latitude,
                longitude=longitude,
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
            
            # 認証設定を適用（認証が有効な場合）
            print(f"[DEBUG] Location client 認証チェック: enabled={self.auth_enabled}, passphrase={'設定済み' if self.auth_passphrase else '未設定'}")
            if self.auth_enabled and self.auth_passphrase:
                print(f"[DEBUG] Location client 認証設定を適用します")
                request.enable_auth(self.auth_passphrase)
                request.set_auth_flags()
                print(f"[DEBUG] Location client 認証設定後のex_field: {request.ex_field._data if hasattr(request, 'ex_field') and request.ex_field else 'None'}")
                if debug_enabled:
                    self.logger.debug("認証ハッシュをLocationリクエストに設定しました")
            else:
                print(f"[DEBUG] Location client 認証設定をスキップしました")
            
            request_time = time.time() - request_start
            
            if debug_enabled:
                self._debug_print_request(request)

            # リクエスト送信とレスポンス受信
            network_start = time.time()
            self.sock.sendto(request.to_bytes(), (self.server_host, self.server_port))
            self.logger.debug(f"Sent request to {self.server_host}:{self.server_port}")

            data, addr = self.sock.recvfrom(1024)
            network_time = time.time() - network_start
            self.logger.debug(f"Received response from {addr}")

            # 専用クラスでレスポンス解析
            parse_start = time.time()
            response = LocationResponse.from_bytes(data)
            parse_time = time.time() - parse_start
            
            if debug_enabled:
                self._debug_print_response(response)

            # レスポンス検証
            if validate_response and response and not response.is_valid():
                self.logger.warning("Response validation failed")
                if debug_enabled:
                    self.logger.debug(f"Invalid response details: {response.get_response_summary()}")
            
            # レスポンスが有効で、キャッシュ使用が有効な場合はキャッシュに保存
            if use_cache and response and response.is_valid():
                area_code = response.get_area_code()
                if area_code:
                    cache_key = self._get_cache_key(latitude, longitude)
                    self.cache.set(cache_key, area_code)
                    self.logger.debug(f"Cached area code for coordinates ({latitude}, {longitude}): {area_code}")

            total_time = time.time() - start_time

            if debug_enabled:
                self.logger.debug("\n=== TIMING INFORMATION ===")
                self.logger.debug(f"Request creation time: {request_time*1000:.2f}ms")
                self.logger.debug(f"Request send time: {(network_start - request_start)*1000:.2f}ms")
                self.logger.debug(f"Network round-trip time: {network_time*1000:.2f}ms")
                self.logger.debug(f"Response parsing time: {parse_time*1000:.2f}ms")
                self.logger.debug(f"Total processing time: {total_time*1000:.2f}ms")
                self.logger.debug("========================\n")

            # サーバーからのレスポンスの場合はcache_hitをFalseに設定
            if response:
                response.cache_hit = False
            return response, total_time

        except socket.timeout:
            self.logger.error("411: クライアントエラー: 座標解決サーバ接続タイムアウト")
            if self.debug:
                self.logger.exception("Traceback:")
            return None, 0
        except (ValueError, struct.error) as e:
            self.logger.error(f"400: クライアントエラー: 不正なパケット: {e}")
            if self.debug:
                self.logger.exception("Traceback:")
            return None, 0
        except Exception as e:
            self.logger.error(f"410: クライアントエラー: 座標解決サーバが見つからない: {e}")
            if self.debug:
                self.logger.exception("Traceback:")
            return None, 0

    def _create_cached_response(self, area_code, latitude, longitude):
        """
        キャッシュされたエリアコードから簡易的なLocationResponseを作成
        
        Args:
            area_code: キャッシュされたエリアコード
            latitude: 緯度
            longitude: 経度
            
        Returns:
            LocationResponse: 簡易的なレスポンスオブジェクト
        """
        # 最低限のレスポンス情報を持つオブジェクトを作成
        # 実際のLocationResponseクラスの仕様に合わせて調整が必要
        class CachedLocationResponse:
            def __init__(self, area_code, latitude, longitude):
                self.area_code = area_code
                self.latitude = latitude
                self.longitude = longitude
                self.type = 0  # タイプ0（座標解決レスポンス）
                self.cache_hit = False  # デフォルトはFalse、後で設定される
                
            def is_valid(self):
                return True
                
            def get_area_code(self):
                return self.area_code
                
            def get_response_summary(self):
                return {
                    "area_code": self.area_code,
                    "latitude": self.latitude,
                    "longitude": self.longitude,
                    "source": "cache"
                }
                
            def get_source_info(self):
                return "cache"
                
            def to_bytes(self):
                # キャッシュからの場合は実際のバイト列は不要
                return b''
        
        return CachedLocationResponse(area_code, latitude, longitude)

    def get_area_code_simple(self, latitude, longitude, source=None, use_cache=True, return_cache_info=False):
        """
        座標からエリアコードのみを取得する簡便メソッド（統一命名規則版）
        
        Args:
            latitude: 緯度
            longitude: 経度
            source: 送信元情報 (ip, port) のタプル
            use_cache: キャッシュを使用するかどうか
            return_cache_info: キャッシュ情報も返すかどうか
            
        Returns:
            str または tuple: エリアコード（失敗時はNone）
                              return_cache_info=Trueの場合は (area_code, cache_hit) のタプル
        """
        response, _ = self.get_location_data(latitude, longitude, source, use_cache=use_cache)
        if response and response.is_valid():
            area_code = response.get_area_code()
            if return_cache_info:
                cache_hit = getattr(response, 'cache_hit', False)
                return area_code, cache_hit
            return area_code
        self.logger.error("400: クライアントエラー: 不正なパケット")
        if return_cache_info:
            return None, False
        return None

    def get_cached_area_code(self, latitude, longitude):
        """
        キャッシュから座標に対応するエリアコードを取得（キャッシュのみ、ネットワークアクセスなし）
        
        Args:
            latitude: 緯度
            longitude: 経度
            
        Returns:
            str または None: キャッシュされたエリアコード（キャッシュミスの場合はNone）
        """
        cache_key = self._get_cache_key(latitude, longitude)
        cached_area_code = self.cache.get(cache_key)
        
        if cached_area_code:
            self.logger.debug(f"Cache hit for coordinates ({latitude}, {longitude}): {cached_area_code}")
        else:
            self.logger.debug(f"Cache miss for coordinates ({latitude}, {longitude})")
            
        return cached_area_code

    def set_cached_area_code(self, latitude, longitude, area_code):
        """
        指定した座標にエリアコードをキャッシュに保存
        
        Args:
            latitude: 緯度
            longitude: 経度
            area_code: エリアコード
        """
        cache_key = self._get_cache_key(latitude, longitude)
        self.cache.set(cache_key, area_code)
        self.logger.debug(f"Cached area code for coordinates ({latitude}, {longitude}): {area_code}")

    # 後方互換性のためのエイリアスメソッド
    def get_location_info(self, latitude, longitude, source=None):
        """後方互換性のため - get_location_data()を使用してください"""
        return self.get_location_data(latitude, longitude, source=source)

    def get_area_code_from_coordinates(self, latitude, longitude, source=None):
        """後方互換性のため - get_area_code_simple()を使用してください"""
        return self.get_area_code_simple(latitude, longitude, source)

    def get_cache_stats(self):
        """
        キャッシュの統計情報を取得
        
        Returns:
            dict: キャッシュの統計情報
        """
        return {
            "cache_size": self.cache.size(),
            "cache_ttl_hours": self.cache.ttl_seconds / 3600,
            "cache_file": str(self.cache.cache_file)
        }
    
    def clear_cache(self):
        """
        キャッシュをクリア
        """
        self.cache.clear()
        self.logger.debug("Location client cache cleared")

    def close(self):
        """ソケットを閉じる"""
        self.sock.close()


def main():
    """メイン関数 - 使用例（専用パケットクラス版）"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Location Client Example (Enhanced with Specialized Packet Classes)")
    logger.info("=" * 70)
    
    # 東京の座標を使用
    latitude = 35.6895
    longitude = 139.6917
    
    client = LocationClient(debug=True)
    try:
        logger.info("\nTesting location resolution for coordinates:")
        logger.info(f"Latitude: {latitude}, Longitude: {longitude}")
        logger.info("-" * 50)
        
        # 改良版のメソッドを使用
        response, total_time = client.get_location_data(
            latitude=latitude,
            longitude=longitude,
            source=("127.0.0.1", 9999)
        )
        
        if response and response.is_valid():
            logger.info(f"\nLocation request completed in {total_time*1000:.2f}ms")
            logger.info(f"Area Code: {response.get_area_code()}")
            logger.info(f"Response Summary: {response.get_response_summary()}")
            
            # 簡便メソッドのテスト
            logger.info(f"\n--- Testing convenience method ---")
            area_code = client.get_area_code_simple(latitude, longitude)
            logger.info(f"Area Code (convenience method): {area_code}")
            
        else:
            logger.error("400: クライアントエラー: 不正なパケット")
            if response:
                logger.error(f"Response valid: {response.is_valid()}")
                
    finally:
        client.close()
        
    logger.info("\n" + "="*70)
    logger.info("Enhanced Location Client Example completed")
    logger.info("Using specialized packet classes for improved usability")


