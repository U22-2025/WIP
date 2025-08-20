#pragma once

#include <vector>
#include <string>
#include <random>
#include <chrono>
#include <cstdint>
#include <ctime>
#include <cmath>
#include "mock_server.hpp"

// パフォーマンステスト用のリクエスト構造体
struct PerformanceTestRequest {
    uint32_t area_code;
    std::pair<double, double> coordinates;
    std::time_t timestamp;
};

// パフォーマンステストデータセット
struct PerformanceTestData {
    std::vector<PerformanceTestRequest> requests;
    std::vector<WeatherData> expected_responses;
    size_t concurrent_count;
};

// パケットテストセット
struct TestPacketSet {
    std::vector<std::vector<uint8_t>> packets;
    std::vector<WeatherData> expected_results;
};

// テストデータ生成器クラス
class TestDataGenerator {
public:
    // コンストラクタ
    TestDataGenerator();
    explicit TestDataGenerator(uint32_t seed);
    
    // 天気データ生成
    WeatherData generate_weather_data();
    WeatherData generate_realistic_weather_data(double latitude, double longitude);
    std::vector<WeatherData> generate_weather_time_series(size_t count, std::chrono::hours interval = std::chrono::hours(1));
    
    // 座標データ生成
    std::pair<double, double> generate_coordinates();
    std::pair<double, double> generate_japan_coordinates();
    
    // エリアコード生成
    uint32_t generate_area_code();
    uint32_t generate_japan_area_code();
    
    // クエリ・レスポンス生成
    std::string generate_sql_query();
    std::string generate_json_response();
    
    // パケットデータ生成
    std::vector<uint8_t> generate_packet_data(size_t size);
    std::vector<uint8_t> generate_valid_wip_packet();
    
    // テストセット生成
    TestPacketSet generate_packet_test_set(size_t count);
    PerformanceTestData generate_performance_test_data(size_t request_count, size_t concurrent_count);
    
    // エラーメッセージ生成
    std::string generate_error_message();
    std::string generate_japanese_error_message();
    
    // ランダムシード設定
    void set_seed(uint32_t seed) { rng_.seed(seed); }
    
private:
    std::mt19937 rng_;
    
    // 内部ヘルパーメソッド
    void add_temporal_variation(WeatherData& current, const WeatherData& previous);
    bool is_coastal_area(double latitude, double longitude);
    std::string format_query_template(const std::string& template_str);
    uint16_t calculate_simple_checksum(const std::vector<uint8_t>& data);
};