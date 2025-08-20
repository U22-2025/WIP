# Unified Client CLI 使用方法

`unified_client_cli` は、Python版 `client.py` に相当するC++のオールインワンCLIツールです。
1つのファイルでオプションを変更するだけで、天気データ取得とセンサーデータレポート送信の両方を実行できます。

## ビルド方法

```bash
cd cpp/build
cmake ..
make unified_client_cli
```

## 基本的な使用方法

### コマンド形式
```bash
./unified_client_cli [mode] [common_options] [mode_specific_options]
```

## モード

### 1. weather モード（デフォルト）
天気データ取得を行います。Python版 `client.py` の天気取得機能に相当します。

### 2. report モード  
センサーデータのレポート送信を行います。Python版 `report_client.py` の機能に相当します。

## 実行例

### 天気データ取得

#### 1. 座標による天気データ取得
```bash
# 東京の座標で天気データを取得
./unified_client_cli weather --coords 35.6762 139.6503 --temperature --precipitation

# デバッグ情報付きで実行
./unified_client_cli weather --coords 35.6762 139.6503 --debug
```

#### 2. エリアコードによる天気データ取得
```bash
# 東京（130010）の天気データを取得
./unified_client_cli weather --area 130010 --weather --temperature

# プロキシサーバー経由で取得
./unified_client_cli weather --proxy --host 127.0.0.1 --port 4110 --area 130010
```

#### 3. 詳細な天気情報取得
```bash
# 警報・災害情報も含めて取得
./unified_client_cli weather --area 130010 --weather --temperature --precipitation --alerts --disaster

# 明日の天気を取得
./unified_client_cli weather --area 130010 --day 1 --temperature
```

### センサーデータレポート送信

#### 1. 基本的なレポート送信
```bash
# 基本的なセンサーデータをレポート
./unified_client_cli report --area 130010 --weather-code 1 --temp 25.5 --precipitation-prob 30

# レポートサーバーのポートを指定
./unified_client_cli report --host 127.0.0.1 --port 4112 --area 130010 --weather-code 2
```

#### 2. 警報・災害情報付きレポート
```bash
# 警報情報付きでレポート
./unified_client_cli report --area 130010 --weather-code 2 --alert "強風注意報" --alert "大雨警報"

# 災害情報付きでレポート  
./unified_client_cli report --area 130010 --disaster "地震情報" --disaster "台風情報"

# 警報と災害情報の両方を含むレポート
./unified_client_cli report --area 130010 --weather-code 3 --temp 18.0 \
    --alert "雷注意報" --disaster "地震速報" --debug
```

### 認証付きでの実行

#### 1. 天気データ取得（認証あり）
```bash
# クエリサービス認証を使用
./unified_client_cli weather --auth-enabled --auth-query "secret123" --area 130010

# 複数サービスの認証を設定
./unified_client_cli weather --auth-enabled --auth-location "locsecret" --auth-query "querysecret" \
    --coords 35.6762 139.6503
```

#### 2. レポート送信（認証あり）
```bash
# レポートサービス認証を使用
./unified_client_cli report --auth-enabled --auth-report "reportsecret" \
    --area 130010 --weather-code 1 --temp 25.0

# 環境変数の認証設定を無効化
./unified_client_cli report --no-auth-enabled --area 130010 --weather-code 2
```

## 共通オプション

| オプション | 説明 | デフォルト |
|-----------|------|----------|
| `--host <HOST>` | サーバーホスト | 127.0.0.1 |
| `--port <PORT>` | サーバーポート | weather: 4110, report: 4112 |
| `--debug` | デバッグ出力を有効 | false |
| `--help, -h` | ヘルプを表示 | - |

## 天気モード専用オプション

| オプション | 説明 | デフォルト |
|-----------|------|----------|
| `--coords <LAT> <LON>` | 緯度・経度で指定 | - |
| `--area <AREA_CODE>` | エリアコード（6桁）で指定 | - |
| `--proxy` | プロキシサーバー経由 | false |
| `--weather` / `--no-weather` | 天気データ | true |
| `--temperature` / `--no-temperature` | 気温データ | true |
| `--precipitation` / `--no-precipitation` | 降水確率 | true |
| `--alerts` | 警報情報 | false |
| `--disaster` | 災害情報 | false |
| `--day <0-7>` | 日付オフセット | 0 |

## レポートモード専用オプション

| オプション | 説明 | 必須 |
|-----------|------|------|
| `--area <AREA_CODE>` | エリアコード（6桁） | ✓ |
| `--weather-code <CODE>` | 天気コード（1-4） | - |
| `--temp <CELSIUS>` | 気温（摂氏） | - |
| `--precipitation-prob <0-100>` | 降水確率（%） | - |
| `--alert "<MESSAGE>"` | 警報メッセージ（複数回指定可） | - |
| `--disaster "<MESSAGE>"` | 災害メッセージ（複数回指定可） | - |

## 認証オプション

| オプション | 説明 |
|-----------|------|
| `--auth-enabled` / `--no-auth-enabled` | 認証の有効/無効 |
| `--auth-weather <PASS>` | 天気サービスパスフレーズ |
| `--auth-location <PASS>` | 位置サービスパスフレーズ |
| `--auth-query <PASS>` | クエリサービスパスフレーズ |
| `--auth-report <PASS>` | レポートサービスパスフレーズ |

## エラーと対処法

### 1. 接続エラー
```
Weather query failed: connection refused
Report sending failed: timeout
```
**対処法**: サーバーが起動していることを確認し、ホスト・ポート設定を確認してください。

### 2. 認証エラー
```
Weather query failed: authentication failed
```
**対処法**: 正しいパスフレーズを設定し、`--auth-enabled`オプションを使用してください。

### 3. パラメータエラー
```
Weather mode: Specify either --coords or --area
Report mode: --area is required
```
**対処法**: 必須パラメータを正しく指定してください。

## Python版 client.py との比較

| Python版 | C++版 unified_client_cli |
|---------|-------------------------|
| `python client.py --weather --area 130010` | `./unified_client_cli weather --area 130010` |
| `python client.py --report --area 130010` | `./unified_client_cli report --area 130010` |
| `python client.py --coords 35.6 139.7` | `./unified_client_cli weather --coords 35.6 139.7` |
| `python client.py --debug` | `./unified_client_cli --debug` |

## 実行環境

- **対応OS**: Linux, Windows (WSL), macOS
- **必要な依存関係**: CMake 3.20+, C++20対応コンパイラ
- **動作確認済み**: Ubuntu 20.04+, Windows 11 WSL2

## トラブルシューティング

### ビルドエラー
```bash
# クリーンビルドを試す
rm -rf build && mkdir build && cd build
cmake ..
make unified_client_cli
```

### 実行時エラー
```bash
# デバッグ情報付きで実行
./unified_client_cli [mode] [options] --debug
```

### パフォーマンス確認
```bash
# レスポンス時間も表示される
./unified_client_cli report --area 130010 --weather-code 1 --debug
```

このツールにより、Python版と完全同等の機能をC++で提供し、単一ファイルでの柔軟なテストが可能になります。