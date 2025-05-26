"""
テスト実行スクリプト

WTP Packet テストスイートの統合実行スクリプトです。
カテゴリ別のテスト実行、レポート生成、カバレッジ測定などを提供します。
"""

import sys
import os
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.utils import TestHelpers


class TestRunner:
    """テスト実行管理クラス"""
    
    def __init__(self):
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent
        self.reports_dir = self.test_dir / "reports"
        
        # レポートディレクトリを作成
        self.reports_dir.mkdir(exist_ok=True)
        (self.reports_dir / "coverage").mkdir(exist_ok=True)
        (self.reports_dir / "performance").mkdir(exist_ok=True)
        (self.reports_dir / "logs").mkdir(exist_ok=True)
    
    def run_tests(self, 
                  category: Optional[str] = None,
                  file_pattern: Optional[str] = None,
                  coverage: bool = False,
                  verbose: bool = False,
                  markers: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        テストを実行する
        
        Args:
            category: テストカテゴリ ('unit', 'integration', 'performance', 'robustness')
            file_pattern: 特定のテストファイルパターン
            coverage: カバレッジ測定を行うか
            verbose: 詳細出力するか
            markers: pytestマーカーのフィルタ
            
        Returns:
            実行結果の辞書
        """
        cmd = ["python", "-m", "pytest"]
        
        # テストディレクトリの指定
        if category:
            test_path = self.test_dir / category
            if not test_path.exists():
                raise ValueError(f"テストカテゴリ '{category}' が存在しません")
            cmd.append(str(test_path))
        elif file_pattern:
            cmd.extend(["-k", file_pattern])
        else:
            cmd.append(str(self.test_dir))
        
        # オプションの追加
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        # マーカーフィルタ
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])
        
        # カバレッジ測定
        if coverage:
            cmd.extend([
                "--cov=wtp.packet",
                "--cov-report=html:" + str(self.reports_dir / "coverage" / "html"),
                "--cov-report=xml:" + str(self.reports_dir / "coverage" / "coverage.xml"),
                "--cov-report=term"
            ])
        
        # JUnit XML レポート
        cmd.extend([
            "--junit-xml=" + str(self.reports_dir / "junit.xml")
        ])
        
        # 実行時間測定
        start_time = time.time()
        
        try:
            print(f"実行コマンド: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
            execution_time = time.time() - start_time
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'execution_time': execution_time,
                'command': ' '.join(cmd)
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'execution_time': execution_time,
                'command': ' '.join(cmd),
                'exception': e
            }
    
    def run_unit_tests(self, coverage: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """ユニットテストを実行"""
        print("=" * 60)
        print("ユニットテスト実行中...")
        print("=" * 60)
        
        return self.run_tests(
            category="unit",
            coverage=coverage,
            verbose=verbose
        )
    
    def run_integration_tests(self, coverage: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """統合テストを実行"""
        print("=" * 60)
        print("統合テスト実行中...")
        print("=" * 60)
        
        return self.run_tests(
            category="integration",
            coverage=coverage,
            verbose=verbose,
            markers=["integration"]
        )
    
    def run_performance_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """パフォーマンステストを実行"""
        print("=" * 60)
        print("パフォーマンステスト実行中...")
        print("=" * 60)
        
        return self.run_tests(
            category="performance",
            verbose=verbose,
            markers=["performance"]
        )
    
    def run_robustness_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """堅牢性テストを実行"""
        print("=" * 60)
        print("堅牢性テスト実行中...")
        print("=" * 60)
        
        return self.run_tests(
            category="robustness",
            verbose=verbose,
            markers=["robustness"]
        )
    
    def run_all_tests(self, coverage: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """全テストを実行"""
        print("=" * 60)
        print("全テスト実行中...")
        print("=" * 60)
        
        return self.run_tests(
            coverage=coverage,
            verbose=verbose
        )
    
    def run_quick_tests(self, verbose: bool = False) -> Dict[str, Any]:
        """クイックテスト（slowマーカーを除外）を実行"""
        print("=" * 60)
        print("クイックテスト実行中...")
        print("=" * 60)
        
        return self.run_tests(
            verbose=verbose,
            markers=["not slow"]
        )
    
    def validate_environment(self) -> Dict[str, Any]:
        """テスト環境の検証"""
        print("テスト環境を検証中...")
        
        env_info = TestHelpers.validate_test_environment()
        
        print(f"Python バージョン: {env_info['python_version'].split()[0]}")
        print(f"プラットフォーム: {env_info['platform']}")
        
        if env_info['wtp_packet_available']:
            print("✓ wtp.packet モジュールが利用可能")
        else:
            print(f"✗ wtp.packet モジュールが利用できません: {env_info.get('wtp_packet_error', '')}")
        
        if env_info['pytest_available']:
            print(f"✓ pytest が利用可能 (バージョン: {env_info['pytest_version']})")
        else:
            print("✗ pytest が利用できません")
        
        return env_info
    
    def generate_report(self, results: List[Dict[str, Any]], output_file: Optional[str] = None) -> str:
        """テスト結果のレポートを生成"""
        if not output_file:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_file = str(self.reports_dir / f"test_report_{timestamp}.txt")
        
        # 結果を TestHelpers 用の形式に変換
        test_results = []
        for result in results:
            test_results.append({
                'name': result.get('command', 'Unknown'),
                'status': 'passed' if result.get('success', False) else 'failed',
                'execution_time': result.get('execution_time', 0),
                'error': result.get('stderr', '') if not result.get('success', False) else None
            })
        
        report = TestHelpers.generate_test_report(test_results, output_file)
        print(f"レポートを生成しました: {output_file}")
        
        return report
    
    def print_result_summary(self, result: Dict[str, Any], test_name: str):
        """テスト結果のサマリーを表示"""
        print(f"\n{test_name} 結果:")
        print("-" * 40)
        
        if result['success']:
            print("✓ 成功")
        else:
            print("✗ 失敗")
            print(f"終了コード: {result['returncode']}")
        
        print(f"実行時間: {result['execution_time']:.2f}秒")
        
        if result['stdout']:
            print("\n標準出力:")
            print(result['stdout'])
        
        if result['stderr']:
            print("\n標準エラー:")
            print(result['stderr'])


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="WTP Packet テストスイート実行スクリプト")
    
    # テストカテゴリの選択
    parser.add_argument("--unit", action="store_true", help="ユニットテストを実行")
    parser.add_argument("--integration", action="store_true", help="統合テストを実行")
    parser.add_argument("--performance", action="store_true", help="パフォーマンステストを実行")
    parser.add_argument("--robustness", action="store_true", help="堅牢性テストを実行")
    parser.add_argument("--all", action="store_true", help="全テストを実行")
    parser.add_argument("--quick", action="store_true", help="クイックテスト（slowマーカー除外）を実行")
    
    # 特定ファイル指定
    parser.add_argument("--file", type=str, help="特定のテストファイルを実行")
    
    # オプション
    parser.add_argument("--coverage", action="store_true", help="カバレッジ測定を行う")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細出力")
    parser.add_argument("--validate-env", action="store_true", help="テスト環境の検証のみ実行")
    parser.add_argument("--report", type=str, help="レポート出力ファイル名")
    
    args = parser.parse_args()
    
    runner = TestRunner()
    results = []
    
    # 環境検証
    if args.validate_env:
        runner.validate_environment()
        return
    
    # 環境検証（常に実行）
    env_info = runner.validate_environment()
    if not env_info['wtp_packet_available']:
        print("エラー: wtp.packet モジュールが利用できません。テストを中止します。")
        sys.exit(1)
    
    print()  # 空行
    
    try:
        # テスト実行
        if args.unit:
            result = runner.run_unit_tests(coverage=args.coverage, verbose=args.verbose)
            runner.print_result_summary(result, "ユニットテスト")
            results.append(result)
        
        elif args.integration:
            result = runner.run_integration_tests(coverage=args.coverage, verbose=args.verbose)
            runner.print_result_summary(result, "統合テスト")
            results.append(result)
        
        elif args.performance:
            result = runner.run_performance_tests(verbose=args.verbose)
            runner.print_result_summary(result, "パフォーマンステスト")
            results.append(result)
        
        elif args.robustness:
            result = runner.run_robustness_tests(verbose=args.verbose)
            runner.print_result_summary(result, "堅牢性テスト")
            results.append(result)
        
        elif args.all:
            result = runner.run_all_tests(coverage=args.coverage, verbose=args.verbose)
            runner.print_result_summary(result, "全テスト")
            results.append(result)
        
        elif args.quick:
            result = runner.run_quick_tests(verbose=args.verbose)
            runner.print_result_summary(result, "クイックテスト")
            results.append(result)
        
        elif args.file:
            result = runner.run_tests(file_pattern=args.file, coverage=args.coverage, verbose=args.verbose)
            runner.print_result_summary(result, f"ファイル指定テスト ({args.file})")
            results.append(result)
        
        else:
            # デフォルト: クイックテストを実行
            print("テストカテゴリが指定されていません。クイックテストを実行します。")
            print("使用方法: python test_runner.py --help")
            print()
            
            result = runner.run_quick_tests(verbose=args.verbose)
            runner.print_result_summary(result, "クイックテスト")
            results.append(result)
        
        # レポート生成
        if results:
            runner.generate_report(results, args.report)
        
        # 終了コードの決定
        failed_tests = [r for r in results if not r['success']]
        if failed_tests:
            print(f"\n{len(failed_tests)} 個のテストカテゴリで失敗がありました。")
            sys.exit(1)
        else:
            print("\n全てのテストが成功しました！")
            sys.exit(0)
    
    except KeyboardInterrupt:
        print("\nテスト実行が中断されました。")
        sys.exit(130)
    
    except Exception as e:
        print(f"\nテスト実行中にエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
