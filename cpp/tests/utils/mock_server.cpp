#include "mock_server.hpp"
#include <thread>
#include <chrono>
#include <sstream>
#include <iostream>

MockServer::MockServer() : running_(false), port_(0), server_thread_() {}

MockServer::~MockServer() {
    stop();
}

bool MockServer::start(int port) {
    if (running_) {
        return false;
    }
    
    port_ = port;
    running_ = true;
    
    // サーバースレッドを開始
    server_thread_ = std::thread(&MockServer::server_loop, this);
    
    // サーバーが起動するまで少し待機
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    
    return true;
}

void MockServer::stop() {
    if (running_) {
        running_ = false;
        if (server_thread_.joinable()) {
            server_thread_.join();
        }
    }
}

void MockServer::set_weather_response(uint32_t area_code, const WeatherData& data) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    weather_responses_[area_code] = data;
}

void MockServer::set_weather_response_for_coordinates(double latitude, double longitude, const WeatherData& data) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    CoordinateKey key{latitude, longitude};
    coordinate_weather_responses_[key] = data;
}

void MockServer::set_location_response(double latitude, double longitude, uint32_t area_code) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    CoordinateKey key{latitude, longitude};
    location_responses_[key] = area_code;
}

void MockServer::set_query_response(const std::string& query, const std::string& result) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    query_responses_[query] = result;
}

void MockServer::set_error_response(uint32_t area_code, const std::string& message, int code) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    ErrorResponse error{message, code};
    error_responses_[area_code] = error;
}

void MockServer::set_location_error_response(double latitude, double longitude, const std::string& message, int code) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    CoordinateKey key{latitude, longitude};
    ErrorResponse error{message, code};
    coordinate_error_responses_[key] = error;
}

void MockServer::set_query_error_response(const std::string& query, const std::string& message, int code) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    ErrorResponse error{message, code};
    query_error_responses_[query] = error;
}

void MockServer::set_delayed_response(uint32_t area_code, std::chrono::milliseconds delay) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    delayed_responses_[area_code] = delay;
}

void MockServer::set_location_delayed_response(double latitude, double longitude, uint32_t area_code, std::chrono::milliseconds delay) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    CoordinateKey key{latitude, longitude};
    location_responses_[key] = area_code;
    coordinate_delayed_responses_[key] = delay;
}

void MockServer::set_query_delayed_response(const std::string& query, const std::string& result, std::chrono::milliseconds delay) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    query_responses_[query] = result;
    query_delayed_responses_[query] = delay;
}

void MockServer::set_retry_scenario(uint32_t area_code, int fail_count) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    retry_scenarios_[area_code] = {fail_count, 0};
}

void MockServer::set_location_retry_scenario(double latitude, double longitude, int fail_count) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    CoordinateKey key{latitude, longitude};
    coordinate_retry_scenarios_[key] = {fail_count, 0};
}

void MockServer::set_streaming_query_response(const std::string& query, const std::vector<std::string>& chunks) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    streaming_query_responses_[query] = chunks;
}

void MockServer::set_batch_query_response(const std::vector<std::string>& queries, const std::vector<std::string>& results) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    
    if (queries.size() != results.size()) {
        return; // サイズが一致しない場合は設定しない
    }
    
    for (size_t i = 0; i < queries.size(); ++i) {
        batch_query_responses_[queries[i]] = results[i];
    }
}

void MockServer::set_prepared_statement_response(const std::string& stmt_id, const std::vector<std::string>& parameters, const std::string& result) {
    std::lock_guard<std::mutex> lock(responses_mutex_);
    PreparedStatementKey key{stmt_id, parameters};
    prepared_statement_responses_[key] = result;
}

void MockServer::server_loop() {
    // 簡単なサーバーシミュレーション
    // 実際の実装では適切なソケットサーバーを使用
    
    while (running_) {
        // クライアントからのリクエストを待機
        // この実装では実際のネットワーク通信は行わず、
        // テスト用の疑似的な処理のみを行う
        
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
        
        // レスポンスの処理（実際のリクエストパースは省略）
        process_pending_requests();
    }
}

