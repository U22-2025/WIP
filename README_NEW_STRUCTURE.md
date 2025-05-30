# WTP プロジェクト構造（新構造）

## 概要
WTPプロジェクトは、共通ライブラリを使用した構造に再編成されました。
これにより、クライアントとサーバー間でコードの重複を避け、メンテナンスが容易になります。

## ディレクトリ構造

```
WTP/
├── common/                 # 共通ライブラリ
│   ├── __init__.py
│   ├── packet/            # パケット処理（統合済み）
│   │   ├── __init__.py
│   │   ├── exceptions.py
│   │   ├── bit_utils.py
│   │   ├── extended_field.py
│   │   ├── format_base.py
│   │   ├── format_extended.py
│   │   ├── format.py
│   │   ├── request.py
│   │   └── response.py
│   ├── clients/           # 共通クライアント実装
│   │   ├── __init__.py
│   │   ├── location_client.py
│   │   ├── query_client.py
│   │   ├── weather_client.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── packet_id_generator.py
│   └── utils/             # 共通ユーティリティ
│       ├── __init__.py
│       └── debug.py
│
├── WTP_Client/            # クライアント固有の実装（削除予定）
│   └── （古い構造、移行後削除）
│
├── WTP_Server/            # サーバー固有の実装
│   ├── servers/           # 各種サーバー実装
│   ├── data/              # サーバー固有のデータ処理
│   ├── scripts/           # サーバー管理スクリプト
│   └── utils/             # サーバー固有のユーティリティ
│       └── config_loader.py
│
├── client.py              # クライアントのエントリーポイント
├── server.py              # サーバーのエントリーポイント
└── start_servers.bat      # サーバー起動スクリプト
```

## 使用方法

### クライアントの実行
```bash
python client.py
```

### サーバーの実行
```bash
python start_servers.bat
# または個別に
python -m WTP_Server.servers.location_server.location_server
python -m WTP_Server.servers.weather_server.weather_server
python -m WTP_Server.servers.query_server.query_server
```

## インポートの例

### クライアント側（client.py）
```python
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from common.clients.weather_client import WeatherClient
from common.packet import Request, Response
```

### サーバー側（WTP_Server内）
```python
import sys
import os
# WTP_Serverの親ディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.packet import Request, Response, BitFieldError
from common.clients.location_client import LocationClient
```

## 移行の利点

1. **コードの重複削除**: パケット処理とクライアントコードが統一
2. **メンテナンスの簡素化**: 一箇所の変更で全体に反映
3. **GitHubでの配布が簡単**: 追加のインストール手順が不要
4. **明確な責任分離**: 共通部分とサーバー/クライアント固有部分が明確

## 今後の作業

1. WTP_Server内のインポートを更新
2. WTP_Client/とWTP_Server/packet/を削除
3. テストの実行と動作確認
