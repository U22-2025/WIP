#!/usr/bin/env python3
"""
Simple Weather Data Flow Test

既に起動しているサーバーを使用して、
シンプルなデータフローをテストします。

前提条件:
- Redis サーバーが起動している
- Report Server が起動している (通常はport 9999)
- Query Server が起動している (通常はport 4111)

使用方法:
python simple_flow_test.py [--report-port 9999] [--query-port 4111]
"""

import sys
import os
import time
import argparse
import json
from typing import Dict, Any

# WIPCommonPyをインポートするためのパス設定
sys.path.insert(0, '/mnt/c/Users/ポッポ焼き/Desktop/WIP/src')
sys.path.insert(0, '/mnt/c/Users/ポッポ焼き/Desktop/WIP/python/application/tools')

from weather_api_reporter import WeatherAPIReporter
from WIPCommonPy.clients.query_client import QueryClient
from WIPServerPy.data.redis_manager import WeatherRedisManager


class SimpleFlowTester:
    """シンプルなフローテスター"""
    
    def __init__(self, report_port: int = 9999, query_port: int = 4111, debug: bool = True):
        self.report_port = report_port
        self.query_port = query_port
        self.debug = debug
        self.test_prefix = "test_simple_"
        
        # テスト用環境変数設定
        os.environ["REDIS_KEY_PREFIX"] = self.test_prefix
        os.environ["REPORT_DB_KEY_PREFIX"] = self.test_prefix
        
        print(f"Simple Flow Tester")
        print(f"Report Server: localhost:{report_port}")
        print(f"Query Server: localhost:{query_port}")
        print(f"Redis Prefix: {self.test_prefix}")
        print("="*50)
    
    def cleanup_test_data(self):
        """テストデータをクリーンアップ"""
        try:
            import redis
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            keys = redis_client.keys(f"{self.test_prefix}*")
            if keys:
                redis_client.delete(*keys)
                print(f"🧹 Cleaned up {len(keys)} test keys from Redis")
        except Exception as e:
            print(f"⚠️  Redis cleanup warning: {e}")
    
    def test_basic_flow(self) -> bool:
        """基本フローをテスト"""
        print("\n🔄 Testing Basic Flow...")
        print("-" * 30)
        
        test_area_code = "130000"  # 東京
        test_data = {
            "area_code": test_area_code,
            "weather_code": 100,  # 晴れ
            "temperature": 25.5,  # 25.5℃
            "precipitation_prob": 30,  # 30%
            "alert": ["テスト警報"],
            "disaster": ["テスト災害情報"]
        }
        
        try:
            # Step 1: データ送信
            print("📤 Step 1: Sending data to Report Server...")
            reporter = WeatherAPIReporter(
                report_server_host="localhost",
                report_server_port=self.report_port,
                debug=self.debug
            )
            
            success = reporter.send_weather_report(test_data)
            if not success:
                print("❌ Failed to send data to Report Server")
                return False
            print("✅ Data sent successfully")
            
            # 少し待機してデータが保存されるのを待つ
            time.sleep(2)
            
            # Step 2: Redis確認
            print("🗄️  Step 2: Checking data in Redis...")
            redis_manager = WeatherRedisManager(
                debug=self.debug,
                key_prefix=self.test_prefix
            )
            
            stored_data = redis_manager.get_weather_data(test_area_code)
            if not stored_data:
                print("❌ No data found in Redis")
                return False
            
            print(f"✅ Data found in Redis:")
            print(f"   Weather: {stored_data.get('weather', 'N/A')}")
            print(f"   Temperature: {stored_data.get('temperature', 'N/A')}℃")
            print(f"   POP: {stored_data.get('precipitation_prob', 'N/A')}%")
            print(f"   Warnings: {stored_data.get('warnings', [])}")
            print(f"   Disasters: {stored_data.get('disaster', [])}")
            
            # Step 3: クエリサーバーから取得
            print("🔍 Step 3: Querying data from Query Server...")
            query_client = QueryClient(
                host="localhost",
                port=self.query_port,
                debug=self.debug
            )
            
            try:
                response = query_client.get_weather_data(
                    area_code=test_area_code,
                    weather=True,
                    temperature=True,
                    pop=True,
                    alert=True,
                    disaster=True
                )
                
                if not response or not response.get("success"):
                    print("❌ Query failed or returned error")
                    return False
                
                data = response.get("data", {})
                print(f"✅ Query successful:")
                print(f"   Weather Code: {data.get('weather_code', 'N/A')}")
                print(f"   Temperature: {data.get('temperature', 'N/A')}℃")
                print(f"   POP: {data.get('precipitation_prob', 'N/A')}%")
                print(f"   Alerts: {data.get('alerts', [])}")
                print(f"   Disasters: {data.get('disasters', [])}")
                
                # データ整合性確認
                if (data.get('weather_code') == test_data['weather_code'] and
                    data.get('temperature') == test_data['temperature'] and
                    data.get('precipitation_prob') == test_data['precipitation_prob']):
                    print("✅ Data integrity confirmed!")
                    return True
                else:
                    print("⚠️  Data integrity check failed")
                    print(f"   Expected: weather={test_data['weather_code']}, temp={test_data['temperature']}, pop={test_data['precipitation_prob']}")
                    print(f"   Got: weather={data.get('weather_code')}, temp={data.get('temperature')}, pop={data.get('precipitation_prob')}")
                    return False
                
            finally:
                query_client.close()
                redis_manager.close()
                
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            if self.debug:
                import traceback
                traceback.print_exc()
            return False
    
    def test_multiple_cities(self) -> bool:
        """複数都市のフローテスト"""
        print("\n🌍 Testing Multiple Cities Flow...")
        print("-" * 40)
        
        test_cities = {
            "130000": {"name": "Tokyo", "weather": 100, "temp": 25.5, "pop": 30},
            "270000": {"name": "Osaka", "weather": 300, "temp": 18.7, "pop": 80},
            "011000": {"name": "Sapporo", "weather": 400, "temp": -2.1, "pop": 90}
        }
        
        try:
            reporter = WeatherAPIReporter(
                report_server_host="localhost",
                report_server_port=self.report_port,
                debug=False  # 複数実行時はログを簡潔に
            )
            
            # 送信
            print("📤 Sending data for multiple cities...")
            success_count = 0
            for area_code, info in test_cities.items():
                test_data = {
                    "area_code": area_code,
                    "weather_code": info["weather"],
                    "temperature": info["temp"],
                    "precipitation_prob": info["pop"],
                    "alert": [f"{info['name']}テスト警報"],
                    "disaster": []
                }
                
                if reporter.send_weather_report(test_data):
                    success_count += 1
                    print(f"   ✅ {info['name']} ({area_code})")
                else:
                    print(f"   ❌ {info['name']} ({area_code})")
            
            print(f"📊 Sent: {success_count}/{len(test_cities)} cities")
            
            if success_count == 0:
                return False
            
            # 少し待機
            time.sleep(2)
            
            # クエリテスト
            print("🔍 Querying multiple cities...")
            query_client = QueryClient(
                host="localhost",
                port=self.query_port,
                debug=False
            )
            
            try:
                query_success_count = 0
                for area_code, info in test_cities.items():
                    response = query_client.get_weather_data(
                        area_code=area_code,
                        weather=True,
                        temperature=True,
                        pop=True
                    )
                    
                    if response and response.get("success"):
                        query_success_count += 1
                        data = response.get("data", {})
                        print(f"   ✅ {info['name']}: W={data.get('weather_code')}, T={data.get('temperature')}℃")
                    else:
                        print(f"   ❌ {info['name']}: Query failed")
                
                print(f"📊 Queried: {query_success_count}/{len(test_cities)} cities")
                return query_success_count > 0
                
            finally:
                query_client.close()
                
        except Exception as e:
            print(f"❌ Multiple cities test failed: {e}")
            return False
    
    def run_all_tests(self) -> bool:
        """全テストを実行"""
        print("\n🚀 Starting Flow Tests...")
        print("=" * 50)
        
        # テストデータクリーンアップ
        self.cleanup_test_data()
        
        results = []
        
        # 基本フローテスト
        results.append(("Basic Flow", self.test_basic_flow()))
        
        # 複数都市テスト
        results.append(("Multiple Cities", self.test_multiple_cities()))
        
        # 結果サマリー
        print("\n📊 Test Results Summary:")
        print("=" * 30)
        passed = 0
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        
        total = len(results)
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        print(f"\nOverall: {passed}/{total} tests passed ({success_rate:.1f}%)")
        
        # クリーンアップ
        self.cleanup_test_data()
        
        return passed == total


def main():
    parser = argparse.ArgumentParser(description="Simple Weather Data Flow Test")
    parser.add_argument("--report-port", type=int, default=9999, 
                       help="Report Server port (default: 9999)")
    parser.add_argument("--query-port", type=int, default=4111,
                       help="Query Server port (default: 4111)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    parser.add_argument("--no-cleanup", action="store_true",
                       help="Skip cleanup (keep test data in Redis)")
    
    args = parser.parse_args()
    
    # Redis接続確認
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        redis_client.ping()
        print("✅ Redis connection confirmed")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("💡 Please start Redis server before running tests")
        return 1
    
    # テスト実行
    tester = SimpleFlowTester(
        report_port=args.report_port,
        query_port=args.query_port,
        debug=args.debug
    )
    
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! Data flow is working correctly.")
        return 0
    else:
        print("\n💥 Some tests failed. Please check server status and logs.")
        return 1


if __name__ == "__main__":
    sys.exit(main())