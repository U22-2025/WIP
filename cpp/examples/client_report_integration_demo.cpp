#include <iostream>
#include <memory>
#include <thread>
#include <chrono>

#include "wiplib/client/client.hpp"

int main() {
    std::cout << "=== Client Report Integration Demo ===" << std::endl;
    
    try {
        // Python版Client互換のコンストラクタでクライアント作成
        auto client = std::make_unique<wiplib::client::Client>(
            "localhost",    // host
            4112,          // port (Report Server)
            std::nullopt,  // server_config
            true           // debug = true
        );
        
        std::cout << "✓ Client created successfully with Report support" << std::endl;
        
        // 1. Python版互換のset_sensor_data APIテスト
        std::cout << "\n--- Testing set_sensor_data API ---" << std::endl;
        client->set_sensor_data(
            "130010",                                   // area_code (東京)
            1,                                          // weather_code (晴れ)
            25.5f,                                      // temperature (25.5°C)
            30,                                         // precipitation_prob (30%)
            std::vector<std::string>{"強風注意報"},        // alert
            std::vector<std::string>{"地震情報"}          // disaster
        );
        std::cout << "✓ set_sensor_data() completed" << std::endl;
        
        // 2. 個別setter APIテスト
        std::cout << "\n--- Testing individual setter APIs ---" << std::endl;
        client->set_area_code("130020");
        client->set_weather_code(2);
        client->set_temperature(22.0f);
        client->set_precipitation_prob(50);
        client->set_alert({"雷注意報", "大雨警報"});
        client->set_disaster({"台風情報"});
        std::cout << "✓ Individual setters completed" << std::endl;
        
        // 3. データ取得APIテスト
        std::cout << "\n--- Testing get_current_data API ---" << std::endl;
        auto current_data = client->get_current_data();
        std::cout << "✓ get_current_data() returned " << current_data.size() << " fields" << std::endl;
        
        // 4. レポート送信APIテスト（サーバー接続なしでもAPIシグネチャ確認）
        std::cout << "\n--- Testing send_report_data APIs ---" << std::endl;
        
        // 同期送信
        auto result = client->send_report_data();
        if (result.has_value()) {
            std::cout << "✓ send_report_data() succeeded" << std::endl;
            const auto& report_result = result.value();
            std::cout << "  Type: " << report_result.type << std::endl;
            std::cout << "  Success: " << (report_result.success ? "true" : "false") << std::endl;
            std::cout << "  Response time: " << report_result.response_time_ms << "ms" << std::endl;
        } else {
            std::cout << "✗ send_report_data() failed: " << result.error().message() << std::endl;
            std::cout << "  (Expected if no server is running)" << std::endl;
        }
        
        // 非同期送信
        auto future_result = client->send_report_data_async();
        std::cout << "✓ send_report_data_async() future created" << std::endl;
        
        // 簡単送信
        auto simple_result = client->send_data_simple();
        if (simple_result.has_value()) {
            std::cout << "✓ send_data_simple() succeeded" << std::endl;
        } else {
            std::cout << "✗ send_data_simple() failed: " << simple_result.error().message() << std::endl;
            std::cout << "  (Expected if no server is running)" << std::endl;
        }
        
        // 5. 後方互換性APIテスト
        std::cout << "\n--- Testing backward compatibility APIs ---" << std::endl;
        auto report_compat = client->send_report();
        auto current_compat = client->send_current_data();
        std::cout << "✓ Backward compatibility APIs executed" << std::endl;
        
        // 6. データクリアAPIテスト
        std::cout << "\n--- Testing clear_data API ---" << std::endl;
        client->clear_data();
        auto cleared_data = client->get_current_data();
        std::cout << "✓ clear_data() completed, remaining fields: " << cleared_data.size() << std::endl;
        
        // 7. 天気データ取得とレポート送信の統合テスト
        std::cout << "\n--- Testing Weather + Report Integration ---" << std::endl;
        
        // 座標設定（天気データ取得用）
        client->set_coordinates(35.6762, 139.6503);  // 東京座標
        
        // 天気データ取得（既存機能）
        auto weather_result = client->get_weather();
        if (weather_result.has_value()) {
            std::cout << "✓ get_weather() succeeded" << std::endl;
            // const auto& weather_data = weather_result.value();
            // std::cout << "  Area: " << weather_data.area_code << std::endl;
        } else {
            std::cout << "✗ get_weather() failed: " << weather_result.error().message() << std::endl;
            std::cout << "  (Expected if no weather server is running)" << std::endl;
        }
        
        // レポート送信（新機能）
        client->set_sensor_data("130010", 1, 25.0f, 40);
        auto integrated_report = client->send_report_data();
        std::cout << "✓ Integrated weather + report functionality tested" << std::endl;
        
        // 8. サーバー設定変更テスト
        std::cout << "\n--- Testing server configuration change ---" << std::endl;
        client->set_server("localhost", 4112);
        client->set_sensor_data("999888", 3, 18.0f, 70);
        std::cout << "✓ Server configuration change handled" << std::endl;
        
        // 9. 正常終了
        std::cout << "\n--- Testing close functionality ---" << std::endl;
        client->close();
        std::cout << "✓ Client closed successfully" << std::endl;
        
        std::cout << "\n=== All Client Report Integration Tests Completed Successfully! ===" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "✗ Error: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}