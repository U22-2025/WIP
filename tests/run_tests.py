import unittest
import csv
import time
import os
from test_checksum import TestChecksum
from test_server_checksum import TestServerChecksum

def run_performance_tests():
    """パフォーマンステストを実行し結果をCSV出力"""
    results = []
    test_cases = [
        ('1KB Data', lambda: TestChecksum().test_load_performance()),
        ('1MB Data', lambda: TestChecksum().test_performance())
    ]
    
    for name, test_func in test_cases:
        start = time.perf_counter()
        test_func()
        elapsed = time.perf_counter() - start
        results.append({
            'Test Case': name,
            'Execution Time (ms)': round(elapsed * 1000, 2)
        })
    
    # CSV出力
    csv_path = 'test_results/performance.csv'
    os.makedirs('test_results', exist_ok=True)
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    print(f"Performance results saved to {csv_path}")

if __name__ == '__main__':
    # ユニットテストを実行
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestChecksum)
    suite.addTests(loader.loadTestsFromTestCase(TestServerChecksum))
    
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
    
    # パフォーマンステストを実行
    run_performance_tests()