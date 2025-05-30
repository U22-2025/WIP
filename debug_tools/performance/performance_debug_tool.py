#!/usr/bin/env python3
"""
拡張フィールド処理のパフォーマンステストツール
大量データでの処理性能と安定性を検証します
"""

import sys
import os
import time
import random
import statistics
from typing import Dict, Any, List, Tuple
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'wtp'))

from wtp.packet import Format
from wtp.packet.extended_field_mixin import ExtendedFieldType


class PerformanceDebugger:
    """パフォーマンステスト用デバッグクラス"""
    
    def __init__(self):
        self.test_results = []
        
    def log(self, message: str):
        """ログ出力"""
        print(f"[PERF] {message}")
        
    def generate_test_data(self, count: int) -> List[Dict[str, Any]]:
        """テストデータを生成"""
        test_data = []
        
        for i in range(count):
            data = {}
            
            # ランダムにフィールドを選択
            if random.choice([True, False]):
                data['alert'] = [f"警報{i}", f"追加警報{i}"]
                
            if random.choice([True, False]):
                data['disaster'] = [f"災害{i}"]
                
            if random.choice([True, False]):
                # ランダムな座標（日本周辺）
                data['latitude'] = random.uniform(24.0, 46.0)
                data['longitude'] = random.uniform(123.0, 146.0)
                
            if random.choice([True, False]):
                # ランダムなIPアドレス
                data['source_ip'] = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
                
            test_data.append(data)
            
        return test_data
        
    def measure_encoding_performance(self, test_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """エンコード性能を測定"""
        self.log(f"エンコード性能測定開始 ({len(test_data)}件)")
        
        times = []
        success_count = 0
        error_count = 0
        
        for i, data in enumerate(test_data):
            try:
                start_time = time.perf_counter()
                
                packet = Format(
                    version=1,
                    packet_id=i,
                    ex_flag=1,
                    timestamp=int(time.time()),
                    ex_field=data
                )
                
                byte_data = packet.to_bytes()
                
                end_time = time.perf_counter()
                times.append(end_time - start_time)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                self.log(f"エンコードエラー {i}: {e}")
                
        if times:
            results = {
                "total_count": len(test_data),
                "success_count": success_count,
                "error_count": error_count,
                "min_time": min(times),
                "max_time": max(times),
                "avg_time": statistics.mean(times),
                "median_time": statistics.median(times),
                "total_time": sum(times)
            }
            
            if len(times) > 1:
                results["std_dev"] = statistics.stdev(times)
            else:
                results["std_dev"] = 0.0
                
            self.log(f"エンコード結果: 成功{success_count}, エラー{error_count}")
            self.log(f"平均時間: {results['avg_time']:.6f}秒")
            self.log(f"総時間: {results['total_time']:.6f}秒")
            
            return results
        else:
            return {"error": "測定データなし"}
            
    def measure_decoding_performance(self, encoded_data: List[bytes]) -> Dict[str, float]:
        """デコード性能を測定"""
        self.log(f"デコード性能測定開始 ({len(encoded_data)}件)")
        
        times = []
        success_count = 0
        error_count = 0
        
        for i, data in enumerate(encoded_data):
            try:
                start_time = time.perf_counter()
                
                packet = Format.from_bytes(data)
                ex_field = packet.ex_field
                
                end_time = time.perf_counter()
                times.append(end_time - start_time)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                self.log(f"デコードエラー {i}: {e}")
                
        if times:
            results = {
                "total_count": len(encoded_data),
                "success_count": success_count,
                "error_count": error_count,
                "min_time": min(times),
                "max_time": max(times),
                "avg_time": statistics.mean(times),
                "median_time": statistics.median(times),
                "total_time": sum(times)
            }
            
            if len(times) > 1:
                results["std_dev"] = statistics.stdev(times)
            else:
                results["std_dev"] = 0.0
                
            self.log(f"デコード結果: 成功{success_count}, エラー{error_count}")
            self.log(f"平均時間: {results['avg_time']:.6f}秒")
            self.log(f"総時間: {results['total_time']:.6f}秒")
            
            return results
        else:
            return {"error": "測定データなし"}
            
    def measure_roundtrip_performance(self, test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """ラウンドトリップ性能を測定"""
        self.log(f"ラウンドトリップ性能測定開始 ({len(test_data)}件)")
        
        times = []
        success_count = 0
        error_count = 0
        data_integrity_errors = 0
        
        for i, original_data in enumerate(test_data):
            try:
                start_time = time.perf_counter()
                
                # エンコード
                packet = Format(
                    version=1,
                    packet_id=i,
                    ex_flag=1,
                    timestamp=int(time.time()),
                    ex_field=original_data
                )
                
                byte_data = packet.to_bytes()
                
                # デコード
                restored_packet = Format.from_bytes(byte_data)
                restored_data = restored_packet.ex_field
                
                end_time = time.perf_counter()
                times.append(end_time - start_time)
                
                # データ整合性チェック
                if self._verify_data_integrity(original_data, restored_data):
                    success_count += 1
                else:
                    data_integrity_errors += 1
                    self.log(f"データ整合性エラー {i}: {original_data} != {restored_data}")
                    
            except Exception as e:
                error_count += 1
                self.log(f"ラウンドトリップエラー {i}: {e}")
                
        if times:
            results = {
                "total_count": len(test_data),
                "success_count": success_count,
                "error_count": error_count,
                "data_integrity_errors": data_integrity_errors,
                "min_time": min(times),
                "max_time": max(times),
                "avg_time": statistics.mean(times),
                "median_time": statistics.median(times),
                "total_time": sum(times)
            }
            
            if len(times) > 1:
                results["std_dev"] = statistics.stdev(times)
            else:
                results["std_dev"] = 0.0
                
            self.log(f"ラウンドトリップ結果: 成功{success_count}, エラー{error_count}, 整合性エラー{data_integrity_errors}")
            self.log(f"平均時間: {results['avg_time']:.6f}秒")
            
            return results
        else:
            return {"error": "測定データなし"}
            
    def _verify_data_integrity(self, original: Dict[str, Any], restored: Dict[str, Any]) -> bool:
        """データ整合性を検証"""
        for key, original_value in original.items():
            if key not in restored:
                return False
                
            restored_value = restored[key]
            
            if isinstance(original_value, float):
                # 浮動小数点数の比較（誤差許容）
                if abs(original_value - restored_value) >= 0.000001:
                    return False
            else:
                # その他の値の比較
                if original_value != restored_value:
                    return False
                    
        return True
        
    def test_memory_usage(self, test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """メモリ使用量をテスト"""
        self.log(f"メモリ使用量テスト開始 ({len(test_data)}件)")
        
        try:
            import psutil
            process = psutil.Process()
            
            # 開始時のメモリ使用量
            initial_memory = process.memory_info().rss
            
            # 大量のパケットを作成
            packets = []
            for i, data in enumerate(test_data):
                packet = Format(
                    version=1,
                    packet_id=i,
                    ex_flag=1,
                    timestamp=int(time.time()),
                    ex_field=data
                )
                packets.append(packet)
                
            # ピーク時のメモリ使用量
            peak_memory = process.memory_info().rss
            
            # パケットを削除
            del packets
            
            # 削除後のメモリ使用量
            final_memory = process.memory_info().rss
            
            results = {
                "initial_memory_mb": initial_memory / 1024 / 1024,
                "peak_memory_mb": peak_memory / 1024 / 1024,
                "final_memory_mb": final_memory / 1024 / 1024,
                "memory_increase_mb": (peak_memory - initial_memory) / 1024 / 1024,
                "memory_per_packet_kb": (peak_memory - initial_memory) / len(test_data) / 1024
            }
            
            self.log(f"メモリ使用量: 初期{results['initial_memory_mb']:.2f}MB, "
                    f"ピーク{results['peak_memory_mb']:.2f}MB, "
                    f"パケット当たり{results['memory_per_packet_kb']:.2f}KB")
            
            return results
            
        except ImportError:
            self.log("psutilが利用できません。メモリテストをスキップします。")
            return {"error": "psutil not available"}
        except Exception as e:
            self.log(f"メモリテストエラー: {e}")
            return {"error": str(e)}
            
    def test_concurrent_access(self, test_data: List[Dict[str, Any]], thread_count: int = 4) -> Dict[str, Any]:
        """並行アクセステスト"""
        self.log(f"並行アクセステスト開始 (スレッド数: {thread_count})")
        
        try:
            import threading
            import queue
            
            results_queue = queue.Queue()
            errors_queue = queue.Queue()
            
            def worker_thread(thread_id: int, data_chunk: List[Dict[str, Any]]):
                """ワーカースレッド"""
                try:
                    thread_results = []
                    for i, data in enumerate(data_chunk):
                        start_time = time.perf_counter()
                        
                        packet = Format(
                            version=1,
                            packet_id=thread_id * 1000 + i,
                            ex_flag=1,
                            timestamp=int(time.time()),
                            ex_field=data
                        )
                        
                        byte_data = packet.to_bytes()
                        restored = Format.from_bytes(byte_data)
                        
                        end_time = time.perf_counter()
                        thread_results.append(end_time - start_time)
                        
                    results_queue.put((thread_id, thread_results))
                    
                except Exception as e:
                    errors_queue.put((thread_id, str(e)))
                    
            # データを分割
            chunk_size = len(test_data) // thread_count
            threads = []
            
            start_time = time.perf_counter()
            
            for i in range(thread_count):
                start_idx = i * chunk_size
                end_idx = start_idx + chunk_size if i < thread_count - 1 else len(test_data)
                data_chunk = test_data[start_idx:end_idx]
                
                thread = threading.Thread(
                    target=worker_thread,
                    args=(i, data_chunk)
                )
                threads.append(thread)
                thread.start()
                
            # スレッドの完了を待機
            for thread in threads:
                thread.join()
                
            end_time = time.perf_counter()
            
            # 結果を集計
            all_times = []
            thread_results = {}
            
            while not results_queue.empty():
                thread_id, times = results_queue.get()
                thread_results[thread_id] = times
                all_times.extend(times)
                
            # エラーを集計
            errors = []
            while not errors_queue.empty():
                thread_id, error = errors_queue.get()
                errors.append(f"Thread {thread_id}: {error}")
                
            if all_times:
                results = {
                    "thread_count": thread_count,
                    "total_operations": len(all_times),
                    "total_time": end_time - start_time,
                    "avg_time_per_operation": statistics.mean(all_times),
                    "operations_per_second": len(all_times) / (end_time - start_time),
                    "errors": errors,
                    "thread_results": {
                        tid: {
                            "count": len(times),
                            "avg_time": statistics.mean(times),
                            "total_time": sum(times)
                        }
                        for tid, times in thread_results.items()
                    }
                }
                
                self.log(f"並行処理結果: {results['operations_per_second']:.2f} ops/sec")
                
                return results
            else:
                return {"error": "測定データなし"}
                
        except ImportError:
            self.log("threadingが利用できません。並行テストをスキップします。")
            return {"error": "threading not available"}
        except Exception as e:
            self.log(f"並行テストエラー: {e}")
            return {"error": str(e)}
            
    def run_performance_tests(self, test_sizes: List[int] = [100, 1000, 5000]):
        """パフォーマンステストを実行"""
        self.log("パフォーマンステスト開始")
        
        for size in test_sizes:
            self.log(f"\n{'='*50}")
            self.log(f"テストサイズ: {size}")
            
            # テストデータ生成
            test_data = self.generate_test_data(size)
            
            # エンコード性能テスト
            encoding_results = self.measure_encoding_performance(test_data)
            
            # エンコードされたデータを準備
            encoded_data = []
            for i, data in enumerate(test_data):
                try:
                    packet = Format(
                        version=1,
                        packet_id=i,
                        ex_flag=1,
                        timestamp=int(time.time()),
                        ex_field=data
                    )
                    encoded_data.append(packet.to_bytes())
                except:
                    pass
                    
            # デコード性能テスト
            decoding_results = self.measure_decoding_performance(encoded_data)
            
            # ラウンドトリップ性能テスト
            roundtrip_results = self.measure_roundtrip_performance(test_data[:min(100, size)])
            
            # メモリ使用量テスト
            memory_results = self.test_memory_usage(test_data[:min(100, size)])
            
            # 並行アクセステスト
            concurrent_results = self.test_concurrent_access(test_data[:min(50, size)])
            
            # 結果を保存
            test_result = {
                "test_size": size,
                "encoding": encoding_results,
                "decoding": decoding_results,
                "roundtrip": roundtrip_results,
                "memory": memory_results,
                "concurrent": concurrent_results
            }
            
            self.test_results.append(test_result)
            
        # レポート生成
        self.generate_performance_report()
        
    def generate_performance_report(self, output_file: str = None):
        """パフォーマンスレポートを生成"""
        # デフォルトのファイル名を設定
        if output_file is None:
            # reportsフォルダに保存
            reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            output_file = os.path.join(reports_dir, "performance_debug_report.json")
            
        report = {
            "test_results": self.test_results,
            "summary": self._generate_summary()
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        self.log(f"パフォーマンスレポートを生成しました: {output_file}")
        
    def _generate_summary(self) -> Dict[str, Any]:
        """サマリーを生成"""
        if not self.test_results:
            return {}
            
        summary = {
            "test_count": len(self.test_results),
            "encoding_performance": {},
            "decoding_performance": {},
            "roundtrip_performance": {}
        }
        
        # エンコード性能のサマリー
        encoding_times = []
        for result in self.test_results:
            if "avg_time" in result["encoding"]:
                encoding_times.append(result["encoding"]["avg_time"])
                
        if encoding_times:
            summary["encoding_performance"] = {
                "avg_time": statistics.mean(encoding_times),
                "min_time": min(encoding_times),
                "max_time": max(encoding_times)
            }
            
        # デコード性能のサマリー
        decoding_times = []
        for result in self.test_results:
            if "avg_time" in result["decoding"]:
                decoding_times.append(result["decoding"]["avg_time"])
                
        if decoding_times:
            summary["decoding_performance"] = {
                "avg_time": statistics.mean(decoding_times),
                "min_time": min(decoding_times),
                "max_time": max(decoding_times)
            }
            
        return summary


def main():
    """メイン関数"""
    debugger = PerformanceDebugger()
    debugger.run_performance_tests([100, 500, 1000])


if __name__ == "__main__":
    main()
