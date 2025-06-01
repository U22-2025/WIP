# WTP (Weather Transfer Protocol)

WTP（Weather Transfer Protocol）は、NTPをベースとした軽量な気象データ転送プロトコルです。IoT機器でも使用できるよう、小さなデータサイズでの通信を実現し、気象庁の公開データを効率的に配信します。

## 概要

- **プロトコル**: NTPベースのUDPアプリケーションプロトコル
- **ポート番号**: UDP/4110
- **データサイズ**: 48バイト程度の軽量パケット
- **通信方式**: 1:1のリクエスト・レスポンス形式
- **データソース**: 気象庁公開データ（XML/JSON形式）
- **対応データ**: 気象情報、災害情報、注意報・警報

## 特徴

### 軽量設計
- バイナリ形式でのデータ転送
- 基本パケットサイズ48バイト
- IoT機器での使用を想定した省帯域設計

### 分散アーキテクチャ
- ルートサーバによる地域別サーバ管理
- 地域コードベースのデータ分散
- プロキシサーバによる透過的な転送

### 拡張性
- 可変長拡張フィールドサポート
- 座標を使ったデータ要求
- 災害情報・警報データの配信

## アーキテクチャ

```
[クライアント] ←→ [Weather Server (Proxy) / Location Server] ←→ [Query Server]
                                                                    ↓
                                                            [気象庁データソース]
```

### サーバ構成

1. **Weather Server (Port 4110)** - プロキシサーバ
   - クライアントからのリクエストを受信
   - 適切なサーバへリクエストを転送
   - レスポンスをクライアントに返送

2. **Location Server (Port 4109)** - 座標解決サーバ
   - 緯度・経度から地域コードへの変換
   - 地域コードキャッシュ管理

3. **Query Server (Port 4111)** - 気象データサーバ
   - 気象庁データの取得・処理
   - 気象データのキャッシュ管理
   - レスポンスパケットの生成

## プロトコル仕様

### パケットフォーマット

#### 基本ヘッダー (128ビット)
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|　Ver　|  　　  Packet ID 　    |Typ|W|T|P|A|D|E|  Day  |Reserv |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|                           Timestamp                           |
|                                                               |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|              Area Code                |       Checksum        |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

#### フィールド詳細
- **Version (4bit)**: プロトコルバージョン（現在は1）
- **Packet ID (12bit)**: パケット識別子
- **Type (3bit)**: パケットタイプ
  - 0: 座標解決リクエスト
  - 1: 座標解決レスポンス
  - 2: 気象データリクエスト
  - 3: 気象データレスポンス
- **フラグフィールド (6bit)**:
  - W: 天気データ取得
  - T: 気温データ取得
  - P: 降水確率取得
  - A: 注意報・警報取得
  - D: 災害情報取得
  - E: 拡張フィールド使用
- **Day (3bit)**: 予報日（0=当日、1=翌日...）
- **Timestamp (64bit)**: UNIX時間
- **Area Code (20bit)**: 気象庁地域コード
- **Checksum (12bit)**: パケット誤り検出

#### レスポンス専用フィールド
- **Weather Code (16bit)**: 天気コード
- **Temperature (8bit)**: 気温（2の補数、+100オフセット）
- **Precipitation (8bit)**: 降水確率（%）

#### 拡張フィールド（可変長）
- **ヘッダー (16bit)**: データ長(10bit) + データ種別(6bit)
- **データ種別**:
  - 000001: 注意報・警報
  - 000010: 災害情報
  - 100001: 緯度
  - 100010: 経度
  - 101000: 送信元IPアドレス

## インストール・セットアップ

### 必要環境
- Python 3.10+
- PostgreSQL (座標解決用)
- PostGIS (地理情報処理)
- Redis (キャッシュ)

### 依存関係のインストール
```bash
# Condaを使用する場合
conda env create -f environment.yml
conda activate U22-2025

# pipを使用する場合
pip install requests python-dotenv redis psycopg2-binary
```

### 環境変数設定
`.env`ファイルを作成し、以下を設定：
```env
# サーバ設定
WEATHER_SERVER_PORT=4110
LOCATION_RESOLVER_HOST=localhost
LOCATION_RESOLVER_PORT=4109
QUERY_GENERATOR_HOST=localhost
QUERY_GENERATOR_PORT=4111

# データベース設定
DATABASE_URL=postgresql://user:password@localhost/wtp_db

# Redis設定
REDIS_HOST=localhost
REDIS_PORT=6379
```

