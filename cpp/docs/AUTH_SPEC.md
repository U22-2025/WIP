# WIP クライアント認証 仕様と実装方針（C++ 再現）

この文書は Python 版 WIP の認証仕様を精査し、C++ 版クライアントで完全に再現するための要件・実装方針・テスト計画をまとめたものです。

## 目的

- Python 実装で定義されている「パケット認証（HMAC）」の振る舞いとワイヤフォーマットを正確に理解し、C++ クライアントから送信するパケットへ同等の `auth_hash` を付与できるようにする。
- 直接接続（Location/Query サーバー宛）および Weather サーバー経由の両経路で、Python サーバー群と相互運用できる互換性を担保する。

---

## Python 版の認証仕様（調査結果）

参照:
- `src/WIPCommonPy/utils/auth.py`
- `src/WIPCommonPy/packet/core/extended_field.py`
- `src/WIPCommonPy/packet/format_spec/extended_fields.json`
- `src/WIPServerPy/servers/weather_server/weather_server.py`
- `src/WIPServerPy/servers/weather_server/handlers.py`
- `tests/test_weather_auth_verify.py`

### 1) HMAC 計算仕様

- アルゴリズム: HMAC-SHA256 固定
- メッセージ（UTF-8）: `"{packet_id}:{timestamp}:{passphrase}"`
  - `packet_id` は 12bit のパケット ID 値（整数）。Python 側は与えられた整数をそのまま使用。
  - `timestamp` は UNIX 秒（整数）。
  - `passphrase` はサーバー種別ごとに定義された共有秘密。
- キー（UTF-8）: `passphrase`
- 出力: 32 バイト（digest）。

Python 実装:
- 計算: `WIPAuth.calculate_auth_hash(packet_id, timestamp, passphrase) -> bytes`
- 検証: `WIPAuth.verify_auth_hash(packet_id, timestamp, passphrase, received_hash) -> bool`

### 2) 拡張フィールドへの格納

- 拡張フィールド定義（`extended_fields.json`）
  - `auth_hash`: id = 4, type = "str"
  - `source`: id = 40, type = "str"
  - `latitude`: id = 33 (float), `longitude`: id = 34 (float) など

- on-wire 形式:
  - キー（6bit）と長さ（10bit）からなる 16bit ヘッダ + 値のバイト列（LE）が連続。
  - `auth_hash` は「文字列型」として定義されており、値は「hex 文字列（ASCII/UTF-8）」として格納される。
    - 例: `b"aabbcc..."`（長さ 64 の hex）
  - パケットの固定ヘッダ側では `extended` フラグが立つ。

### 3) どこで `auth_hash` を付与/検証するか

- Weather Server 受信時（`weather_server.py`）
  - `WEATHER_SERVER_AUTH_ENABLED=true` の場合、受信パケットの `ex_field.auth_hash` を取り出し、
    `WIPAuth.verify_auth_hash` で検証。失敗時はログ出力して拒否。
  - パスフレーズはパケット種別や送信元ポートから判断（weather/location/query/report）。
    - `WEATHER_SERVER_PASSPHRASE`, `LOCATION_SERVER_PASSPHRASE`, `QUERY_SERVER_PASSPHRASE`, `REPORT_SERVER_PASSPHRASE` を使用。

- Weather Server 送信時（ハンドラ内）
  - Location/Query/Report サーバーへ転送するリクエストに対して、対応するパスフレーズで `auth_hash` を計算し、拡張フィールドに `hex` 文字列として設定（`ex_flag=1`）。

- クライアント側の検証について
  - Python クライアントの一般的な実装では、レスポンスの `auth_hash` を検証していない（サーバー内部の hop で設定/検証）。
  - ただし `FormatBase` には `verify_auth_from_extended_field` 等の補助が存在し、検証を導入する余地はある。

---

## C++ 版での完全再現 要件

### A. プロトコル互換（必須）

- `auth_hash` は拡張フィールド ID = 4 で送信すること。
  - 値は 32 バイト HMAC の `hex 文字列`（小文字、長さ 64）を UTF-8 で格納。
