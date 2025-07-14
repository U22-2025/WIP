# 次世代気象情報マップアプリケーション

地図上の任意の場所をクリックしてリアルタイム気象情報を取得できる、次世代Webアプリケーションです。

## 🌟 主な機能

### 📍 インタラクティブ地図
- **クリック操作**: 地図上の任意の場所をクリックして気象情報を取得
- **リアルタイム表示**: 座標、住所、天気情報を即座に表示
- **レスポンシブデザイン**: PC・スマートフォン・タブレット対応

### 🌤️ 詳細な気象情報
- **現在の天気**: 天気コード、気温、降水確率
- **週間予報**: 7日間の詳細な天気予報
- **視覚的表示**: 天気アイコンとエフェクト付き
- **住所情報**: 逆ジオコーディングによる詳細な住所表示

### ⚡ 高性能・最新技術
- **HTTP/3対応**: 最新プロトコルによる高速通信
- **非同期処理**: 並列データ取得による高速レスポンス
- **PWA対応**: プログレッシブWebアプリ機能
- **アクセシビリティ**: スクリーンリーダー対応

## 🚀 クイックスタート

### 簡単起動（推奨）

```bash
cd application/map
python start_http3_server.py
python start_fastapi_server.py
```

### 手動起動

```bash
# 1. 依存関係をインストール
pip install -r requirements_http3.txt

# 2. SSL証明書を生成（HTTP/3用）
python generate_cert.py

# 3. サーバーを起動
python app_http3.py
```

### アクセス方法

- **HTTP/3対応**: https://localhost:5000
- **標準版**: http://localhost:5000 (app.pyを使用)

## 📁 プロジェクト構成

```
application/map/
├── app.py                    # Flask版メインアプリケーション
├── app_http3.py             # HTTP/3対応版（Quart）
├── fastapi_app.py           # FastAPI版アプリケーション
├── start_http3_server.py    # 自動セットアップ・起動スクリプト
├── start_fastapi_server.py  # FastAPI開発サーバー
├── generate_cert.py         # SSL証明書生成スクリプト
├── requirements_http3.txt   # HTTP/3用依存関係
├── README.md               # このファイル
├── README_HTTP3.md         # HTTP/3詳細ドキュメント
├── MIGRATION_COMPLETE.md   # HTTP/3移行報告書
├── cert.pem / key.pem     # SSL証明書（生成後）
├── templates/             # HTMLテンプレート
│   ├── map.html          # メインHTML
│   └── weather_code.json # 天気コード定義 (logs/json に配置)
└── static/               # 静的ファイル
    ├── css/
    │   ├── variables.css   # 変数定義
    │   ├── base.css        # ベーススタイル
    │   ├── components.css  # コンポーネントスタイル
    │   └── log-panel.css   # ログパネルスタイル
    └── js/
        └── weather-app.js # JavaScriptロジック
```

## 🔧 技術スタック

### バックエンド
- **Flask** (標準版) / **Quart** (HTTP/3版)
- **Hypercorn**: HTTP/3対応ASGIサーバー
- **WIP_Client**: 独自天気情報取得システム

### フロントエンド
- **Leaflet**: インタラクティブ地図ライブラリ
- **Font Awesome**: アイコンフォント
- **Progressive Web App**: PWA機能
- **レスポンシブデザイン**: モバイルファーストUI

### プロトコル・性能
- **HTTP/3 (QUIC)**: 最新高速プロトコル
- **HTTP/2**: フォールバック対応
- **SSL/TLS**: セキュア通信
- **非同期処理**: 並列データ取得

## 🌐 API エンドポイント

| エンドポイント | メソッド | 説明 |
|---------------|----------|------|
| `/` | GET | メインマップページ |
| `/weather_code.json` | GET | 天気コード定義 |
| `/weekly_forecast` | POST | 週間天気予報取得 |
| `/ws` | WebSocket | ログメッセージ購読 |

ログメッセージは JSON 形式で配信され、`level` フィールドには
`success`、`warning`、`error` のいずれかが設定されます。HTTP ステータス
コードに応じて分類されるため、クライアント側で容易に重要度を判別できます。

### リクエスト例

```javascript
// 週間天気予報の取得
fetch('/weekly_forecast', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        lat: 35.6762,
        lng: 139.6503
    })
})
.then(response => response.json())
.then(data => console.log(data));
```

### レスポンス例

