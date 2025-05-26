# WTP Packet テストスイート

このディレクトリには、`wtp.packet` モジュールの包括的なテストスイートが含まれています。

## 📁 ディレクトリ構造

```
tests/
├── __init__.py                    # テストパッケージ初期化
├── conftest.py                    # pytest共通設定とフィクスチャ
├── test_runner.py                 # テスト実行スクリプト
├── run_tests.bat                  # Windows用実行バッチファイル
├── README.md                      # このファイル
├── utils/                         # テストユーティリティ
│   ├── __init__.py
│   ├── test_data_generator.py     # テストデータ生成
│   ├── assertions.py              # カスタムアサーション
│   └── helpers.py                 # ヘルパー関数
├── unit/                          # ユニットテスト
│   ├── __init__.py
│   ├── test_bit_utils.py          # ビット操作ユーティリティのテスト
│   ├── test_exceptions.py         # 例外クラスのテスト
│   ├── test_format_base.py        # 基底クラスのテスト
│   ├── test_extended_field_mixin.py # 拡張フィールド処理のテスト
│   ├── test_format_extended.py    # 拡張フォーマットのテスト
│   ├── test_format.py             # 汎用フォーマットのテスト
│   ├── test_request.py            # リクエストパケットのテスト
│   └── test_response.py           # レスポンスパケットのテスト
├── integration/                   # 統合テスト
│   ├── __init__.py
│   ├── test_data_integrity.py     # データ整合性テスト（最重要）
│   ├── test_conversions.py        # 相互変換テスト
│   └── test_real_scenarios.py     # 実用的なシナリオテスト
├── performance/                   # パフォーマンステスト
│   ├── __init__.py
│   ├── test_performance.py        # パフォーマンス測定
│   └── test_concurrency.py        # 並行処理テスト
├── robustness/                    # 堅牢性テスト
│   ├── __init__.py
│   ├── test_error_handling.py     # エラー処理テスト
│   ├── test_security.py           # セキュリティテスト
│   └── test_edge_cases.py         # エッジケーステスト
└── reports/                       # テストレポート出力先
    ├── coverage/                  # カバレッジレポート
    ├── performance/               # パフォーマンスレポート
    └── logs/                      # ログファイル
```

## 🚀 クイックスタート

### 1. 環境確認
```bash
# テスト環境の検証
python tests/test_runner.py --validate-env
```

### 2. クイックテスト実行
```bash
# 基本的なテストを実行（推奨）
python tests/test_runner.py --quick

# または Windows の場合
tests/run_tests.bat quick
```

### 3. 全テスト実行
```bash
# 全テストを実行
python tests/test_runner.py --all

# カバレッジ付きで実行
python tests/test_runner.py --all --coverage
```

## 📋 テストカテゴリ

### 🔧 ユニットテスト
個別のクラスや関数の単体テストです。

```bash
python tests/test_runner.py --unit
```

**主要テスト項目:**
- ビット操作ユーティリティ関数
- 例外クラスの動作
- 各パケットクラスの基本機能
- フィールド値の検証
- プロパティの動作

### 🔗 統合テスト
複数のコンポーネントを組み合わせたテストです。**最も重要**なテストカテゴリです。

```bash
python tests/test_runner.py --integration
```

**主要テスト項目:**
- **データ整合性**: パケット ⇔ ビット列 ⇔ バイト列の往復変換
- **拡張フィールド処理**: 日本語テキスト、特殊文字、数値の正確な処理
- **チェックサム計算**: 自動計算と検証の正確性
- **境界値処理**: 最大値・最小値での動作確認

### ⚡ パフォーマンステスト
処理速度とメモリ使用量のテストです。

```bash
python tests/test_runner.py --performance
```

**主要テスト項目:**
- 大量データ処理の性能
- メモリ使用量の測定
- 並行処理での安全性
- ビット操作の効率

### 🛡️ 堅牢性テスト
エラー処理とセキュリティのテストです。

```bash
python tests/test_runner.py --robustness
```

**主要テスト項目:**
- 不正データの処理
- エラー回復機能
- メモリ制限での動作
- セキュリティ脆弱性の確認

## 🎯 重要なテスト

### データ整合性テスト（最重要）
`tests/integration/test_data_integrity.py` は最も重要なテストファイルです。

```bash
# データ整合性テストのみ実行
python tests/test_runner.py --file test_data_integrity
```

このテストは以下を検証します：
- パケット作成 → バイト列変換 → パケット復元の完全な往復変換
- 拡張フィールドの値が正確に保持されること
- 日本語テキストの正確な処理
- チェックサムの自動計算と検証

## 🛠️ 使用方法

### コマンドライン実行

