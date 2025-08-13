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
  QueryOptions opt;  // weather/temperature=on,他は必要に応じて
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

既知の差分/今後の拡張
- 認証・キャッシュ・詳細ロガー: Python版の一部機能（例: request_auth/response_authの実処理、Cache, UnifiedLog）は最小実装です。必要であれば拡張可能です。
- 例外ではなく `wiplib::Result<T>` によるエラー伝播を採用。
- 温度値はPython版同様にパケット内では+100オフセット。`WipClient` は摂氏に戻して返却します。

ツール
- `wip_client_cli`: 天気取得の簡易CLI。
- `wip_packet_gen`: パケットの生成（バイナリ出力）。
- `wip_packet_decode`: バイナリのデコード検証。

ヘッダ/リンク
- 追加インクルード: `-I cpp/include`
- リンク: `wiplib`（静的/共有はCMakeオプションで切替）
