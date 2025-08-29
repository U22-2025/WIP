# WIP (Weather Information Protocol)

WIP（Weather Information Protocol）は、NTPをベースとした軽量な気象データ転送プロトコルです。IoT機器でも使用できるよう、小さなデータサイズでの通信を実現し、気象庁の公開データを効率的に配信します。

## 概要

- **プロトコル**: NTPベースのUDPアプリケーションプロトコル
- **ポート番号**: UDP/4110（Rust/Python共通）
- **データサイズ**: 基本16バイト程度の軽量パケット
- **通信方式**: 1:1のリクエスト・レスポンス形式
- **データソース**: 気象庁公開データ（XML/JSON形式）
- **対応データ**: 気象情報、災害情報、注意報・警報

## 特徴

### 軽量設計
- バイナリ形式でのデータ転送
- 基本パケットサイズ16バイト
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

1. **Weather Server (Port 4110)** - プロキシサーバ（Rust/Python共通ポート）
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

4. **Report Server (Port 4112)** - センサーデータレポートサーバ
   - IoT機器からのレポートデータを受信
   - データの検証と蓄積を担当

## プロトコル仕様

### パケットフォーマット

#### 基本ヘッダー (128ビット)
```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|　Ver　|  　　  Packet ID 　    |Typ|W|T|P|A|D|E|RA|RS| Day |Res |
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
- **フラグフィールド (8bit)**:
  - W: 天気データ取得
  - T: 気温データ取得
  - P: 降水確率取得
  - A: 注意報・警報取得
  - D: 災害情報取得
  - E: 拡張フィールド使用
  - RA: リクエスト認証フラグ
  - RS: レスポンス認証フラグ
  - **Day (3bit)**: 予報日（0=当日、1=翌日...）
  - **Reserved (2bit)**: 予約領域
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
  - 000100: 認証ハッシュ
  - 100001: 緯度
  - 100010: 経度
  - 101000: 送信元IPアドレス

## インストール・セットアップ

### 必要環境
- Python 3.10+
- PostgreSQL (座標解決用)
- PostGIS (地理情報処理)
- Dragonfly (キャッシュ)
- Dragonfly (ログ配信用)

### 依存関係のインストール
```bash
# Condaを使用する場合
conda env create -f yml/env311.yml
conda activate U22-WIP

# pipを使用する場合
pip install -r requirements.txt

# ライブラリとして開発モードでインストールする場合
pip install -e .

# テスト環境を構築する場合
pip install -e .[dev]

# サーバーを個別にインストールする場合
pip install -e .[location_server]
pip install -e .[query_server]

# すべてのサーバーをインストールする場合
pip install -e .[servers]

# PyPI から全機能をインストールする場合
pip install "wiplib[all]"
```

### 環境変数設定
`.env`ファイルを作成し、以下を設定：
```env
# サーバ設定
WEATHER_SERVER_PORT=4110  # Rust/Python共通
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

#### クライアント環境変数

Rust 版の `wip-weather` と Python 版の `WeatherClient` は、環境変数 `WEATHER_SERVER_HOST` と `WEATHER_SERVER_PORT` を参照します。未設定の場合はそれぞれ `127.0.0.1` と `4110` が使用され、コマンドラインの `--host` / `--port` オプションが指定された場合はそちらが優先されます。

例:
```bash
export WEATHER_SERVER_HOST=weather.example.com
export WEATHER_SERVER_PORT=5000
wip-weather get 11000 --weather
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

# 手動で個別起動（Python ランチャー経由）
python python/launch_server.py --weather
python python/launch_server.py --location
python python/launch_server.py --query
python python/launch_server.py --report
```

### クライアントの使用

#### 基本的な使用例
```python
from WIPCommonPy.clients.weather_client import WeatherClient
from WIPCommonPy.packet import LocationRequest

# クライアント初期化（"localhost" は自動で IPv4 に解決されます）
client = WeatherClient(host='localhost', port=4110, debug=True)

# 座標から天気情報を取得（座標→エリア解決→天気データ）
req = LocationRequest.create_coordinate_lookup(
    latitude=35.6895,   # 東京の緯度
    longitude=139.6917, # 東京の経度
    packet_id=1,
    weather=True,
    temperature=True,
    precipitation_prob=True,
    version=1,
)
result = client._execute_location_request(req)

if result:
    print(f"Area Code: {result['area_code']}")
    print(f"Weather Code: {result['weather_code']}")
    print(f"Temperature: {result['temperature']}°C")
    print(f"precipitation_prob: {result['precipitation_prob']}%")

# エリアコードから直接取得
result = client.get_weather_by_area_code(
    area_code="130010",  # 東京都東京地方
    weather=True,
    temperature=True,
    precipitation_prob=True,
)

client.close()
```

#### 簡易実行のヒント
- Python クライアント各モジュールはスクリプト実行用エントリは提供していません。上記のサンプルのように API から呼び出してください。

#### 迅速な疎通テスト（Pythonモックサーバー + C++ CLI）
本番サーバ群の代わりに、簡易モックサーバーで C++ クライアントの疎通確認ができます。

1) モックサーバー起動（別ターミナル）
```bash
python python/tools/mock_weather_server.py  # UDP/4110 を待受
```

2) C++ CLI ビルド（CMake なしの場合）
```bash
# Windows (Developer Command Prompt)
cpp\tools\build_no_cmake.bat

# Linux/macOS/MSYS2
bash cpp/tools/build_no_cmake.sh
```

3) 疎通確認
```bash
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4110 --area 130010 --weather --temperature
```

モックサーバーは有効な WeatherResponse を即時返却します（エリアコード: 130010、天気コード: 100、温度: 22℃、降水確率: 10%）。

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

