# サーバー命名規則統一仕様書

## 概要
WIP_Server/servers ディレクトリ内の各サーバープロセスで統一された命名規則を適用し、各サーバー間の処理の類似性を把握しやすくするための仕様書です。

## 統一された命名規則

### 1. メソッド命名パターン

#### 初期化・設定系
- `_setup_{機能名}()` - 初期化処理（データベース、キャッシュ、ログファイルなど）
- `_init_{機能名}()` - 廃止予定（`_setup_`に統一）

#### データ処理系
- `_get_{データ名}()` - データ取得処理
- `_extract_{データ名}()` - データ抽出処理
- `_validate_{データ名}()` - データ検証処理
- `_process_{データ名}()` - データ処理・変換処理
- `_create_{オブジェクト名}()` - オブジェクト作成処理

#### リクエスト・レスポンス処理系
- `_handle_{パケット型}_request()` - リクエスト処理
- `_handle_{パケット型}_response()` - レスポンス処理
- `_debug_print_{request|response}()` - デバッグ出力

#### スケジューラ・ユーティリティ系
- `_setup_scheduler()` - スケジューラ設定
- `_update_{リソース名}_scheduled()` - スケジュール実行処理
- `_cleanup()` - クリーンアップ処理

### 2. ログ出力形式の統一

#### 基本形式
```
[{self.server_name}] メッセージ内容
```

#### エラーメッセージ形式
```
{エラーコード}: [{self.server_name}] エラー内容
```

#### デバッグ出力見出し形式
```
[{self.server_name}] === 見出し ===
```

### 3. サーバー名統一
各サーバーの `self.server_name` を以下に統一：
- `LocationServer` - 位置解決サーバー
- `QueryServer` - 気象データサーバー
- `WeatherServer (Enhanced)` - 天気プロキシサーバー
- `ReportServer` - レポートサーバー

## 各サーバーの共通処理と類似性

### 1. 基底クラス継承パターン
全サーバーが `BaseServer` を継承し、以下の共通メソッドを実装：

#### 必須実装メソッド
- `parse_request(data)` - リクエストパース
- `create_response(request)` - レスポンス作成
- `validate_request(request)` - リクエスト検証

#### オプション実装メソッド
- `_debug_print_request(data, parsed)` - リクエストデバッグ出力
- `_debug_print_response(response, request)` - レスポンスデバッグ出力
- `_cleanup()` - クリーンアップ処理

### 2. 初期化処理の類似性

#### 設定ファイル読み込み
```python
config_path = Path(__file__).parent / 'config.ini'
self.config = ConfigLoader(config_path)
```

#### サーバー設定取得パターン
```python
if host is None:
    host = self.config.get('server', 'host', 'デフォルト値')
if port is None:
    port = self.config.getint('server', 'port', デフォルト値)
```

#### デバッグ設定パターン
```python
if debug is None:
    debug_str = self.config.get('server', 'debug', 'false')
    debug = debug_str.lower() == 'true'
```

### 3. データ処理パターンの類似性

#### データ抽出処理
- **LocationServer**: `_extract_sensor_data()` - 座標データ抽出
- **QueryServer**: 気象データ取得・処理
- **ReportServer**: `_extract_sensor_data()` - センサーデータ抽出

#### データ検証処理
- **LocationServer**: `validate_request()` - 座標検証
- **QueryServer**: `validate_request()` - エリアコード・フラグ検証
- **ReportServer**: `_validate_sensor_data()` - センサーデータ検証

#### キャッシュ処理
- **LocationServer**: `_setup_cache()` - 地域コードキャッシュ
- **WeatherServer**: 天気データ・エリアキャッシュ

### 4. エラーハンドリングパターンの類似性

#### ErrorResponse作成パターン
```python
error_response = ErrorResponse(
    version=self.version,
    packet_id=request.packet_id,
    error_code=エラーコード,
    timestamp=int(datetime.now().timestamp())
)
```

#### 送信元情報の取得・設定パターン
```python
if hasattr(request, 'ex_field') and request.ex_field:
    source = request.ex_field.source
    if isinstance(source, tuple) and len(source) == 2:
        error_response.ex_field.source = source
```

### 5. ログ・統計処理の類似性

#### 統計カウンタ更新
```python
with self.lock:
    self.request_count += 1
    self.error_count += 1  # エラー時
```

#### パフォーマンス測定
```python
start_time = time.time()
result, elapsed_time = self._measure_time(function, *args)
timing_info[process_name] = elapsed_time
```

## 今後の開発指針

### 1. 新規メソッド追加時
- 命名規則に従った名前を使用
- 類似処理は既存パターンを参考に実装
- ログ出力は統一形式を使用

### 2. 共通化推進
- 類似処理は基底クラスまたは共通ユーティリティに移動検討
- 設定管理の共通化
- エラーハンドリングのさらなる統一

### 3. ドキュメント更新
- 新機能追加時はこのドキュメントを更新
- 処理フローの図式化検討

## 変更履歴

### 2025/7/4
- 初版作成
- 全サーバーの命名規則統一完了
- 共通処理パターンの分析・文書化完了