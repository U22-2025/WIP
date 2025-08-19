#pragma once

#include <thread>
#include <mutex>
#include <map>
#include <vector>
#include <string>
#include <chrono>
#include <optional>
#include <cstdint>
#include <ctime>

// テスト用の天気データ構造体
struct WeatherData {
    double temperature;
    int humidity;
    double pressure;
    double wind_speed;
    int wind_direction;
    double precipitation;
    std::time_t timestamp;
    std::optional<double> visibility;
    std::optional<int> uv_index;
    std::optional<int> cloud_coverage;
    
    WeatherData();
    bool operator==(const WeatherData& other) const;
};

// モックサーバークラス
class MockServer {
public:
    MockServer();
    ~MockServer();
    
    // サーバーの開始と停止
    bool start(int port);
    void stop();
    
    // 天気データのレスポンス設定
    void set_weather_response(uint32_t area_code, const WeatherData& data);
    void set_weather_response_for_coordinates(double latitude, double longitude, const WeatherData& data);
    
    // 位置データのレスポンス設定
    void set_location_response(double latitude, double longitude, uint32_t area_code);
    
    // クエリレスポンス設定
    void set_query_response(const std::string& query, const std::string& result);
    
    // エラーレスポンス設定
    void set_error_response(uint32_t area_code, const std::string& message, int code = 500);
    void set_location_error_response(double latitude, double longitude, const std::string& message, int code = 500);
    void set_query_error_response(const std::string& query, const std::string& message, int code = 500);
    
    // 遅延レスポンス設定
    void set_delayed_response(uint32_t area_code, std::chrono::milliseconds delay);
    void set_location_delayed_response(double latitude, double longitude, uint32_t area_code, std::chrono::milliseconds delay);
    void set_query_delayed_response(const std::string& query, const std::string& result, std::chrono::milliseconds delay);
    
    // リトライシナリオ設定
    void set_retry_scenario(uint32_t area_code, int fail_count);
    void set_location_retry_scenario(double latitude, double longitude, int fail_count);
    
    // ストリーミングクエリレスポンス設定
    void set_streaming_query_response(const std::string& query, const std::vector<std::string>& chunks);
    
    // バッチクエリレスポンス設定
    void set_batch_query_response(const std::vector<std::string>& queries, const std::vector<std::string>& results);
    
    // プリペアドステートメントレスポンス設定
    void set_prepared_statement_response(const std::string& stmt_id, const std::vector<std::string>& parameters, const std::string& result);
    
private:
    // 内部構造体
    struct ErrorResponse {
        std::string message;
        int code;
        
        ErrorResponse(const std::string& msg, int err_code);
    };
    
    struct RetryScenario {
        int fail_count;
        int current_count;
        
        RetryScenario(int fail_cnt = 0, int curr_cnt = 0);
    };
    
    struct CoordinateKey {
        double latitude;
        double longitude;
        
        bool operator<(const CoordinateKey& other) const;
        bool operator==(const CoordinateKey& other) const;
    };
    
    struct PreparedStatementKey {
        std::string statement_id;
        std::vector<std::string> parameters;
        
        bool operator<(const PreparedStatementKey& other) const;
        bool operator==(const PreparedStatementKey& other) const;
    };
    
    // サーバー状態
    bool running_;
    int port_;
    std::thread server_thread_;
    std::mutex responses_mutex_;
    
    // レスポンスマップ
    std::map<uint32_t, WeatherData> weather_responses_;
    std::map<CoordinateKey, WeatherData> coordinate_weather_responses_;
    std::map<CoordinateKey, uint32_t> location_responses_;
    std::map<std::string, std::string> query_responses_;
    
    // エラーレスポンスマップ
    std::map<uint32_t, ErrorResponse> error_responses_;
    std::map<CoordinateKey, ErrorResponse> coordinate_error_responses_;
    std::map<std::string, ErrorResponse> query_error_responses_;
    
    // 遅延レスポンスマップ
    std::map<uint32_t, std::chrono::milliseconds> delayed_responses_;
    std::map<CoordinateKey, std::chrono::milliseconds> coordinate_delayed_responses_;
    std::map<std::string, std::chrono::milliseconds> query_delayed_responses_;
    
    // リトライシナリオマップ
    std::map<uint32_t, RetryScenario> retry_scenarios_;
    std::map<CoordinateKey, RetryScenario> coordinate_retry_scenarios_;
    
    // 高度な機能のレスポンスマップ
    std::map<std::string, std::vector<std::string>> streaming_query_responses_;
    std::map<std::string, std::string> batch_query_responses_;
    std::map<PreparedStatementKey, std::string> prepared_statement_responses_;
    
    // 内部メソッド
    void server_loop();
    void process_pending_requests();
    
    // レスポンスフォーマッター
    std::string format_weather_response(const WeatherData& data);
    std::string format_location_response(uint32_t area_code);
    std::string format_error_response(const ErrorResponse& error);
    
    // リトライ判定
    bool should_fail_retry(uint32_t area_code);
    bool should_fail_coordinate_retry(double latitude, double longitude);
};