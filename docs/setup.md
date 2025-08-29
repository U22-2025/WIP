# 目次
- [目次](#目次)
- [0. 前提条件](#0-前提条件)
- [1. リポジトリのクローン](#1-リポジトリのクローン)
- [2. 必要パッケージのインストール](#2-必要パッケージのインストール)
- [3. PostgreSQL + PostGIS セットアップ](#3-postgresql--postgis-セットアップ)
  - [3.1 PostgreSQL インストール](#31-postgresql-インストール)
  - [3.2 初期設定とユーザ作成](#32-初期設定とユーザ作成)
  - [3.3 データベース作成と拡張](#33-データベース作成と拡張)
  - [3.4 空間データインポート（JMA 一次細分区域）](#34-空間データインポートjma-一次細分区域)
- [4. Dragonfly セットアップ（Redis互換 + JSON + Pub/Sub, 必須）](#4-dragonfly-セットアップredis互換--json--pubsub-必須)
  - [4.1 インストール（.deb）](#41-インストールdeb)
  - [4.2 データディレクトリ作成](#42-データディレクトリ作成)
  - [4.3 systemd ユニット作成（2 インスタンス）](#43-systemd-ユニット作成2-インスタンス)
- [5. Python 環境構築](#5-python-環境構築)
- [6. .env の用意と編集](#6-env-の用意と編集)
- [7. サーバ群とアプリの起動](#7-サーバ群とアプリの起動)
  - [7.1 起動](#71-起動)
  - [7.2 初期データ更新（気象庁から取得）](#72-初期データ更新気象庁から取得)
  - [7.3 動作確認（Map/API）](#73-動作確認mapapi)
- [8. Report サーバへ気象情報をアップロード](#8-report-サーバへ気象情報をアップロード)
- [9. C++ のビルドと確認](#9-c-のビルドと確認)
- [10. Rust のビルドと確認](#10-rust-のビルドと確認)
- [付録: トラブルシューティング](#付録-トラブルシューティング)

---

# 0. 前提条件
- 対象 OS: Ubuntu 24.04 LTS（サーバ/デスクトップどちらでも可）
- ネットワーク接続（気象庁/JMA への HTTP アクセスが必要）
- 管理者権限（`sudo`）

---

# 1. リポジトリのクローン
```bash
git clone https://github.com/U22-2025/WIP.git
cd WIP
```

---

# 2. 必要パッケージのインストール
```bash
sudo apt update
sudo apt install -y \
  git curl build-essential cmake pkg-config \
  python3 python3-venv python3-pip \
  postgresql postgresql-contrib postgis gdal-bin \
  libpq-dev \
  jq
```
補足:
- `jq` は API 応答の JSON 整形/抽出に使用（後述の Report 手順で使用）
- Port 80 は root 権限が必要なため、Map/Weather API は 8000/8001 を使用します

---

# 3. PostgreSQL + PostGIS セットアップ
## 3.1 PostgreSQL インストール
上のパッケージインストールに含まれています（`postgresql`, `postgis`）。

## 3.2 初期設定とユーザ作成
```bash
sudo systemctl enable --now postgresql
sudo -u postgres psql
```
psql 内で以下を実行（自分のユーザ名/パスワードに置換）：
```sql
CREATE ROLE wip WITH LOGIN PASSWORD 'wippass';
ALTER ROLE wip CREATEDB;
```

## 3.3 データベース作成と拡張
```sql
CREATE DATABASE weather_forecast_map OWNER wip;
\c weather_forecast_map
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
\q
```

## 3.4 空間データインポート（JMA 一次細分区域）
JMA の一次細分区域 Shapefile を取り込み、座標→区域コード解決に使用します。

1) データ取得（公式 URL 例）
```bash
cd /tmp
wget -O jma_area.zip "https://www.data.jma.go.jp/developer/gis/20190125_AreaForecastLocalM_1saibun_GIS.zip"
unzip jma_area.zip -d jma_area
```
2) Shapefile を PostGIS に投入（SRID 6668）
```bash
shp2pgsql -W utf-8 -D -I -s 6668 \
  "jma_area/一次細分区域等.shp" public.jma_districts_raw > /tmp/jma_insert.sql
psql -h 127.0.0.1 -U wip -d weather_forecast_map -f /tmp/jma_insert.sql
```
3) アプリが期待するテーブル名/カラムに整備
```bash
 psql -h 127.0.0.1 -U wip -d weather_forecast_map
```
psql 内で以下を実行：
```sql
-- 名前に日本語が含まれるため、アプリ互換名へリネーム
ALTER TABLE IF EXISTS jma_districts_raw RENAME TO districts;
-- コード列が 'code' で無い場合に備え、代表コード列を code に揃える（存在チェックのうえ調整）
-- 例: ALTER TABLE districts RENAME COLUMN 区域コード TO code;
-- 例: ALTER TABLE districts RENAME COLUMN geom TO geom; -- 既に geom であれば不要
-- 最低限、以下の列が存在する必要があります：
--   geom: geometry(Polygon/MultiPolygon, 6668)
--   code: varchar/text（6桁地域コード）
\q
```

---

# 4. Dragonfly セットアップ（Redis互換 + JSON + Pub/Sub, 必須）
Query/Report パイプラインは JSON 機能が必須です。Dragonfly は Redis 互換で JSON/PubSub をデフォルトで利用できます。

ここでは .deb パッケージで Dragonfly を導入し、2 インスタンス（データ:6379、ログ:6380）を systemd で常駐起動します。

## 4.1 インストール（.deb）
```bash
cd /tmp
wget -O dragonfly_amd64.deb \
  https://dragonflydb.gateway.scarf.sh/latest/dragonfly_amd64.deb
sudo apt install -y ./dragonfly_amd64.deb

# 動作確認（バージョン表示）
dragonfly --version || /usr/bin/dragonfly --version || true
```

## 4.2 データディレクトリ作成
```bash
sudo mkdir -p /var/lib/dragonfly/6379 /var/lib/dragonfly/6380
```

## 4.3 systemd ユニット作成（2 インスタンス）
`/etc/systemd/system/dragonfly-6379.service` を作成：
```ini
[Unit]
Description=Dragonfly (data) on 6379
After=network.target

[Service]
ExecStart=/usr/bin/dragonfly --port=6379 --dir=/var/lib/dragonfly/6379
Restart=always
LimitNOFILE=100000

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/dragonfly-6380.service` を作成：
```ini
[Unit]
Description=Dragonfly (log pubsub) on 6380
After=network.target

[Service]
ExecStart=/usr/bin/dragonfly --port=6380 --dir=/var/lib/dragonfly/6380
Restart=always
LimitNOFILE=100000

[Install]
WantedBy=multi-user.target
```

ユニットを読み込み・自動起動・起動：
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now dragonfly-6379 dragonfly-6380
sudo systemctl --no-pager --full status dragonfly-6379
```

以降の `.env` では次を前提とします：
- `REDIS_PORT=6379`（データ: Query/Report 用, Dragonfly JSON）
- `LOG_REDIS_PORT=6380`（Map 共有ログ: Pub/Sub 用 Dragonfly）

---

# 5. Python 環境構築
```bash
# プロジェクト直下で実行
python3 -m venv .venv
source .venv/bin/activate

# 本リポジトリのパッケージ群を開発モードで導入（src/ を import 可能に）
pip install -e .[all]
```

---

# 6. .env の用意と編集
```bash
cp .env.example .env
```
最低限、以下を環境に合わせて編集してください（`nano .env` 等）：

- DB 系
  - `DB_HOST=localhost`
  - `DB_PORT=5432`
  - `DB_NAME=weather_forecast_map`
  - `DB_USERNAME=wip`
  - `DB_PASSWORD=wippass`
  - `MAP_HTTP_PORT=80`
  - `WEATHER_API_PORT=80`
- Dragonfly（Redis互換）
  - `REDIS_PORT=6379`（データ: Query/Report 用, JSON 利用）
  - `LOG_REDIS_PORT=6380`（Map の共有ログ Pub/Sub 用）

他は既定値のままで問題ありません（必要に応じて `WEATHER_*_PORT` 等を調整）。

---

# 7. サーバ群とアプリの起動
## 7.1 起動
全サーバ（Weather/Location/Query/Report）と Map+Weather API をまとめて起動：
```bash
source .venv/bin/activate
python python/launch_server.py --all
```
表示:
- Map: `http://localhost:8000`
- Weather API: `http://localhost:8000/api`（Map にサブマウント）

## 7.2 初期データ更新（気象庁から取得）
起動直後はデータが空の場合があります。API を叩いて強制更新してください：
```bash
curl -X POST http://localhost:8000/api/update/weather    # 天気・気温・降水確率更新
curl -X POST http://localhost:8000/api/update/disaster   # 注意報/警報・災害/地震情報更新
```

任意：対象オフィス（都道府県）を絞りたい場合は `.env` に以下を追加（カンマ区切り）：
```env
WEATHER_API_TARGET_OFFICES=130000,270000
```

## 7.3 動作確認（Map/API）
```bash
# API 健康確認
curl http://localhost:8000/api/health

# 任意の地域コード（例: 東京 130010）のデータ取得
curl "http://localhost:8000/api/weather?area_code=130010" | jq

# 週間予報（座標指定）
curl -X POST http://localhost:8000/weekly_forecast \
  -H 'Content-Type: application/json' \
  -d '{"lat":35.6895, "lng":139.6917}' | jq
```

---

# 8. Report サーバへ気象情報をアップロード
「気象庁から取得した最新データ」を Report サーバに送る手順です。

1) 最新データを API で取得（例: 東京 130010）
```bash
read WC TEMP POP < <(curl -s "http://localhost:8000/api/weather?area_code=130010" \
  | jq -r '[.weather,.temperature,.precipitation_prob] | @tsv')
echo "weather=$WC temp=$TEMP pop=$POP"
```
2) 取得値をレポート送信（UDP/4112, ReportServer）
```bash
source .venv/bin/activate
python python/client.py --report \
  --area 130010 \
  --weather "$WC" \
  --pops "$POP" \
  --temp "$TEMP"
```
成功時は `OK Report sent successfully!` が表示されます。

（備考）`--alert` や `--disaster` オプションで追加情報も送信可能です。

---

# 9. C++ のビルドと確認
依存：`build-essential`, `cmake`, `g++`（前述インストール済）

```bash
# CMake ビルド（ユーティリティCLIを含む）
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build -j

# 疎通テスト（Weather Server へ UDP リクエスト）
./cpp/build/unified_client_cli weather --area 130010 --host 127.0.0.1 --proxy
```
オプション例：
- 座標指定: `./cpp/build/unified_client_cli weather --coords 35.6895 139.6917`
- 直接 WeatherServer: `--host 127.0.0.1 --port 4110`

---

# 10. Rust のビルドと確認
依存：`rustup`/`cargo`
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
source "$HOME/.cargo/env"

cd Rust
cargo build --release --bins

# 疎通テスト（エリアコード）
./target/release/wip-weather get 130010 --weather --temperature --precipitation

# 座標指定の例
./target/release/wip-weather coords 35.6895 139.6917 --weather --temperature --precipitation
```

---

# 付録: トラブルシューティング
- Map/Weather API が 80 番ポートで失敗する:
  - `.env` で `MAP_HTTP_PORT=8000`, `WEATHER_API_PORT=8001` に変更（本手順通り）
- LocationServer が DB 接続に失敗する:
  - `.env` の `DB_*` が DB 実体と一致しているか確認（ユーザ/パスワード/DB 名）
  - `psql -U wip -d weather_forecast_map -c "SELECT 1"` で疎通確認
- 地域コード解決が常に失敗する:
  - PostGIS テーブル `districts(geom, code)` が存在するか確認
  - SRID 6668 で取り込まれているか確認（`geometry_columns` 参照）
- Dragonfly（Redis互換）関連のエラー:
  - `docker ps` で `dfly-data` / `dfly-log` が起動中か確認
  - `redis-cli -p 6379 ping` / `redis-cli -p 6380 ping` で疎通確認
  - JSON コマンドが失敗する場合は `dfly-data` に対して実行しているか確認（6379）