## 使用方法

### サーバの起動

#### 全サーバを一括起動
```bash
# Windowsの場合
start_servers.bat

# 手動で個別起動
python -m wtp.servers.weather_server.weather_server
python -m wtp.servers.location_server.location_server
python -m wtp.servers.query_server.query_server
```

### クライアントの使用

#### 基本的な使用例
```python
from wtp.clients.weather_client import WeatherClient

# クライアント初期化
client = WeatherClient(host='localhost', port=4110, debug=True)

# 座標から天気情報を取得
result = client.get_weather_by_coordinates(
    latitude=35.6895,   # 東京の緯度
    longitude=139.6917, # 東京の経度
    weather=True,       # 天気データ
    temperature=True,   # 気温データ
    precipitation=True  # 降水確率
)

print(f"Area Code: {result['area_code']}")
print(f"Weather Code: {result['weather_code']}")
print(f"Temperature: {result['temperature']}°C")
print(f"Precipitation: {result['precipitation']}%")

# エリアコードから直接取得
result = client.get_weather_by_area_code(
    area_code="130010",  # 東京都東京地方
    weather=True,
    temperature=True,
    alerts=True,         # 警報情報
    disaster=True        # 災害情報
)

client.close()
```

#### コマンドライン実行
```bash
# クライアントのテスト実行
python -m wtp.clients.weather_client

# 座標解決のテスト
python -m wtp.clients.location_client

# 気象データクエリのテスト
python -m wtp.clients.query_client
```

## データ形式

### 天気コード
気象庁の天気コードに準拠（`weather_code.json`参照）
```json
{
  "100": "晴れ",
  "101": "晴れ時々曇り",
  "200": "曇り",
  "300": "雨"
}
```

### 地域コード
気象庁の地域コード体系を使用
- 6桁の数値コード
- 上位桁で地方、下位桁で詳細地域を表現
- 例: "130010" = 東京都東京地方

### 気温データ
- 8ビット2の補数表現
- +100オフセット（0℃ = 100, -10℃ = 90, 30℃ = 130）
- 範囲: -128℃ ～ +127℃

## 開発・デバッグ

### デバッグツール
プロジェクトには包括的なデバッグツールが含まれています：

```bash
# 統合デバッグツール
python debug_tools/core/integrated_debug_suite.py

# パフォーマンス分析
python debug_tools/performance/performance_debug_tool.py

# 個別フィールドデバッグ
python debug_tools/individual/debug_extended_field.py
```

### テスト実行
```bash
# API性能テスト
python test/api_test.py

# プロトコルテスト
python -m wtp.packet.format  # パケット形式テスト
```

### ログ出力
デバッグモードでの詳細ログ出力：
```python
# サーバ起動時にデバッグモードを有効化
server = WeatherServer(debug=True)
client = WeatherClient(debug=True)
```

## パフォーマンス

### ベンチマーク結果
- **レスポンス時間**: 平均 < 100ms
- **スループット**: > 100 req/sec
- **パケットサイズ**: 基本48バイト、拡張時最大1024バイト
- **同時接続**: 最大100接続

### 最適化ポイント
- Redis キャッシュによる高速データアクセス
- バイナリ形式による効率的なデータ転送

## API比較

外部気象APIとの性能比較（`test/api_test.py`で測定可能）：
- Open-Meteo API
- wttr.in API
- met.no API
- 気象庁API

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

## サポート

- 問題報告: GitHub Issues
- 技術的質問: Discussions
- メール: szk27@outlook.jp

## 関連ドキュメント

- [WTP仕様表.md](WTP仕様表.md) - 詳細な技術仕様
- [project_detail.md](project_detail.md) - プロジェクト詳細
- [debug_tools/docs/](debug_tools/docs/) - デバッグツール文書
- [protocol_format.xlsx](protocol_format.xlsx) - パケット形式詳細

## 更新履歴

### v1.0.0 (2025-06-01)
- 初回リリース
- 基本プロトコル実装
- 3サーバ構成の実装
- クライアントライブラリ
- デバッグツール群
- パフォーマンステスト
