#include <iostream>
#include "../../clients/QueryClient.hpp"
#include "../../clients/utils/PacketIDGenerator.hpp"
#include "../types/ReportPacket.hpp"
#include "../types/LocationPacket.hpp"
#include "../types/QueryPacket.hpp"

using namespace std;
using wip::packet::PacketIDGenerator12Bit;

// 従来方式でのパケット生成例
void traditional_usage_example(PacketIDGenerator12Bit &pidg) {
    cout << "=== 従来の使用方法 ===" << endl;

    Request request;
    request.version = 1;
    request.packet_id = pidg.next_id();
    request.type = 0; // 座標解決リクエスト
    request.timestamp = static_cast<int>(time(nullptr));
    request.weather_flag = 1;
    request.temperature_flag = 1;
    request.pop_flag = 1;
    request.alert_flag = 0;
    request.disaster_flag = 0;
    request.day = 0;
    request.ex_field["latitude"] = 35.6895;
    request.ex_field["longitude"] = 139.6917;
    request.ex_flag = 1;

    cout << "従来のRequest作成:" << endl;
    cout << "  Type: " << request.type << endl;
    cout << "  Flags: " << request.weather_flag << ", "
         << request.temperature_flag << ", " << request.pop_flag << endl;
}

// 新しい専用クラスの使用例
void modern_usage_example(PacketIDGenerator12Bit &pidg) {
    cout << "\n=== 新しい専用クラスの使用方法 ===" << endl;

    auto location_req = LocationRequest::create_coordinate_lookup(
        35.6895, 139.6917,
        pidg.next_id(),
        true,  // weather
        true,  // temperature
        true   // precipitation_prob
    );

    cout << "新しいLocationRequest作成:" << endl;
    cout << "  Type: " << location_req.type << endl;
    cout << "  Summary: " << location_req.get_request_summary() << endl;
}

// レスポンス処理の例
void response_processing_example(PacketIDGenerator12Bit &pidg) {
    cout << "\n=== レスポンス処理の比較 ===" << endl;

    Response sample_response;
    sample_response.version = 1;
    sample_response.packet_id = 123;
    sample_response.type = 3;
    sample_response.area_code = "011000";
    sample_response.timestamp = static_cast<int>(time(nullptr));
    sample_response.weather_flag = 1;
    sample_response.temperature_flag = 1;
    sample_response.pop_flag = 1;
    sample_response.alert_flag = 1;
    sample_response.disaster_flag = 0;
    sample_response.ex_flag = 1;
    sample_response.weather_code = 100;
    sample_response.temperature = 125; // 25℃ + 100
    sample_response.pop = 30;
    sample_response.ex_field["alert"] = {"大雨警報", "洪水注意報"};

    cout << "従来のレスポンス処理:" << endl;
    cout << "  気温: " << sample_response.temperature - 100 << "℃" << endl;
    cout << "  天気コード: " << sample_response.weather_code << endl;
    cout << "  降水確率: " << sample_response.pop << "%" << endl;

    auto response_bytes = sample_response.to_bytes();
    auto weather_resp = QueryResponse::from_bytes(response_bytes);

    cout << "\n新しいWeatherResponse処理:" << endl;
    cout << "  気温: " << weather_resp.get_temperature() << "℃" << endl;
    cout << "  天気コード: " << weather_resp.get_weather_code() << endl;
    cout << "  降水確率: " << weather_resp.get_precipitation_prob() << "%" << endl;
    cout << "  警報: " << weather_resp.get_alerts() << endl;
    cout << "  成功判定: " << weather_resp.is_success() << endl;
}

// クライアント統合の例
void client_integration_example(PacketIDGenerator12Bit &pidg) {
    cout << "\n=== クライアント統合例 ===" << endl;

    auto create_weather_request_easily = [&](double lat, double lon) {
        return LocationRequest::create_coordinate_lookup(
            lat,
            lon,
            pidg.next_id(),
            true,
            true,
            true
        );
    };

    auto tokyo_request = create_weather_request_easily(35.6895, 139.6917);
    auto sapporo_request = create_weather_request_easily(43.0642, 141.3469);

    cout << "簡潔なリクエスト作成:" << endl;
    cout << "  東京: " << tokyo_request.get_request_summary() << endl;
    cout << "  札幌: " << sapporo_request.get_request_summary() << endl;
}

// 互換性テスト
void compatibility_test(PacketIDGenerator12Bit &pidg) {
    cout << "\n=== 互換性テスト ===" << endl;

    auto weather_req = LocationRequest::create_coordinate_lookup(
        35.6895, 139.6917, pidg.next_id(), true, true
    );
    auto bytes = weather_req.to_bytes();
    auto traditional_req = Request::from_bytes(bytes);

    cout << "新→従来 互換性:" << endl;
    cout << "  Type: " << traditional_req.type << endl;
    auto coords = traditional_req.ex_field.get_coordinates();
    cout << "  Coordinates: " << coords.first << ", " << coords.second << endl;

    Request old_req;
    old_req.version = 1;
    old_req.packet_id = pidg.next_id();
    old_req.type = 0;
    old_req.weather_flag = 1;
    old_req.temperature_flag = 1;
    old_req.timestamp = static_cast<int>(time(nullptr));
    old_req.ex_field["latitude"] = 43.0642;
    old_req.ex_field["longitude"] = 141.3469;
    old_req.ex_flag = 1;

    auto old_bytes = old_req.to_bytes();
    auto new_weather_req = Request::from_bytes(old_bytes);

    cout << "\n従来→新 互換性:" << endl;
    cout << "  Summary: " << new_weather_req.get_request_summary() << endl;
}

int main() {
    cout << "専用パケットクラス使用例" << endl;
    cout << string(60, '=') << endl;

    PacketIDGenerator12Bit pidg;

    traditional_usage_example(pidg);
    modern_usage_example(pidg);
    response_processing_example(pidg);
    client_integration_example(pidg);
    compatibility_test(pidg);

    cout << "\n" << string(60, '=') << endl;
    cout << "専用パケットクラスの利点:" << endl;
    cout << "\xE2\x9C\x93 コード行数が大幅削減（従来の約半分）" << endl;
    cout << "\xE2\x9C\x93 型安全性の向上" << endl;
    cout << "\xE2\x9C\x93 直感的なメソッド名" << endl;
    cout << "\xE2\x9C\x93 自動的なデータ変換" << endl;
    cout << "\xE2\x9C\x93 既存コードとの完全互換性" << endl;
    cout << "\xE2\x9C\x93 エラーの少ない開発" << endl;
}

