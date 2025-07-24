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
- [4. RedisJSON セットアップ](#4-redisjson-セットアップ)
  - [4.1 標準インストール](#41-標準インストール)

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
## 4.1 標準インストール
```bash
sudo apt update
sudo apt install redis-server
```
