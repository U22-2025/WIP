# WIP Packet Library

Weather Transmission Protocol (WIP) パケットライブラリは、気象データ通信のためのコンパクトで拡張可能なパケットフォーマットを提供します。

## 📋 概要

WIPパケットは以下の特徴を持つ2層構造のプロトコルです：

- **基本フィールド**: 128ビット固定長の共通ヘッダー
- **拡張フィールド**: 可変長の追加データ領域
- **リトルエンディアン**: 効率的なビット操作
- **拡張性**: バージョン管理と後方互換性
- **柔軟な定義**: `format_spec` 配下のJSONファイルを編集するだけでフィールド構成を変更可能

## 🚀 クイックスタート

### 基本的な使用方法

```python
from common.packet import Format
from datetime import datetime

# 基本パケットの作成
packet = Format(
    version=1,
    packet_id=123,
    weather_flag=1,
    timestamp=int(datetime.now().timestamp()),
    area_code=13101  # 東京都千代田区
)

# バイト列への変換
data = packet.to_bytes()

# バイト列からの復元
restored_packet = Format.from_bytes(data)
```

### 拡張フィールド付きパケット

```python
# 警報情報付きパケット
alert_packet = Format(
    version=1,
    packet_id=456,
    ex_flag=1,  # 拡張フィールド有効
    timestamp=int(datetime.now().timestamp()),
    area_code=27100,  # 大阪府
    ex_field={
        'alert': ["津波警報", "大雨警報"],
        'latitude': 34.6937,
        'longitude': 135.5023
    }
)
```

## 📁 モジュール構成

```
common/packet/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── bit_utils.py
│   ├── exceptions.py
│   ├── extended_field.py
│   ├── format_base.py
│   ├── format_extended.py
│   └── format.py
├── models/
│   ├── __init__.py
│   ├── request.py
│   └── response.py
├── types/
│   ├── __init__.py
│   ├── location_packet.py
│   ├── query_packet.py
│   ├── report_packet.py
│   └── error_response.py
├── examples/
│   └── example_usage.py
└── docs/
    ├── README.md
    ├── PACKET_STRUCTURE.md
    └── HIERARCHY.md
```
```

## 🔧 メインクラス

### Format クラス

メインのパケットフォーマットクラス。基本フィールドと拡張フィールドの両方をサポート。

```python
from common.packet import Format

# 初期化
packet = Format(
    version=1,           # プロトコルバージョン (4bit)
    packet_id=123,       # パケットID (12bit)
    type=0,             # パケットタイプ (3bit)
    weather_flag=1,      # 天気フラグ (1bit)
    temperature_flag=0,  # 気温フラグ (1bit)
    pop_flag=0,        # 降水確率フラグ (1bit)
    alert_flag=0,       # 警報フラグ (1bit)
    disaster_flag=0,    # 災害フラグ (1bit)
    ex_flag=1,          # 拡張フィールドフラグ (1bit)
    day=0,              # 日数 (3bit)
    timestamp=1234567890, # タイムスタンプ (64bit)
    area_code=13101,    # エリアコード (20bit)
    checksum=0,         # チェックサム (12bit)
    ex_field={}         # 拡張フィールド辞書
)
```

### 特殊化パケット

特定用途に最適化されたパケットクラス：

```python
from common.packet import LocationRequest
from common.packet import QueryRequest

# 位置情報リクエスト
location = LocationRequest.create_coordinate_lookup(
    latitude=35.6895,
    longitude=139.6917,
    packet_id=1
)

# 気象データリクエスト
query = QueryRequest.create_query_request(
    area_code="13101",
    packet_id=2,
    weather=True,
    temperature=True
)
```

## 📊 拡張フィールド

拡張フィールドは`ex_flag=1`の場合に有効になり、以下のフィールドタイプをサポート：

| フィールド名 | キー | データ型 | 説明 |
|-------------|------|---------|------|
| `alert` | 1 | List[str] | 警報情報リスト |
| `disaster` | 2 | List[str] | 災害情報リスト |
| `latitude` | 33 | float | 緯度座標 |
| `longitude` | 34 | float | 経度座標 |
| `source` | 40 | str | 送信元情報 |

### 拡張フィールドの使用例 (新旧方式)

#### 新しいプロパティアクセス方式 (推奨)
```python
packet = Format(
    version=1,
    packet_id=789,
    ex_flag=1,
    timestamp=int(datetime.now().timestamp()),
    area_code=13101
)

