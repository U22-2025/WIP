# WTP Packet 移行ガイド

## 概要

このガイドは、既存のWTP_ClientとWTP_Serverプロジェクトを、新しい統合されたwtp-packetパッケージに移行する方法を説明します。

## パッケージのインストール

### 1. 開発モードでのインストール（推奨）

プロジェクトルートから：

```bash
cd wtp-packet
pip install -e .
```

### 2. 通常のインストール

```bash
cd wtp-packet
pip install .
```

## 移行手順

### 1. インポートの変更

既存のコード：
```python
# WTP_Client/clients/weather_client.py
from ..packet import Request, Response
```

新しいコード：
```python
# WTP_Client/clients/weather_client.py
from wtp_packet import Request, Response
```

### 2. 主な変更点

#### a. 統一されたExtendedFieldクラス

- `extended_field_mixin.py`は削除されました
- すべての拡張フィールド処理は`ExtendedField`クラスに統一されています

#### b. ex_fieldパラメータの柔軟性

新しいパッケージでは、ex_fieldパラメータは辞書またはExtendedFieldオブジェクトの両方を受け入れます：

```python
# 辞書での指定
request = Request(ex_field={'alert': ['警報']})

# ExtendedFieldオブジェクトでの指定
ex_field = ExtendedField({'alert': ['警報']})
request = Request(ex_field=ex_field)
```

#### c. ヘッダーサイズの統一

拡張フィールドのヘッダーサイズは16ビット（2バイト）に統一されています。

### 3. 移行チェックリスト

- [ ] wtp-packetパッケージをインストール
- [ ] すべてのインポート文を更新
- [ ] WTP_Client/packetディレクトリを削除（またはバックアップ）
- [ ] WTP_Server/packetディレクトリを削除（またはバックアップ）
- [ ] テストを実行して動作確認

### 4. 互換性の確認

移行後、以下のコマンドでテストを実行して互換性を確認してください：

```bash
cd wtp-packet
python -m pytest tests/ -v
```

## トラブルシューティング

### インポートエラー

もし`ModuleNotFoundError: No module named 'wtp_packet'`が発生した場合：

1. パッケージが正しくインストールされているか確認
2. Pythonパスが正しく設定されているか確認
3. 仮想環境を使用している場合、正しい環境がアクティブになっているか確認

### チェックサムエラー

新しいパッケージでは自動チェックサム計算が改善されています。
手動でチェックサムを設定していた箇所は削除してください。

## ベストプラクティス

1. **段階的な移行**: まず開発環境で移行を行い、十分なテストを実施してから本番環境に適用
2. **バックアップ**: 既存のpacketディレクトリはバックアップを取ってから削除
3. **テストの追加**: 移行後も互換性を保証するため、追加のテストケースを作成

## サポート

問題や質問がある場合は、プロジェクトのイシュートラッカーに報告してください。
