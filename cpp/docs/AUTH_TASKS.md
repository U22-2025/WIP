# C++ 認証 実装タスク分解（Pythonクライアント完全再現）

本ドキュメントは、`cpp/docs/AUTH_SPEC.md` に基づき、Python クライアントの認証挙動を C++ で完全再現するための作業項目を段階的に整理したものです。実装順序、担当ファイル、受け入れ条件（Done の定義）を明記します。

---


## フェーズ 1: ヘルパと設定の導入

1. ヘルパ関数の追加（`WIPAuth` もしくはユーティリティ）
   - 追加: `bool attach_auth_hash(proto::Packet&, const std::string& passphrase)`
   - 処理: `calculate_auth_hash(packet_id, timestamp, passphrase)` → hex 文字列化 → `extensions.push_back({data_type=4, data=utf8(hex)})` → `flags.extended=true`
   - 変更ファイル: `cpp/include/wiplib/utils/auth.hpp`, `cpp/src/utils/auth.cpp`

2. 認証設定構造体の追加
   - 追加: `struct AuthConfig { bool enabled; std::optional<std::string> weather, location, query, report; bool verify_response=false; };`
   - 環境変数読取（任意）: `WEATHER_SERVER_PASSPHRASE`, `LOCATION_SERVER_PASSPHRASE`, `QUERY_SERVER_PASSPHRASE`, `REPORT_SERVER_PASSPHRASE`
   - 変更ファイル: `cpp/include/wiplib/client/*`（公開 API）、`cpp/src/client/*`

受け入れ条件
- ヘルパが単体で動作し、拡張フィールド（ID=4）が正しく付与されること。
- AuthConfig を任意のクライアントに設定できること（デフォルトは無効）。

---

## フェーズ 2: クライアントへの組込み

3. WeatherClient 送信経路での付与
   - 対象: `cpp/src/client/weather_client.cpp`
   - `request_and_parse` 内、エンコード直前に `AuthConfig.enabled` を確認し、`weather` パスフレーズで `attach_auth_hash` を実行。

4. LocationClient 送信経路での付与
   - 対象: `cpp/src/client/location_client.cpp`
   - Location Resolver 向けリクエスト作成時に `location` パスフレーズで付与。

5. QueryClient 送信経路での付与
   - 対象: `cpp/src/client/query_client.cpp`
   - Query Generator 向けリクエスト作成時に `query` パスフレーズで付与。

6. WipClient からの設定伝播
   - 対象: `cpp/src/client/wip_client.cpp` とヘッダ
   - 直接接続モード時に `AuthConfig` を `LocationClient`/`QueryClient` へ伝播できる setter を追加（もしくはコンストラクタ引数）。

7. レスポンス検証（任意）
   - `AuthConfig.verify_response=true` の場合、受信パケットに `auth_hash` があれば検証。
   - 失敗時は `auth_failed` 相当のエラーを返却（エラーコード定義がなければ `invalid_packet` で代替、後続で定義）。

受け入れ条件
- 認証有効時、送出パケットに `auth_hash` が必ず付与される（Weather/Location/Query 宛でそれぞれ）。
- 無効時は現行挙動からの回 regress なし。
- 任意のレスポンス検証が有効化できること（デフォルト off）。

---

## フェーズ 3: CLI/設定/ドキュメント

8. CLI オプションの追加（任意）
   - 対象: `cpp/tools/wip_client_cli.cpp`
   - 追加フラグ: `--auth-enabled`, `--auth-weather PASS`, `--auth-location PASS`, `--auth-query PASS`, `--auth-report PASS`, `--verify-response`
   - CLI から `AuthConfig` を組み立て、クライアントへ適用。

9. ドキュメント更新
   - `cpp/README.md` に利用方法（環境変数・CLI フラグ・API setter）を追記。
   - `cpp/docs/AUTH_SPEC.md` と整合チェック。

受け入れ条件
- CLI で簡単に認証付与をオン/オフし、パスフレーズを指定できる。
- README の手順で相互運用テストが再現できる。

---

## フェーズ 4: テスト

10. 単体テスト（GTest）
   - 既知ベクタ: `packet_id=10, timestamp=123456, passphrase="pass"` などを Python で生成した hex と一致。
   - `attach_auth_hash` により `data_type=4`、UTF-8 hex64、`flags.extended=true` を確認。
   - 宛先別パスフレーズで異なる HMAC になること。

11. 疑似結合テスト
   - 生成した C++ パケットを Python の `Request.from_bytes` で decode → `WIPAuth.verify_auth_hash` で True になること（可能ならテスト補助スクリプトで確認）。

受け入れ条件
- 追加したユニットテストが通る。
- 手動/補助でのクロス言語検証が成功する。

---

## フェーズ 5: 品質/安全

12. ログ/エラー方針
   - 機微情報（パスフレーズ/HMAC）をログ出力しない。
   - 認証付与エラー時の扱い方針（エラーで送信中止 or 認証無しで送信）を決定（デフォルトは送信中止）。

13. スタブ暗号 API の扱い
   - `WIPAuth` の他メソッド（PBKDF2, AES 等のスタブ）は今回範囲外。安全でない関数を公開 API として示さないよう注記。

受け入れ条件
- ログに秘密情報が出ない。
- 非対象機能の混入がない。

---

## 実装メモ（ファイル別リスト）

- `cpp/include/wiplib/utils/auth.hpp`, `cpp/src/utils/auth.cpp`
  - `attach_auth_hash(Packet&, const std::string&)` の追加
  - hex 文字列化のユーティリティ（小文字、長さ 64）

- `cpp/src/client/weather_client.cpp`
  - `request_and_parse` で付与（Weather 用パスフレーズ）

- `cpp/src/client/location_client.cpp`
  - リクエスト作成→送信直前で付与（Location 用パスフレーズ）

- `cpp/src/client/query_client.cpp`
  - 同上（Query 用パスフレーズ）

- `cpp/src/client/wip_client.cpp` (+ ヘッダ)
  - `set_auth_config(AuthConfig)` を追加し、内部クライアントへ伝播

- `cpp/tools/wip_client_cli.cpp`（任意）
  - 認証関連フラグの追加・パース → `AuthConfig` 生成

- `cpp/tests/unit/test_auth_compat.cpp`（新規）
  - 既知ベクタ・拡張付与の検証

---

## ロールアウト手順

1) フェーズ 1 を実装 → 単体で `attach_auth_hash` のテストを追加/実行
2) フェーズ 2 を WeatherClient → LocationClient → QueryClient の順に反映
3) フェーズ 3 の CLI/README を更新
4) フェーズ 4 のユニット/疑似結合テストを通す
5) フェーズ 5 の最終確認（ログ/エラー方針）

完了定義
- すべてのフェーズの受け入れ条件を満たし、Python サーバーに対して `auth_hash` 付与済みパケットが正しく受理されること。

