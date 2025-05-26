# 拡張フィールド処理デバッグツール集

拡張フィールド処理の問題を特定・解決するための網羅的なデバッグツール集です。

## 🛠️ ツール一覧

### 1. 統合デバッグスイート (`integrated_debug_suite.py`)
**推奨**: 最初に使用すべきメインツール

全てのデバッグ機能を統合した包括的なテストスイートです。

```bash
# フルテスト実行（推奨）
python integrated_debug_suite.py --mode full

# クイック検証のみ
python integrated_debug_suite.py --mode quick

# パフォーマンステストをスキップ
python integrated_debug_suite.py --mode full --no-performance

# 特定のテストサイズでパフォーマンステスト
python integrated_debug_suite.py --mode performance --performance-sizes 100 500 1000
```

**出力**: `integrated_debug_report.json` - 包括的な結果レポート

### 2. 網羅的デバッグツール (`comprehensive_debug_tool.py`)
詳細なエンコード・デコード処理の追跡

```bash
# 全ての詳細デバッグを実行
python comprehensive_debug_tool.py
```

**機能**:
- フィールド定数の検証
- 個別フィールドのエンコード・デコード詳細追跡
- 複数フィールド組み合わせテスト
- エッジケーステスト
- 詳細なビット操作ログ

**出力**: `comprehensive_debug_report.json`

### 3. パフォーマンステストツール (`performance_debug_tool.py`)
大量データでの性能・安定性検証

```bash
# パフォーマンステスト実行
python performance_debug_tool.py
```

**機能**:
- エンコード・デコード性能測定
- ラウンドトリップ性能測定
- メモリ使用量テスト
- 並行アクセステスト
- 統計分析（平均・中央値・標準偏差）

**出力**: `performance_debug_report.json`

### 4. 個別デバッグスクリプト
特定の問題を詳細に調査するためのスクリプト群

- `debug_field_encoding.py` - 基本的なフィールドエンコードテスト
- `debug_detailed_encoding.py` - エンコード処理の詳細追跡
- `debug_decode_process.py` - デコード処理のステップバイステップ追跡
- `debug_fetch_ex_field.py` - fetch_ex_fieldメソッドの詳細デバッグ
- `debug_encoding_step_by_step.py` - エンコード処理の手動再現

## 🚀 使用方法

### 基本的なワークフロー

1. **問題の初期確認**
   ```bash
   python integrated_debug_suite.py --mode quick
   ```

2. **詳細な問題分析**
   ```bash
   python integrated_debug_suite.py --mode comprehensive
   ```

3. **パフォーマンス問題の調査**
   ```bash
   python integrated_debug_suite.py --mode performance
   ```

4. **回帰テスト**
   ```bash
   python integrated_debug_suite.py --mode regression
   ```

### 問題別の推奨ツール

#### 🔍 エンコード・デコードが失敗する場合
```bash
# 1. 統合スイートで全体確認
python integrated_debug_suite.py --mode comprehensive

# 2. 詳細なビット操作を確認
python comprehensive_debug_tool.py

# 3. 特定フィールドの詳細調査
python debug_encoding_step_by_step.py
```

#### ⚡ パフォーマンス問題の場合
```bash
# 1. パフォーマンス測定
python performance_debug_tool.py

# 2. 統合スイートでストレステスト
python integrated_debug_suite.py --mode stress
```

#### 🐛 特定のフィールドで問題が発生する場合
```bash
# 個別フィールドの詳細デバッグ
python debug_field_encoding.py
python debug_decode_process.py
```

## 📊 レポートの読み方

### 統合デバッグレポート (`integrated_debug_report.json`)

