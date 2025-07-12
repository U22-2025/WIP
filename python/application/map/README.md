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

### 簡単起動（FastAPI 版）

```bash
cd application/map
uvicorn app_fastapi:app --reload
```

### 手動起動

```bash
# 1. 依存関係をインストール
pip install fastapi uvicorn geopy

# 2. サーバーを起動
uvicorn app_fastapi:app --reload
```

## 🔄 FastAPI への移行手順

1. `app_fastapi.py` を追加し、Flask で実装していた API を FastAPI 形式に書き換えます。
2. 既存のテンプレートや静的ファイルはそのまま利用できます。
3. `uvicorn` を使ってサーバーを起動し、動作確認を行います。
4. 動作が安定したら不要になった Flask 版を段階的に廃止します。

### アクセス方法

- **FastAPI版**: http://localhost:5000
- **Flask版**: http://localhost:5000 (app.py)

## 📁 プロジェクト構成

```
application/map/
├── app.py              # Flask版メインアプリケーション
├── app_fastapi.py      # FastAPI版アプリケーション
├── generate_cert.py    # SSL証明書生成スクリプト（任意）
├── README.md           # このファイル
├── MIGRATION_COMPLETE.md   # FastAPI移行報告書
├── cert.pem / key.pem     # SSL証明書（生成後）
├── templates/             # HTMLテンプレート
│   ├── map.html          # メインHTML
│   └── weather_code.json # 天気コード定義
└── static/               # 静的ファイル
    ├── css/
    │   └── styles.css    # メインスタイルシート
    └── js/
        └── weather-app.js # JavaScriptロジック
```

## 🔧 技術スタック

### バックエンド
- **Flask** (従来版) / **FastAPI** (新バージョン)
- **Uvicorn**: ASGIサーバー
- **geopy**: 地理情報処理・逆ジオコーディング
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
| `/click` | POST | 座標クリック時の天気・住所取得 |
| `/get_address` | POST | 住所情報のみ取得 |
| `/weekly_forecast` | POST | 週間天気予報取得 |

### リクエスト例

```javascript
// 座標クリック時の天気情報取得
fetch('/click', {
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
  "weather": {
    "weather_code": "100",
    "temperature": "22",
    "precipitation_prob": "10",
    "area_code": "130010"
  },
  "address": {
    "full_address": "日本, 東京都千代田区",
    "prefecture": "東京都",
    "city": "千代田区",
    "country": "日本"
  }
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
geopy>=2.3.0
requests>=2.31.0
```

#### FastAPI版
```txt
fastapi>=0.110.0
uvicorn>=0.29.0
geopy>=2.3.0
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
pip install fastapi uvicorn geopy

# 開発サーバー起動
uvicorn app_fastapi:app --reload
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
`static/css/styles.css`でUI要素のスタイルをカスタマイズ可能

## 🔒 セキュリティ

### SSL証明書

開発用でも本番用でも SSL/TLS を利用できます：

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
pip install fastapi uvicorn geopy
```

#### SSL証明書エラー
```bash
python generate_cert.py
```

#### ポート使用中エラー
```python
# uvicorn 起動コマンドのポートを変更
uvicorn app_fastapi:app --port 5001 --reload
```

#### OpenSSL が見つからない（Windows）
1. Git for Windows のインストール
2. Win32/Win64 OpenSSL のインストール
3. Chocolatey: `choco install openssl`

### デバッグモード

```python
# app.py でデバッグ実行
app.run(debug=True)
# FastAPI 版
uvicorn app_fastapi:app --reload
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
**バージョン**: FastAPI版 1.0
