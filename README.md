# WIP (Weather Transfer Protocol)

WIP（Weather Transfer Protocol）は、NTPをベースとした軽量な気象データ転送プロトコルです。IoT機器でも使用できるよう、小さなデータサイズでの通信を実現し、気象庁の公開データを効率的に配信します。

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
- **precipitation_prob (8bit)**: 降水確率（%）

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
- KeyDB (ログ配信用)

### 依存関係のインストール
```bash
# Condaを使用する場合
conda env create -f yml/env311.yml
conda activate U22-WIP

# pipを使用する場合
pip install -r requirements.txt

# テスト環境を構築する場合
pip install -e .[dev]
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
DATABASE_URL=postgresql://user:password@localhost/wip_db

# Redis設定
REDIS_HOST=localhost
REDIS_PORT=6379
LOG_REDIS_HOST=localhost
LOG_REDIS_PORT=6380
LOG_REDIS_DB=1
```
KeyDB を使用してログを配信する場合は、以下の例のように Docker で起動できます。
```bash
docker run -d --name keydb -p 6380:6379 eqalpha/keydb
# conf/keydb_log.conf を使う場合
# docker run -d --name keydb -v $(pwd)/conf/keydb_log.conf:/etc/keydb/keydb.conf eqalpha/keydb keydb-server /etc/keydb/keydb.conf
```
RedisJSON モジュールは特に必要ありません。
`localhost` を指定した場合は内部で IPv4 アドレス `127.0.0.1` に解決されます。環境によっては直接 `127.0.0.1` を指定することもできます。

## 使用方法

### サーバの起動

#### 全サーバを一括起動
```bash
# Windowsの場合
start_servers.bat

# 手動で個別起動
python -m wip.servers.weather_server.weather_server
python -m wip.servers.location_server.location_server
python -m wip.servers.query_server.query_server
```

### クライアントの使用

#### 基本的な使用例
```python
from wip.clients.weather_client import WeatherClient

# クライアント初期化（"localhost" は自動で IPv4 に解決されます）
client = WeatherClient(host='localhost', port=4110, debug=True)

# 座標から天気情報を取得
result = client.get_weather_by_coordinates(
    latitude=35.6895,   # 東京の緯度
    longitude=139.6917, # 東京の経度
    weather=True,       # 天気データ
    temperature=True,   # 気温データ
    precipitation_prob=True  # 降水確率
)

print(f"Area Code: {result['area_code']}")
print(f"Weather Code: {result['weather_code']}")
print(f"Temperature: {result['temperature']}°C")
print(f"precipitation_prob: {result['precipitation_prob']}%")

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
python -m WIPCommonPy.clients.weather_client

# 座標解決のテスト
python -m WIPCommonPy.clients.location_client

# 気象データクエリのテスト
python -m WIPCommonPy.clients.query_client

# センサーデータレポートのテスト
python -m WIPCommonPy.clients.report_client
```

## データ形式

### 天気コード
気象庁の天気コードに準拠（`weather_code.json`参照）

#### 主要な天気コード
| コード | 天気 |
|--------|------|
| 100 | 晴れ |
| 101 | 晴れ 時々 くもり |
| 200 | くもり |
| 201 | くもり 時々 晴 |
| 300 | 雨 |
| 301 | 雨 時々 晴れ |
| 400 | 雪 |
| 401 | 雪 時々 晴れ |

#### 詳細な天気コード
- **100番台**: 晴れ系（100-181）
- **200番台**: くもり系（200-281）
- **300番台**: 雨系（300-371）
- **400番台**: 雪系（400-427）

### 地域コード
気象庁の地域コード体系を使用
- 6桁の数値コード
- 上位桁で地方、下位桁で詳細地域を表現
- 例: "130010" = 東京都東京地方

#### 主要地域コード例
| コード | 地域 |
|--------|------|
| 011000 | 北海道 石狩地方 |
| 040010 | 宮城県 東部 |
| 130010 | 東京都 東京地方 |
| 140010 | 神奈川県 東部 |
| 270000 | 大阪府 |
| 400010 | 福岡県 福岡地方 |

