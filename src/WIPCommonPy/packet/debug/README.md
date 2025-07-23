# パケットデバッグログの改善

## 概要

各クライアント（`query_client.py`, `weather_client.py`, `location_client.py`, `report_client.py`）で重複していたデバッグログ機能を共通化し、ログの量を重要な情報のみに簡略化しました。

## 主な改善点

### 1. 冗長なログの削除

**改善前**:
- 詳細なhexダンプ表示
- ビット列の詳細表示
- 生のパケットバイナリデータ
- 冗長なヘッダー情報

**改善後**:
- パケットタイプと操作名のみ
- 重要なデータフィールドのみ
- 簡潔なサマリー情報
- パケットサイズのみ（詳細なhexダンプは削除）

### 2. コードの集約化

**改善前**:
```python
# 各クライアントで重複していたコード
def _hex_dump(self, data):
    """バイナリデータのhexダンプを作成"""
    hex_str = ' '.join(f'{b:02x}' for b in data)
    ascii_str = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in data)
    return f"Hex: {hex_str}\nASCII: {ascii_str}"

def _debug_print_request(self, request, request_type):
    """リクエストのデバッグ情報を出力（改良版）"""
    self.logger.debug("\n=== SENDING REQUEST PACKET ===")
    # 30行以上の冗長なログ出力...
```

**改善後**:
```python
# 共通のデバッグロガーを使用
from ..packet.debug import create_debug_logger

self.debug_logger = create_debug_logger(__name__, debug)
self.debug_logger.log_request(request, "QUERY REQUEST")
```

### 3. ログ出力例の比較

**改善前のログ出力**:
```
=== SENDING QUERY REQUEST PACKET ===
Total Length: 64 bytes
Area Code: 011000
Requested Data: {'weather': True, 'temperature': True, 'precipitation_prob': True}
Source: ('127.0.0.1', 9999)

Raw Packet:
Hex: 01 00 02 00 a4 12 00 00 67 2b 5e 00 b0 ae 01 00 64 00 00 07 00 00 00 00 00 00 00 00 00 00 00 00
ASCII: ........g+^.....d...................

Header:
Version: 1
Type: 2
Packet ID: 4772
Timestamp: Mon Jul  8 18:15:51 2025
Area Code: 011000

Flags:
Weather: True
Temperature: True
pop: True
Alert: False
Disaster: False
============================
```

**改善後のログ出力**:
```
=== QUERY REQUEST ===
Type: Query Request (2)
Packet ID: 4772
Request: Area Code: 011000
Data Requested: Weather, Temperature, Precipitation
Packet Size: 64 bytes
==============================
```

## 使用方法

### 基本的な使用方法

```python
from WIPCommonPy.packet.debug import create_debug_logger

# デバッグロガーの作成
debug_logger = create_debug_logger(__name__, debug_enabled=True)

# リクエストログ
debug_logger.log_request(request_packet, "CUSTOM REQUEST")

# レスポンスログ
debug_logger.log_response(response_packet, "CUSTOM RESPONSE")

# タイミング情報
debug_logger.log_timing("OPERATION NAME", {
    'total_time': 123.45,
    'network_roundtrip': 89.01,
    'cache_hit': False
})

# キャッシュ操作
debug_logger.log_cache_operation("hit", "cache_key", True)

# エラーログ
debug_logger.log_error("エラーメッセージ", "ERROR_CODE")

# 成功時の結果表示（非デバッグモードでも表示）
debug_logger.log_success_result(result_dict, "OPERATION NAME")
```

### クライアントでの実装例

```python
class QueryClient:
    def __init__(self, debug=False):
        self.debug_logger = create_debug_logger(__name__, debug)
    
    def get_weather_data(self, area_code):
        # リクエスト送信前
        self.debug_logger.log_request(request, "WEATHER DATA REQUEST")
        
        # レスポンス受信後
        self.debug_logger.log_response(response, "WEATHER DATA RESPONSE")
        
        # タイミング情報
        self.debug_logger.log_timing("WEATHER OPERATION", timing_info)
        
        # 成功時の結果表示
        if 'error' not in result:
            self.debug_logger.log_success_result(result, "WEATHER DATA OPERATION")
```

## 追加機能: 成功時の結果表示統合

### 新機能: `log_success_result()`

成功時のパケット内容表示も共通ロガーに統合しました。この機能により、各クライアントで重複していた成功時の結果表示コードが削除され、統一された形式で結果が表示されます。

**改善前（各クライアントで重複）**:
```python
if 'error' not in result:
    logger.info("✓ Request successful!")
    logger.info(f"Area Code: {result.get('area_code')}")
    logger.info(f"Weather Code: {result.get('weather_code')}")
    logger.info(f"Temperature: {result.get('temperature')}°C")
    logger.info(f"precipitation_prob: {result.get('precipitation_prob')}%")
    if result.get('alert'):
        logger.info(f"Alert: {result.get('alert')}")
    if result.get('disaster'):
        logger.info(f"Disaster Info: {result.get('disaster')}")
```

**改善後（共通ロガー使用）**:
```python
if 'error' not in result:
    client.debug_logger.log_success_result(result, "OPERATION NAME")
```

### 表示される情報

- ✓ 操作成功メッセージ
- エリアコード
- タイムスタンプ（利用可能な場合）
- 気象コード
- 気温（℃）
- 降水確率（%）
- 警報情報（存在する場合）
- 災害情報（存在する場合）
- キャッシュ情報（キャッシュヒットの場合）
- レスポンス時間

## 削減されたログ量

- **hexダンプ**: 完全に削除（約50-100行削減）
- **詳細ヘッダー情報**: 重要な項目のみに簡略化（約20行削減）
- **フラグ情報**: 有効なフラグのみを1行で表示（約10行削減）
- **生バイナリデータ**: 削除（約30行削減）
- **成功時の結果表示**: 統一された共通ロガーに集約（約10-15行削減）

**全体として、1回のリクエスト/レスポンスペアで約100-200行のログが5-10行程度に簡略化されました。**

## ファイル構造

```
WIPCommonPy/packet/debug/
├── __init__.py           # デバッグモジュールのエントリポイント
├── debug_logger.py       # PacketDebugLoggerクラスの実装
└── README.md            # このファイル
```

## 影響を受けるファイル

- `WIPCommonPy/clients/query_client.py` - 更新済み
- `WIPCommonPy/clients/weather_client.py` - 更新済み
- `WIPCommonPy/clients/location_client.py` - 更新済み
- `WIPCommonPy/clients/report_client.py` - 更新済み
- `WIPCommonPy/packet/__init__.py` - デバッグ機能をエクスポート

## 後方互換性

- 既存のAPIは変更されていません
- デバッグ機能は完全に新しい実装に置き換えられましたが、外部から見える動作は同じです
- 環境変数やデバッグフラグの動作は変更されていません