- パケット固定ヘッダの `flags.extended` を有効化。
- HMAC のメッセージ/キー/アルゴリズムは Python と同一（HMAC-SHA256, `"{packet_id}:{timestamp}:{passphrase}"`）。
  - `packet_id` はヘッダに設定する 12bit の整数値をそのまま使用する。
  - `timestamp` はヘッダに設定する UNIX 秒。

注意: C++ 実装には `Flags.request_auth`/`response_auth` が存在するが、Python 版の検証処理はこれらのフラグに依存していない。互換優先のため、フラグはオプション（`extended` は必須）。

### B. クライアント送信時の付与（必須）

1) Weather サーバー（プロキシ）へ送るクライアントリクエスト（`WeatherRequest`/`CoordinateRequest`）
   - 認証が有効化されている場合、`WEATHER_SERVER_PASSPHRASE`（または API で設定されたパスフレーズ）で `auth_hash` を付与。

2) 直接接続（Location/Query サーバーに直接送るモード）
   - Location Resolver 宛のリクエストには `LOCATION_SERVER_PASSPHRASE`、
     Query Generator 宛には `QUERY_SERVER_PASSPHRASE` を使用して `auth_hash` を付与。

3) Report サーバーを叩く機能を将来追加する場合は `REPORT_SERVER_PASSPHRASE` を使用。

環境変数（推奨デフォルト）:
- `WIP_CLIENT_AUTH_ENABLED` = `true|false`（デフォルト: `false`）
- `WEATHER_SERVER_PASSPHRASE`, `LOCATION_SERVER_PASSPHRASE`, `QUERY_SERVER_PASSPHRASE`, `REPORT_SERVER_PASSPHRASE`
  - API での上書きを優先し、未設定時は空扱い（= 認証付与しない）。

### C. レスポンス検証（任意）

- Python 版では必須ではないが、C++ クライアント側にも「受信パケットに `auth_hash` があれば検証する」オプションを提供可能。
  - 有効化時の失敗は `auth_failed` 相当のエラーとして扱う（上位へ伝播）。

### D. C++ 実装の改修ポイント

- `wiplib::utils::WIPAuth`
  - 既存の `calculate_auth_hash(uint16_t, uint64_t, const std::string&, HashAlgorithm)` を使用（デフォルト SHA256）。
  - 便宜関数: `attach_auth_hash(proto::Packet&, const std::string& passphrase)` を追加（計算→hex 文字列化→拡張に追加）。

- Extended Field 生成
  - `proto::ExtendedField` にて `data_type = 4`（auth_hash）を設定。
  - `data` に hex 文字列（UTF-8 バイト列）を格納。
  - パケットの `header.flags.extended = true` を忘れずに。

- クライアント群
  - `WeatherClient` 送信直前に、`WIP_CLIENT_AUTH_ENABLED` と `WEATHER_SERVER_PASSPHRASE` を確認し、必要なら `auth_hash` を付与。
  - `LocationClient` / `QueryClient`（直叩きのとき）も同様に、宛先別パスフレーズで付与。
  - 高水準 `WipClient` は内部で利用する `LocationClient`/`QueryClient` に伝播できるよう設定 API を用意。

- フラグ
  - 互換性維持の観点から `request_auth`/`response_auth` は必須ではない。
  - 実装コストが低ければ `request_auth=true` を付与してもよい（サーバー側の検証は拡張フィールド存在で行われるため挙動は変わらない）。

### E. エラーハンドリング/ロギング（推奨）

- パスフレーズ未設定・空文字の場合は `auth_hash` を付与しない（明示ログ: debug レベル）。
- 認証有効化だがパスフレーズなし → 明示的に無効化扱いで続行（デフォルト挙動）。
- 認証付与に失敗した場合（理論上稀）→ 送信を中断しエラーを返すか、認証無しで送信するかはオプション化。
  - 既定は「失敗時はエラー」でよい。
- 機微情報（パスフレーズ、HMAC、生のヘッダ）はログに出さない。

