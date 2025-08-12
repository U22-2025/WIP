# JMA Weather API Integration Tests

JMAからの気象情報取得→レポートクライアント送信→Redis保存→フォワード処理の完全フローをテストするテストスイートです。

## データフロー

```
[JMA API] → [Weather API Server] → [Report Client] → [Report Server] → [Redis] 
                                                           ↓
                                              [Forward Server] (オプション)
```

## テストファイル概要

```
tests/
├── test_jma_full_integration.py   # 完全統合テスト（テスト用サーバー自動起動）
├── test_jma_api_simple.py         # 簡単統合テスト（既存サーバー使用）
├── run_jma_tests.bat             # Windows用テスト実行スクリプト
└── README_JMA_TESTS.md           # このファイル
```

## 前提条件

### 必要なサービス

1. **Redis Server** (必須)
   ```bash
   redis-server
   ```

2. **Weather API Server** (必須)
   ```bash
   cd python/application/weather_api
   python start_server.py
   ```

3. **Report Server** (必須)
   ```bash
   python -m WIPServerPy.servers.report_server.report_server
   ```

### Python依存関係
```bash
pip install requests redis fastapi uvicorn
```

## テスト実行方法

### 1. 簡単統合テスト（推奨）

既に起動しているサーバーを使用してテスト：

```bash
cd /mnt/c/Users/ポッポ焼き/Desktop/WIP

# 基本実行
python tests/test_jma_api_simple.py

# カスタムポート指定
python tests/test_jma_api_simple.py --api-port 8001 --report-port 9999

# デバッグモード
python tests/test_jma_api_simple.py --debug
```

### 2. 完全統合テスト

テスト専用サーバーを自動起動：

```bash
# 完全テスト実行
python -m pytest tests/test_jma_full_integration.py -v

# 特定のテストのみ
python -m pytest tests/test_jma_full_integration.py::JMAFullIntegrationTest::test_02_jma_data_fetch -v
```

### 3. Windows自動テストスクリプト

```cmd
cd C:\Users\ポッポ焼き\Desktop\WIP

# 簡単テスト
tests\run_jma_tests.bat simple

# 完全テスト
tests\run_jma_tests.bat full

# 両方のテスト
tests\run_jma_tests.bat both
```

## テスト内容詳細

### Simple Integration Test

1. **Weather API Server Health Check**
   - サーバーの起動確認
   - ヘルスエンドポイントの確認

2. **JMA Data Fetch Test**
   - JMAからの気象データ更新トリガー
   - 利用可能エリアの取得
   - サンプルエリアの気象データ取得

3. **Report Submission Test**
   - APIデータのレポート形式変換
   - ReportClientでの送信
   - 送信成功の確認

4. **Redis Storage Test**
   - Redis内のデータ保存確認
   - データ整合性確認

5. **Multiple Areas Test**
   - 複数エリアの一括処理テスト

### Full Integration Test

1. **Weather API Server Health**
2. **JMA Data Fetch**
3. **API to Report Flow**
4. **Disaster/Alert Data Flow**
5. **Forward Processing**
6. **End-to-End Integration**

## 期待される出力例

### 成功時

```
JMA Weather API Simple Tester
Weather API: localhost:8001
Report Server: localhost:9999
Redis Prefix: test_jma_api_
==================================================

📡 Testing JMA Data Fetch...
------------------------------
🔄 Triggering weather data update...
✅ Weather update: updated weather for 5 offices
✅ Found 45 areas
🎯 Testing area: 130000
✅ Weather data retrieved:
   Weather: [100, 200, 100]
   Temperature: ['25', '22', '27']
   POP: ['30', '60', '20']
   Warnings: 0 items
   Disasters: 0 items

📤 Testing Report Submission...
------------------------------
📊 Converted data:
   Area: 130000
   Weather Code: 100
   Temperature: 25.0
   POP: 30
✅ Report sent successfully
   Packet ID: 1234
   Response time: 145.2ms

🗄️ Testing Redis Storage...
------------------------------
✅ Data found in Redis for 130000:
   Weather: 100
   Temperature: 25.0
   POP: 30
   Warnings: 0 items
   Disasters: 0 items

📊 Test Results Summary:
==============================
JMA Data Fetch: ✅ PASS
Report Submission: ✅ PASS
Redis Storage: ✅ PASS
Multiple Areas (3/3): ✅ PASS

Overall: 4/4 tests passed (100.0%)

🎉 All tests passed! JMA integration is working correctly.

📋 Data flow confirmed:
   JMA → Weather API → Report Client → Report Server → Redis
```

### 失敗時

```
❌ Weather API Server is not running
💡 Start the server with: python python/application/weather_api/start_server.py
```

## トラブルシューティング

### Weather API Server接続エラー
```
❌ Weather API Server is not running
```
**解決方法**: Weather API Serverを起動
```bash
cd python/application/weather_api
python start_server.py
```

### JMAデータ取得タイムアウト
```
❌ Request timed out (JMA might be slow)
```
**解決方法**: 
- JMAサーバーの状況により時間がかかる場合があります
- しばらく待ってから再実行
- ネットワーク接続を確認

### Report Server接続エラー
```
❌ Report Server is not running
```
**解決方法**: Report Serverを起動
```bash
python -m WIPServerPy.servers.report_server.report_server
```

### Redis接続エラー
```
❌ Redis connection failed
```
**解決方法**: Redisサーバーを起動
```bash
redis-server
```

### データ変換エラー
```
❌ Report submission error: ... conversion failed
```
**解決方法**: 
- JMAデータ形式の変更に対応が必要な場合があります
- デバッグモードで詳細を確認
- データ型の確認と変換ロジックの調整

## 設定カスタマイズ

### 対象エリアの変更

Weather API Serverの環境変数で設定：

```bash
export WEATHER_API_TARGET_OFFICES="130000,270000,011000,400000"
python start_server.py
```

### フォワード処理の有効化

Report Serverの設定ファイルまたは環境変数：

```ini
[forwarding]
enable_client_forward = true
forward_host = localhost
forward_port = 19997
```

### テストデータプレフィックス

テストスクリプト内で変更：

```python
self.test_prefix = "my_test_prefix_"
```

## 高度な使用方法

### 特定エリアのみテスト

```python
# test_jma_api_simple.py を修正
test_areas = ["130000", "270000"]  # 東京、大阪のみ
```

### 継続監視テスト

```bash
# 10分おきに実行
while true; do
    python tests/test_jma_api_simple.py
    sleep 600
done
```

### パフォーマンステスト

```bash
# 複数回実行して平均時間測定
for i in {1..10}; do
    echo "Run $i"
    time python tests/test_jma_api_simple.py
done
```

## 注意事項

1. **JMA API制限**: 気象庁APIには利用制限があります。頻繁な実行は控えてください
2. **テストデータ**: テストデータは自動的にクリーンアップされます
3. **ネットワーク依存**: インターネット接続が必要です
4. **サーバー負荷**: 複数エリアテスト時はサーバー負荷に注意してください
5. **タイムアウト**: JMAサーバーの応答により時間がかかる場合があります

## ログ確認

### サーバーログ
- Weather API Server: コンソール出力
- Report Server: コンソール出力
- Redis: Redisログファイル

### テストログ
```bash
# デバッグモードでより詳細なログ
python tests/test_jma_api_simple.py --debug
```

### Redisデータ確認
```bash
# テスト後のデータ確認
redis-cli keys "test_jma_api_*"
redis-cli get "test_jma_api_weather:130000"
```