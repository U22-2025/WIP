# C++ WIP Client ↔ Python WIP Client 互換性監査レポート

本レポートは、本リポジトリ内の C++ 版クライアント（`cpp/`）と Python 版クライアント（`src/WIPClientPy/`, `src/WIPCommonPy/`）の機能互換性を網羅的に確認した結果をまとめたものです。対象はクライアント API、CLI、パケット仕様、認証、環境変数・設定、エラーハンドリング等です。

## 結論サマリー
- 互換性の到達度: 高い（主要機能は同等に利用可能）
- 要対応/調査事項: 小〜中の差分が数点あり（下記に列挙）

主な差分（修正提案・調査推奨）
- area_code のゼロ詰め出力（C++/proxy・座標→エリア変換経路の一部で6桁ゼロ詰めされない可能性）
- 直接接続(direct)時の Location/Query エンドポイントの環境変数反映（C++は固定デフォルト127.0.0.1で `.env` 未反映）
- Python 側にあるキャッシュ（座標・クエリ）の厳密な動作差（C++側は未実装）

---

## チェック対象と概観
- Weather 取得系
  - 高水準 `Client`（Python: `WIPClientPy.Client` / C++: `wiplib::client::Client`）
  - Proxy（Weather Server/4110）と Direct（Location/4109 → Query/4111）両モード
  - 座標/エリアコード指定、day/各種フラグ（weather/temperature/precipitation/alert/disaster）
- Report 送信系
  - Python: `WIPCommonPy.clients.report_client.ReportClient`
  - C++: `wiplib::client::ReportClient`（`Client` 経由でも送信可能）
  - 直接（Report/4112）および Proxy（Weather/4110 経由）の両方
- 認証
  - 各サービス向け `*_REQUEST_AUTH_ENABLED` と `*_SERVER_PASSPHRASE` の扱い
  - レスポンス検証（C++は追加で `WIP_CLIENT_VERIFY_RESPONSE_AUTH` をサポート）
- CLI
  - Python: `python/client.py`
  - C++: `cpp/tools/unified_client_cli.cpp`（weather / report 両モードに対応）

---

## 機能別の互換性結果

### API（高水準クライアント）
- C++ `wiplib::client::Client` は Python `WIPClientPy.Client` と同等のメソッド群を提供:
  - `set_coordinates(lat, lon)` / `set_area_code(code)`
  - `get_weather(...)` / `get_weather_by_coordinates(...)` / `get_weather_by_area_code(...)`
  - Report 用の `set_sensor_data(...)`, `send_report_data(...)` 等
- 動作差分/注意:
  - 返り値表現: Python は `dict`/`None`/`{"type":"error", ...}`、C++ は `Result<T>`（成功/エラーを型で表現）。設計上の言語差で互換性には問題なし。
  - 温度値: パケット内部 +100 → 表示/返却は摂氏へ変換。両実装で整合。
  - area_code の表現: Python は常に6桁文字列。C++は direct 経路では6桁ゼロ詰め済みだが、proxy+座標経路で `std::to_string()` によるゼロ詰め欠落の可能性（要修正。詳細は「修正提案1」）。

### Weather 取得（Proxy/Direct）
- Proxy（Weather/4110）: 双方とも対応。C++は `Client`/`WipClient` が `WeatherClient` に委譲。
- Direct（Location/4109 → Query/4111）: 双方対応。
  - Python は `LOCATION_RESOLVER_HOST/PORT`, `QUERY_GENERATOR_HOST/PORT` から接続先を解決。
  - C++ は `WipClient` のデフォルトが `127.0.0.1:4109/4111` 固定で、`.env` からの上書きを現状行っていない（要改善。詳細は「修正提案2」）。
- day/flags（weather/temperature/precipitation_prob/alert/disaster）: 双方で同機能・同フラグ名（C++内部は `alerts`/`disaster` として受けるが対応済み）。

### Report 送信
- API 互換: フィールド（area_code, weather_code, temperature, precipitation_prob, alert[], disaster[]）は同等。
- 経路: 直接(4112) と Proxy(4110 経由) の両方を Python/C++ がサポート。
- 応答: Python は `dict`（ACK/エラー）、C++ は `Result<ReportResult>`。意味的に等価。

### 認証
- サービス別の有効化/パスフレーズ
  - 環境変数は Python/C++ とも以下を利用：
    - `WEATHER_SERVER_REQUEST_AUTH_ENABLED`, `WEATHER_SERVER_PASSPHRASE`
    - `LOCATION_RESOLVER_REQUEST_AUTH_ENABLED`, `LOCATION_SERVER_PASSPHRASE`
    - `QUERY_GENERATOR_REQUEST_AUTH_ENABLED`, `QUERY_SERVER_PASSPHRASE`
    - `REPORT_SERVER_REQUEST_AUTH_ENABLED`, `REPORT_SERVER_PASSPHRASE`
  - C++ の `AuthConfig::from_env()` は上記を取り込み、`enabled` を自動集約。
- レスポンス検証
  - C++ のみ `WIP_CLIENT_VERIFY_RESPONSE_AUTH` をサポート（任意）。Python 側で明示的な同等機能は見当たらず（差分だが後方互換性は阻害しない）。