---

## 実装計画（C++）

1) Auth 設定
   - `struct AuthConfig { bool enabled; std::optional<std::string> weather; std::optional<std::string> location; std::optional<std::string> query; std::optional<std::string> report; };`
   - `WeatherClient`, `LocationClient`, `QueryClient`, `WipClient` に設定を渡す/上書きする API を追加（環境変数からの自動読取もサポート）。

2) 付与ヘルパ
   - `bool attach_auth_hash(Packet&, const std::string& passphrase)` を `WIPAuth` に追加（または util 関数）
     - `HMAC = calculate_auth_hash(header.packet_id, header.timestamp, passphrase, SHA256)`
     - `hex = to_hex(HMAC)`
     - `extensions.push_back({ .data_type = 4, .data = bytes(hex) })`
     - `header.flags.extended = true`

3) クライアント送信箇所の改修
   - `WeatherClient::request_and_parse` の直前で `auth_hash` 付与（有効時）。
   - `LocationClient`/`QueryClient` の `get_*` 送信前でも同様。

4) 受信検証（任意機能）
   - オプション `verify_response_auth` が有効なら、受信パケットに `auth_hash` がある場合に検証。
   - 失敗時は `WipErrc::auth_failed` を返す。

5) CLI 拡張（任意）
   - `wip_client_cli` に `--auth-{weather,location,query,report} <pass>` と `--auth-enabled` を追加。

---

## テスト計画

### 単体テスト

- HMAC 既知テスト
  - 例: `packet_id=10, timestamp=123456, passphrase="pass"` の期待 hex を Python で生成し、C++ 側 `calculate_auth_hash` 出力と一致を確認。

- 拡張フィールド付与
  - `attach_auth_hash` で `data_type=4` かつ `data` が 64 桁 hex の UTF-8 であることを確認。
  - `flags.extended` が立つこと。

- 宛先ごとのパスフレーズ選択
  - Weather/Location/Query それぞれ別パスを設定し、送出パケットの `auth_hash` が変わることを確認。

### 結合テスト（擬似）

- 送信したパケットを Python の `Request.from_bytes` 相当でデコードし、`ex_field.auth_hash` を抽出→`verify_auth_hash` で検証 OK になること（クロス言語互換確認）。

---

## セキュリティ注意点

- パスフレーズはプロセス外部に漏らさない（ログ/例外に含めない）。
- 比較は定数時間比較（検証側）を維持（Python 同等）。
- 現状の C++ `WIPAuth` は認証管理（ユーザー/トークン）用途の関数がスタブのため、今回の範囲では「パケット署名（HMAC）」のみに限定して利用する。

---

## 参考コード断片（C++ 側での付与イメージ）

```cpp
// Packet pkt; // ヘッダ (packet_id, timestamp) を設定済み
std::string pass = /* WEATHER_SERVER_PASSPHRASE 等 */;
auto mac = wiplib::utils::WIPAuth::calculate_auth_hash(
    pkt.header.packet_id, pkt.header.timestamp, pass, wiplib::utils::HashAlgorithm::SHA256);

// hex 文字列化
static const char* hex = "0123456789abcdef";
std::string hexstr; hexstr.resize(mac.size()*2);
for (size_t i=0;i<mac.size();++i){ hexstr[i*2]=hex[(mac[i]>>4)&0xF]; hexstr[i*2+1]=hex[mac[i]&0xF]; }

wiplib::proto::ExtendedField f;
f.data_type = 4; // auth_hash
f.data.assign(hexstr.begin(), hexstr.end());
pkt.extensions.push_back(std::move(f));
pkt.header.flags.extended = true;
```

---

## 今後の拡張（任意）

- レスポンス検証の標準化（クライアント側で `verify_response_auth=true` 時に一律検証）。
- `request_auth`/`response_auth` フラグの運用ルール策定（デバッグ用途の目印として利用）。
- サーバー別のキー管理（KMS/ファイル）やローテーション、フェイルオーバー時の二重キー対応（v2）。