# プロパティとして直接アクセス
packet.ex_field.alert = ["津波警報", "土砂災害警戒情報"]
packet.ex_field.disaster = ["土砂崩れ", "河川氾濫"]
packet.ex_field.latitude = 35.6895
packet.ex_field.longitude = 139.6917
packet.ex_field.source = "気象庁データセンター"
```

#### 旧方式 (非推奨)
```python
packet = Format(
    version=1,
    packet_id=789,
    ex_flag=1,
    timestamp=int(datetime.now().timestamp()),
    area_code=13101,
    ex_field={
        'alert': ["津波警報", "土砂災害警戒情報"],
        'disaster': ["土砂崩れ", "河川氾濫"],
        'latitude': 35.6895,
        'longitude': 139.6917,
        'source': "気象庁データセンター"
    }
)

# プロパティアクセス方式 (推奨)
packet.ex_field.alert = ["津波警報", "土砂災害警戒情報"]
alerts = packet.ex_field.alert
```

> **非推奨について**
> `.get()`/`.set()`メソッドは非推奨となり、将来のバージョンで削除される予定です。
> 新しいプロパティアクセス方式に移行してください。

## 🛠️ ユーティリティ

### デバッグツール

現在、デバッグ専用スクリプトは提供していません。

### ビット操作

```python
from common.packet.bit_utils import extract_bits, set_bits

# ビット抽出
value = extract_bits(data, position=0, length=4)

# ビット設定
result = set_bits(data, position=0, length=4, value=15)
```

### フィールド定義の再読み込み

`format_spec/` 以下の JSON を更新した後は、以下のように再読み込みを行います。

```python
from common.packet.core.format_base import FormatBase
from common.packet.models.request import Request

FormatBase.reload_field_spec("custom_request_fields.json")
Request.reload_request_spec()
```

`reload_field_spec()` だけでは可変長フィールドの開始位置が更新されません。必ず `Request.reload_request_spec()` を続けて呼び出してください。
フィールドを追加・変更した場合でも、上記の再読み込み処理を行うだけで`FormatBase`クラスに新しいプロパティが自動生成されます。
拡張フィールド定義も`reload_extended_spec()`を実行することで同様にプロパティが再生成されます。

## 🔍 Request/Response パターン

```python
from common.packet import Request
from common.packet import Response

# リクエストパケット
request = Request(
    packet_id=123,
    query_type="weather_forecast",
    area_code=13101
)

# レスポンスパケット
response = Response(
    packet_id=123,
    status=200,
    data={
        'weather': 'sunny',
        'temperature': 25.5
    }
)
```

## 📈 パフォーマンス

### パケットサイズ

| パケットタイプ | 基本サイズ | 拡張フィールド | 総サイズ |
|---------------|-----------|---------------|----------|
| 基本パケット | 16バイト | なし | 16バイト |
| 警報パケット | 16バイト | 28バイト | 44バイト |
| フルパケット | 16バイト | 112バイト | 128バイト |

### ビット効率

- **基本フィールド**: 128ビット固定
- **拡張ヘッダー**: レコードあたり16ビット
- **データ部分**: 最適化された可変長エンコード

## 🧪 テスト

```bash
# 使用例の確認
python -m common.packet.examples.example_usage
```

## 📝 使用例とベストプラクティス

### 1. 基本的な気象データ送信

```python
def send_weather_data(weather_code, temperature, area_code):
    packet = Format(
        version=1,
        packet_id=generate_packet_id(),
        weather_flag=1,
        temperature_flag=1,
        timestamp=int(datetime.now().timestamp()),
        area_code=area_code,
        ex_field={
            'weather_code': weather_code,
            'temperature': temperature
        }
    )
    return packet.to_bytes()
```

### 2. 警報システム

```python
def create_alert_packet(alerts, area_code):
    return Format(
        version=1,
        packet_id=generate_packet_id(),
        alert_flag=1,
        ex_flag=1,
        timestamp=int(datetime.now().timestamp()),
        area_code=area_code,
        ex_field={'alert': alerts}
    )
```

### 3. 位置ベースクエリ

```python
def query_weather_by_location(lat, lon):
    return Format(
        version=1,
        packet_id=generate_packet_id(),
        type=1,  # クエリタイプ
        ex_flag=1,
        timestamp=int(datetime.now().timestamp()),
        ex_field={
            'latitude': lat,
            'longitude': lon,
            'query_type': 'weather_by_location'
        }
    )
```

## 🔗 関連ドキュメント

- [PACKET_STRUCTURE.md](./PACKET_STRUCTURE.md) - 詳細なパケット構造仕様
- [example_usage.py](../examples/example_usage.py) - 実践的な使用例

## 📞 サポート

パケットフォーマットに関する質問や問題は、`example_usage.py` を参考に
パケット生成と解析方法を確認してください。

## 📄 ライセンス

このライブラリはWIPプロジェクトの一部として開発されています。
