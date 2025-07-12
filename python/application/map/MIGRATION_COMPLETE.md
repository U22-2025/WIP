# FastAPI 移行メモ

## ✅ 移行状況

**元のファイル**: `app.py` (Flask)
**新しいファイル**: `app_fastapi.py` (FastAPI + Uvicorn)

FastAPI 版への移行作業を進行中です。

## 📊 比較表

| 項目 | Flask版 (app.py) | FastAPI版 (app_fastapi.py) |
|------|------------------|----------------------------|
| **フレームワーク** | Flask | FastAPI |
| **サーバー** | Flask開発サーバー | Uvicorn |
| **プロトコル** | HTTP/1.1 | HTTP/1.1/HTTP/2 |
| **非同期サポート** | ❌ | ✅ |
| **起動方法** | `python app.py` | `uvicorn app_fastapi:app --reload` |
| **ポート** | 5000 | 5000 |
| **URL** | http://localhost:5000 | http://localhost:5000 |

## 🚀 起動方法

### 簡単起動
```bash
cd application/map
uvicorn app_fastapi:app --reload
```

### 手動インストール
```bash
cd application/map
pip install fastapi uvicorn geopy
uvicorn app_fastapi:app --reload
```

## 🎯 次のステップ

1. テスト整備と動作確認
2. パフォーマンス比較
3. 本番環境用設定の検討

**更新日**: 2025年6月4日
**担当者**: システム自動移行
**バージョン**: FastAPI版 1.0
