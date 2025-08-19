# C++ Unified Client CLI Implementation

## 概要
Python版 `client.py` に相当するC++のオールインワンCLIツール `unified_client_cli` を実装完了。

## 実装されたファイル

### 1. メインCLIツール
- **ファイル**: `cpp/tools/unified_client_cli.cpp`
- **機能**: 天気データ取得とレポート送信の両方に対応
- **特徴**: モード切り替えでパケットタイプを変更可能

### 2. ドキュメント
- **ファイル**: `cpp/docs/UNIFIED_CLIENT_CLI_USAGE.md`
- **内容**: 詳細な使用方法、実行例、オプション一覧

### 3. ビルド設定
- **CMakeLists.txt**: `unified_client_cli` ターゲット追加済み

## 使用方法

### ビルド
```bash
cd cpp/build
cmake ..
make unified_client_cli
```

### 実行モード

#### 1. Weather Mode（天気データ取得）
```bash
# エリアコードで取得
./unified_client_cli weather --area 130010 --debug

# 座標で取得
./unified_client_cli weather --coords 35.6762 139.6503 --temperature --precipitation

# プロキシ経由
./unified_client_cli weather --proxy --host 127.0.0.1 --port 4110 --area 130010

# 認証付き
./unified_client_cli weather --auth-enabled --auth-query "secret123" --area 130010
```

#### 2. Report Mode（センサーデータレポート）
```bash
# 基本レポート
./unified_client_cli report --area 130010 --weather-code 1 --temp 25.5 --precipitation-prob 30

# 警報・災害情報付き
./unified_client_cli report --area 130010 --weather-code 2 --alert "強風注意報" --disaster "地震情報"

# 認証付き
./unified_client_cli report --auth-enabled --auth-report "reportsecret" --area 130010 --weather-code 1
```

## 主要オプション

### 共通オプション
- `--host <HOST>`: サーバーホスト（デフォルト: 127.0.0.1）
- `--port <PORT>`: サーバーポート（weather: 4110, report: 4112）
- `--debug`: デバッグ出力を有効
- `--help, -h`: ヘルプ表示

### Weather Mode専用
- `--coords <LAT> <LON>`: 座標指定
- `--area <AREA_CODE>`: エリアコード（6桁）
- `--proxy`: プロキシサーバー経由
- `--weather`, `--temperature`, `--precipitation`: データ種別
- `--alerts`, `--disaster`: 警報・災害情報
- `--day <0-7>`: 日付オフセット

### Report Mode専用
- `--area <AREA_CODE>`: エリアコード（必須）
- `--weather-code <CODE>`: 天気コード（1-4）
- `--temp <CELSIUS>`: 気温
- `--precipitation-prob <0-100>`: 降水確率
- `--alert "<MESSAGE>"`: 警報メッセージ（複数指定可）
- `--disaster "<MESSAGE>"`: 災害メッセージ（複数指定可）

### 認証オプション
- `--auth-enabled` / `--no-auth-enabled`: 認証有効/無効
- `--auth-weather <PASS>`: 天気サービスパスフレーズ
- `--auth-location <PASS>`: 位置サービスパスフレーズ
- `--auth-query <PASS>`: クエリサービスパスフレーズ
- `--auth-report <PASS>`: レポートサービスパスフレーズ

## 技術的詳細

### アーキテクチャ
- **ClientMode enum**: Weather/Report モード切り替え
- **Args struct**: 全オプションを統一管理
- **関数分離**: `run_weather_mode()`, `run_report_mode()`
- **統合Client使用**: `wiplib::client::Client` クラスを活用

### Python版との互換性
| Python版 | C++版 unified_client_cli |
|---------|-------------------------|
| `python client.py --weather --area 130010` | `./unified_client_cli weather --area 130010` |
| `python client.py --report --area 130010` | `./unified_client_cli report --area 130010` |
| `python client.py --coords 35.6 139.7` | `./unified_client_cli weather --coords 35.6 139.7` |

### エラーハンドリング
- 接続エラー: "connection refused", "timeout"
- 認証エラー: "authentication failed"
- パラメータエラー: 必須パラメータチェック

## テスト結果

### 動作確認済み
- ✅ ヘルプ表示: `./unified_client_cli --help`
- ✅ 天気データ取得: `./unified_client_cli weather --area 130010 --debug`
- ✅ レポート送信: `./unified_client_cli report --area 130010 --weather-code 1 --temp 25.5`
- ✅ 認証オプション: パースとAuth設定確認済み
- ✅ エラーハンドリング: サーバー接続エラー時の適切なメッセージ

### パフォーマンス
- ビルド時間: 数秒
- 実行時間: 即座にレスポンス（サーバー接続時）
- メモリ使用量: 軽量

## Phase4.2 統合完了

この `unified_client_cli` により、Phase4.2「既存Client統合」が完全に達成されました：

1. ✅ **統一インターフェース**: 単一CLIで天気取得とレポート送信
2. ✅ **Python完全互換**: 同等のオプション体系とAPI
3. ✅ **柔軟なテスト**: オプション変更でパケットタイプ切り替え
4. ✅ **実用性**: 実際のテストとデバッグに使用可能

Python版 `client.py` と同様の利便性をC++で実現し、開発・テスト効率を大幅に向上させました。