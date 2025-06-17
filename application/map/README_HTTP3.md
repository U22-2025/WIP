# HTTP/3対応 WTPマップサーバー

FlaskベースのWTPマップサーバーをHTTP/3対応に移行しました。

## 📋 概要

- **元のフレームワーク**: Flask (HTTP/1.1)
- **新しいフレームワーク**: Quart + Hypercorn (HTTP/3, HTTP/2, HTTP/1.1)
- **主な改善点**:
  - HTTP/3プロトコルサポート
  - 非同期処理による性能向上
  - 下位互換性（HTTP/2, HTTP/1.1もサポート）

## 🚀 クイックスタート

### 1. 自動セットアップ（推奨）

```bash
cd application/map
python start_http3_server.py
```

このスクリプトは以下を自動で行います：
- 依存関係のインストール
- SSL証明書の生成
- HTTP/3サーバーの起動

### 2. 手動セットアップ

#### 2.1 依存関係のインストール

```bash
# 必要なパッケージをインストール
pip install -r requirements_http3.txt

# または個別にインストール
pip install quart hypercorn[h3] geopy aioquic
```

#### 2.2 SSL証明書の生成

HTTP/3にはHTTPSが必要なため、開発用の自己署名証明書を生成します：

```bash
python generate_cert.py
```

#### 2.3 サーバー起動

```bash
python app_http3.py
```

## 🌐 アクセス方法

サーバー起動後、以下のURLでアクセスできます：

- **HTTPS (推奨)**: https://localhost:5000
- **HTTP**: http://localhost:5000 (SSL証明書がない場合)

### ブラウザでの証明書警告について

開発用の自己署名証明書を使用するため、ブラウザで「証明書が信頼できません」という警告が表示されます。

**Chrome/Edge**:
1. 「詳細設定」をクリック
2. 「localhost にアクセスする（安全ではありません）」をクリック

**Firefox**:
1. 「詳細設定」をクリック
2. 「危険性を承知で続行」をクリック

## 🔧 技術詳細

### 使用技術

| 技術 | バージョン | 用途 |
|------|------------|------|
| Quart | >=0.19.0 | ASGIウェブフレームワーク |
| Hypercorn | >=0.16.0 | HTTP/3対応ASGIサーバー |
| aioquic | >=0.9.20 | QUIC/HTTP3プロトコル実装 |
| geopy | >=2.3.0 | 地理情報処理 |

### プロトコルサポート

サーバーは以下のプロトコルをサポートします：

1. **HTTP/3** (優先) - QUIC over UDP
2. **HTTP/2** (フォールバック) - TCP with TLS
3. **HTTP/1.1** (フォールバック) - TCP with/without TLS

ブラウザは自動的に最適なプロトコルを選択します。

### 性能改善

HTTP/3移行により以下の改善が期待されます：

- **レイテンシ削減**: 0-RTT接続再開
- **パケットロス耐性**: QUIC の優れたエラー訂正
- **マルチプレキシング**: ヘッドオブライン・ブロッキングの解消
- **非同期処理**: 並列リクエスト処理による高いスループット

## 📁 ファイル構成

```
application/map/
├── app.py                  # 元のFlaskアプリケーション
├── app_http3.py           # HTTP/3対応Quartアプリケーション
├── start_http3_server.py  # 自動起動スクリプト
├── generate_cert.py       # SSL証明書生成スクリプト
├── requirements_http3.txt # HTTP/3用依存関係
├── README_HTTP3.md        # このファイル
├── cert.pem              # SSL証明書（生成後）
├── key.pem               # SSL秘密鍵（生成後）
├── templates/            # HTMLテンプレート
│   ├── map.html
│   └── weather_code.json
└── static/               # 静的ファイル
    ├── css/styles.css
    └── js/weather-app.js
```

## 🔍 API エンドポイント

元のFlaskアプリケーションと同じAPIエンドポイントを提供：

- `GET /` - メインマップページ
- `GET /weather_code.json` - 天気コード定義
- `POST /click` - 座標クリック時の天気・住所取得
- `POST /get_address` - 住所情報のみ取得
- `POST /weekly_forecast` - 週間天気予報取得

## 🐛 トラブルシューティング

### 依存関係のエラー

```bash
# パッケージが見つからない場合
pip install --upgrade pip
pip install -r requirements_http3.txt
```

### SSL証明書のエラー

```bash
# 証明書を再生成
python generate_cert.py
```

### OpenSSLが見つからない場合（Windows）

以下のいずれかの方法でOpenSSLをインストール：

1. **Git for Windows** (推奨)
2. **Win32/Win64 OpenSSL**: https://slproweb.com/products/Win32OpenSSL.html
3. **Chocolatey**: `choco install openssl`

### ポートが使用中の場合

別のポートを使用する場合は、`app_http3.py`の以下の行を変更：

```python
config.bind = ["localhost:5001"]  # ポート番号を変更
```

## 📈 性能監視

HTTP/3接続の確認方法：

1. **Chromeデベロッパーツール**:
   - F12 → Network → Protocol列で "h3" を確認

2. **コマンドライン**:
   ```bash
   curl --http3 https://localhost:5000 -v
   ```

## 🔒 セキュリティ注意事項

- 本実装は**開発用**です
- 本番環境では正式なSSL証明書を使用してください
- ファイアウォール設定を適切に行ってください

## 📞 サポート

問題や質問がある場合は、プロジェクトのIssueページまでお知らせください。