```json
{
  "summary": {
    "total_tests": 25,
    "total_successes": 25,
    "success_rate": 100.0,
    "test_categories": {
      "quick_validation": {"success_count": 6, "total_count": 6, "success_rate": 100.0},
      "comprehensive_analysis": {"success_count": 5, "total_count": 5, "success_rate": 100.0},
      "stress_test": {"success_count": 4, "total_count": 4, "success_rate": 100.0},
      "regression_test": {"success_count": 8, "total_count": 8, "success_rate": 100.0}
    }
  },
  "recommendations": [
    "全てのテストが正常に完了しました - 現在の実装は安定しています"
  ]
}
```

### パフォーマンスレポート (`performance_debug_report.json`)

```json
{
  "summary": {
    "encoding_performance": {
      "avg_time": 0.000123,
      "min_time": 0.000089,
      "max_time": 0.000156
    },
    "decoding_performance": {
      "avg_time": 0.000098,
      "min_time": 0.000067,
      "max_time": 0.000134
    }
  }
}
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. "キーマッピングが見つかりません" エラー
```bash
# フィールド定数を確認
python -c "
from comprehensive_debug_tool import ExtendedFieldDebugger
debugger = ExtendedFieldDebugger()
debugger.debug_field_constants()
"
```

#### 2. "ビット数不足" エラー
```bash
# ビット長の詳細を確認
python debug_decode_process.py
```

#### 3. 座標値の精度問題
```bash
# 座標エンコード・デコードの詳細確認
python debug_encoding_step_by_step.py
```

#### 4. パフォーマンス劣化
```bash
# 詳細なパフォーマンス分析
python performance_debug_tool.py
```

### デバッグログの活用

各ツールは詳細なログを出力します：

- `[INFO]` - 一般的な情報
- `[ERROR]` - エラー情報
- `[PERF]` - パフォーマンス関連
- `[SUITE]` - 統合スイート関連

## 📈 継続的な品質管理

### 定期実行の推奨

```bash
# 毎日の回帰テスト
python integrated_debug_suite.py --mode regression

# 週次の包括的テスト
python integrated_debug_suite.py --mode full

# リリース前の完全テスト
python integrated_debug_suite.py --mode full --performance-sizes 100 500 1000 5000
```

### CI/CDでの活用

```yaml
# GitHub Actions例
- name: Extended Field Debug Tests
  run: |
    python integrated_debug_suite.py --mode regression
    python integrated_debug_suite.py --mode quick
```

## 🎯 カスタマイズ

### 新しいテストケースの追加

`integrated_debug_suite.py`の`run_regression_test()`メソッドに追加：

```python
regression_cases = [
    # 既存のケース...
    {"new_field": "test_value"},  # 新しいテストケース
]
```

### パフォーマンス閾値の調整

`performance_debug_tool.py`の閾値を調整：

```python
if avg_time > 0.001:  # 1ms → 任意の値に変更
    recommendations.append("パフォーマンス最適化が必要")
```

## 📝 ログ出力例

### 成功時のログ
```
[SUITE] 統合デバッグスイート開始
[SUITE] クイック検証開始
[INFO] === 複数フィールド組み合わせデバッグ ===
[INFO] テストデータ: {'alert': ['津波警報']}
[INFO] 作成されたex_field: {'alert': ['津波警報']}
[INFO] バイト列長: 36 bytes
[INFO] 復元されたex_field: {'alert': ['津波警報']}
[INFO] alert: ✅
[INFO] 全体結果: ✅ 成功
[SUITE] クイック検証完了: 100.0% 成功
```

### エラー時のログ
```
[ERROR] キーマッピングが見つかりません: unknown_field
[ERROR] ビット数不足: 必要48 > 利用可能42
[ERROR] 座標値が32ビット整数範囲を超えています: 2147483648
```

## 🤝 貢献

新しいデバッグ機能の追加や改善の提案は歓迎します。

1. 新しいテストケースの追加
2. パフォーマンス測定項目の追加
3. エラー検出ロジックの改善
4. レポート形式の改善

---

**注意**: これらのツールは開発・デバッグ用途です。本番環境での使用は推奨されません。
