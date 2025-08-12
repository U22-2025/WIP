# Weather Data Flow Tests

APIから気象データ取得→レポートサーバー送信→Redis保存→クエリサーバー応答の全体フローをテストするテストスイートです。

## テストファイル概要

```
tests/
├── test_full_weather_flow.py   # 完全な統合テスト（自動サーバー起動）
├── simple_flow_test.py         # 簡単なフローテスト（既存サーバー使用）
├── run_flow_tests.sh          # テスト実行スクリプト
└── README_TESTS.md            # このファイル
```

## データフロー

```
[External API] → [weather_api_reporter.py] → [report_client.py] 
                                                     ↓
[Redis Database] ← [Report Server] ← [ReportRequest]
                                                     
[Redis Database] → [Query Server] → [QueryResponse] → [Client]
```

## 前提条件

### 必要なサービス

1. **Redis Server** (必須)
   ```bash
   # Redis起動
   redis-server
   
   # 動作確認
   redis-cli ping
   # PONG が返れば OK
   ```

2. **Python依存関係**
   ```bash
   pip install redis requests schedule
   ```

### サーバー起動（Simple Testの場合）

```bash
# Report Server起動
cd /mnt/c/Users/ポッポ焼き/Desktop/WIP
python -m WIPServerPy.servers.report_server.report_server

# Query Server起動 (別ターミナル)
python -m WIPServerPy.servers.query_server.query_server
```

## テスト実行方法

### 1. 簡単なフローテスト（推奨）

既に起動しているサーバーを使用してテストします：

```bash
cd /mnt/c/Users/ポッポ焼き/Desktop/WIP

# 基本実行
python tests/simple_flow_test.py

# カスタムポート指定
python tests/simple_flow_test.py --report-port 9999 --query-port 4111

# デバッグモード
python tests/simple_flow_test.py --debug
```

### 2. 完全な統合テスト

テスト専用サーバーを自動起動してテストします：

```bash
cd /mnt/c/Users/ポッポ焼き/Desktop/WIP

# 統合テスト実行
python -m pytest tests/test_full_weather_flow.py -v

# 特定のテストのみ実行
python -m pytest tests/test_full_weather_flow.py::FullWeatherFlowTest::test_01_basic_flow_single_city -v
```

### 3. 自動テストスクリプト

```bash
cd /mnt/c/Users/ポッポ焼き/Desktop/WIP

# 両方のテストを実行
bash tests/run_flow_tests.sh both

# 簡単なテストのみ
bash tests/run_flow_tests.sh simple

# 完全なテストのみ  
bash tests/run_flow_tests.sh full
```

## テスト内容詳細

### Simple Flow Test

1. **基本フロー**
   - 東京(130000)のダミー天気データ送信
   - Redis保存確認
   - クエリサーバーからの取得確認
   - データ整合性確認

2. **複数都市フロー**
   - 東京、大阪、札幌の複数データ送信
   - 各都市のデータ保存・取得確認

### Full Integration Test

1. **基本フロー** - 単一都市データの完全フロー
2. **複数都市フロー** - 複数都市の並行処理
3. **警報・災害情報フロー** - 拡張データの処理
4. **エラーハンドリング** - 無効データの適切な処理
5. **パフォーマンステスト** - 複数リクエストの性能確認

## 期待される出力例

### 成功時

```
🚀 Starting Flow Tests...
==================================================

🔄 Testing Basic Flow...
------------------------------
📤 Step 1: Sending data to Report Server...
✅ Data sent successfully
🗄️  Step 2: Checking data in Redis...
✅ Data found in Redis:
   Weather: 100
   Temperature: 25.5℃
   POP: 30%
🔍 Step 3: Querying data from Query Server...
✅ Query successful:
   Weather Code: 100
   Temperature: 25.5℃
   POP: 30%
✅ Data integrity confirmed!

📊 Test Results Summary:
==============================
Basic Flow: ✅ PASS
Multiple Cities: ✅ PASS

Overall: 2/2 tests passed (100.0%)

🎉 All tests passed! Data flow is working correctly.
```

### 失敗時

```
❌ Failed to send data to Report Server
💥 Some tests failed. Please check server status and logs.
```

## トラブルシューティング

### Redis接続エラー
```
❌ Redis connection failed: [Errno 111] Connection refused
💡 Please start Redis server before running tests
```
**解決方法**: `redis-server` コマンドでRedisを起動

### Report Server接続エラー
```
✗ Report Server is not running on port 9999
```
**解決方法**: Report Serverを起動
```bash
python -m WIPServerPy.servers.report_server.report_server
```

### Query Server接続エラー
```
✗ Query Server is not running on port 4111
```
**解決方法**: Query Serverを起動
```bash
python -m WIPServerPy.servers.query_server.query_server
```

### Pythonパスエラー
```
ModuleNotFoundError: No module named 'WIPCommonPy'
```
**解決方法**: PYTHONPATHを設定
```bash
export PYTHONPATH="/mnt/c/Users/ポッポ焼き/Desktop/WIP/src:$PYTHONPATH"
```

### ポート衝突
```
OSError: [Errno 98] Address already in use
```
**解決方法**: 
1. 既存プロセスを停止
2. 別のポートを使用
3. `--report-port` `--query-port` オプションで別ポート指定

## 高度な使用方法

### カスタムテストデータ

`simple_flow_test.py`を修正してカスタムテストデータを使用：

```python
# test_basic_flow メソッド内で修正
test_data = {
    "area_code": "270000",  # 大阪
    "weather_code": 300,    # 雨
    "temperature": 18.5,
    "precipitation_prob": 85,
    "alert": ["大雨警報"],
    "disaster": ["洪水注意報"]
}
```

### 継続実行テスト

```bash
# 10回連続実行してパフォーマンステスト
for i in {1..10}; do
    echo "Test run $i"
    python tests/simple_flow_test.py
    sleep 1
done
```

### デバッグモード

```bash
# 詳細ログ付きでテスト実行
python tests/simple_flow_test.py --debug
```

## テスト結果の確認

### Redis内容確認

```bash
# テストデータの確認
redis-cli keys "test_simple_*"
redis-cli get "test_simple_weather:130000"
```

### ログファイル確認

サーバーログを確認してエラーの詳細を調査：
- Report Server: コンソールに出力
- Query Server: コンソールに出力
- Redis: `/var/log/redis/redis-server.log` (設定により異なる)

## 注意事項

1. **テストプレフィックス**: テストデータは `test_` プレフィックス付きでRedisに保存され、テスト後に自動削除されます
2. **ポート競合**: 本番サーバーと異なるポートを使用してください
3. **データクリーンアップ**: テスト後は自動的にテストデータが削除されます
4. **認証無効化**: テスト時は認証が無効化されます