#!/usr/bin/env python3
"""
Full Weather Data Flow Test

外部API → レポートサーバー → Redis → クエリサーバーの
全体的なデータフローをテストします。

テストフロー:
1. Weather API Reporter でダミーデータを送信
2. Report Server が Redis に保存
3. Query Server が Redis から読み取り
4. 全体の整合性を確認
"""

import unittest
import time
import threading
import socket
import json
import redis
import sys
import os
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Optional

# WIPCommonPyをインポートするためのパス設定
sys.path.insert(0, '/mnt/c/Users/ポッポ焼き/Desktop/WIP/src')
sys.path.insert(0, '/mnt/c/Users/ポッポ焼き/Desktop/WIP/python/application/tools')

from WIPCommonPy.clients.report_client import ReportClient
from WIPCommonPy.clients.query_client import QueryClient
from WIPServerPy.servers.report_server.report_server import ReportServer
from WIPServerPy.servers.query_server.query_server import QueryServer
from WIPServerPy.data.redis_manager import WeatherRedisManager
from weather_api_reporter import WeatherAPIReporter


class FullWeatherFlowTest(unittest.TestCase):
    """全体フロー統合テスト"""

    @classmethod
    def setUpClass(cls):
        """テストクラス初期化"""
        cls.test_prefix = "test_flow_"
        cls.report_port = 19999  # テスト用ポート
        cls.query_port = 14111   # テスト用ポート
        
        # Redis設定（テスト用キープレフィックス）
        os.environ["REDIS_KEY_PREFIX"] = cls.test_prefix
        os.environ["REPORT_DB_KEY_PREFIX"] = cls.test_prefix
        
        # サーバー認証を無効化（テスト用）
        os.environ["REPORT_SERVER_AUTH_ENABLED"] = "false"
        os.environ["QUERY_SERVER_AUTH_ENABLED"] = "false"
        
        cls.servers_started = False
        cls.report_server = None
        cls.query_server = None
        cls.server_threads = []

    def setUp(self):
        """各テスト前の初期化"""
        # Redisクリーンアップ
        self.cleanup_redis()
        
        # サーバー起動（初回のみ）
        if not self.__class__.servers_started:
            self.start_test_servers()
            self.__class__.servers_started = True
            time.sleep(2)  # サーバー起動待機

    def tearDown(self):
        """各テスト後のクリーンアップ"""
        self.cleanup_redis()

    @classmethod 
    def tearDownClass(cls):
        """テストクラス終了処理"""
        cls.stop_test_servers()
        
        # 環境変数クリーンアップ
        for key in ["REDIS_KEY_PREFIX", "REPORT_DB_KEY_PREFIX", 
                   "REPORT_SERVER_AUTH_ENABLED", "QUERY_SERVER_AUTH_ENABLED"]:
            if key in os.environ:
                del os.environ[key]

    def cleanup_redis(self):
        """Redisのテストデータをクリーンアップ"""
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            # テストプレフィックスのキーのみ削除
            keys = redis_client.keys(f"{self.test_prefix}*")
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            print(f"Redis cleanup warning: {e}")

    def start_test_servers(self):
        """テスト用サーバーを起動"""
        try:
            # Report Server起動
            self.__class__.report_server = ReportServer(
                host="localhost",
                port=self.report_port,
                debug=True,
                max_workers=2
            )
            
            report_thread = threading.Thread(
                target=self.__class__.report_server.start,
                daemon=True
            )
            report_thread.start()
            self.__class__.server_threads.append(report_thread)
            print(f"✓ Test Report Server started on port {self.report_port}")
            
            # Query Server起動
            self.__class__.query_server = QueryServer(
                host="localhost", 
                port=self.query_port,
                debug=True,
                max_workers=2,
                noupdate=True  # 更新処理無効化
            )
            
            query_thread = threading.Thread(
                target=self.__class__.query_server.start,
                daemon=True
            )
            query_thread.start()
            self.__class__.server_threads.append(query_thread)
            print(f"✓ Test Query Server started on port {self.query_port}")
            
        except Exception as e:
            print(f"✗ Test server startup failed: {e}")
            raise

    @classmethod
    def stop_test_servers(cls):
        """テスト用サーバーを停止"""
        if cls.report_server:
            try:
                cls.report_server.stop()
            except:
                pass
        if cls.query_server:
            try:
                cls.query_server.stop()
            except:
                pass

    def wait_for_server(self, host: str, port: int, timeout: int = 10) -> bool:
        """サーバーの起動を待機"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1)
                sock.sendto(b'test', (host, port))
                sock.close()
                return True
            except:
                time.sleep(0.5)
        return False

    def test_01_basic_flow_single_city(self):
        """基本フロー: 単一都市のデータ送信→保存→取得"""
        print("\n" + "="*60)
        print("TEST 1: 基本フロー - 単一都市")
        print("="*60)
        
        test_area_code = "130000"  # 東京
        test_weather_code = 100    # 晴れ
        test_temperature = 25.5    # 25.5℃
        test_pop = 30             # 30%
        
        # Step 1: WeatherAPIReporterでデータ送信
        print("\nStep 1: Weather API Reporter → Report Server")
        reporter = WeatherAPIReporter(
            report_server_host="localhost",
            report_server_port=self.report_port,
            debug=True
        )
        
        # ダミーデータを設定
        weather_data = {
            "area_code": test_area_code,
            "weather_code": test_weather_code,
            "temperature": test_temperature,
            "precipitation_prob": test_pop,
            "alert": ["テスト警報"],
            "disaster": []
        }
        
        # レポート送信
        success = reporter.send_weather_report(weather_data)
        self.assertTrue(success, "Weather report should be sent successfully")
        print("✓ Data sent to Report Server")
        
        # Step 2: Redisでデータ確認
        print("\nStep 2: Redis データ確認")
        time.sleep(1)  # 保存処理待機
        
        redis_manager = WeatherRedisManager(
            debug=True,
            key_prefix=self.test_prefix
        )
        
        stored_data = redis_manager.get_weather_data(test_area_code)
        self.assertIsNotNone(stored_data, "Data should be stored in Redis")
        print(f"✓ Data found in Redis: {stored_data}")
        
        # データ内容確認
        self.assertEqual(stored_data.get("weather"), test_weather_code)
        self.assertEqual(stored_data.get("temperature"), test_temperature)
        self.assertEqual(stored_data.get("precipitation_prob"), test_pop)
        self.assertIn("テスト警報", stored_data.get("warnings", []))
        
        # Step 3: QueryClientでデータ取得
        print("\nStep 3: Query Client → Query Server")
        query_client = QueryClient(
            host="localhost",
            port=self.query_port,
            debug=True
        )
        
        try:
            response = query_client.get_weather_data(
                area_code=test_area_code,
                weather=True,
                temperature=True,
                pop=True,
                alert=True
            )
            
            self.assertIsNotNone(response, "Query response should not be None")
            self.assertTrue(response.get("success", False), "Query should be successful")
            print(f"✓ Query response received: {response}")
            
            # レスポンス内容確認
            response_data = response.get("data", {})
            self.assertEqual(response_data.get("weather_code"), test_weather_code)
            self.assertEqual(response_data.get("temperature"), test_temperature)
            self.assertEqual(response_data.get("precipitation_prob"), test_pop)
            
        finally:
            query_client.close()
        
        redis_manager.close()
        print("✓ Test 1 完了: 基本フロー成功")

    def test_02_multiple_cities_flow(self):
        """複数都市のデータフロー"""
        print("\n" + "="*60)
        print("TEST 2: 複数都市フロー")
        print("="*60)
        
        test_cities = {
            "130000": {"weather": 100, "temp": 25.5, "pop": 30},  # 東京
            "270000": {"weather": 300, "temp": 18.7, "pop": 80},  # 大阪
            "011000": {"weather": 400, "temp": -2.1, "pop": 90}   # 札幌
        }
        
        # Step 1: 複数都市データ送信
        print("\nStep 1: 複数都市データ送信")
        reporter = WeatherAPIReporter(
            report_server_host="localhost",
            report_server_port=self.report_port,
            debug=True
        )
        
        success_count = 0
        for area_code, data in test_cities.items():
            weather_data = {
                "area_code": area_code,
                "weather_code": data["weather"],
                "temperature": data["temp"],
                "precipitation_prob": data["pop"],
                "alert": [f"{area_code}テスト警報"],
                "disaster": []
            }
            
            if reporter.send_weather_report(weather_data):
                success_count += 1
                print(f"✓ {area_code}: データ送信成功")
        
        self.assertEqual(success_count, len(test_cities), "All cities should be sent successfully")
        
        # Step 2: Redis内容確認
        print("\nStep 2: Redis 複数都市確認")
        time.sleep(1)
        
        redis_manager = WeatherRedisManager(
            debug=True,
            key_prefix=self.test_prefix
        )
        
        for area_code, expected in test_cities.items():
            stored_data = redis_manager.get_weather_data(area_code)
            self.assertIsNotNone(stored_data, f"Data for {area_code} should be stored")
            self.assertEqual(stored_data.get("weather"), expected["weather"])
            self.assertEqual(stored_data.get("temperature"), expected["temp"])
            print(f"✓ {area_code}: Redis確認完了")
        
        # Step 3: クエリサーバーから全都市取得
        print("\nStep 3: 全都市クエリテスト")
        query_client = QueryClient(
            host="localhost",
            port=self.query_port,
            debug=True
        )
        
        try:
            query_success_count = 0
            for area_code, expected in test_cities.items():
                response = query_client.get_weather_data(
                    area_code=area_code,
                    weather=True,
                    temperature=True,
                    pop=True
                )
                
                if response and response.get("success"):
                    query_success_count += 1
                    response_data = response.get("data", {})
                    self.assertEqual(response_data.get("weather_code"), expected["weather"])
                    print(f"✓ {area_code}: クエリ成功")
            
            self.assertEqual(query_success_count, len(test_cities), "All cities should be queried successfully")
            
        finally:
            query_client.close()
        
        redis_manager.close()
        print("✓ Test 2 完了: 複数都市フロー成功")

    def test_03_alert_disaster_flow(self):
        """警報・災害情報フロー"""
        print("\n" + "="*60)
        print("TEST 3: 警報・災害情報フロー")
        print("="*60)
        
        test_area_code = "270000"  # 大阪
        test_alerts = ["大雨警報", "洪水注意報"]
        test_disasters = ["河川氾濫危険情報", "土砂災害警戒情報"]
        
        # Step 1: 警報・災害情報送信
        print("\nStep 1: 警報・災害情報送信")
        reporter = WeatherAPIReporter(
            report_server_host="localhost",
            report_server_port=self.report_port,
            debug=True
        )
        
        weather_data = {
            "area_code": test_area_code,
            "weather_code": 300,  # 雨
            "temperature": 18.0,
            "precipitation_prob": 85,
            "alert": test_alerts,
            "disaster": test_disasters
        }
        
        success = reporter.send_weather_report(weather_data)
        self.assertTrue(success, "Alert/disaster report should be sent successfully")
        print("✓ 警報・災害情報送信完了")
        
        # Step 2: Redis確認
        print("\nStep 2: 警報・災害情報Redis確認")
        time.sleep(1)
        
        redis_manager = WeatherRedisManager(
            debug=True,
            key_prefix=self.test_prefix
        )
        
        stored_data = redis_manager.get_weather_data(test_area_code)
        self.assertIsNotNone(stored_data, "Alert/disaster data should be stored")
        
        stored_warnings = stored_data.get("warnings", [])
        stored_disasters = stored_data.get("disaster", [])
        
        for alert in test_alerts:
            self.assertIn(alert, stored_warnings, f"Alert '{alert}' should be stored")
        
        for disaster in test_disasters:
            self.assertIn(disaster, stored_disasters, f"Disaster '{disaster}' should be stored")
        
        print(f"✓ 警報情報確認: {stored_warnings}")
        print(f"✓ 災害情報確認: {stored_disasters}")
        
        # Step 3: クエリサーバーで警報・災害情報取得
        print("\nStep 3: 警報・災害情報クエリ")
        query_client = QueryClient(
            host="localhost",
            port=self.query_port,
            debug=True
        )
        
        try:
            response = query_client.get_weather_data(
                area_code=test_area_code,
                weather=True,
                alert=True,
                disaster=True
            )
            
            self.assertIsNotNone(response, "Alert/disaster query should succeed")
            self.assertTrue(response.get("success"), "Alert/disaster query should be successful")
            
            response_data = response.get("data", {})
            response_alerts = response_data.get("alerts", [])
            response_disasters = response_data.get("disasters", [])
            
            print(f"✓ クエリ応答警報: {response_alerts}")
            print(f"✓ クエリ応答災害: {response_disasters}")
            
            # 警報情報の確認（部分一致でも可）
            self.assertTrue(len(response_alerts) > 0, "Some alerts should be returned")
            self.assertTrue(len(response_disasters) > 0, "Some disasters should be returned")
            
        finally:
            query_client.close()
        
        redis_manager.close()
        print("✓ Test 3 完了: 警報・災害情報フロー成功")

    def test_04_error_handling_flow(self):
        """エラーハンドリングフロー"""
        print("\n" + "="*60)
        print("TEST 4: エラーハンドリング")
        print("="*60)
        
        query_client = QueryClient(
            host="localhost",
            port=self.query_port,
            debug=True
        )
        
        try:
            # Step 1: 存在しないエリアコードのクエリ
            print("\nStep 1: 存在しないエリアコードテスト")
            response = query_client.get_weather_data(
                area_code="999999",  # 存在しないエリア
                weather=True
            )
            
            # エラーレスポンスまたはデータなしのレスポンスを期待
            if response:
                if not response.get("success", True):
                    print("✓ 適切にエラーレスポンスを受信")
                else:
                    # データが空の場合も正常
                    data = response.get("data", {})
                    if not data.get("weather_code"):
                        print("✓ データなしの適切なレスポンス")
            else:
                print("✓ エラー時の適切な処理")
            
            # Step 2: 無効なエリアコードでのレポート送信
            print("\nStep 2: 無効データレポートテスト")
            reporter = WeatherAPIReporter(
                report_server_host="localhost",
                report_server_port=self.report_port,
                debug=True
            )
            
            invalid_data = {
                "area_code": "000000",  # 無効エリアコード
                "weather_code": 100,
                "temperature": 25.0,
                "precipitation_prob": 50
            }
            
            # エラーが適切に処理されることを確認
            try:
                result = reporter.send_weather_report(invalid_data)
                if result is False:
                    print("✓ 無効データの適切な拒否")
                else:
                    print("! 無効データが受け入れられました（要確認）")
            except Exception as e:
                print(f"✓ 例外による適切なエラー処理: {e}")
            
        finally:
            query_client.close()
        
        print("✓ Test 4 完了: エラーハンドリング確認")

    def test_05_performance_flow(self):
        """パフォーマンステスト"""
        print("\n" + "="*60)
        print("TEST 5: パフォーマンステスト")
        print("="*60)
        
        num_requests = 5  # テスト用に少数で実行
        test_area_codes = ["130000", "270000", "011000", "400000", "230000"]
        
        # Step 1: 複数リクエストの送信時間測定
        print(f"\nStep 1: {num_requests}件のレポート送信測定")
        start_time = time.time()
        
        reporter = WeatherAPIReporter(
            report_server_host="localhost",
            report_server_port=self.report_port,
            debug=False  # パフォーマンステストではデバッグ無効
        )
        
        success_count = 0
        for i in range(num_requests):
            area_code = test_area_codes[i % len(test_area_codes)]
            weather_data = {
                "area_code": area_code,
                "weather_code": 100 + (i % 4) * 100,
                "temperature": 20.0 + i,
                "precipitation_prob": 10 + (i * 10) % 90,
                "alert": [],
                "disaster": []
            }
            
            if reporter.send_weather_report(weather_data):
                success_count += 1
        
        send_time = time.time() - start_time
        print(f"✓ 送信完了: {success_count}/{num_requests} ({send_time:.2f}秒)")
        self.assertEqual(success_count, num_requests, "All requests should succeed")
        
        # Step 2: クエリ応答時間測定
        print(f"\nStep 2: {num_requests}件のクエリ応答測定")
        time.sleep(1)  # データ保存完了待機
        
        query_client = QueryClient(
            host="localhost",
            port=self.query_port,
            debug=False
        )
        
        try:
            start_time = time.time()
            query_success_count = 0
            
            for i in range(num_requests):
                area_code = test_area_codes[i % len(test_area_codes)]
                response = query_client.get_weather_data(
                    area_code=area_code,
                    weather=True,
                    temperature=True,
                    pop=True
                )
                
                if response and response.get("success"):
                    query_success_count += 1
            
            query_time = time.time() - start_time
            print(f"✓ クエリ完了: {query_success_count}/{num_requests} ({query_time:.2f}秒)")
            
            # パフォーマンス指標
            avg_send_time = (send_time / num_requests) * 1000  # ms
            avg_query_time = (query_time / num_requests) * 1000  # ms
            
            print(f"📊 平均送信時間: {avg_send_time:.1f}ms/req")
            print(f"📊 平均クエリ時間: {avg_query_time:.1f}ms/req")
            
            # 基本的なパフォーマンス確認（緩い閾値）
            self.assertLess(avg_send_time, 5000, "Average send time should be under 5 seconds")
            self.assertLess(avg_query_time, 3000, "Average query time should be under 3 seconds")
            
        finally:
            query_client.close()
        
        print("✓ Test 5 完了: パフォーマンステスト完了")


if __name__ == "__main__":
    print("Full Weather Data Flow Integration Test")
    print("="*70)
    print("Testing: API → Report Server → Redis → Query Server")
    print("="*70)
    
    # テスト実行前の環境確認
    try:
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        redis_client.ping()
        print("✓ Redis connection confirmed")
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("Please start Redis server before running tests")
        sys.exit(1)
    
    # テスト実行
    unittest.main(verbosity=2, buffer=True)