### 気温データ
- 8ビット2の補数表現
- +100オフセット（0℃ = 100, -10℃ = 90, 30℃ = 130）
- 範囲: -128℃ ～ +127℃

### 注意報・警報データ
拡張フィールドで配信される災害情報：
- **注意報**: 大雨注意報、強風注意報、雷注意報など
- **警報**: 大雨警報、暴風警報、大雪警報など
- **特別警報**: 大雨特別警報、暴風特別警報など

### 災害情報データ
- **地震情報**: 震度、震源地、マグニチュード
- **津波情報**: 津波警報、津波注意報
- **火山情報**: 噴火警報、噴火予報

## 開発・デバッグ

### デバッグツール
プロジェクトには包括的なデバッグツールが含まれています：

#### 統合デバッグスイート
```bash
# フルテスト実行（推奨）
python debug_tools/core/integrated_debug_suite.py --mode full

# クイック検証のみ
python debug_tools/core/integrated_debug_suite.py --mode quick

# パフォーマンステストをスキップ
python debug_tools/core/integrated_debug_suite.py --mode full --no-performance
```

#### 個別デバッグツール
```bash
# パフォーマンス分析
python debug_tools/performance/performance_debug_tool.py

# 個別フィールドデバッグ
python debug_tools/individual/debug_extended_field.py

# エンコード・デコード詳細追跡
python debug_tools/individual/debug_encoding_step_by_step.py
```

### テスト実行
```bash
# API性能テスト
python test/api_test.py

# プロトコルテスト
python -m wip.packet.format  # パケット形式テスト
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
- 分散アーキテクチャによる負荷分散
- 座標解決結果のキャッシュ

### パフォーマンス測定
```bash
# 統合パフォーマンステスト
python debug_tools/performance/performance_debug_tool.py

# 外部API比較テスト
python test/api_test.py
```

## API比較

外部気象APIとの性能比較（`test/api_test.py`で測定可能）：

### 対象API
- **Open-Meteo API**: 無料の気象データAPI
- **wttr.in API**: シンプルな天気情報API
- **met.no API**: ノルウェー気象研究所のAPI
- **気象庁API**: 日本の公式気象データAPI

### 比較項目
- レスポンス時間
- スループット
- データサイズ
- 同時接続性能
- 成功率

### WIPの優位性
- **軽量**: 48バイトの小さなパケットサイズ
- **高速**: 平均100ms以下のレスポンス時間
- **効率**: バイナリ形式による効率的なデータ転送
- **拡張性**: 災害情報・警報データの統合配信

## セキュリティ

### 実装済み機能
- **チェックサム**: パケット誤り検出
- **タイムスタンプ**: リプレイ攻撃対策
- **パケットID**: 重複パケット検出

### 推奨セキュリティ対策
- ファイアウォールによるアクセス制御
- VPNによる通信暗号化
- レート制限によるDoS攻撃対策

## 拡張機能

### Wiresharkプロトコル解析
```bash
# Wiresharkでのパケット解析用Luaスクリプト
# wireshark.luaをWiresharkのプラグインディレクトリに配置
```

### 自動データ更新
```bash
# 気象データの定期更新スクリプト
python wip/scripts/update_weather_data.py
```

### キャッシュ管理
- Redis による高速キャッシュ
- 地域コードキャッシュ（`cache/area_cache.json`）
- 気象データキャッシュ（TTL: 1時間）
- 各キャッシュは設定ファイルの `enable_*_cache` オプションで有効/無効を切り替え可能
- WIP_Client の座標キャッシュは `python/WIP_Client/config.ini` の
  `enable_coordinate_cache` でオン/オフを設定

## トラブルシューティング

### よくある問題

#### 1. 接続エラー
```bash
# サーバが起動しているか確認
netstat -an | grep 4110

