#!/usr/bin/env python3
"""
WTP拡張フィールド処理デバッグツール
wtpフォルダから実行可能な統合デバッグインターフェース
"""

import sys
import os
import argparse

# デバッグツールのパスを追加
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(current_dir)
debug_tools_path = os.path.join(project_root, 'debug_tools')

# wtpパッケージのパスを追加
sys.path.insert(0, project_root)

# デバッグツールのパスを追加
sys.path.append(debug_tools_path)
sys.path.append(os.path.join(debug_tools_path, 'core'))
sys.path.append(os.path.join(debug_tools_path, 'performance'))
sys.path.append(os.path.join(debug_tools_path, 'individual'))

def print_banner():
    """バナーを表示"""
    print("=" * 60)
    print("WTP拡張フィールド処理デバッグツール")
    print("=" * 60)
    print()

def show_help():
    """ヘルプメッセージを表示"""
    print_banner()
    print("使用方法:")
    print("  python debug.py [コマンド] [オプション]")
    print()
    print("利用可能なコマンド:")
    print("  quick       - クイック検証（基本的な動作確認）")
    print("  full        - フルテスト実行（推奨）")
    print("  comprehensive - 包括的解析（詳細なデバッグ）")
    print("  performance - パフォーマンステスト")
    print("  stress      - ストレステスト")
    print("  regression  - 回帰テスト")
    print("  field       - 個別フィールドテスト")
    print("  encoding    - エンコード処理の詳細デバッグ")
    print("  help        - このヘルプを表示")
    print()
    print("オプション:")
    print("  --no-performance    パフォーマンステストをスキップ")
    print("  --sizes N1 N2 ...   パフォーマンステストのサイズ指定")
    print("  --output FILE       出力ファイル名")
    print()
    print("使用例:")
    print("  python debug.py quick                    # クイック検証")
    print("  python debug.py full --no-performance    # パフォーマンステストなしでフルテスト")
    print("  python debug.py performance --sizes 100 500 1000  # カスタムサイズでパフォーマンステスト")
    print("  python debug.py field                    # 個別フィールドテスト")
    print()

def run_integrated_suite(mode, **kwargs):
    """統合デバッグスイートを実行"""
    try:
        from integrated_debug_suite import IntegratedDebugSuite
        
        print_banner()
        print(f"統合デバッグスイート実行中: {mode}モード")
        print()
        
        suite = IntegratedDebugSuite()
        
        if mode == "quick":
            suite.run_quick_validation()
        elif mode == "comprehensive":
            suite.run_comprehensive_analysis()
        elif mode == "performance":
            sizes = kwargs.get('sizes', [100, 500])
            suite.run_performance_analysis(sizes)
        elif mode == "stress":
            suite.run_stress_test()
        elif mode == "regression":
            suite.run_regression_test()
        elif mode == "full":
            include_performance = not kwargs.get('no_performance', False)
            sizes = kwargs.get('sizes', [100, 500])
            suite.run_full_suite(include_performance, sizes)
            
        # レポート生成（fullモード以外の場合）
        if mode != "full":
            reports_dir = os.path.join(project_root, 'debug_tools', 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            output_file = kwargs.get('output', os.path.join(reports_dir, f"{mode}_debug_report.json"))
            suite.generate_comprehensive_report(output_file)
            
    except ImportError as e:
        print(f"エラー: デバッグツールのインポートに失敗しました: {e}")
        print("debug_toolsフォルダが正しく配置されているか確認してください。")
        return False
    except Exception as e:
        print(f"エラー: {e}")
        return False
        
    return True

def run_performance_test(**kwargs):
    """パフォーマンステストを実行"""
    try:
        from performance_debug_tool import PerformanceDebugger
        
        print_banner()
        print("パフォーマンステスト実行中")
        print()
        
        debugger = PerformanceDebugger()
        sizes = kwargs.get('sizes', [100, 500, 1000])
        debugger.run_performance_tests(sizes)
        
    except ImportError as e:
        print(f"エラー: パフォーマンステストツールのインポートに失敗しました: {e}")
        return False
    except Exception as e:
        print(f"エラー: {e}")
        return False
        
    return True

def run_field_test():
    """個別フィールドテストを実行"""
    try:
        from debug_field_encoding import debug_field_constants, debug_single_field
        
        print_banner()
        print("個別フィールドテスト実行中")
        print()
        
        # 定数確認
        debug_field_constants()
        
        # 各フィールドを個別にテスト
        test_cases = [
            ('latitude', 35.6895, 1),
            ('longitude', 139.6917, 2),
            ('source_ip', '192.168.1.1', 3),
            ('alert', ['津波警報'], 4),
            ('disaster', ['土砂崩れ'], 5)
        ]
        
        for field_name, field_value, packet_id in test_cases:
            debug_single_field(field_name, field_value, packet_id)
            
    except ImportError as e:
        print(f"エラー: フィールドテストツールのインポートに失敗しました: {e}")
        return False
    except Exception as e:
        print(f"エラー: {e}")
        return False
        
    return True

def run_encoding_debug():
    """エンコード処理の詳細デバッグを実行"""
    try:
        from comprehensive_debug_tool import ExtendedFieldDebugger
        
        print_banner()
        print("エンコード処理詳細デバッグ実行中")
        print()
        
        debugger = ExtendedFieldDebugger()
        debugger.run_comprehensive_debug()
        
    except ImportError as e:
        print(f"エラー: エンコードデバッグツールのインポートに失敗しました: {e}")
        return False
    except Exception as e:
        print(f"エラー: {e}")
        return False
        
    return True

def main():
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="WTP拡張フィールド処理デバッグツール",
        add_help=False  # カスタムヘルプを使用
    )
    
    parser.add_argument('command', nargs='?', default='help',
                       choices=['quick', 'full', 'comprehensive', 'performance', 
                               'stress', 'regression', 'field', 'encoding', 'help'],
                       help='実行するコマンド')
    
    parser.add_argument('--no-performance', action='store_true',
                       help='パフォーマンステストをスキップ')
    
    parser.add_argument('--sizes', nargs='+', type=int, default=[100, 500],
                       help='パフォーマンステストのサイズ')
    
    parser.add_argument('--output', default=None,
                       help='出力ファイル名')
    
    parser.add_argument('--help', '-h', action='store_true',
                       help='ヘルプを表示')
    
    args = parser.parse_args()
    
    # ヘルプ表示
    if args.command == 'help' or args.help:
        show_help()
        return
    
    # 各コマンドの実行
    success = False
    
    if args.command in ['quick', 'full', 'comprehensive', 'stress', 'regression']:
        success = run_integrated_suite(
            args.command,
            no_performance=args.no_performance,
            sizes=args.sizes,
            output=args.output
        )
    elif args.command == 'performance':
        success = run_performance_test(sizes=args.sizes)
    elif args.command == 'field':
        success = run_field_test()
    elif args.command == 'encoding':
        success = run_encoding_debug()
    
    if success:
        print()
        print("=" * 60)
        print("デバッグ実行完了")
        print("=" * 60)
        print()
        print("生成されたレポートは debug_tools/reports/ フォルダを確認してください。")
    else:
        print()
        print("=" * 60)
        print("デバッグ実行失敗")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()
