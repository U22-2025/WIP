# 目次
- [目次](#目次)
- [1. リポジトリのクローン](#1-リポジトリのクローン)
- [2. Ubuntu 24.04 インストール](#2-ubuntu-2404-インストール)
- [3. PostgreSQL セットアップ](#3-postgresql-セットアップ)
  - [3.1 PostgreSQL インストール](#31-postgresql-インストール)
  - [3.2 データベース設定](#32-データベース設定)
  - [3.3 データベース作成](#33-データベース作成)
  - [3.4 PostGIS 拡張機能インストール](#34-postgis-拡張機能インストール)
  - [3.5 空間データインポート](#35-空間データインポート)
    - [3.5.1 気象庁GISデータのダウンロード](#351-気象庁gisデータのダウンロード)
    - [3.5.2 GISデータのインポート](#352-gisデータのインポート)
- [4. RedisJSON セットアップ](#4-redisjson-セットアップ)
  - [4.1 依存ツールを用意](#41-依存ツールを用意)
  - [4.2 公式 GPG キーを登録](#42-公式-gpg-キーを登録)
  - [4.3 APT リポジトリを追加（拡張子は .list！）](#43-apt-リポジトリを追加拡張子は-list)
  - [4.4 パッケージリスト更新 \& インストール](#44-パッケージリスト更新--インストール)
  - [4.5 サービス起動と自動起動設定](#45-サービス起動と自動起動設定)
  - [4.6 ポート設定変更（6380番ポートで動作させる）](#46-ポート設定変更6380番ポートで動作させる)
  - [4.7 バージョン \& JSON コマンド確認](#47-バージョン--json-コマンド確認)
- [5. Dragonfly セットアップ](#5-dragonfly-セットアップ)
  - [5.1 Dragonfly インストール](#51-dragonfly-インストール)
  - [5.2 サービス確認と動作テスト](#52-サービス確認と動作テスト)

---

# 1. リポジトリのクローン
```bash
git clone https://github.com/U22-2025/WIP.git
```

---

# 2. Ubuntu 24.04 インストール
- Ubuntu 24.04 LTS(または22.04 LTS) をインストール

---

# 3. PostgreSQL セットアップ
## 3.1 PostgreSQL インストール
```bash
$ sudo apt install postgresql postgresql-contrib
```

## 3.2 データベース設定
```bash
$ sudo -u postgres psql
```
- ユーザ作成:
```sql
> CREATE USER [ユーザ名];
```

## 3.3 データベース作成
```sql
> CREATE DATABASE weather_forecast_map OWNER [ユーザ名];
> \q
```

## 3.4 PostGIS 拡張機能インストール
```
$ psql --version
psql (PostgreSQL) 16.9 (Ubuntu 16.9-0ubuntu0.24.04.1)

$ sudo apt install postgis postgresql-16-postgis-3
(( sudo apt install postgis postgresql-{psqlのバージョン番号}-postgis-3 ))
```

```sql
> CREATE EXTENSION postgis;
> CREATE EXTENSION postgis_topology;
> \q
```

## 3.5 空間データインポート
### 3.5.1 気象庁GISデータのダウンロード
気象庁の[GISデータ](https://www.data.jma.go.jp/developer/gis/20190125_AreaForecastLocalM_1saibun_GIS.zip)をダウンロード。
### 3.5.2 GISデータのインポート
```bash
$ shp2pgsql -W utf-8 -D -I -s 6668 20190125_AreaForecastLocalM_1saibun_GIS/一次細分区域等.shp > insert.sql
$ psql weather_forecast_map

> \i insert.sql
```
テーブル名がエラーを起こしそうなので変更しておく。
```sql
> ALTER TABLE 一次細分区域等 RENAME TO districts;
```

---

# 4. RedisJSON セットアップ
## 4.1 依存ツールを用意
```bashsudo apt-get update
sudo apt-get install -y lsb-release curl gpg
```
## 4.2 公式 GPG キーを登録
```bash
curl -fsSL https://packages.redis.io/gpg \
 | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
```
## 4.3 APT リポジトリを追加（拡張子は .list！）
```bash
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] \
https://packages.redis.io/deb $(lsb_release -cs) main" \
 | sudo tee /etc/apt/sources.list.d/redis.list
```
## 4.4 パッケージリスト更新 & インストール
```bash
sudo apt-get update
sudo apt-get install -y redis-server
```
## 4.5 サービス起動と自動起動設定
```bash
sudo systemctl enable --now redis-server
sudo systemctl status redis-server --no-pager
```

## 4.6 ポート設定変更（6380番ポートで動作させる）
```bash
# 設定ファイルの場所を確認
ls /etc/redis/
sudo ls /etc/redis/

# redis.conf 内の "port 6379" を "port 6380" に書き換える
sudo sed -i 's/^port 6379/port 6380/' /etc/redis/redis.conf

# Redis サーバーを再起動
sudo systemctl restart redis-server
```
## 4.7 バージョン & JSON コマンド確認
```bash
redis-server --version
redis-cli ping              # → PONG
redis-cli JSON.SET test $ '{"hello":"world"}'  # → OK
redis-cli JSON.GET test     # → "{\"hello\":\"world\"}"
redis-cli del test          # → (integer) 1
```

---

# 5. Dragonfly セットアップ
## 5.1 Dragonfly インストール
```bash
wget https://dragonflydb.gateway.scarf.sh/latest/dragonfly_amd64.deb
ls
sudo apt install -y ./dragonfly_amd64.deb
```

## 5.2 サービス確認と動作テスト
```bash
sudo systemctl status dragonfly.service
redis-cli -p 6379 ping
```