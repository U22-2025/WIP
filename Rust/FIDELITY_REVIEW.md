# Rust TASKS 完了タスクの忠実度・完成度レビュー（Python版WIPクライアント準拠）

`Rust/TASKS.md` の更新後状態に基づき、完了（[x]）とされた範囲の実装有無・Python準拠度を再評価しました。今回の更新で `Rust/src/wip_common_rs/*` に大幅なコード追加があり、Phase 1/2 の進捗が実質的に前進しています。


**結論（サマリ）**
- Phase 1 のコア（checksum/bit_utils/exceptions/format_base）は実装が入り、基本テストも追加。方向性は良好。
- Phase 2 のクライアント群は同期/非同期両対応、ID待ち受け・送信安全化・接続プール等、Python版以上のユーティリティが実装済み。
- 一方でパケット型（特に Query/Location/Report）の実装は、まだPythonのFormatBase的な動的仕様適用が不十分で、型・エンコード規約に不一致が残っています。
- 完了チェックは概ね妥当化しつつあるが、Type実装の仕上げ（FormatBase統合、温度/area_codeの規約統一、チェックサム検証の徹底）までは「部分的完了」と見なすのが安全です。


## 追加実装の評価（良くなった点）
- Core
  - `packet/core/checksum.rs`: 12bitチェックサムの計算/検証/簡易最適化とテストが実装。Pythonの語義に沿う（キャリーフォールド→反転→12bitマスク）。
  - `packet/core/bit_utils.rs`: `extract_bits`/`set_bits`/`bytes_to_u128_le`/`u128_to_bytes_le` と `BitField`/`PacketFields` の基盤が整備済み。
  - `packet/core/exceptions.rs`: 解析/チェックサム/フィールドの各エラー型と `WipPacketError` による集約、From変換、表示文字列まで定義済み。
  - `packet/core/format_base.rs`: `PacketFormat` trait、`PacketDefinitionBuilder`、JSON仕様ローダ`JsonPacketSpecLoader`、`PacketValidator` を追加。将来の動的仕様適用の足場が整備。
- Clients/Utils
  - `clients/async_weather_client.rs`: リトライ/タイムアウト/キャッシュ/同時性制御/接続プール/メトリクスを備えた非同期クライアントが追加。
  - `clients/utils/receive_with_id.rs`: 同期/非同期のID待ち受け、バッファリング、複数ID対応などが用意。
  - `clients/utils/safe_sock_sendto.rs`: 送信リトライ、タイムアウト、フラグメント送信、輻輳制御とメトリクスの実装。
  - `src/lib.rs` の `prelude` は新しい `wip_common_rs` を参照し、旧構成は「廃止予定」と明記。


## 依然残る不一致・未整備（重要）
- FormatBase連携の不足
  - `packet/types/query_packet.rs` は `bitvec` による手組みで、`PacketFields`/`JsonPacketSpecLoader` を使った動的仕様に未移行。
  - `packet/types/location_packet.rs`/`report_packet.rs` は `PacketFormat` 実装の体裁だが、`get_field_definitions()` などFormatBase由来の関数の実体が未確認（ビルダー/ローダと実配線の不足）。
- エンコード規約の差異
  - `area_code`: Pythonは外部APIで6桁文字列→内部20bit。RustのQueryは `u32` で直接20bit格納。外部/内部の正規化方針を統一すべき。
  - `temperature`: Pythonは+100オフセット（0℃=100）。Rust QueryResponseは `u8`→`i8` 変換のみでオフセット未適用。レスポンス解釈がズレる。
- チェックサムの統一適用
  - Queryの `to_bytes` は独自`calc_checksum12`を内包。共通`core/checksum.rs`のAPIで計算・検証し、`verify_checksum12`も受信側で必ず通すべき。
- `receive_with_id` のID抽出
  - ユーティリティ版の `extract_packet_id` は先頭2バイトをそのまま `u16` 化。プロトコル上は `version(4bit) + packet_id(12bit)` のため、`(value >> 4) & 0x0FFF` のマスク処理が必要（同期版`WeatherClient`は実装済み）。
- 旧実装との二重化
  - 旧コードは `deprecated/common/*` に移動され、利用経路の混在リスクは解消された。
- 座標フィールド
  - Location系は緯度経度の固定小数点格納コメントあり。実際の拡張フィールド/ビット位置へのマッピングは未完。


