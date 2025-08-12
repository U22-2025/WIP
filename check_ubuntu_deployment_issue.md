# Ubuntu サーバーでの QueryServer XML自動取得問題 診断・解決ガイド

## 問題の概要
Ubuntuサーバー上で`get-data-from-api`ブランチをデプロイすると、QueryServer起動時に古い仕様のXML自動取得処理が実行されてしまう問題。

## 現在の正しい実装状態
✅ ローカル環境の`get-data-from-api`ブランチでは、QueryServerからXML自動取得処理は**完全に削除済み**
✅ QueryServerは読み取り専用サーバーとして実装されている
✅ `noupdate=True`パラメータが利用可能

## 考えられる原因

### 1. ブランチの同期問題
```bash
# Ubuntuサーバーで実行して確認
git branch --show-current  # get-data-from-apiになっているか
git status                # 未コミットの変更があるか
git log --oneline -5      # 最新コミットが反映されているか
```

### 2. ファイルキャッシュ問題
```bash
# Pythonバイトコードキャッシュをクリア
find . -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
```

### 3. 古いプロセスが動作中
```bash
# QueryServerプロセスを確認・停止
ps aux | grep -i query
# 必要に応じてkill <PID>

# ポート使用状況確認
lsof -i :4111  # デフォルトのQueryServerポート
```

### 4. 間違った実装ファイルを参照
```bash
# QueryServerファイルの場所と内容確認
find . -name "query_server.py" -type f
grep -n "update.*weather\|xml\|schedule" src/WIPServerPy/servers/query_server/query_server.py
```

## 解決手順

### Step 1: 環境の完全確認
```bash
cd /path/to/WIP/project
pwd
git branch --show-current
git pull origin get-data-from-api
```

### Step 2: QueryServer実装の確認
```bash
# XML/Update関連処理が残っていないか確認
grep -rn "update.*weather\|xml\|schedule\|災害\|警報" src/WIPServerPy/servers/query_server/
```

### Step 3: キャッシュとプロセスのクリア
```bash
# Pythonキャッシュクリア
find . -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# 古いQueryServerプロセス停止
pkill -f query_server
```

### Step 4: 正しい起動方法
```bash
# noupdateパラメータを明示的に指定して起動
python -m WIPServerPy.servers.query_server.query_server --noupdate
```

または

```python
from WIPServerPy.servers.query_server.query_server import QueryServer

# noupdateを明示的にTrueに設定
server = QueryServer(
    host="0.0.0.0",
    port=4111,
    debug=True,
    noupdate=True  # 重要: 自動更新を無効化
)
server.run()
```

## 確認用QueryServer実装チェックスクリプト

以下の内容をUbuntuサーバー上で実行してください：

```python
#!/usr/bin/env python3
import sys
import inspect
from pathlib import Path

# プロジェクトパスを設定
sys.path.insert(0, '/path/to/your/WIP/src')

try:
    from WIPServerPy.servers.query_server.query_server import QueryServer
    
    print("QueryServer インポート成功")
    print(f"ファイル位置: {inspect.getfile(QueryServer)}")
    
    # __init__シグネチャチェック
    sig = inspect.signature(QueryServer.__init__)
    print(f"__init__ シグネチャ: {sig}")
    
    if 'noupdate' in str(sig):
        print("✅ 'noupdate'パラメータが存在 - 新しい実装")
    else:
        print("❌ 'noupdate'パラメータなし - 古い実装の可能性")
    
    # 危険なメソッド/属性をチェック
    dangerous_methods = []
    for attr in dir(QueryServer):
        if any(keyword in attr.lower() for keyword in 
               ['update', 'xml', 'schedule', 'thread', 'disaster', 'alert']):
            dangerous_methods.append(attr)
    
    if dangerous_methods:
        print(f"⚠️  以下のメソッド/属性が見つかりました: {dangerous_methods}")
    else:
        print("✅ XML/Update関連のメソッドは見つかりませんでした")

except Exception as e:
    print(f"エラー: {e}")
```

## 最終確認事項

1. **ブランチ確認**: `git branch --show-current` で `get-data-from-api` であること
2. **最新取得**: `git pull origin get-data-from-api` で最新版取得
3. **ファイル確認**: QueryServerファイルにXML処理が含まれていないこと
4. **起動パラメータ**: `noupdate=True` を明示的に指定
5. **プロセス確認**: 古いQueryServerプロセスが残っていないこと

## 追加のデバッグ手順

もし問題が継続する場合:

1. QueryServerの起動ログを詳細に確認
2. 実際に動作しているファイルパスを特定
3. 環境変数の設定を確認
4. 依存関係(dateutil等)を解決

これらの手順により、Ubuntuサーバーでも正しくQueryServerが読み取り専用として動作するはずです。