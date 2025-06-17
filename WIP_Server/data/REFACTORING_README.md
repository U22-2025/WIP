# データ処理モジュール リファクタリング

## 概要

`get_alert.py`と`get_disaster.py`のコードが散在していたため、保守性と再利用性を向上させるためにリファクタリングを実施しました。

## リファクタリング前の問題点

1. **コードの重複**: XMLデータ取得、解析、JSON出力などの共通機能が重複していた
2. **責任の分散**: 単一のファイルに複数の責任が混在していた
3. **保守性の低下**: コードが散在し、修正時の影響範囲が不明確だった
4. **再利用性の欠如**: 共通機能を他のモジュールで再利用できなかった

## リファクタリング後の構造

### 1. 基底クラス: `xml_base.py`

**役割**: 気象庁XMLデータ処理の共通機能を提供

**主な機能**:
- XMLデータの取得 (`fetch_xml`)
- XML解析 (`parse_xml`)
- 共通名前空間の定義
- 報告時刻の取得 (`get_report_time`)
- JSONファイル保存 (`save_json`)
- Atomフィードからのエントリ取得 (`get_feed_entry_urls`)

**設計パターン**: Abstract Base Class (ABC)を使用し、継承先で具体的な処理を実装

### 2. 警報・注意報処理: `alert_processor.py`

**役割**: 警報・注意報XMLデータの専門処理

**主なクラス**:
- `AlertProcessor`: 警報・注意報情報の取得・統合処理

**主な機能**:
- 警報・注意報種別の抽出
- エリアコード別の情報整理
- 複数XMLファイルの統合処理
- JSON形式での出力

### 3. 災害情報処理: `disaster_processor.py`

**役割**: 災害情報XMLデータの専門処理

**主なクラス**:
- `DisasterXMLProcessor`: XML解析・抽出専門クラス
- `TimeProcessor`: 時間情報処理専門クラス
- `AreaCodeValidator`: エリアコード検証・変換クラス
- `VolcanoCoordinateProcessor`: 火山座標処理クラス
- `DisasterDataProcessor`: 統合制御クラス

**主な機能**:
- 災害種別とエリアコードの抽出
- 火山座標データの処理
- 時間範囲の統合
- エリアコードの検証・変換
- LocationClientとの連携

### 4. 更新されたエントリーポイント

#### `get_alert.py`
- リファクタリング前: 全ての処理ロジックを含む単一ファイル
- リファクタリング後: `AlertProcessor`を使用するシンプルなエントリーポイント

#### `get_disaster.py`
- リファクタリング前: 複数のクラスが混在する大きなファイル
- リファクタリング後: `DisasterDataProcessor`を使用するシンプルなエントリーポイント

## 設計原則

### 1. 単一責任原則 (Single Responsibility Principle)
各クラスは単一の責任を持つように設計されています。

### 2. 開放閉鎖原則 (Open/Closed Principle)
基底クラス`XMLBaseProcessor`を継承することで、新しい処理タイプを追加できます。

### 3. 依存関係逆転原則 (Dependency Inversion Principle)
抽象クラスに依存し、具象クラスの詳細に依存しない設計です。

### 4. DRY原則 (Don't Repeat Yourself)
共通機能を基底クラスに集約し、コードの重複を排除しました。

## 利用方法

### 警報・注意報情報の取得
```python
from alert_processor import AlertProcessor

processor = AlertProcessor()
result = processor.process_all_alerts('output.json')
```

### 災害情報の取得
```python
from disaster_processor import DisasterDataProcessor

processor = DisasterDataProcessor()
# 詳細な処理フローは get_disaster.py を参照
```

### 新しい処理タイプの追加
```python
from xml_base import XMLBaseProcessor

class NewProcessor(XMLBaseProcessor):
    def process_xml_data(self, xml_data: str) -> Dict[str, Any]:
        # 具体的な処理を実装
        pass
    
    def process_multiple_urls(self, url_list: List[str]) -> Dict[str, Any]:
        # 複数URL処理を実装
        pass
```

## ファイル構成

```
WTP_Server/data/
├── xml_base.py              # 基底クラス
├── alert_processor.py       # 警報・注意報処理
├── disaster_processor.py    # 災害情報処理
├── get_alert.py            # 警報・注意報エントリーポイント
├── get_disaster.py         # 災害情報エントリーポイント
└── REFACTORING_README.md   # このファイル
```

## 改善効果

1. **保守性の向上**: 責任が明確に分離され、修正箇所が特定しやすくなった
2. **再利用性の向上**: 共通機能を他のモジュールで再利用可能
3. **テスタビリティの向上**: 各クラスが独立してテスト可能
4. **拡張性の向上**: 新しい処理タイプを容易に追加可能
5. **可読性の向上**: コードの構造が明確になり、理解しやすくなった

## 今後の拡張

- 新しい気象データタイプの処理クラス追加
- エラーハンドリングの強化
- ログ機能の追加
- 非同期処理の対応
- キャッシュ機能の追加