## TASKS 対応状況の見立て（完了印の妥当性）
- Phase 1 Core: 実装/テストが入り「完了」妥当。ただし FormatBase は「仕様ローダ＋検証器まで」で、各Typeへの適用は今後。表現上「完了（基盤）」と補足するのが適切。
- Phase 1 Types: ファイル・骨組みは揃い、Queryは動作レベルにあるが、FormatBase統合やエンコード規約統一が残るため「部分的完了」。
- Phase 2 Clients/Utils: 同期/非同期両系で充実。「完了」妥当。ただしID抽出のマスク適用をユーティリティ側へ反映要。
- Phase 3 以降: 未着手/プレースホルダが中心で、TASKSの現状表記（未完了）に合致。


## 修正提案（優先度順）
- Query を FormatBase ベースへ移行
  - `packet/types/query_packet.rs` を `PacketFields`＋`JsonPacketSpecLoader` による仕様駆動へ置換。
  - `area_code` は外部APIでは6桁文字列を受け取り、内部20bitへ正規化して格納。
  - `temperature` の+100オフセットをレスポンス復号に適用（Python同等）。
  - 送受信のチェックサムを `core/checksum.rs` に統一し、`verify_checksum12` を受信直後に通す。
- Location/Report/Error を FormatBase に統合
  - `get_field_definitions()` と `get_checksum_field()` を各Typeで実装し、`format_spec/*.json` を確実に反映。
  - 緯度/経度の固定小数点格納の実体実装（拡張フィールドのエンコード/デコード含む）。
- `receive_with_id` のID抽出修正
  - `extract_packet_id()` で `(value >> 4) & 0x0FFF` を適用。同期/非同期/複数IDの全系で一貫。
- 旧コードの明示的な切替
  - READMEに「`wip_common_rs` を正」とし、`common/*` はサンプル/旧版として非推奨扱いを明記。テスト/Examplesは新系に寄せる。
- 相互検証テスト
  - Python実装で生成した既知バイト列と Rust の to_bytes/from_bytes が一致するゴールデンテストを `core`/`types` ごとに追加。


## 参考（実装位置）
- Python 参照実装: `src/WIPCommonPy/packet/core/*.py`, `src/WIPCommonPy/packet/types/*.py`, `src/WIPCommonPy/clients/*.py`
- Rust 現行実装:
  - Core: `Rust/src/wip_common_rs/packet/core/*.rs`
  - Types: `Rust/src/wip_common_rs/packet/types/*.rs`
  - Clients: `Rust/src/wip_common_rs/clients/*.rs`（同期/非同期, utils 含む）


以上。次のマイルストーンとしては「QueryのFormatBase移行＋温度/area_code規約統一＋受信側チェックサム検証の徹底」を最初に仕上げるのが、Python互換達成への近道です。


## この更新で反映した修正（差分）
- `packet/types/query_packet.rs`
  - 送信: チェックサム計算を共通 `calc_checksum12` に統一。
  - 受信: `verify_checksum12` を適用し、チェックサム不正時は `None` を返却。
  - 仕様駆動: リクエストのビット配置は `request_fields.json` を取り込み、`PacketFields` を用いて動的に設定。レスポンスの抽出も `response_fields.json` の範囲を参照。
  - 温度: Python準拠の+100オフセットをデコードに反映（120→20℃ など）。
  - 外部API: `create_query_request()` を追加し、6桁文字列のエリアコード正規化に対応。
  - 冗長な `println!` を削減（ノイズ抑制）。
- `clients/utils/receive_with_id.rs`
  - パケットID抽出ロジックをプロトコル準拠に修正（先頭2バイト→右シフト4→12bitマスク）。
- `packet/types/location_packet.rs`
  - PythonのLocationRequest.create_coordinate_lookupを忠実化（type=0）。
  - ヘッダは `request_fields.json` に基づき動的に構成、チェックサムは共通関数で算出。
  - 緯度・経度を拡張フィールドとしてエンコード（ExtendedFieldManager）。
  - 受信は `LocationResponseEx::from_bytes()` を追加（16B/20Bヘッダ対応、checksum検証、latitude/longitude/source復号）。
  - `types/mod.rs` で `LocationResponseEx` を `LocationResponse` 名で再エクスポートしてAPI統一。

残課題
- Query はまだ `PacketFields/JsonPacketSpecLoader` による仕様駆動へ完全移行していない（次対応）。
- Location/Report/Error についても FormatBase 統合と座標／拡張フィールドの実体化が必要。
  - LocationResponse/Report系は未統合。エリアコード正規化や拡張フィールドの双方向処理を追加する。
  - Examples/README を新APIに合わせて更新（旧 `common/*` は非推奨明記）。

## 追加テスト
- Location/Report: ヘッダ16Bのchecksum検証、タイプ値、tailの固定フィールドの検証、拡張フィールド復号（lat/lon/source）を確認するユニットテストを追加。
