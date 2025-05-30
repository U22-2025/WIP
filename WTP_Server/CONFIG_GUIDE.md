# WTPサーバー設定ガイド

## 概要

WTPサーバーは、各サーバーのディレクトリ内に配置された`config.ini`ファイルから設定を読み込みます。
設定ファイルは環境変数の展開をサポートしており、機密情報（パスワードなど）は環境変数で管理できます。

## 設定ファイルの場所

```
WTP_Server/servers/
├── weather_server/
│   └── config.ini
├── location_server/
│   └── config.ini
└── query_server/
    └── config.ini
```

## 設定ファイルの形式

INI形式を使用し、`${VARIABLE_NAME}`の形式で環境変数を参照できます。

### weather_server/config.ini

```ini
[server]
host = 0.0.0.0
port = ${WEATHER_SERVER_PORT}        # デフォルト: 4110
debug = ${WTP_DEBUG}                 # デフォルト: false
max_workers = 10

[connections]
location_server_host = ${LOCATION_RESOLVER_HOST}  # デフォルト: localhost
location_server_port = ${LOCATION_RESOLVER_PORT}  # デフォルト: 4109
query_server_host = ${QUERY_GENERATOR_HOST}       # デフォルト: localhost
query_server_port = ${QUERY_GENERATOR_PORT}       # デフォルト: 4111

[network]
udp_buffer_size = ${UDP_BUFFER_SIZE}  # デフォルト: 4096

[system]
protocol_version = ${PROTOCOL_VERSION}  # デフォルト: 1
```

### location_server/config.ini

```ini
[server]
host = 0.0.0.0
port = ${LOCATION_RESOLVER_PORT}     # デフォルト: 4109
debug = ${WTP_DEBUG}
max_workers = 10

[cache]
max_cache_size = ${MAX_CACHE_SIZE}   # デフォルト: 1000

[database]
host = ${DB_HOST}                    # デフォルト: localhost
port = ${DB_PORT}                    # デフォルト: 5432
name = ${DB_NAME}                    # デフォルト: weather_forecast_map
user = ${DB_USERNAME}                # デフォルト: postgres
password = ${DB_PASSWORD}            # 必須、デフォルトなし

[network]
udp_buffer_size = ${UDP_BUFFER_SIZE}

[system]
protocol_version = ${PROTOCOL_VERSION}
```

### query_server/config.ini

```ini
[server]
host = 0.0.0.0
port = ${QUERY_GENERATOR_PORT}       # デフォルト: 4111
debug = ${WTP_DEBUG}
max_workers = 10

[redis]
host = ${REDIS_HOST}                 # デフォルト: localhost
port = ${REDIS_PORT}                 # デフォルト: 6379
db = 0

[database]
weather_output_file = ${WEATHER_OUTPUT_FILE}  # デフォルト: wtp/resources/test.json

[network]
udp_buffer_size = ${UDP_BUFFER_SIZE}

[system]
protocol_version = ${PROTOCOL_VERSION}
```

## 環境変数

必要な環境変数は`.env`ファイルで管理できます：

```env
# データベース設定
DB_USERNAME=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=weather_forecast_map

# サーバー設定
LOCATION_RESOLVER_HOST=localhost
LOCATION_RESOLVER_PORT=4109
QUERY_GENERATOR_HOST=localhost
QUERY_GENERATOR_PORT=4111
WEATHER_SERVER_PORT=4110

# Redis設定
REDIS_HOST=localhost
REDIS_PORT=6379

# その他
WTP_DEBUG=false
PROTOCOL_VERSION=1
UDP_BUFFER_SIZE=4096
MAX_CACHE_SIZE=1000
WEATHER_OUTPUT_FILE=wtp/resources/test.json
```

## 使用方法

### デフォルト設定で起動

```python
from WTP_Server import WeatherServer

# config.iniから設定を読み込んで起動
server = WeatherServer()
server.run()
```

### 設定を上書きして起動

```python
from WTP_Server import WeatherServer

# 一部の設定を上書き
server = WeatherServer(
    host='0.0.0.0',
    port=5000,
    debug=True
)
server.run()
```

## 設定の優先順位

1. コンストラクタ引数（最優先）
2. config.iniファイル
3. デフォルト値（最後の手段）

## メリット

1. **環境別管理** - 開発/本番環境で異なる設定ファイルを使用可能
2. **機密情報の分離** - パスワードは環境変数で管理
3. **柔軟な設定** - サーバーごとに独立した設定が可能
4. **後方互換性** - 既存のコードは変更不要