```bash
# 基本的な使用方法
python tests/test_runner.py [オプション]

# 利用可能なオプション
--unit              # ユニットテストを実行
--integration       # 統合テストを実行
--performance       # パフォーマンステストを実行
--robustness        # 堅牢性テストを実行
--all               # 全テストを実行
--quick             # クイックテスト（slowマーカー除外）
--file PATTERN      # 特定のテストファイルを実行
--coverage          # カバレッジ測定を行う
--verbose, -v       # 詳細出力
--validate-env      # テスト環境の検証のみ
--report FILE       # レポート出力ファイル名
--help              # ヘルプ表示
```

### Windows バッチファイル

```cmd
# 簡単な実行方法（Windows）
tests\run_tests.bat [オプション]

# 利用可能なオプション
unit                # ユニットテスト
integration         # 統合テスト
all                 # 全テスト
quick               # クイックテスト
coverage            # カバレッジ付き全テスト
validate            # 環境検証
```

### pytest直接実行

```bash
# pytest を直接使用する場合
cd tests
python -m pytest unit/                    # ユニットテストのみ
python -m pytest integration/             # 統合テストのみ
python -m pytest -m "not slow"           # slowマーカー除外
python -m pytest --cov=wtp.packet        # カバレッジ付き
```

## 📊 レポートとカバレッジ

### テストレポート
テスト実行後、`tests/reports/` ディレクトリにレポートが生成されます：

- `test_report_YYYYMMDD_HHMMSS.txt`: テスト結果サマリー
- `junit.xml`: JUnit形式のテスト結果
- `coverage/html/index.html`: HTMLカバレッジレポート
- `coverage/coverage.xml`: XMLカバレッジレポート

### カバレッジ確認
```bash
# カバレッジ付きでテスト実行
python tests/test_runner.py --all --coverage

# HTMLレポートをブラウザで開く
start tests/reports/coverage/html/index.html  # Windows
open tests/reports/coverage/html/index.html   # macOS
```

## 🔍 テストの追加

### 新しいテストファイルの作成

1. 適切なカテゴリディレクトリに配置
2. `test_` で始まるファイル名を使用
3. 共通フィクスチャを活用（`conftest.py`）
4. カスタムアサーションを使用（`tests.utils.PacketAssertions`）

### テストデータの生成

```python
from tests.utils import TestDataGenerator

# ランダムなパケットデータ
data = TestDataGenerator.generate_random_packet_data()

# 境界値テストケース
cases = TestDataGenerator.generate_boundary_test_cases()

# 拡張フィールドデータ
ex_field = TestDataGenerator.generate_extended_field_data('complex')
```

### カスタムアサーション

```python
from tests.utils import PacketAssertions

# 往復変換の検証
restored = PacketAssertions.assert_roundtrip_conversion(packet)

# 拡張フィールドの整合性確認
PacketAssertions.assert_extended_field_integrity(packet, expected_data)

# チェックサムの検証
PacketAssertions.assert_checksum_valid(packet)
```

## 🐛 トラブルシューティング

### よくある問題

1. **ImportError: No module named 'wtp.packet'**
   ```bash
   # プロジェクトルートから実行してください
   cd /path/to/WTP
   python tests/test_runner.py --validate-env
   ```

2. **pytest not found**
   ```bash
   # pytest をインストール
   pip install pytest pytest-cov
   ```

3. **テストが失敗する**
   ```bash
   # 詳細な出力でテスト実行
   python tests/test_runner.py --unit --verbose
   ```

4. **カバレッジレポートが生成されない**
   ```bash
   # pytest-cov をインストール
   pip install pytest-cov
   ```

### デバッグ方法

```python
# テストヘルパーを使用したデバッグ
from tests.utils import TestHelpers

# パケットのビット構造をデバッグ表示
debug_info = TestHelpers.debug_packet_bits(packet)
print(debug_info)

# 実行時間の測定
result, time_taken = TestHelpers.measure_execution_time(lambda: packet.to_bytes())
```

## 📈 継続的改善

### テスト品質の向上
- 新機能追加時は対応するテストも追加
- カバレッジ率90%以上を目標
- 失敗したテストは必ず修正

### パフォーマンス監視
- 定期的にパフォーマンステストを実行
- 処理時間の劣化を監視
- メモリ使用量の増加をチェック

### レポート活用
- テスト結果を定期的にレビュー
- 失敗パターンの分析
- 改善点の特定と対応

## 📞 サポート

テストに関する質問や問題がある場合は、以下を確認してください：

1. このREADMEファイル
2. `python tests/test_runner.py --help`
3. 各テストファイルのドキュメント文字列
4. `tests/conftest.py` の共通フィクスチャ

---

**重要**: データの整合性が最も重要です。新しい機能を追加する際は、必ず統合テスト（特に `test_data_integrity.py`）を実行して、往復変換が正しく動作することを確認してください。
