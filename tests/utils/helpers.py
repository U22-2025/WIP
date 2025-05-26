"""
テストヘルパー関数

テスト実行を支援するユーティリティ関数を提供します。
"""

import time
import traceback
import functools
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager
from datetime import datetime


class TestHelpers:
    """テスト実行支援のヘルパークラス"""
    
    @staticmethod
    def measure_execution_time(func: Callable) -> Tuple[Any, float]:
        """
        関数の実行時間を測定
        
        Args:
            func: 実行する関数
            
        Returns:
            (関数の戻り値, 実行時間(秒))
        """
        start_time = time.perf_counter()
        try:
            result = func()
            end_time = time.perf_counter()
            return result, end_time - start_time
        except Exception as e:
            end_time = time.perf_counter()
            raise e
    
    @staticmethod
    def retry_on_failure(max_retries: int = 3, delay: float = 0.1):
        """
        失敗時にリトライするデコレータ
        
        Args:
            max_retries: 最大リトライ回数
            delay: リトライ間隔（秒）
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                last_exception = None
                
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries:
                            time.sleep(delay)
                        else:
                            raise last_exception
                            
            return wrapper
        return decorator
    
    @staticmethod
    @contextmanager
    def capture_exceptions():
        """
        例外をキャプチャするコンテキストマネージャ
        
        Yields:
            例外情報を格納するリスト
        """
        exceptions = []
        
        class ExceptionCapture:
            def __init__(self):
                self.exceptions = exceptions
            
            def add(self, exception: Exception):
                self.exceptions.append({
                    'exception': exception,
                    'type': type(exception).__name__,
                    'message': str(exception),
                    'traceback': traceback.format_exc(),
                    'timestamp': datetime.now()
                })
        
        capture = ExceptionCapture()
        
        try:
            yield capture
        except Exception as e:
            capture.add(e)
            raise
    
    @staticmethod
    def create_test_matrix(parameters: Dict[str, List[Any]]) -> List[Dict[str, Any]]:
        """
        テストパラメータの組み合わせマトリックスを作成
        
        Args:
            parameters: パラメータ名と値のリストの辞書
            
        Returns:
            全組み合わせのリスト
        """
        import itertools
        
        keys = list(parameters.keys())
        values = list(parameters.values())
        
        combinations = []
        for combination in itertools.product(*values):
            combinations.append(dict(zip(keys, combination)))
        
        return combinations
    
    @staticmethod
    def compare_performance(func1: Callable, func2: Callable, iterations: int = 100) -> Dict[str, Any]:
        """
        2つの関数のパフォーマンスを比較
        
        Args:
            func1: 比較対象関数1
            func2: 比較対象関数2
            iterations: 実行回数
            
        Returns:
            パフォーマンス比較結果
        """
        times1 = []
        times2 = []
        
        # func1の測定
        for _ in range(iterations):
            _, exec_time = TestHelpers.measure_execution_time(func1)
            times1.append(exec_time)
        
        # func2の測定
        for _ in range(iterations):
            _, exec_time = TestHelpers.measure_execution_time(func2)
            times2.append(exec_time)
        
        avg1 = sum(times1) / len(times1)
        avg2 = sum(times2) / len(times2)
        
        return {
            'func1': {
                'average': avg1,
                'min': min(times1),
                'max': max(times1),
                'times': times1
            },
            'func2': {
                'average': avg2,
                'min': min(times2),
                'max': max(times2),
                'times': times2
            },
            'comparison': {
                'ratio': avg1 / avg2 if avg2 > 0 else float('inf'),
                'difference': avg1 - avg2,
                'faster': 'func1' if avg1 < avg2 else 'func2'
            }
        }
    
    @staticmethod
    def generate_test_report(test_results: List[Dict[str, Any]], output_file: Optional[str] = None) -> str:
        """
        テスト結果のレポートを生成
        
        Args:
            test_results: テスト結果のリスト
            output_file: 出力ファイル名（Noneの場合は文字列で返す）
            
        Returns:
            レポート文字列
        """
        report_lines = []
        report_lines.append("=" * 60)
        report_lines.append("テスト実行レポート")
        report_lines.append("=" * 60)
        report_lines.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results if result.get('status') == 'passed')
        failed_tests = total_tests - passed_tests
        
        report_lines.append("サマリー:")
        report_lines.append(f"  総テスト数: {total_tests}")
        report_lines.append(f"  成功: {passed_tests}")
        report_lines.append(f"  失敗: {failed_tests}")
        report_lines.append(f"  成功率: {(passed_tests/total_tests*100):.1f}%")
        report_lines.append("")
        
        if failed_tests > 0:
            report_lines.append("失敗したテスト:")
            for result in test_results:
                if result.get('status') == 'failed':
                    report_lines.append(f"  - {result.get('name', 'Unknown')}")
                    if 'error' in result:
                        report_lines.append(f"    エラー: {result['error']}")
            report_lines.append("")
        
        # パフォーマンス情報があれば追加
        performance_results = [r for r in test_results if 'execution_time' in r]
        if performance_results:
            report_lines.append("パフォーマンス:")
            avg_time = sum(r['execution_time'] for r in performance_results) / len(performance_results)
            max_time = max(r['execution_time'] for r in performance_results)
            min_time = min(r['execution_time'] for r in performance_results)
            
            report_lines.append(f"  平均実行時間: {avg_time:.4f}秒")
            report_lines.append(f"  最大実行時間: {max_time:.4f}秒")
            report_lines.append(f"  最小実行時間: {min_time:.4f}秒")
            report_lines.append("")
        
        report_content = "\n".join(report_lines)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
        
        return report_content
    
    @staticmethod
    def validate_test_environment() -> Dict[str, Any]:
        """
        テスト環境の検証
        
        Returns:
            環境情報の辞書
        """
        import sys
        import platform
        
        env_info = {
            'python_version': sys.version,
            'platform': platform.platform(),
            'architecture': platform.architecture(),
            'processor': platform.processor(),
            'timestamp': datetime.now().isoformat()
        }
        
        # パッケージの存在確認
        try:
            import wtp.packet
            env_info['wtp_packet_available'] = True
            env_info['wtp_packet_path'] = wtp.packet.__file__
        except ImportError as e:
            env_info['wtp_packet_available'] = False
            env_info['wtp_packet_error'] = str(e)
        
        # pytest の存在確認
        try:
            import pytest
            env_info['pytest_available'] = True
            env_info['pytest_version'] = pytest.__version__
        except ImportError:
            env_info['pytest_available'] = False
        
        return env_info
    
    @staticmethod
    def create_mock_packet_data(packet_type: str = 'basic') -> Dict[str, Any]:
        """
        モックパケットデータを作成
        
        Args:
            packet_type: パケットタイプ ('basic', 'extended', 'response')
            
        Returns:
            モックデータ辞書
        """
        base_data = {
            'version': 1,
            'packet_id': 100,
            'type': 1,
            'weather_flag': 1,
            'temperature_flag': 0,
            'pops_flag': 0,
            'alert_flag': 0,
            'disaster_flag': 0,
            'ex_flag': 0,
            'day': 1,
            'reserved': 0,
            'timestamp': int(datetime.now().timestamp()),
            'area_code': 12345,
            'checksum': 0
        }
        
        if packet_type == 'extended':
            base_data['ex_flag'] = 1
            base_data['ex_field'] = {
                'alert': ['テスト警報'],
                'latitude': 35.6895,
                'longitude': 139.6917
            }
        elif packet_type == 'response':
            base_data.update({
                'weather_code': 1000,
                'temperature': 125,
                'pops': 30
            })
        
        return base_data
    
    @staticmethod
    def debug_packet_bits(packet: Any, show_fields: bool = True) -> str:
        """
        パケットのビット構造をデバッグ表示用に整形
        
        Args:
            packet: デバッグ対象のパケット
            show_fields: フィールド情報も表示するか
            
        Returns:
            デバッグ情報文字列
        """
        debug_info = []
        
        if show_fields:
            debug_info.append("フィールド情報:")
            packet_dict = packet.as_dict()
            for field, value in packet_dict.items():
                debug_info.append(f"  {field}: {value}")
            debug_info.append("")
        
        # ビット列情報
        bitstr = packet.to_bits()
        debug_info.append(f"ビット列: {bitstr}")
        debug_info.append(f"16進: 0x{bitstr:x}")
        debug_info.append(f"ビット長: {bitstr.bit_length()}")
        
        # ビットパターン表示（最初の64ビット）
        bit_pattern = format(bitstr, f'0{min(bitstr.bit_length(), 64)}b')
        debug_info.append(f"ビットパターン: {bit_pattern}")
        
        # バイト列情報
        try:
            bytes_data = packet.to_bytes()
            debug_info.append(f"バイト列長: {len(bytes_data)}")
            debug_info.append(f"バイト列(hex): {bytes_data.hex()}")
        except Exception as e:
            debug_info.append(f"バイト列変換エラー: {e}")
        
        return "\n".join(debug_info)