void MockServer::process_pending_requests() {
    // 保留中のリクエストを処理
    // 実際の実装では、受信したリクエストを解析して適切なレスポンスを返す
    
    std::lock_guard<std::mutex> lock(responses_mutex_);
    
    // リトライシナリオの処理
    for (auto& scenario : retry_scenarios_) {
        if (scenario.second.current_count < scenario.second.fail_count) {
            scenario.second.current_count++;
        }
    }
    
    for (auto& scenario : coordinate_retry_scenarios_) {
        if (scenario.second.current_count < scenario.second.fail_count) {
            scenario.second.current_count++;
        }
    }
}

std::string MockServer::format_weather_response(const WeatherData& data) {
    std::ostringstream oss;
    oss << "{"
        << "\"temperature\": " << data.temperature << ", "
        << "\"humidity\": " << data.humidity << ", "
        << "\"pressure\": " << data.pressure << ", "
        << "\"wind_speed\": " << data.wind_speed << ", "
        << "\"wind_direction\": " << data.wind_direction << ", "
        << "\"precipitation\": " << data.precipitation << ", "
        << "\"timestamp\": " << data.timestamp;
    
    if (data.visibility.has_value()) {
        oss << ", \"visibility\": " << data.visibility.value();
    }
    if (data.uv_index.has_value()) {
        oss << ", \"uv_index\": " << data.uv_index.value();
    }
    if (data.cloud_coverage.has_value()) {
        oss << ", \"cloud_coverage\": " << data.cloud_coverage.value();
    }
    
    oss << "}";
    return oss.str();
}

std::string MockServer::format_location_response(uint32_t area_code) {
    std::ostringstream oss;
    oss << "{\"area_code\": " << area_code << "}";
    return oss.str();
}

std::string MockServer::format_error_response(const ErrorResponse& error) {
    std::ostringstream oss;
    oss << "{"
        << "\"error\": {"
        << "\"code\": " << error.code << ", "
        << "\"message\": \"" << error.message << "\""
        << "}"
        << "}";
    return oss.str();
}

bool MockServer::should_fail_retry(uint32_t area_code) {
    auto it = retry_scenarios_.find(area_code);
    if (it != retry_scenarios_.end()) {
        return it->second.current_count < it->second.fail_count;
    }
    return false;
}

bool MockServer::should_fail_coordinate_retry(double latitude, double longitude) {
    CoordinateKey key{latitude, longitude};
    auto it = coordinate_retry_scenarios_.find(key);
    if (it != coordinate_retry_scenarios_.end()) {
        return it->second.current_count < it->second.fail_count;
    }
    return false;
}

// WeatherData のデフォルトコンストラクタと比較演算子
WeatherData::WeatherData() 
    : temperature(0.0)
    , humidity(0)
    , pressure(0.0)
    , wind_speed(0.0)
    , wind_direction(0)
    , precipitation(0.0)
    , timestamp(0)
    , visibility(std::nullopt)
    , uv_index(std::nullopt)
    , cloud_coverage(std::nullopt) {}

bool WeatherData::operator==(const WeatherData& other) const {
    return temperature == other.temperature &&
           humidity == other.humidity &&
           pressure == other.pressure &&
           wind_speed == other.wind_speed &&
           wind_direction == other.wind_direction &&
           precipitation == other.precipitation &&
           timestamp == other.timestamp &&
           visibility == other.visibility &&
           uv_index == other.uv_index &&
           cloud_coverage == other.cloud_coverage;
}

// CoordinateKey の比較演算子
bool MockServer::CoordinateKey::operator<(const CoordinateKey& other) const {
    if (latitude != other.latitude) {
        return latitude < other.latitude;
    }
    return longitude < other.longitude;
}

bool MockServer::CoordinateKey::operator==(const CoordinateKey& other) const {
    return latitude == other.latitude && longitude == other.longitude;
}

// PreparedStatementKey の比較演算子
bool MockServer::PreparedStatementKey::operator<(const PreparedStatementKey& other) const {
    if (statement_id != other.statement_id) {
        return statement_id < other.statement_id;
    }
    return parameters < other.parameters;
}

bool MockServer::PreparedStatementKey::operator==(const PreparedStatementKey& other) const {
    return statement_id == other.statement_id && parameters == other.parameters;
}

// ErrorResponse のコンストラクタ
MockServer::ErrorResponse::ErrorResponse(const std::string& msg, int err_code) 
    : message(msg), code(err_code) {}

// RetryScenario のコンストラクタ
MockServer::RetryScenario::RetryScenario(int fail_cnt, int curr_cnt) 
    : fail_count(fail_cnt), current_count(curr_cnt) {}