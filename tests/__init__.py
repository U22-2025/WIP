"""
WTP Packet テストスイート

このパッケージは wtp.packet モジュールの包括的なテストを提供します。

テスト構造:
- unit/: ユニットテスト
- integration/: 統合テスト  
- performance/: パフォーマンステスト
- robustness/: 堅牢性テスト
- utils/: テストユーティリティ
"""

import sys
import os

# テスト対象のパッケージをパスに追加
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(test_dir)
sys.path.insert(0, project_root)

__version__ = "1.0.0"
__author__ = "WTP Test Suite"
