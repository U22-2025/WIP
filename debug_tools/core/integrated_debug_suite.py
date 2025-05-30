#!/usr/bin/env python3
"""
拡張フィールド処理の統合デバッグスイート
全てのデバッグツールを統合し、包括的な検証を提供します
"""

import sys
import os
import argparse
import json
from typing import Dict, Any, List

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'wtp'))

# デバッグツールをインポート
import sys
import os
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'performance'))

from comprehensive_debug_tool import ExtendedFieldDebugger
from performance_debug_tool import PerformanceDebugger


class IntegratedDebugSuite:
    """統合デバッグスイートクラス"""
    
    def __init__(self):
        self.comprehensive_debugger = ExtendedFieldDebugger()
        self.performance_debugger = PerformanceDebugger()
        self.results = {}
        
    def log(self, message: str):
        """ログ出力"""
        print(f"[SUITE] {message}")
        
    def run_quick_validation(self):
        """クイック検証（基本的な動作確認）"""
        self.log("クイック検証開始")
        
        # 基本的なテストケース
        test_cases = [
            {"alert": ["津波警報"]},
            {"disaster": ["土砂崩れ"]},
            {"latitude": 35.6895},
            {"longitude": 139.6917},
            {"source_ip": "192.168.1.1"},
            {
                "alert": ["津波警報"],
                "latitude": 35.6895,
                "longitude": 139.6917,
                "source_ip": "192.168.1.1"
            }
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            self.log(f"テストケース {i+1}: {test_case}")
            success = self.comprehensive_debugger.debug_multiple_fields(test_case)
            results.append({
                "test_case": test_case,
                "success": success
            })
            
        self.results["quick_validation"] = {
            "test_cases": results,
            "success_count": sum(1 for r in results if r["success"]),
            "total_count": len(results)
        }
        
        success_rate = self.results["quick_validation"]["success_count"] / len(results) * 100
        self.log(f"クイック検証完了: {success_rate:.1f}% 成功")
        
    def run_comprehensive_analysis(self):
        """包括的解析（詳細なデバッグ）"""
        self.log("包括的解析開始")
        
        # 定数検証
        self.comprehensive_debugger.debug_field_constants()
        
        # 個別フィールドの詳細テスト
        detailed_results = []
        test_fields = [
            ("alert", ["津波警報"]),
            ("disaster", ["土砂崩れ"]),
            ("latitude", 35.6895),
            ("longitude", 139.6917),
            ("source_ip", "192.168.1.1")
        ]
        
        for field_name, field_value in test_fields:
            self.log(f"詳細テスト: {field_name}")
            
            # エンコードテスト
            data = self.comprehensive_debugger.debug_single_field_encoding(field_name, field_value)
            
            # デコードテスト
            if data:
                success = self.comprehensive_debugger.debug_single_field_decoding(data, field_name, field_value)
                detailed_results.append({
                    "field": field_name,
                    "value": field_value,
                    "success": success
                })
            else:
                detailed_results.append({
                    "field": field_name,
                    "value": field_value,
                    "success": False
                })
                
        # エッジケーステスト
        self.comprehensive_debugger.debug_edge_cases()
        
        self.results["comprehensive_analysis"] = {
            "detailed_results": detailed_results,
            "success_count": sum(1 for r in detailed_results if r["success"]),
            "total_count": len(detailed_results)
        }
        
        self.log("包括的解析完了")
        
    def run_performance_analysis(self, test_sizes: List[int] = [100, 500]):
        """パフォーマンス解析"""
        self.log("パフォーマンス解析開始")
        
        # パフォーマンステストを実行
        self.performance_debugger.run_performance_tests(test_sizes)
        
        # 結果を統合
        self.results["performance_analysis"] = {
            "test_results": self.performance_debugger.test_results,
            "summary": self.performance_debugger._generate_summary()
        }
        
        self.log("パフォーマンス解析完了")
        
    def run_stress_test(self):
        """ストレステスト（高負荷での安定性確認）"""
        self.log("ストレステスト開始")
        
        stress_results = []
        
        # 大量データテスト
        large_data_test = {
            "alert": ["非常に長い警報メッセージ" * 50],
            "disaster": ["長い災害情報" * 30],
            "latitude": 35.6895,
            "longitude": 139.6917,
            "source_ip": "192.168.1.1"
        }
        
        try:
            success = self.comprehensive_debugger.debug_multiple_fields(large_data_test)
            stress_results.append({
                "test_type": "large_data",
                "success": success,
                "error": None
            })
        except Exception as e:
            stress_results.append({
                "test_type": "large_data",
                "success": False,
                "error": str(e)
            })
            
        # 極値テスト
        extreme_values = [
            {"latitude": 90.0, "longitude": 180.0},
            {"latitude": -90.0, "longitude": -180.0},
            {"latitude": 0.0, "longitude": 0.0},
        ]
        
        for i, extreme_case in enumerate(extreme_values):
            try:
                success = self.comprehensive_debugger.debug_multiple_fields(extreme_case)
                stress_results.append({
                    "test_type": f"extreme_values_{i}",
                    "test_case": extreme_case,
                    "success": success,
                    "error": None
                })
            except Exception as e:
                stress_results.append({
                    "test_type": f"extreme_values_{i}",
                    "test_case": extreme_case,
                    "success": False,
                    "error": str(e)
                })
                
        self.results["stress_test"] = {
            "results": stress_results,
            "success_count": sum(1 for r in stress_results if r["success"]),
            "total_count": len(stress_results)
        }
        
        self.log("ストレステスト完了")
        
    def run_regression_test(self):
        """回帰テスト（既知の問題の再発確認）"""
        self.log("回帰テスト開始")
        
        # 修正前に問題があったケースをテスト
        regression_cases = [
            # 個別フィールドテスト
            {"latitude": 35.6895},
            {"longitude": 139.6917},
            {"source_ip": "192.168.1.1"},
            
            # 組み合わせテスト
            {"latitude": 35.6895, "longitude": 139.6917},
            {"alert": ["津波警報"], "source_ip": "192.168.1.1"},
            
            # 座標精度テスト
            {"latitude": 0.0, "longitude": 0.0},
            {"latitude": 90.0, "longitude": 180.0},
            {"latitude": -90.0, "longitude": -180.0},
        ]
        
        regression_results = []
        for i, test_case in enumerate(regression_cases):
            try:
                success = self.comprehensive_debugger.debug_multiple_fields(test_case)
                regression_results.append({
                    "case_id": i,
                    "test_case": test_case,
                    "success": success,
                    "error": None
                })
            except Exception as e:
                regression_results.append({
                    "case_id": i,
                    "test_case": test_case,
                    "success": False,
                    "error": str(e)
                })
                
        self.results["regression_test"] = {
            "results": regression_results,
            "success_count": sum(1 for r in regression_results if r["success"]),
            "total_count": len(regression_results)
        }
        
        success_rate = self.results["regression_test"]["success_count"] / len(regression_results) * 100
        self.log(f"回帰テスト完了: {success_rate:.1f}% 成功")
        
    def generate_comprehensive_report(self, output_file: str = None):
        """包括的レポートを生成"""
        self.log("包括的レポート生成開始")
        
        # 全体サマリーを計算
        overall_summary = {
            "total_tests": 0,
            "total_successes": 0,
            "success_rate": 0.0,
            "test_categories": {}
        }
        
        for category, result in self.results.items():
            if "success_count" in result and "total_count" in result:
                overall_summary["total_tests"] += result["total_count"]
                overall_summary["total_successes"] += result["success_count"]
                overall_summary["test_categories"][category] = {
                    "success_count": result["success_count"],
                    "total_count": result["total_count"],
                    "success_rate": result["success_count"] / result["total_count"] * 100 if result["total_count"] > 0 else 0
                }
                
        if overall_summary["total_tests"] > 0:
            overall_summary["success_rate"] = overall_summary["total_successes"] / overall_summary["total_tests"] * 100
            
        # 推奨事項を生成
        recommendations = self._generate_recommendations()
        
        # 最終レポート
        final_report = {
            "summary": overall_summary,
            "detailed_results": self.results,
            "recommendations": recommendations,
            "debug_logs": {
                "comprehensive": self.comprehensive_debugger.debug_log,
                "errors": self.comprehensive_debugger.error_log
            }
        }
        
        # デフォルトのファイル名を設定
        if output_file is None:
            # reportsフォルダに保存
            reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            output_file = os.path.join(reports_dir, "integrated_debug_report.json")
            
        # ファイルに保存
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)
            
        self.log(f"包括的レポートを生成しました: {output_file}")
        
        # サマリーを表示
        self._display_summary(overall_summary)
        
    def _generate_recommendations(self) -> List[str]:
        """推奨事項を生成"""
        recommendations = []
        
        # 成功率に基づく推奨事項
        for category, result in self.results.items():
            if "success_count" in result and "total_count" in result:
                success_rate = result["success_count"] / result["total_count"] * 100 if result["total_count"] > 0 else 0
                
                if success_rate < 100:
                    recommendations.append(f"{category}: 成功率{success_rate:.1f}% - 失敗ケースの詳細調査が必要")
                elif success_rate == 100:
                    recommendations.append(f"{category}: 成功率100% - 良好な状態")
                    
        # パフォーマンスに基づく推奨事項
        if "performance_analysis" in self.results:
            perf_data = self.results["performance_analysis"]
            if "summary" in perf_data and "encoding_performance" in perf_data["summary"]:
                avg_time = perf_data["summary"]["encoding_performance"].get("avg_time", 0)
                if avg_time > 0.001:  # 1ms以上
                    recommendations.append(f"パフォーマンス: エンコード平均時間{avg_time:.6f}秒 - 最適化を検討")
                    
        # エラーログに基づく推奨事項
        if self.comprehensive_debugger.error_log:
            recommendations.append(f"エラー: {len(self.comprehensive_debugger.error_log)}件のエラーが記録されています - 詳細調査が必要")
            
        if not recommendations:
            recommendations.append("全てのテストが正常に完了しました - 現在の実装は安定しています")
            
        return recommendations
        
    def _display_summary(self, summary: Dict[str, Any]):
        """サマリーを表示"""
        self.log("=" * 60)
        self.log("統合デバッグスイート実行結果")
        self.log("=" * 60)
        self.log(f"総テスト数: {summary['total_tests']}")
        self.log(f"成功数: {summary['total_successes']}")
        self.log(f"全体成功率: {summary['success_rate']:.1f}%")
        self.log("")
        
        self.log("カテゴリ別結果:")
        for category, result in summary["test_categories"].items():
            self.log(f"  {category}: {result['success_count']}/{result['total_count']} ({result['success_rate']:.1f}%)")
            
        self.log("=" * 60)
        
    def run_full_suite(self, include_performance: bool = True, performance_sizes: List[int] = [100, 500]):
        """フルスイートを実行"""
        self.log("統合デバッグスイート開始")
        
        # 1. クイック検証
        self.run_quick_validation()
        
        # 2. 包括的解析
        self.run_comprehensive_analysis()
        
        # 3. パフォーマンス解析（オプション）
        if include_performance:
            self.run_performance_analysis(performance_sizes)
            
        # 4. ストレステスト
        self.run_stress_test()
        
        # 5. 回帰テスト
        self.run_regression_test()
        
        # 6. レポート生成
        self.generate_comprehensive_report()
        
        self.log("統合デバッグスイート完了")