### デバッグツール（同梱）
- Python モックサーバー: `python python/tools/mock_weather_server.py`（UDP/4110 を待受）
- C++ デバッグ/検証ツール: `cpp/tools/*.cpp`（CMake もしくは付属スクリプトでビルド）

### テスト/検証
- C++ 単体テスト: `./cpp/build/wiplib_tests`
- ゴールデンベクタ検証:
  - 生成: `python python/tools/generate_golden_vectors.py`
  - 検証: `cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Debug && cmake --build cpp/build --config Debug && ./cpp/build/wiplib_golden`

### C++ クライアント（wiplib-cpp）
このリポジトリには C++20 実装（クライアントおよびパケットコーデック）が含まれます。ビルド手順:

```bash
# CMake 3.20+ と C++20 対応コンパイラを用意してください
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build --config Release

# 単体テスト（簡易）
./cpp/build/wiplib_tests

# CLI ツール実行例（Python サーバ群起動後）
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4110 --area 130010 --weather --temperature --precipitation

# 座標指定の例（東京）
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4110 --coords 35.6895 139.6917 --weather --temperature --precipitation
```

CLI オプション:
- `--host`, `--port`: 接続先 Weather Server (UDP/4110)
- `--coords <lat> <lon>` または `--area <6桁コード>`
- `--weather|--no-weather`, `--temperature|--no-temperature`, `--precipitation`, `--alerts`, `--disaster`, `--day <0-7>`

備考:
- C++ 実装は Python 実装と同じリトルエンディアン表現・12bitチェックサム（1の補数折返し）で動作します。相互運用で不一致があれば Issue へ報告ください。

### ゴールデンベクタ生成（Python → C++ 検証）
Python 実装から既知のパケットを生成して C++ でデコード検証できます。

```bash
# 1) ゴールデンベクタを生成（dist/golden/*.bin）
python python/tools/generate_golden_vectors.py

# 2) C++ 側で検証実行
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Debug
cmake --build cpp/build --config Debug
./cpp/build/wiplib_golden
```

### ソケット無しの相互運用テスト
C++で生成したリクエストをPythonが解釈、Pythonが生成したレスポンスをC++が解釈するテストを自動実行できます。

```bash
# C++ツールのビルド（gen/decode）
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Debug
cmake --build cpp/build --config Debug --target wip_packet_gen wip_packet_decode

# パス指定してテスト実行（Windowsは exe 拡張子）
export WIP_CPP_BIN_DIR=cpp/build
python python/tools/interop_no_socket.py
```

#### CMake なしでビルドする場合（全OS対応）

環境に CMake が無い場合でも、同梱スクリプトでビルドできます。

- Windows（MSVC / Developer Command Prompt）
  - `cpp\tools\build_no_cmake.bat`
  - 出力: `cpp\build\wip_client_cli.exe`, `cpp\build\wiplib_tests.exe`
- Windows（MSYS2/MinGW）/ Linux / macOS（clang++/g++）
  - `bash cpp/tools/build_no_cmake.sh`
  - 出力: `cpp/build/wip_client_cli`, `cpp/build/wiplib_tests`

実行例:
```bash
# CLI
./cpp/build/wip_client_cli --host 127.0.0.1 --port 4110 --area 130010 --weather --temperature

# テスト（コーデックの往復確認）
./cpp/build/wiplib_tests
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
 - **パケットサイズ**: 基本16バイト、拡張時最大1023バイト
- **同時接続**: 最大100接続

### 最適化ポイント
- Redis キャッシュによる高速データアクセス
- バイナリ形式による効率的なデータ転送
- 分散アーキテクチャによる負荷分散
- 座標解決結果のキャッシュ

### パフォーマンス測定
性能評価には C++ 実装のベンチツール（`cpp/` 配下）や実運用環境でのメトリクス収集をご利用ください。

## API比較

外部気象APIとの性能比較（ベンチマークは別途ツール/環境で実施）：

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
 - **軽量**: 16バイトの小さなパケットサイズ
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
# Wiresharkでのパケット解析用 Lua スクリプト
# lua/wireshark.lua を Wireshark のプラグインディレクトリに配置
```

### 自動データ更新
```bash
# 気象データの定期更新スクリプト
python src/WIPServerPy/scripts/update_weather_data.py
```

### キャッシュ管理
- Redis による高速キャッシュ
- 地域コードキャッシュ（クライアント側: `src/WIPClientPy/coordinate_cache.json`）
- 気象データキャッシュ（TTL: 1時間）
- 各キャッシュは設定ファイルの `enable_*_cache` オプションで有効/無効を切り替え可能
- WIPClientPy の座標キャッシュは `src/WIPClientPy/config.ini` の
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
```python
# デバッグモードでパケット内容確認（Python クライアント）
from WIPCommonPy.clients.weather_client import WeatherClient
client = WeatherClient(debug=True)
# 以降、通常の API 呼び出しで詳細ログが出力されます
```

#### 3. パフォーマンス問題
- ボトルネックの切り分けに C++ ベンチ（`cpp/`）や外部モニタリングを使用してください。

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
このプロジェクトはMITライセンスの下で公開されています。詳しくは [LICENSE](LICENSE) をご覧ください。

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
- [docs/project_detail.md](docs/project_detail.md) - プロジェクト詳細
- [docs/protocol_format.xlsx](docs/protocol_format.xlsx) - パケット形式詳細

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
 - 16バイト軽量パケット
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

**WIP (Weather Information Protocol)** - 軽量で効率的な気象データ転送プロトコル

プロジェクトの詳細情報や最新の更新については、[GitHub リポジトリ](https://github.com/U22-2025/WIP)をご確認ください。
