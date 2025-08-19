WIP C++ Library (wiplib)

概要
- Python版の WIPCommonPy/WIPClientPy を参考に、同等のパケット仕様と高水準クライアントAPIをC++で提供します。
- ライブラリは `wiplib` としてビルドされ、C++アプリからヘッダ経由で利用できます。

提供コンポーネント
- パケット/コーデック: `wiplib/packet` 配下
  - `packet.hpp`: ヘッダ、拡張、レスポンスフィールドの型定義
  - `types.hpp`: パケット種別とフラグ
  - `codec.hpp`: エンコード/デコード（固定16バイトヘッダ＋可変長）
- クライアント: `wiplib/client` 配下
  - `weather_client.hpp`: Pythonの `WIPCommonPy.clients.weather_client` 相当（Weather Server プロキシ直叩き）
  - `wip_client.hpp`: Pythonの `WIPClientPy.client.Client` 相当（状態保持と direct/proxy 両モード）
  - `simple_report_client.hpp`: Pythonの `WIPCommonPy.clients.report_client` 相当（センサーデータレポート送信）

ビルド
1) CMake の使用
   - 依存: CMake 3.20+, C++20コンパイラ
   - 手順:
     - Linux/macOS
       - `cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release`
       - `cmake --build cpp/build --config Release -j`  
     - Windows (Visual Studio開発者コマンドプロンプト)
       - `cmake -S cpp -B cpp/build -G "Visual Studio 17 2022"`
       - `cmake --build cpp/build --config Release`
   - 成果物:
     - ライブラリ: `cpp/build/(lib)wiplib.*`
     - ツール: `wip_client_cli`, `wip_packet_gen`, `wip_packet_decode`

2) 単体ビルド（ツールのみ）
   - `cpp/tools/build_no_cmake.(sh|bat)` を参照（最小限のビルド例）

使用例

WeatherClient (プロキシ)
```
#include "wiplib/client/weather_client.hpp"
using namespace wiplib::client;

int main(){
  WeatherClient cli("127.0.0.1", 4110);
  QueryOptions opt;  // weather/temperature/precipitation_prob=on,他は必要に応じて
  auto res = cli.get_weather_by_area_code("011000", opt);
  if(!res){ /* エラー処理 */ return 1; }
  const auto& r = res.value();
  // r.area_code, r.weather_code, r.temperature(=+100オフセットの生値)
}
```

WipClient (高水準, PythonのClient相当)
```
#include "wiplib/client/client.hpp"
using namespace wiplib::client;

int main(){
  Client client({"127.0.0.1", 4110}); // Weather Server(プロキシ)
  WeatherOptions opt; opt.precipitation_prob = true; opt.day = 0;

  // 方式1: エリアコード指定（proxy=false で direct query）
  client.set_area_code("011000");
  auto r1 = client.get_weather(opt, /*proxy=*/false);

  // 方式2: 座標指定
  client.set_coordinates(35.6895, 139.6917);
  auto r2 = client.get_weather(opt, /*proxy=*/true); // プロキシ経由
}
```

Python版との対応
- パケット仕様: フィールド配置/チェックサム/拡張フィールドは Python 実装の `WIPCommonPy.packet` に準拠。
- `WeatherClient`: Python版の `WeatherClient.get_weather_data`／`get_weather_by_*` に相当する `get_weather_by_area_code`／`get_weather_by_coordinates` を提供。
- `WipClient`: Python版の `Client.get_weather/get_weather_by_*` と同等の役割。座標→エリア解決（Location Server 4109）→Query Server 4111 への direct モード、および Weather Server(4110) プロキシ経由の2経路に対応。
- `SimpleReportClient`: Python版の `ReportClient` と同等のセンサーデータ送信APIを提供。

既知の差分/今後の拡張
- 認証・キャッシュ・詳細ロガー: Python版の一部機能（例: request_auth/response_authの実処理、Cache, UnifiedLog）は最小実装です。必要であれば拡張可能です。
- 例外ではなく `wiplib::Result<T>` によるエラー伝播を採用。
- 温度値はPython版同様にパケット内では+100オフセット。`WipClient` は摂氏に戻して返却します。
- `SimpleReportClient` は Python版 `ReportClient` と同等のAPIを提供するが、
  - 非同期送信は `asyncio` ではなく `std::future` を使用
  - エラーは例外ではなく `Result<ReportResult>` で返却
  - ホスト・ポートは環境変数から自動取得しない