### 環境変数/設定
- Python は `.env` を `dotenv` で読込。
- C++ は `AuthConfig::from_env()` 実行時に `.env` を上位3階層まで自動読込（既存環境は上書きしない）。
- 差分:
  - Direct 経路の Location/Query の host/port について、Python は `.env` 反映、C++ は現状固定（修正提案2）。
  - Report の host/port は Python 同様に C++ 側も `.env` 反映済み（`Client::initialize_report_client`）。

### キャッシュ
- Python:
  - Location: 永続座標キャッシュ（`coordinate_cache.json`）
  - Query: メモリキャッシュ
- C++: キャッシュ未実装（機能差）。API 観点の互換性には直接影響しないが、挙動（応答時間/負荷）差は生じ得る。

### タイムアウト/エラー
- 受信タイムアウト: 双方10秒（C++ は 500ms×リトライで合計10秒相当）。
- 例外/エラー伝搬: Python はログ+None/辞書、C++ は `Result<T>` によるエラーコード返却。意味は同等。

### CLI
- Python: `python/client.py`
  - `--coord`, `--area`, `--proxy`, `--debug`, `--report`, `--temp`, `--pops`, `--alert`, `--disaster`, `--lat`, `--lon` 等
- C++: `unified_client_cli`（weather / report モード）
  - 対応オプションは概ね同等。認証系 `--auth-*` も追加でサポート。

---

## 修正提案 / 追加調査

### 修正提案1: area_code の6桁ゼロ詰め不統一（C++/Proxy/座標経路）
- 事象: `WipClient::get_weather_by_coordinates(..., proxy=true)` の経路で、`area_code` が数値→`std::to_string()` によりゼロ詰めされず返却される可能性。
- 期待: Python と同様、常に6桁ゼロ詰めの文字列（例: `"011000"`）。
- 対応案: `cpp/src/client/wip_client.cpp` 内、`get_weather_by_coordinates`/`get_weather_by_area_code` の `proxy` 分岐で `area_code` を `std::snprintf("%06u")` 等に統一。

### 修正提案2: Direct 経路の Location/Query エンドポイントに `.env` を反映
- 事象: C++ `WipClient` は `location_host_="127.0.0.1"`, `query_host_="127.0.0.1"` 固定。Python は `LOCATION_RESOLVER_HOST/PORT`, `QUERY_GENERATOR_HOST/PORT` を `.env` から読込。
- 期待: C++ も `.env` の内容を既定値として反映し、互換の利便性を向上。
- 対応案: `WipClient` コンストラクタで `AuthConfig::from_env()` 同様に `.env` ロード後、`getenv("LOCATION_RESOLVER_HOST/PORT", "QUERY_GENERATOR_HOST/PORT")` を読込。

### 差分（現状維持/任意）
- キャッシュ層（座標/クエリ）未実装: 互換性に直結しないため任意。ただし大規模リクエスト時の挙動差に注意。
- レスポンス認証検証（C++のみ）: 追加機能として良好だが、Python との設定差は README 等で明記推奨。
- ロギング（UnifiedLog 相当）: Python の詳細ロガーに対し、C++ は簡易出力中心。必要に応じて拡張。

---

## 補足確認項目（調査済み）
- パケット仕様（Type/Flags/拡張/オフセット）: C++ 実装は Python の `WIPCommonPy.packet` に準拠。
- day 指定、alert/disaster 配列: 両実装でエンコード/デコード対応。
- ソケット設定/タイムアウト: 等価（10s相当）。
- 認証フラグ/拡張: 両実装で付与・解析機構あり（C++側は追加で検証可）。

---

## 追加で推奨する動作検証（テスト観点）
- E2E: 実サーバ（Weather/Location/Query/Report）を起動し、以下を Python/C++ で比較実行
  - 座標→Direct→Query（area_code 6桁/値一致）
  - 座標→Proxy 経由（area_code 6桁/値一致）
  - エリアコード→Proxy/Direct（weather_code/temperature/precipitation の値一致）
  - Report 直接/Proxy（ACK内の `area_code`,`packet_id` 等の値整合）
- 認証有効時: 全経路で正常応答/エラー応答の動作確認（HMAC 生成/検証含む）
- 長文 alert/disaster 複数件: 文字列長の上限・切り詰めの有無が一致するかの確認
- day の範囲外指定時のエラー挙動一致
- Windows 環境の UDP タイムアウト挙動一致（WSA の差異考慮）

---

## 変更が必要な場合の実装ポイント（参考）
- 修正提案1（area_code 6桁ゼロ詰め）: `cpp/src/client/wip_client.cpp`
  - 該当箇所: `get_weather_by_coordinates(..., proxy=true)` 内 `out.area_code = std::to_string(...);` を `snprintf` ベースの6桁ゼロ詰めへ。
- 修正提案2（Direct エンドポイントの `.env` 反映）: `cpp/src/client/wip_client.cpp` / `cpp/include/wiplib/client/wip_client.hpp`
  - コンストラクタで `.env` を読み込み、`LOCATION_RESOLVER_*` / `QUERY_GENERATOR_*` を初期化時に反映。

---

## 結び
全体として、C++ 版クライアントは Python 版と高い互換性を達成しています。上記の軽微な差分（特に area_code のゼロ詰めと direct 経路の `.env` 反映）を解消すれば、機能面の互換は実運用レベルで十分に担保できる見込みです。必要であれば、上記提案に基づくパッチ作成も対応可能です。
