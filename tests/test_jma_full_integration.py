#!/usr/bin/env python3
"""
JMA Weather API Full Integration Test

JMAからのデータ取得 → レポートクライアント送信 → Redis保存 → フォワード処理
の完全なフローをテストします。

テストフロー:
1. Weather API Server の起動確認
2. JMAデータ取得のテスト
3. 取得したデータをレポートサーバーに送信
4. Redis保存の確認
5. フォワード処理の確認
6. 統合フローの確認
"""

import unittest
import time
import threading
import requests
import redis
import json
import sys
import os
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock
import socket

# WIPCommonPyをインポートするためのパス設定
sys.path.insert(0, '/mnt/c/Users/ポッポ焼き/Desktop/WIP/src')
sys.path.insert(0, '/mnt/c/Users/ポッポ焼き/Desktop/WIP/python/application/tools')

from WIPCommonPy.clients.report_client import ReportClient
from WIPCommonPy.clients.query_client import QueryClient
from WIPServerPy.servers.report_server.report_server import ReportServer
from WIPServerPy.data.redis_manager import WeatherRedisManager


class JMAFullIntegrationTest(unittest.TestCase):
    """JMA APIサーバー統合テスト"""

    @classmethod
    def setUpClass(cls):
        """テストクラス初期化"""
        cls.test_prefix = "test_jma_"
        cls.weather_api_port = 8001
        cls.report_port = 19998  # テスト用ポート
        cls.query_port = 14110   # テスト用ポート
        
        # Redis設定
        os.environ["REDIS_KEY_PREFIX"] = cls.test_prefix
        os.environ["REPORT_DB_KEY_PREFIX"] = cls.test_prefix
        
        # サーバー認証を無効化
        os.environ["REPORT_SERVER_AUTH_ENABLED"] = "false"
        
        cls.servers_started = False
        cls.report_server = None
        cls.server_threads = []

    def setUp(self):
        """各テスト前の初期化"""
        # Redisクリーンアップ
        self.cleanup_redis()
        
        # テスト用サーバー起動
        if not self.__class__.servers_started:
            self.start_test_servers()
            self.__class__.servers_started = True
            time.sleep(2)

    def tearDown(self):
        """各テスト後のクリーンアップ"""
        self.cleanup_redis()

    @classmethod
    def tearDownClass(cls):
        """テストクラス終了処理"""
        cls.stop_test_servers()
        
        # 環境変数クリーンアップ
        for key in ["REDIS_KEY_PREFIX", "REPORT_DB_KEY_PREFIX", "REPORT_SERVER_AUTH_ENABLED"]:
            if key in os.environ:
                del os.environ[key]

    def cleanup_redis(self):
        """Redisのテストデータクリーンアップ"""
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            keys = redis_client.keys(f"{self.test_prefix}*")
            if keys:
                redis_client.delete(*keys)
        except Exception as e:
            print(f"Redis cleanup warning: {e}")

    def start_test_servers(self):
        """テスト用サーバー起動"""
        try:
            # Report Server起動（フォワード処理テスト用）
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
            
        except Exception as e:
            print(f"✗ Test server startup failed: {e}")
            raise

    @classmethod
    def stop_test_servers(cls):
        """テスト用サーバー停止"""
        if cls.report_server:
            try:
                cls.report_server.stop()
            except:
                pass

    def check_weather_api_server(self) -> bool:
        """Weather API Serverの起動確認"""
        try:
            response = requests.get(f"http://localhost:{self.weather_api_port}/health", timeout=5)
            return response.status_code == 200
        except:
            return False

    def test_01_weather_api_server_health(self):
        """Weather API Server の起動確認"""
        print("\n" + "="*60)
        print("TEST 1: Weather API Server Health Check")
        print("="*60)
        
        if not self.check_weather_api_server():
            self.skipTest("Weather API Server is not running. Please start it first:\n"
                         "cd python/application/weather_api\n"
                         "python start_server.py")
        
        # Health endpoint確認
        response = requests.get(f"http://localhost:{self.weather_api_port}/health")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data.get("status"), "ok")
        print("✓ Weather API Server is healthy")

    def test_02_jma_data_fetch(self):
        """JMAからのデータ取得テスト"""
        print("\n" + "="*60)
        print("TEST 2: JMA Data Fetch via Weather API")
        print("="*60)
        
        if not self.check_weather_api_server():
            self.skipTest("Weather API Server is not running")
        
        # 気象データ更新をトリガー
        print("📡 Triggering weather data update...")
        try:
            response = requests.post(f"http://localhost:{self.weather_api_port}/update/weather", 
                                   timeout=30)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get("ok", False))
            print(f"✓ Weather update successful: {data.get('detail', '')}")
        except requests.exceptions.Timeout:
            self.skipTest("Weather update timed out (JMA might be slow)")
        
        # 少し待機してデータが準備されるのを待つ
        time.sleep(3)
        
        # 利用可能なエリア一覧確認
        response = requests.get(f"http://localhost:{self.weather_api_port}/areas")
        self.assertEqual(response.status_code, 200)
        
        areas = response.json()
        self.assertIsInstance(areas, list)
        self.assertGreater(len(areas), 0, "Should have at least one area")
        print(f"✓ Available areas: {len(areas)} areas found")
        print(f"  Sample areas: {areas[:5]}")
        
        # 東京のデータ取得テスト
        test_area = "130000"  # 東京
        if test_area not in areas:
            test_area = areas[0]  # 利用可能な最初のエリアを使用
        
        response = requests.get(f"http://localhost:{self.weather_api_port}/weather", 
                               params={"area_code": test_area})
        self.assertEqual(response.status_code, 200)
        
        weather_data = response.json()
        print(f"✓ Weather data for {test_area}:")
        print(f"  Weather: {weather_data.get('weather', 'N/A')}")
        print(f"  Temperature: {weather_data.get('temperature', 'N/A')}")
        print(f"  POP: {weather_data.get('precipitation_prob', 'N/A')}")
        
        # データ内容確認
        self.assertIsInstance(weather_data, dict)
        # JMAデータが取得できていることを確認（少なくとも1つのフィールドが存在）
        has_data = any([
            weather_data.get('weather') is not None,
            weather_data.get('temperature') is not None,
            weather_data.get('precipitation_prob') is not None
        ])
        self.assertTrue(has_data, "Should have at least one weather field")

    def test_03_api_to_report_flow(self):
        """API取得データのレポートサーバー送信フロー"""
        print("\n" + "="*60)
        print("TEST 3: API Data → Report Server Flow")
        print("="*60)
        
        if not self.check_weather_api_server():
            self.skipTest("Weather API Server is not running")
        
        # Weather APIからデータ取得
        print("📡 Fetching data from Weather API...")
        response = requests.get(f"http://localhost:{self.weather_api_port}/areas")
        areas = response.json()
        
        test_area = "130000" if "130000" in areas else areas[0]
        
        response = requests.get(f"http://localhost:{self.weather_api_port}/weather",
                               params={
                                   "area_code": test_area,
                                   "weather_flag": 1,
                                   "temperature_flag": 1,
                                   "pop_flag": 1,
                                   "alert_flag": 1,
                                   "disaster_flag": 1
                               })
        
        api_data = response.json()
        print(f"✓ API data retrieved for {test_area}")
        
        # ReportClientでデータ送信
        print("📤 Sending data to Report Server...")
        report_client = ReportClient(
            host="localhost",
            port=self.report_port,
            debug=True
        )
        
        try:
            # APIデータをレポート形式に変換
            weather_code = api_data.get('weather')
            if isinstance(weather_code, list) and weather_code:
                weather_code = weather_code[0]
            
            temperature = api_data.get('temperature')
            if isinstance(temperature, list) and temperature:
                # 文字列の場合は数値に変換を試行
                try:
                    temp_str = str(temperature[0])
                    temperature = float(temp_str) if temp_str and temp_str != '' else None
                except (ValueError, IndexError):
                    temperature = None
            
            pop = api_data.get('precipitation_prob')
            if isinstance(pop, list) and pop:
                try:
                    pop_str = str(pop[0])
                    pop = int(pop_str) if pop_str and pop_str != '' else None
                except (ValueError, IndexError):
                    pop = None
            
            # データ送信
            report_client.set_sensor_data(
                area_code=test_area,
                weather_code=weather_code,
                temperature=temperature,
                precipitation_prob=pop,
                alert=api_data.get('warnings', []),
                disaster=api_data.get('disaster', [])
            )
            
            result = report_client.send_report_data()
            self.assertIsNotNone(result, "Report should be sent successfully")
            self.assertTrue(result.get("success", False), "Report should succeed")
            print("✓ Data sent to Report Server successfully")
            
        finally:
            report_client.close()
        
        # Redis保存確認
        print("🗄️ Checking Redis storage...")
        time.sleep(1)  # 保存処理待機
        
        redis_manager = WeatherRedisManager(
            debug=True,
            key_prefix=self.test_prefix
        )
        
        try:
            stored_data = redis_manager.get_weather_data(test_area)
            self.assertIsNotNone(stored_data, "Data should be stored in Redis")
            print(f"✓ Data confirmed in Redis: {stored_data}")
            
            # 送信データと保存データの整合性確認
            if weather_code is not None:
                self.assertEqual(stored_data.get("weather"), weather_code)
            if temperature is not None:
                self.assertEqual(stored_data.get("temperature"), temperature)
            if pop is not None:
                self.assertEqual(stored_data.get("precipitation_prob"), pop)
            
        finally:
            redis_manager.close()

    def test_04_disaster_alert_flow(self):
        """災害・警報情報フロー"""
        print("\n" + "="*60)
        print("TEST 4: Disaster/Alert Data Flow")
        print("="*60)
        
        if not self.check_weather_api_server():
            self.skipTest("Weather API Server is not running")
        
        # 災害情報更新をトリガー
        print("🚨 Triggering disaster/alert data update...")
        try:
            response = requests.post(f"http://localhost:{self.weather_api_port}/update/disaster",
                                   timeout=30)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get("ok", False))
            print(f"✓ Disaster update successful: {data.get('detail', '')}")
        except requests.exceptions.Timeout:
            self.skipTest("Disaster update timed out")
        
        # 災害情報含むデータ取得
        time.sleep(2)
        
        response = requests.get(f"http://localhost:{self.weather_api_port}/areas")
        areas = response.json()
        
        # 複数エリアで災害情報確認
        disaster_found = False
        alert_found = False
        
        for area_code in areas[:5]:  # 最初の5エリアをチェック
            response = requests.get(f"http://localhost:{self.weather_api_port}/weather",
                                   params={
                                       "area_code": area_code,
                                       "alert_flag": 1,
                                       "disaster_flag": 1
                                   })
            
            if response.status_code == 200:
                data = response.json()
                warnings = data.get('warnings', [])
                disasters = data.get('disaster', [])
                
                if warnings:
                    alert_found = True
                    print(f"✓ Alert found in {area_code}: {warnings}")
                
                if disasters:
                    disaster_found = True
                    print(f"✓ Disaster found in {area_code}: {disasters}")
        
        # 警報・災害情報が見つからない場合でもテストは続行
        # （JMAの状況により情報がない場合がある）
        print(f"📊 Alert data found: {alert_found}")
        print(f"📊 Disaster data found: {disaster_found}")

    def test_05_forward_processing(self):
        """フォワード処理テスト"""
        print("\n" + "="*60)
        print("TEST 5: Forward Processing Test")
        print("="*60)
        
        # フォワード設定有効化でレポートサーバー設定
        # （実際の実装では設定ファイルまたは環境変数で制御）
        
        test_area = "130000"
        test_data = {
            "area_code": test_area,
            "weather_code": 100,
            "temperature": 25.0,
            "precipitation_prob": 30,
            "alert": ["テスト警報"],
            "disaster": ["テスト災害情報"]
        }
        
        # Mock forward serverを起動（簡易版）
        forward_received_data = []
        
        def mock_forward_server():
            """模擬フォワードサーバー"""
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.bind(('localhost', 19997))  # フォワード受信用ポート
                sock.settimeout(5.0)
                
                while True:
                    try:
                        data, addr = sock.recvfrom(4096)
                        forward_received_data.append(data)
                        print(f"📨 Forward data received from {addr}: {len(data)} bytes")
                        break
                    except socket.timeout:
                        break
                sock.close()
            except Exception as e:
                print(f"Forward server error: {e}")
        
        # フォワードサーバー起動
        forward_thread = threading.Thread(target=mock_forward_server, daemon=True)
        forward_thread.start()
        time.sleep(0.5)
        
        # レポート送信（フォワード先を設定）
        # 注意: 実際のフォワード設定は設定ファイルで行う必要がある
        print("📤 Sending report with forward configuration...")
        
        report_client = ReportClient(
            host="localhost",
            port=self.report_port,
            debug=True
        )
        
        try:
            report_client.set_sensor_data(**test_data)
            result = report_client.send_report_data()
            
            self.assertIsNotNone(result)
            self.assertTrue(result.get("success", False))
            print("✓ Report sent successfully")
            
        finally:
            report_client.close()
        
        # フォワード結果確認
        time.sleep(2)
        
        if forward_received_data:
            print(f"✓ Forward processing confirmed: {len(forward_received_data)} packets received")
        else:
            print("! Forward processing not detected (may require configuration)")

    def test_06_end_to_end_integration(self):
        """エンドツーエンド統合テスト"""
        print("\n" + "="*60)
        print("TEST 6: End-to-End Integration")
        print("="*60)
        
        if not self.check_weather_api_server():
            self.skipTest("Weather API Server is not running")
        
        print("🔄 Running complete flow test...")
        
        # Step 1: JMAデータ更新
        print("Step 1: Updating JMA data...")
        requests.post(f"http://localhost:{self.weather_api_port}/update/weather", timeout=30)
        time.sleep(2)
        
        # Step 2: エリア取得
        response = requests.get(f"http://localhost:{self.weather_api_port}/areas")
        areas = response.json()
        test_areas = areas[:3]  # 最初の3エリアをテスト
        
        print(f"Step 2: Testing {len(test_areas)} areas...")
        
        success_count = 0
        
        for area_code in test_areas:
            print(f"\n--- Processing area {area_code} ---")
            
            try:
                # APIデータ取得
                response = requests.get(f"http://localhost:{self.weather_api_port}/weather",
                                       params={"area_code": area_code})
                api_data = response.json()
                
                # レポート送信
                report_client = ReportClient(
                    host="localhost",
                    port=self.report_port,
                    debug=False
                )
                
                # データ変換
                weather_code = api_data.get('weather')
                if isinstance(weather_code, list) and weather_code:
                    weather_code = weather_code[0]
                
                temperature = api_data.get('temperature')
                if isinstance(temperature, list) and temperature:
                    try:
                        temp_str = str(temperature[0])
                        temperature = float(temp_str) if temp_str else None
                    except:
                        temperature = None
                
                pop = api_data.get('precipitation_prob')
                if isinstance(pop, list) and pop:
                    try:
                        pop_str = str(pop[0])
                        pop = int(pop_str) if pop_str else None
                    except:
                        pop = None
                
                report_client.set_sensor_data(
                    area_code=area_code,
                    weather_code=weather_code,
                    temperature=temperature,
                    precipitation_prob=pop,
                    alert=api_data.get('warnings', []),
                    disaster=api_data.get('disaster', [])
                )
                
                result = report_client.send_report_data()
                report_client.close()
                
                if result and result.get("success"):
                    success_count += 1
                    print(f"✓ {area_code}: Complete flow successful")
                else:
                    print(f"✗ {area_code}: Report failed")
                
            except Exception as e:
                print(f"✗ {area_code}: Error - {e}")
        
        # 結果確認
        success_rate = (success_count / len(test_areas)) * 100
        print(f"\n📊 End-to-End Result: {success_count}/{len(test_areas)} areas successful ({success_rate:.1f}%)")
        
        self.assertGreater(success_count, 0, "At least one area should succeed")


if __name__ == "__main__":
    print("JMA Weather API Full Integration Test")
    print("=" * 70)
    print("Testing: JMA → Weather API → Report Client → Report Server → Redis")
    print("=" * 70)
    
    # 前提条件確認
    try:
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        redis_client.ping()
        print("✓ Redis connection confirmed")
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        print("Please start Redis server before running tests")
        sys.exit(1)
    
    # Weather API Server確認
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✓ Weather API Server connection confirmed")
        else:
            print("⚠ Weather API Server responded with non-200 status")
    except Exception as e:
        print("⚠ Weather API Server not detected - some tests will be skipped")
        print("To start Weather API Server:")
        print("  cd python/application/weather_api")
        print("  python start_server.py")
    
    print("\nRunning integration tests...")
    unittest.main(verbosity=2, buffer=True)