#!/usr/bin/env python3
"""
JMA Weather API Simple Test

既に起動しているサーバーを使用して、JMAからのデータ取得から
レポートサーバー送信までの基本フローをテストします。

前提条件:
- Redis サーバーが起動している
- Weather API Server が起動している (port 80)
- Report Server が起動している (port 9999)

使用方法:
python test_jma_api_simple.py [--api-port 80] [--report-port 9999]
"""

import sys
import os
import time
import argparse
import requests
import json
from typing import Dict, Any, List

# WIPCommonPyをインポートするためのパス設定
sys.path.insert(0, '/mnt/c/Users/ポッポ焼き/Desktop/WIP/src')

from WIPCommonPy.clients.report_client import ReportClient
from WIPServerPy.data.redis_manager import WeatherRedisManager


class JMAAPISimpleTester:
    """JMA API シンプルテスター"""
    
    def __init__(self, api_port: int = 80, report_port: int = 9999, debug: bool = True):
        self.api_port = api_port
        self.report_port = report_port
        self.debug = debug
        # Report Serverが使っているプレフィックスを取得
        self.actual_prefix = (
            os.getenv("REPORT_DB_KEY_PREFIX")
            or os.getenv("REDIS_KEY_PREFIX")
            or ""
        )
        
        print(f"JMA Weather API Simple Tester")
        print(f"Weather API: localhost:{api_port}")
        print(f"Report Server: localhost:{report_port}")
        print(f"Redis Prefix: '{self.actual_prefix}' (from environment)")
        print("="*50)
    
    def cleanup_test_data(self):
        """テストデータをクリーンアップ（実際のプレフィックスがtest系の場合のみ）"""
        try:
            import redis
            redis_client = redis.Redis(host='localhost', port=6379, db=0)
            # プレフィックスに"test"が含まれる場合のみクリーンアップ実行
            if "test" in self.actual_prefix.lower():
                keys = redis_client.keys(f"{self.actual_prefix}*")
                if keys:
                    redis_client.delete(*keys)
                    print(f"🧹 Cleaned up {len(keys)} test keys from Redis")
            else:
                print(f"⚠️ Skipping cleanup - prefix '{self.actual_prefix}' doesn't appear to be for testing")
        except Exception as e:
            print(f"⚠️ Redis cleanup warning: {e}")
    
    def check_weather_api_server(self) -> bool:
        """Weather API Serverの起動確認"""
        try:
            response = requests.get(f"http://localhost:{self.api_port}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def check_report_server(self) -> bool:
        """Report Serverの起動確認"""
        try:
            # 実際のReportClientを使用して適切な接続テストを行う
            from WIPCommonPy.clients.report_client import ReportClient
            
            client = ReportClient(host="localhost", port=self.report_port, debug=False)
            client.set_sensor_data(
                area_code="130000",  # 有効なエリアコード
                weather_code=100,
                temperature=20.0,
                precipitation_prob=10,
                alert=[],
                disaster=[]
            )
            
            # 短いタイムアウトでテスト
            client.sock.settimeout(2)
            result = client.send_report_data()
            client.close()
            
            return result is not None and result.get("success", False)
        except:
            return False
    
    def test_jma_data_fetch(self) -> Dict[str, Any]:
        """JMAデータ取得テスト"""
        print("\n📡 Testing JMA Data Fetch...")
        print("-" * 30)
        
        if not self.check_weather_api_server():
            print("❌ Weather API Server is not running")
            print("💡 Start the server with: python python/application/weather_api/start_server.py")
            return {"success": False, "error": "API server not running"}
        
        try:
            # 気象データ更新をトリガー
            print("🔄 Triggering weather data update...")
            response = requests.post(f"http://localhost:{self.api_port}/update/weather", 
                                   timeout=30)
            
            if response.status_code != 200:
                print(f"❌ Weather update failed: {response.status_code}")
                return {"success": False, "error": "Update failed"}
            
            update_result = response.json()
            print(f"✅ Weather update: {update_result.get('detail', 'OK')}")
            
            # 少し待機
            time.sleep(3)
            
            # 利用可能エリア取得
            response = requests.get(f"http://localhost:{self.api_port}/areas")
            if response.status_code != 200:
                print(f"❌ Areas fetch failed: {response.status_code}")
                return {"success": False, "error": "Areas fetch failed"}
            
            areas = response.json()
            print(f"✅ Found {len(areas)} areas")
            
            if not areas:
                print("⚠️ No areas found")
                return {"success": False, "error": "No areas available"}
            
            # サンプルエリアのデータ取得
            test_area = "130000" if "130000" in areas else areas[0]
            print(f"🎯 Testing area: {test_area}")
            
            response = requests.get(f"http://localhost:{self.api_port}/weather",
                                   params={
                                       "area_code": test_area,
                                       "weather_flag": 1,
                                       "temperature_flag": 1,
                                       "pop_flag": 1,
                                       "alert_flag": 1,
                                       "disaster_flag": 1
                                   })
            
            if response.status_code != 200:
                print(f"❌ Weather data fetch failed: {response.status_code}")
                return {"success": False, "error": "Weather data fetch failed"}
            
            weather_data = response.json()
            print(f"✅ Weather data retrieved:")
            print(f"   Weather: {weather_data.get('weather', 'N/A')}")
            print(f"   Temperature: {weather_data.get('temperature', 'N/A')}")
            print(f"   POP: {weather_data.get('precipitation_prob', 'N/A')}")
            print(f"   Warnings: {len(weather_data.get('warnings', []))} items")
            print(f"   Disasters: {len(weather_data.get('disaster', []))} items")
            
            return {
                "success": True,
                "area_code": test_area,
                "data": weather_data,
                "available_areas": areas
            }
            
        except requests.exceptions.Timeout:
            print("❌ Request timed out (JMA might be slow)")
            return {"success": False, "error": "Timeout"}
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {"success": False, "error": str(e)}
    
    def test_report_submission(self, api_result: Dict[str, Any]) -> bool:
        """レポートサーバー送信テスト"""
        print("\n📤 Testing Report Submission...")
        print("-" * 30)
        
        if not api_result.get("success"):
            print("❌ Cannot test report submission - API fetch failed")
            return False
        
        if not self.check_report_server():
            print("❌ Report Server is not running")
            print("💡 Start the server with appropriate command")
            return False
        
        area_code = api_result["area_code"]
        weather_data = api_result["data"]
        
        try:
            # ReportClientでデータ送信
            report_client = ReportClient(
                host="localhost",
                port=self.report_port,
                debug=self.debug
            )
            
            # APIデータをレポート形式に変換
            weather_code = self._extract_value(weather_data.get('weather'))
            temperature = self._extract_numeric_value(weather_data.get('temperature'))
            pop = self._extract_numeric_value(weather_data.get('precipitation_prob'))
            
            print(f"📊 Converted data:")
            print(f"   Area: {area_code}")
            print(f"   Weather Code: {weather_code}")
            print(f"   Temperature: {temperature}")
            print(f"   POP: {pop}")
            
            report_client.set_sensor_data(
                area_code=area_code,
                weather_code=weather_code,
                temperature=temperature,
                precipitation_prob=pop,
                alert=weather_data.get('warnings', []),
                disaster=weather_data.get('disaster', [])
            )
            
            result = report_client.send_report_data()
            report_client.close()
            
            if result and result.get("success"):
                print("✅ Report sent successfully")
                print(f"   Packet ID: {result.get('packet_id')}")
                print(f"   Response time: {result.get('response_time_ms', 0):.1f}ms")
                return True
            else:
                print("❌ Report submission failed")
                return False
                
        except Exception as e:
            print(f"❌ Report submission error: {e}")
            return False
    
    def test_redis_storage(self, area_code: str) -> bool:
        """Redis保存確認テスト"""
        print("\n🗄️ Testing Redis Storage...")
        print("-" * 30)
        
        try:
            # 少し待機してデータが保存されるのを待つ
            time.sleep(2)
            
            # ReportServerと同じロジックでキープレフィックスを決定
            # 優先順位: REPORT_DB_KEY_PREFIX > REDIS_KEY_PREFIX > デフォルト("")
            key_prefix = (
                os.getenv("REPORT_DB_KEY_PREFIX")
                or os.getenv("REDIS_KEY_PREFIX")
                or ""
            )
            
            if self.debug:
                print(f"  [Debug] Reading from Redis with key_prefix='{key_prefix}'")
                print(f"  [Debug] REPORT_DB_KEY_PREFIX='{os.getenv('REPORT_DB_KEY_PREFIX')}'")
                print(f"  [Debug] REDIS_KEY_PREFIX='{os.getenv('REDIS_KEY_PREFIX')}'")
            
            redis_manager = WeatherRedisManager(
                debug=self.debug,
                key_prefix=key_prefix
            )
            
            stored_data = redis_manager.get_weather_data(area_code)
            redis_manager.close()
            
            if stored_data:
                print(f"✅ Data found in Redis for {area_code}:")
                print(f"   Weather: {stored_data.get('weather', 'N/A')}")
                print(f"   Temperature: {stored_data.get('temperature', 'N/A')}")
                print(f"   POP: {stored_data.get('precipitation_prob', 'N/A')}")
                print(f"   Warnings: {len(stored_data.get('warnings', []))} items")
                print(f"   Disasters: {len(stored_data.get('disaster', []))} items")
                return True
            else:
                print(f"❌ No data found in Redis for {area_code}")
                return False
                
        except Exception as e:
            print(f"❌ Redis check error: {e}")
            return False
    
    def test_multiple_areas(self, areas: List[str], max_areas: int = 3) -> Dict[str, bool]:
        """複数エリアのテスト"""
        print(f"\n🌍 Testing Multiple Areas (max {max_areas})...")
        print("-" * 40)
        
        test_areas = areas[:max_areas]
        results = {}
        
        for i, area_code in enumerate(test_areas, 1):
            print(f"\n--- Area {i}/{len(test_areas)}: {area_code} ---")
            
            try:
                # APIデータ取得
                response = requests.get(f"http://localhost:{self.api_port}/weather",
                                       params={"area_code": area_code})
                
                if response.status_code != 200:
                    print(f"❌ API fetch failed")
                    results[area_code] = False
                    continue
                
                api_data = response.json()
                
                # レポート送信
                report_client = ReportClient(
                    host="localhost",
                    port=self.report_port,
                    debug=False
                )
                
                weather_code = self._extract_value(api_data.get('weather'))
                temperature = self._extract_numeric_value(api_data.get('temperature'))
                pop = self._extract_numeric_value(api_data.get('precipitation_prob'))
                
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
                    print(f"✅ {area_code}: Complete flow successful")
                    results[area_code] = True
                else:
                    print(f"❌ {area_code}: Report failed")
                    results[area_code] = False
                
            except Exception as e:
                print(f"❌ {area_code}: Error - {e}")
                results[area_code] = False
            
            # 短い待機（サーバー負荷軽減）
            time.sleep(0.5)
        
        return results
    
    def _extract_value(self, value):
        """値の抽出（リストの場合は最初の要素）"""
        if isinstance(value, list) and value:
            return value[0]
        return value
    
    def _extract_numeric_value(self, value):
        """数値の抽出と変換"""
        extracted = self._extract_value(value)
        if extracted is None or extracted == '':
            return None
        try:
            if isinstance(extracted, str):
                return float(extracted) if '.' in extracted else int(extracted)
            return extracted
        except (ValueError, TypeError):
            return None
    
    def run_all_tests(self) -> bool:
        """全テストを実行"""
        print("\n🚀 Starting JMA API Integration Tests...")
        print("=" * 50)
        
        # テストデータクリーンアップ
        self.cleanup_test_data()
        
        results = []
        
        # JMAデータ取得テスト
        api_result = self.test_jma_data_fetch()
        results.append(("JMA Data Fetch", api_result.get("success", False)))
        
        if api_result.get("success"):
            area_code = api_result["area_code"]
            
            # レポート送信テスト
            report_success = self.test_report_submission(api_result)
            results.append(("Report Submission", report_success))
            
            if report_success:
                # Redis保存確認
                redis_success = self.test_redis_storage(area_code)
                results.append(("Redis Storage", redis_success))
            
            # 複数エリアテスト
            if len(api_result.get("available_areas", [])) > 1:
                multi_results = self.test_multiple_areas(api_result["available_areas"])
                success_count = sum(1 for success in multi_results.values() if success)
                total_count = len(multi_results)
                multi_success = success_count > 0
                results.append((f"Multiple Areas ({success_count}/{total_count})", multi_success))
        
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
    parser = argparse.ArgumentParser(description="JMA Weather API Simple Integration Test")
    parser.add_argument("--api-port", type=int, default=8001,
                       help="Weather API Server port (default: 8001)")
    parser.add_argument("--report-port", type=int, default=9999,
                       help="Report Server port (default: 9999)")
    parser.add_argument("--debug", action="store_true",
                       help="Enable debug output")
    
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
    tester = JMAAPISimpleTester(
        api_port=args.api_port,
        report_port=args.report_port,
        debug=args.debug
    )
    
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All tests passed! JMA integration is working correctly.")
        print("\n📋 Data flow confirmed:")
        print("   JMA → Weather API → Report Client → Report Server → Redis")
        return 0
    else:
        print("\n💥 Some tests failed. Please check server status and logs.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