ツール
- `wip_client_cli`: 天気取得の簡易CLI。
- `wip_packet_gen`: パケットの生成（バイナリ出力）。
- `wip_packet_decode`: バイナリのデコード検証。

ヘッダ/リンク
- 追加インクルード: `-I cpp/include`
- リンク: `wiplib`（静的/共有はCMakeオプションで切替）

認証設定
- 概要: Pythonクライアントの認証挙動を再現。HMAC-SHA256 を拡張フィールド(ID=4)へ hex64 で付与（`flags.extended=true`）。
- 環境変数:
  - `WIP_CLIENT_AUTH_ENABLED=1`（認証付与を有効化）
  - `WIP_CLIENT_VERIFY_RESPONSE_AUTH=1`（受信パケットの検証を有効化）
  - `WEATHER_SERVER_PASSPHRASE`（WeatherServer 宛の共有パスフレーズ）
  - `LOCATION_SERVER_PASSPHRASE`（LocationResolver 宛の共有パスフレーズ）
  - `QUERY_SERVER_PASSPHRASE`（QueryGenerator 宛の共有パスフレーズ）
  - `REPORT_SERVER_PASSPHRASE`（Report 宛の共有パスフレーズ）
- CLI フラグ（`wip_client_cli`）:
  - `--auth-enabled` / `--no-auth-enabled`
  - `--auth-weather <PASS>` `--auth-location <PASS>` `--auth-query <PASS>` `--auth-report <PASS>`
  - `--verify-response` / `--no-verify-response`
  - 例（プロキシ経由）:
    - `./cpp/build/wip_client_cli --proxy --host 127.0.0.1 --port 4110 --area 130010 --weather --temperature --auth-enabled --auth-weather secret`
  - 例（ダイレクト: デフォルト）:
    - `./cpp/build/wip_client_cli --coords 35.6895 139.6917 --auth-enabled --auth-location locpass --auth-query qpass`
- API からの設定例:
```
#include "wiplib/client/weather_client.hpp"
#include "wiplib/client/wip_client.hpp"
#include "wiplib/client/auth_config.hpp"
using namespace wiplib::client;

// WeatherClient（プロキシ）
WeatherClient wc{"127.0.0.1", 4110};
AuthConfig ac = AuthConfig::from_env();
ac.enabled = true;
ac.weather = std::string("secret");
ac.verify_response = true; // 任意
wc.set_auth_config(ac);

// WipClient（ダイレクト/プロキシ両対応）
WipClient c{{"127.0.0.1", 4110}};
c.set_auth_config(ac);
```

注意
- ログにはパスフレーズや HMAC 値を出力しません。
- 受信検証はレスポンス側が `response_auth` フラグと拡張(ID=4, hex64)を付与する場合のみ実施します。

環境変数の読み込み (.env)
- C++ クライアントは `AuthConfig::from_env()` 呼び出し時に、カレントディレクトリから親ディレクトリ方向に最大3階層まで `.env` を自動読み込みします（既存の環境変数は上書きしません）。
- 特定パスを指定したい場合は `WIP_DOTENV_PATH` を設定してください（例: `WIP_DOTENV_PATH=/path/to/.env`）。
- これにより `.env` に `*_REQUEST_AUTH_ENABLED` や `*_SERVER_PASSPHRASE` を記述するだけで、C++ 側でも認証が有効化されます。
- `WeatherClient::from_env()` や `LocationClient::from_env()` などを利用すると、以下の環境変数から接続先ホスト・ポートを取得できます。
  - `WEATHER_SERVER_HOST` / `WEATHER_SERVER_PORT`
  - `LOCATION_RESOLVER_HOST` / `LOCATION_RESOLVER_PORT`
  - `QUERY_GENERATOR_HOST` / `QUERY_GENERATOR_PORT`
  例: `auto cli = wiplib::client::WeatherClient::from_env();`
