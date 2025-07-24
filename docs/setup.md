リポジトリのクローン
git clone https://github.com/U22-2025/WIP.git

ubuntu22.04をインストール

postgreSQLのセットアップ
sudo apt install postgresql postgresql-contrib
sudo -u postgres psql
*ユーザの追加

create database weather_forecast_map owner bababa;
quit
psql -U bababa -d weather_forecast_map
sudo apt install postgis postgresql-14-postgis-3
sudo -u postgres psql -d weather_forecast_map
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
shp2pgsql -W utf-8 -D -I -s 6668 20190125_AreaForecastLocalM_1saibun_GIS/一次細分区域等.shp > insert.sql
psql weather_forecast_map
\i insert.sql
ALTER TABLE 一次細分区域等 RENAME TO districts;


redisJSONのセットアップ
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/redis.gpg
echo "deb https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt install redis-stack-server