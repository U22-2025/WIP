ubuntu22.04, 24.04をインストール
リポジトリのクローンを行う
```
$ git clone https://github.com/U22-2025/WIP.git
```

postgreSQLのセットアップ
```
$ sudo apt install postgresql postgresql-contrib
```
postgreSQLのスーパーユーザ権限でログイン
```
$ sudo -u postgres psql

```
DBにユーザを追加
```
> create user bababa;
```

DBの作成
```
> create database weather_forecast_map owner bababa;
```
DBから抜け出して、ユーザ権限でDBにアクセスできることを確認。
```
> quit
$ psql -U bababa -d weather_forecast_map
```
PostGISのインストール
psqlのバージョンを確認し、それに応じたバージョン番号を入れる。
```
$ psql --version
psql (PostgreSQL) 16.9 (Ubuntu 16.9-0ubuntu0.24.04.1)

sudo apt install postgis postgresql-16-postgis-3
(( sudo apt install postgis postgresql-{psqlのバージョン番号}-postgis-3 ))
```
スーパーユーザ権限で再度DBへ入り、PostGISをインストール
```
$ sudo -u postgres psql -d weather_forecast_map
> CREATE EXTENSION postgis;
> CREATE EXTENSION postgis_topology;
```
気象庁の[GISデータ](https://www.data.jma.go.jp/developer/gis/20190125_AreaForecastLocalM_1saibun_GIS.zip)をダウンロードし、SQLファイルを作成＆インポート。
```
$ shp2pgsql -W utf-8 -D -I -s 6668 20190125_AreaForecastLocalM_1saibun_GIS/一次細分区域等.shp > insert.sql
$ psql weather_forecast_map

> \i insert.sql
```
テーブル名がエラーを起こしそうなので変更しておく。
```
> ALTER TABLE 一次細分区域等 RENAME TO districts;
```


redisJSONのセットアップ
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/redis.gpg
echo "deb https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt install redis-stack-server