# ファイアウォール設定確認
# Windows: Windows Defender ファイアウォール
# Linux: iptables -L
```

#### 2. パケット解析エラー
```bash
# デバッグモードでパケット内容確認
python -m wip.clients.weather_client
```

#### 3. パフォーマンス問題
```bash
# パフォーマンス詳細分析
python debug_tools/performance/performance_debug_tool.py
```

### ログレベル
- `[INFO]`: 一般的な情報
- `[ERROR]`: エラー情報
- `[PERF]`: パフォーマンス関連
- `[DEBUG]`: デバッグ情報

## 技術仕様詳細

### プロトコルスタック
```
+------------------+
| WIP Application  |
+------------------+
| UDP              |
+------------------+
| IP               |
+------------------+
| Ethernet         |
+------------------+
```

### データフロー
1. **クライアント**: 座標またはエリアコードでリクエスト
2. **Weather Server**: リクエストを適切なサーバに転送
3. **Location Server**: 座標を地域コードに変換
4. **Query Server**: 気象庁データを取得・処理
5. **レスポンス**: 気象データをクライアントに返送

### エラーハンドリング
- **タイムアウト**: 10秒でタイムアウト
- **チェックサムエラー**: パケット破棄
- **不正フォーマット**: エラーレスポンス
- **サーバエラー**: 適切なエラーコード返送

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

```
MIT License

Copyright (c) 2025 WIP Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 貢献

### 貢献方法
1. このリポジトリをフォーク
2. 機能ブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

### 開発ガイドライン
- コードスタイル: PEP 8準拠
- テスト: 新機能には必ずテストを追加
- ドキュメント: 変更内容をREADMEに反映
- デバッグ: デバッグツールでの検証を実施


- プロジェクトリーダー: szk27@outlook.jp
- 開発チーム: U22プロジェクトチーム

## サポート



### サポート範囲
- プロトコル仕様に関する質問
- 実装上の問題
- パフォーマンス最適化
- セキュリティ問題

### レスポンス時間
- 重要な問題: 24時間以内
- 一般的な質問: 3営業日以内
- 機能要求: 1週間以内

## 関連ドキュメント

### 技術文書
- [WIP仕様表.md](WIP仕様表.md) - 詳細な技術仕様
- [project_detail.md](project_detail.md) - プロジェクト詳細
- [protocol_format.xlsx](protocol_format.xlsx) - パケット形式詳細

### デバッグ文書
- [debug_tools/docs/DEBUG_TOOLS_README.md](debug_tools/docs/DEBUG_TOOLS_README.md) - デバッグツール使用方法
- [debug_tools/docs/extended_field_fix_report.md](debug_tools/docs/extended_field_fix_report.md) - 拡張フィールド修正レポート

### 設定ファイル
- [yml/env311.yml](yml/env311.yml) - Conda環境設定
- [weather_code.json](weather_code.json) - 天気コード定義
- [start_servers.bat](start_servers.bat) - サーバ起動スクリプト

## 更新履歴

### v1.0.0 (2025-06-01)
- 初回リリース
- 基本プロトコル実装
- 3サーバ構成の実装
- クライアントライブラリ
- デバッグツール群
- パフォーマンステスト

#### 主要機能
- NTPベースのUDPプロトコル
- 48バイト軽量パケット
- 座標解決機能
- 気象データ配信
- 災害情報配信
- 拡張フィールドサポート

#### 技術的改善
- バイナリ形式でのデータ転送
- Redis キャッシュシステム
- 分散アーキテクチャ
- 包括的なデバッグツール
- 外部API性能比較

#### 今後の予定
- v1.1.0: 認証機能追加
- v1.2.0: 暗号化サポート
- v1.3.0: 多言語対応
- v2.0.0: IPv6サポート

---

**WIP (Weather Transfer Protocol)** - 軽量で効率的な気象データ転送プロトコル

プロジェクトの詳細情報や最新の更新については、[GitHub リポジトリ](https://github.com/your-repo/wip)をご確認ください。