```json
{
  "status": "ok",
  "coordinates": {
    "lat": 35.6762,
    "lng": 139.6503
  },
  "area_code": "130010",
  "weekly_forecast": [
    {
      "date": "2024-04-01",
      "day_of_week": "Monday",
      "weather_code": "100",
      "temperature": "22",
      "precipitation_prob": "10",
      "area_code": "130010",
      "day": 0
    },
    {
      "date": "2024-04-02",
      "day_of_week": "Tuesday",
      "weather_code": "101",
      "temperature": "21",
      "precipitation_prob": "20",
      "area_code": "130010",
      "day": 1
    }
  ]
}
```

## 💡 使用方法

### 基本操作

1. **地図表示**: ブラウザでアプリケーションにアクセス
2. **場所選択**: 地図上の任意の場所をクリック
3. **情報表示**: 右側のサイドバーに気象情報が表示
4. **週間予報**: 「週間予報を表示」ボタンで7日間の予報を確認

### モバイル対応

- **サイドバー切り替え**: ハンバーガーメニューでサイドバー表示/非表示
- **タッチ操作**: 地図のピンチズーム・パン操作対応
- **レスポンシブUI**: 画面サイズに応じたレイアウト調整

## 🏗️ 開発情報

### 依存関係

#### 標準版 (Flask)
```txt
flask>=2.3.0
requests>=2.31.0
```

#### HTTP/3版 (Quart)
```txt
quart>=0.19.0
hypercorn[h3]>=0.16.0
aioquic>=0.9.20
```

### 開発環境構築

```bash
# リポジトリクローン
git clone [repository-url]
cd application/map/

# 仮想環境作成（推奨）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係インストール
pip install -r requirements_http3.txt

# 開発サーバー起動
python start_http3_server.py
```

### カスタマイズ

#### 地図設定
`static/js/weather-app.js`で地図の初期設定を変更：

```javascript
// 初期表示位置
const initialLat = 35.6762;  // 緯度
const initialLng = 139.6503; // 経度
const initialZoom = 10;      // ズームレベル
```

#### スタイル変更
`static/css/` 配下の各CSSファイルでUI要素のスタイルをカスタマイズ可能

## 🔒 セキュリティ

### SSL証明書

HTTP/3には SSL/TLS が必須です：

- **開発用**: `generate_cert.py`で自己署名証明書を生成
- **本番用**: 正式なSSL証明書を使用してください

### ブラウザ警告

開発用自己署名証明書使用時：
1. 「詳細設定」をクリック
2. 「localhost にアクセスする（安全ではありません）」を選択

## 📊 性能情報

### HTTP/3の利点

- **低レイテンシ**: 0-RTT接続再開
- **パケットロス耐性**: QUIC プロトコルの優れたエラー訂正
- **多重化**: ヘッドオブライン・ブロッキングの解消
- **高スループット**: 並列リクエスト処理

### ベンチマーク目安

- **初期読み込み**: < 2秒
- **天気データ取得**: < 1秒
- **週間予報**: < 3秒（並列処理）

## 🐛 トラブルシューティング

### よくある問題

#### 依存関係エラー
```bash
pip install --upgrade pip
pip install -r requirements_http3.txt
```

#### SSL証明書エラー
```bash
python generate_cert.py
```

#### ポート使用中エラー
```python
# app_http3.py の設定を変更
config.bind = ["localhost:5001"]  # ポート番号変更
```

#### OpenSSL が見つからない（Windows）
1. Git for Windows のインストール
2. Win32/Win64 OpenSSL のインストール
3. Chocolatey: `choco install openssl`

### デバッグモード

```python
# app.py または app_http3.py
app.run(debug=True)  # Flask版
# または Quart版でデバッグログ有効化
```

## 🤝 コントリビューション

### 開発参加

1. フォーク
2. フィーチャーブランチ作成
3. 変更をコミット
4. プルリクエスト作成

### 報告・要望

- バグ報告: Issue で報告
- 機能要望: Issue で提案
- 質問: Discussions で質問

## 📜 ライセンス

このプロジェクトは [LICENSE] の下で公開されています。

## 🔗 関連リンク

- **WIPプロトコル仕様**: `../../WIP仕様表.md`
- **サーバーサイド**: `../../WIP_Server/`
- **クライアントライブラリ**: `../../WIP_Client/`
- **パケット処理**: `../../common/packet/`

---

**開発者**: WIPチーム  
**最終更新**: 2025年6月4日  
**バージョン**: HTTP/3対応版 1.0
