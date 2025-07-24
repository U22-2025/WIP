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
- Ubuntu 24.04 LTS をインストール

---

# 3. PostgreSQL セットアップ
## 3.1 PostgreSQL インストール
```bash
sudo apt install postgresql postgresql-contrib
```

## 3.2 データベース設定
```bash
sudo -u postgres psql
```
- ユーザ作成:
```sql
CREATE USER bababa WITH PASSWORD 'your_password';
```

## 3.3 データベース作成
```sql
CREATE DATABASE weather_forecast_map OWNER bababa;
\q
```

## 3.4 PostGIS 拡張機能インストール
```bash
sudo apt install postgis postgresql-14-postgis-3
psql -U bababa -d weather_forecast_map
```
```sql
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
\q
```

## 3.5 空間データインポート
```bash
shp2pgsql -W utf-8 -D -I -s 6668 20190125_AreaForecastLocalM_1saibun_GIS/一次細分区域等.shp > insert.sql
psql weather_forecast_map -f insert.sql
```
```sql
ALTER TABLE 一次細分区域等 RENAME TO districts;
```

---

# 4. RedisJSON セットアップ
## 4.1 標準インストール
```bash
sudo apt update
sudo apt install redis-server
```