def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(description="拡張フィールド処理の統合デバッグスイート")
    parser.add_argument("--mode", choices=["quick", "comprehensive", "performance", "stress", "regression", "full"], 
                       default="full", help="実行モード")
    parser.add_argument("--no-performance", action="store_true", help="パフォーマンステストをスキップ")
    parser.add_argument("--performance-sizes", nargs="+", type=int, default=[100, 500], 
                       help="パフォーマンステストのサイズ")
    parser.add_argument("--output", default="integrated_debug_report.json", help="出力ファイル名")
    
    args = parser.parse_args()
    
    suite = IntegratedDebugSuite()
    
    if args.mode == "quick":
        suite.run_quick_validation()
    elif args.mode == "comprehensive":
        suite.run_comprehensive_analysis()
    elif args.mode == "performance":
        suite.run_performance_analysis(args.performance_sizes)
    elif args.mode == "stress":
        suite.run_stress_test()
    elif args.mode == "regression":
        suite.run_regression_test()
    elif args.mode == "full":
        suite.run_full_suite(
            include_performance=not args.no_performance,
            performance_sizes=args.performance_sizes
        )
        
    # レポート生成（fullモード以外の場合）
    if args.mode != "full":
        suite.generate_comprehensive_report(args.output)


if __name__ == "__main__":
    main()
