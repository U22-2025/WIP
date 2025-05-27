# WTPプロジェクト重複コード整理計画

## 発見された重複コード

### 1. デバッグ関数の重複
以下の関数が複数のファイルで重複しています：

#### `_hex_dump` メソッド (8箇所で重複)
- `wtp/weather_server.py`
- `wtp/weather_server copy.py`
- `wtp/query_generator_client.py`
- `wtp/query_generator_modules/debug_helper.py`
- `wtp/location_resolver_client_test.py`
- `wtp/location_resolver_client.py`
- `wtp/location_resolver.py`
- `wtp/client.py`

#### `_debug_print_request` メソッド (7箇所で重複)
- `wtp/weather_server.py`
- `wtp/weather_server copy.py`
- `wtp/query_generator_client.py`
- `wtp/location_resolver_client_test.py`
- `wtp/location_resolver_client.py`
- `wtp/location_resolver.py`
- `wtp/client.py`

#### `_debug_print_response` メソッド (複数箇所で重複)
- 各クライアント・サーバークラスで類似の実装

### 2. クラスの完全重複
#### `LocationResolverClient` クラス
- `wtp/location_resolver_client.py` - 本体
- `wtp/location_resolver_client_test.py` - テスト用だが、ほぼ同じ実装

### 3. ファイルの重複
#### `weather_server.py` vs `weather_server copy.py`
- ほぼ同じ内容のファイルが2つ存在

## 整理計画

### Phase 1: 共通デバッグユーティリティの作成
1. `wtp/utils/debug_utils.py` を作成
2. 以下の共通関数を実装：
   - `hex_dump(data: bytes) -> str`
   - `debug_print_request(data, parsed_data, debug_flag)`
   - `debug_print_response(data, response_data, debug_flag)`

### Phase 2: 重複ファイルの削除
1. `weather_server copy.py` を削除
2. `location_resolver_client_test.py` から重複クラスを削除し、テスト関数のみ残す

### Phase 3: 各クラスのリファクタリング
1. 各クライアント・サーバークラスで共通デバッグユーティリティを使用
2. 重複メソッドを削除

### Phase 4: 共通ベースクラスの検討
1. クライアントクラス用の基底クラス `BaseClient` を作成
2. サーバークラス用の基底クラス `BaseServer` を作成

## 期待される効果

### コード削減
- 約200-300行の重複コードを削除
- メンテナンス性の向上

### 一貫性の向上
- デバッグ出力の統一
- エラーハンドリングの統一

### 拡張性の向上
- 新しいクライアント・サーバーの追加が容易
- 共通機能の追加・修正が一箇所で済む

## 実装優先度

1. **高**: 共通デバッグユーティリティの作成
2. **高**: 重複ファイルの削除
3. **中**: 各クラスのリファクタリング
4. **低**: 共通ベースクラスの作成（将来的な拡張として）

## 注意事項

- 既存の機能を壊さないよう、段階的にリファクタリングを実行
- 各段階でテストを実行して動作確認
- インポート文の調整が必要
