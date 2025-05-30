# 拡張フィールド処理デバッグツール集

拡張フィールド処理の問題を特定・解決するための網羅的なデバッグツール集です。

## 📁 フォルダ構造

```
debug_tools/
├── README.md                    # このファイル
├── core/                        # コアデバッグツール
│   ├── integrated_debug_suite.py   # 統合デバッグスイート（メインツール）
│   └── comprehensive_debug_tool.py # 網羅的デバッグツール
├── performance/                 # パフォーマンステストツール
│   └── performance_debug_tool.py   # パフォーマンステストツール
├── individual/                  # 個別デバッグスクリプト
│   ├── debug_field_encoding.py     # 基本的なフィールドエンコードテスト
│   ├── debug_detailed_encoding.py  # エンコード処理の詳細追跡
│   ├── debug_decode_process.py     # デコード処理のステップバイステップ追跡
│   ├── debug_fetch_ex_field.py     # fetch_ex_fieldメソッドの詳細デバッグ
│   ├── debug_encoding_step_by_step.py # エンコード処理の手動再現
│   ├── debug_extended_field.py     # 拡張フィールド全般のデバッグ
│   ├── debug_multiple_fields.py    # 複数フィールドのデバッグ
│   └── test_extended_field_fix.py  # 修正テスト
├── docs/                        # ドキュメント
│   ├── DEBUG_TOOLS_README.md       # 詳細な使用方法
│   ├── extended_field_fix_summary.md # 修正内容のサマリー
│   └── extended_field_fix_report.md  # 修正レポート
└── reports/                     # 生成されるレポート（実行時に作成）
    ├── integrated_debug_report.json
    ├── comprehensive_debug_report.json
    └── performance_debug_report.json
```

## 🚀 クイックスタート

### 1. 基本的な動作確認
```bash
cd debug_tools/core
python integrated_debug_suite.py --mode quick
```

### 2. 詳細なデバッグ
```bash
cd debug_tools/core
python integrated_debug_suite.py --mode comprehensive
```

### 3. パフォーマンステスト
```bash
cd debug_tools/performance
python performance_debug_tool.py
```

### 4. 個別フィールドのデバッグ
```bash
cd debug_tools/individual
python debug_field_encoding.py
```

## 🛠️ ツール別説明

### コアツール (`core/`)

#### `integrated_debug_suite.py` - 統合デバッグスイート
**推奨**: 最初に使用すべきメインツール

```bash
# フルテスト実行
python integrated_debug_suite.py --mode full

# クイック検証のみ
python integrated_debug_suite.py --mode quick

# パフォーマンステストをスキップ
python integrated_debug_suite.py --mode full --no-performance

# 回帰テスト
python integrated_debug_suite.py --mode regression
```

#### `comprehensive_debug_tool.py` - 網羅的デバッグツール
詳細なエンコード・デコード処理の追跡

```bash
python comprehensive_debug_tool.py
```

### パフォーマンスツール (`performance/`)

#### `performance_debug_tool.py` - パフォーマンステストツール
大量データでの性能・安定性検証

```bash
python performance_debug_tool.py
```

### 個別デバッグスクリプト (`individual/`)

特定の問題を詳細に調査するためのスクリプト群

- `debug_field_encoding.py` - 基本的なフィールドエンコードテスト
- `debug_detailed_encoding.py` - エンコード処理の詳細追跡
- `debug_decode_process.py` - デコード処理のステップバイステップ追跡
- `debug_fetch_ex_field.py` - fetch_ex_fieldメソッドの詳細デバッグ
- `debug_encoding_step_by_step.py` - エンコード処理の手動再現
- `debug_extended_field.py` - 拡張フィールド全般のデバッグ
- `debug_multiple_fields.py` - 複数フィールドのデバッグ
- `test_extended_field_fix.py` - 修正テスト

## 📊 レポート出力

各ツールは以下の場所にレポートを生成します：

- `reports/integrated_debug_report.json` - 統合デバッグレポート
- `reports/comprehensive_debug_report.json` - 詳細デバッグレポート
- `reports/performance_debug_report.json` - パフォーマンスレポート

## 🔧 問題別の推奨ワークフロー

### エンコード・デコードが失敗する場合
1. `core/integrated_debug_suite.py --mode comprehensive`
2. `core/comprehensive_debug_tool.py`
3. `individual/debug_encoding_step_by_step.py`

### パフォーマンス問題の場合
1. `performance/performance_debug_tool.py`
2. `core/integrated_debug_suite.py --mode stress`

### 特定のフィールドで問題が発生する場合
1. `individual/debug_field_encoding.py`
2. `individual/debug_decode_process.py`

## 📝 ログレベル

- `[INFO]` - 一般的な情報
- `[ERROR]` - エラー情報
- `[PERF]` - パフォーマンス関連
- `[SUITE]` - 統合スイート関連

## 🎯 カスタマイズ

新しいテストケースの追加や設定変更については、`docs/DEBUG_TOOLS_README.md` を参照してください。

## ⚠️ 注意事項

- これらのツールは開発・デバッグ用途です
- 本番環境での使用は推奨されません
- 大量データのテスト時はシステムリソースに注意してください

---

詳細な使用方法は `docs/DEBUG_TOOLS_README.md` を参照してください。
