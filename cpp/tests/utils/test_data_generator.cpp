#include "test_data_generator.hpp"
#include <random>
#include <algorithm>
#include <sstream>
#include <iomanip>

TestDataGenerator::TestDataGenerator() : rng_(std::random_device{}()) {}

TestDataGenerator::TestDataGenerator(uint32_t seed) : rng_(seed) {}

WeatherData TestDataGenerator::generate_weather_data() {
    WeatherData data;
    
    // 温度: -20°C から 45°C
    std::uniform_real_distribution<double> temp_dist(-20.0, 45.0);
    data.temperature = temp_dist(rng_);
    
    // 湿度: 0% から 100%
    std::uniform_int_distribution<int> humidity_dist(0, 100);
    data.humidity = humidity_dist(rng_);
    
    // 気圧: 950hPa から 1050hPa
    std::uniform_real_distribution<double> pressure_dist(950.0, 1050.0);
    data.pressure = pressure_dist(rng_);
    
    // 風速: 0 から 30 m/s
    std::uniform_real_distribution<double> wind_speed_dist(0.0, 30.0);
    data.wind_speed = wind_speed_dist(rng_);
    
    // 風向: 0度 から 359度
    std::uniform_int_distribution<int> wind_dir_dist(0, 359);
    data.wind_direction = wind_dir_dist(rng_);
    
    // 降水量: 0 から 50mm
    std::uniform_real_distribution<double> precip_dist(0.0, 50.0);
    data.precipitation = precip_dist(rng_);
    
    // タイムスタンプ: 現在時刻の前後1年
    auto now = std::time(nullptr);
    std::uniform_int_distribution<long> time_dist(-365*24*3600, 365*24*3600);
    data.timestamp = now + time_dist(rng_);
    
    // オプションフィールド（50%の確率で設定）
    std::uniform_int_distribution<int> optional_dist(0, 1);
    
    if (optional_dist(rng_)) {
        std::uniform_real_distribution<double> visibility_dist(0.1, 50.0);
        data.visibility = visibility_dist(rng_);
    }
    
    if (optional_dist(rng_)) {
        std::uniform_int_distribution<int> uv_dist(0, 15);
        data.uv_index = uv_dist(rng_);
    }
    
    if (optional_dist(rng_)) {
        std::uniform_int_distribution<int> cloud_dist(0, 100);
        data.cloud_coverage = cloud_dist(rng_);
    }
    
    return data;
}

WeatherData TestDataGenerator::generate_realistic_weather_data(double latitude, double longitude) {
    WeatherData data = generate_weather_data();
    
    // 緯度に基づいて温度を調整
    double lat_factor = std::cos(latitude * M_PI / 180.0);
    data.temperature = data.temperature * lat_factor;
    
    // 季節要素を追加（簡単なモデル）
    auto now = std::time(nullptr);
    auto tm_ptr = std::localtime(&now);
    int day_of_year = tm_ptr->tm_yday;
    double seasonal_factor = std::sin(2 * M_PI * day_of_year / 365.0);
    
    if (latitude > 0) {
        // 北半球
        data.temperature += 10 * seasonal_factor;
    } else {
        // 南半球
        data.temperature -= 10 * seasonal_factor;
    }
    
    // 海岸地域は湿度が高い傾向
    if (is_coastal_area(latitude, longitude)) {
        data.humidity = std::min(100, data.humidity + 20);
    }
    
    return data;
}

std::vector<WeatherData> TestDataGenerator::generate_weather_time_series(size_t count, std::chrono::hours interval) {
    std::vector<WeatherData> series;
    series.reserve(count);
    
    auto base_time = std::time(nullptr);
    WeatherData base_data = generate_weather_data();
    
    for (size_t i = 0; i < count; ++i) {
        WeatherData data = base_data;
        
        // 時間を設定
        data.timestamp = base_time + i * interval.count() * 3600;
        
        // 前のデータから小さな変化を加える
        if (i > 0) {
            add_temporal_variation(data, series.back());
        }
        
        series.push_back(data);
    }
    
    return series;
}

std::pair<double, double> TestDataGenerator::generate_coordinates() {
    std::uniform_real_distribution<double> lat_dist(-90.0, 90.0);
    std::uniform_real_distribution<double> lon_dist(-180.0, 180.0);
    
    double latitude = lat_dist(rng_);
    double longitude = lon_dist(rng_);
    
    return {latitude, longitude};
}

std::pair<double, double> TestDataGenerator::generate_japan_coordinates() {
    // 日本の緯度経度範囲
    std::uniform_real_distribution<double> lat_dist(24.0, 46.0);  // 沖縄から北海道
    std::uniform_real_distribution<double> lon_dist(123.0, 146.0); // 西端から東端
    
    double latitude = lat_dist(rng_);
    double longitude = lon_dist(rng_);
    
    return {latitude, longitude};
}

uint32_t TestDataGenerator::generate_area_code() {
    // 日本の気象庁エリアコード範囲（概算）
    std::uniform_int_distribution<uint32_t> area_dist(10000, 999999);
    return area_dist(rng_);
}

uint32_t TestDataGenerator::generate_japan_area_code() {
    // 実際の日本のエリアコードパターン
    std::vector<uint32_t> prefecture_codes = {
        11000, 12000, 13000, 14000, 15000, // 関東
        23000, 24000, 25000, 26000, 27000, // 中部・関西
        40000, 41000, 42000, 43000, 44000, // 九州・中国
        1000, 2000, 3000, 4000, 5000       // 北海道・東北
    };
    
    std::uniform_int_distribution<size_t> idx_dist(0, prefecture_codes.size() - 1);
    uint32_t base_code = prefecture_codes[idx_dist(rng_)];
    
    std::uniform_int_distribution<uint32_t> city_dist(10, 990);
    return base_code + city_dist(rng_);
}

std::string TestDataGenerator::generate_sql_query() {
    std::vector<std::string> query_templates = {
        "SELECT temperature, humidity FROM weather WHERE area_code = {}",
        "SELECT * FROM weather WHERE timestamp > '{}'",
        "SELECT AVG(temperature) FROM weather WHERE prefecture = '{}'",
        "SELECT COUNT(*) FROM weather WHERE temperature > {}",
        "SELECT * FROM weather WHERE area_code IN ({}, {}, {})"
    };
    
    std::uniform_int_distribution<size_t> template_dist(0, query_templates.size() - 1);
    std::string query_template = query_templates[template_dist(rng_)];
    
    // プレースホルダーを実際の値で置換
    return format_query_template(query_template);
}

std::string TestDataGenerator::generate_json_response() {
    WeatherData data = generate_weather_data();
    
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(2);
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

std::vector<uint8_t> TestDataGenerator::generate_packet_data(size_t size) {
    std::vector<uint8_t> data(size);
    std::uniform_int_distribution<uint8_t> byte_dist(0, 255);
    
    for (auto& byte : data) {
        byte = byte_dist(rng_);
    }
    
    return data;
}

std::vector<uint8_t> TestDataGenerator::generate_valid_wip_packet() {
    // WIPプロトコルの有効なパケットを生成
    std::vector<uint8_t> packet;
    
    // ヘッダー部分
    packet.push_back(0x01);  // version
    packet.push_back(0x23);  // packet_id (lower)
    packet.push_back(0x01);  // packet_id (upper)
    packet.push_back(0x01);  // type (WeatherRequest)
    
    // フラグ
    packet.push_back(0x03);  // weather + temperature flags
    
    // day
    packet.push_back(0x02);
    
    // timestamp (8 bytes)
    uint64_t timestamp = static_cast<uint64_t>(std::time(nullptr));
    for (int i = 0; i < 8; ++i) {
        packet.push_back(static_cast<uint8_t>(timestamp >> (i * 8)));
    }
    
    // area_code (4 bytes)
    uint32_t area_code = generate_japan_area_code();
    for (int i = 0; i < 4; ++i) {
        packet.push_back(static_cast<uint8_t>(area_code >> (i * 8)));
    }
    
    // チェックサムを計算して追加（簡単な実装）
    uint16_t checksum = calculate_simple_checksum(packet);
    packet.push_back(static_cast<uint8_t>(checksum & 0xFF));
    packet.push_back(static_cast<uint8_t>((checksum >> 8) & 0xFF));
    
    return packet;
}

TestPacketSet TestDataGenerator::generate_packet_test_set(size_t count) {
    TestPacketSet test_set;
    test_set.packets.reserve(count);
    test_set.expected_results.reserve(count);
    
    for (size_t i = 0; i < count; ++i) {
        auto packet = generate_valid_wip_packet();
        auto weather_data = generate_weather_data();
        
        test_set.packets.push_back(packet);
        test_set.expected_results.push_back(weather_data);
    }
    
    return test_set;
}

PerformanceTestData TestDataGenerator::generate_performance_test_data(size_t request_count, size_t concurrent_count) {
    PerformanceTestData test_data;
    test_data.requests.reserve(request_count);
    test_data.expected_responses.reserve(request_count);
    test_data.concurrent_count = concurrent_count;
    
    for (size_t i = 0; i < request_count; ++i) {
        PerformanceTestRequest request;
        request.area_code = generate_japan_area_code();
        request.coordinates = generate_japan_coordinates();
        request.timestamp = std::time(nullptr) + i;
        
        auto weather_data = generate_realistic_weather_data(
            request.coordinates.first, 
            request.coordinates.second
        );
        
        test_data.requests.push_back(request);
        test_data.expected_responses.push_back(weather_data);
    }
    
    return test_data;
}

std::string TestDataGenerator::generate_error_message() {
    std::vector<std::string> error_messages = {
        "Invalid area code",
        "Service temporarily unavailable", 
        "Network connection timeout",
        "Authentication failed",
        "Rate limit exceeded",
        "Internal server error",
        "Invalid request format",
        "Resource not found"
    };
    
    std::uniform_int_distribution<size_t> msg_dist(0, error_messages.size() - 1);
    return error_messages[msg_dist(rng_)];
}

std::string TestDataGenerator::generate_japanese_error_message() {
    std::vector<std::string> japanese_errors = {
        "無効なエリアコードです",
        "サービスが一時的に利用できません",
        "ネットワーク接続がタイムアウトしました", 
        "認証に失敗しました",
        "アクセス制限に達しました",
        "内部サーバーエラーが発生しました",
        "リクエスト形式が正しくありません",
        "指定されたリソースが見つかりません"
    };
    
    std::uniform_int_distribution<size_t> msg_dist(0, japanese_errors.size() - 1);
    return japanese_errors[msg_dist(rng_)];
}

void TestDataGenerator::add_temporal_variation(WeatherData& current, const WeatherData& previous) {
    std::normal_distribution<double> temp_variation(0.0, 2.0);
    std::normal_distribution<double> pressure_variation(0.0, 5.0);
    std::normal_distribution<double> wind_variation(0.0, 3.0);
    std::uniform_int_distribution<int> humidity_variation(-10, 10);
    
    // 温度の時間的変化
    current.temperature = previous.temperature + temp_variation(rng_);
    current.temperature = std::max(-50.0, std::min(50.0, current.temperature));
    
    // 気圧の時間的変化
    current.pressure = previous.pressure + pressure_variation(rng_);
    current.pressure = std::max(900.0, std::min(1100.0, current.pressure));
    
    // 風速の時間的変化
    current.wind_speed = std::max(0.0, previous.wind_speed + wind_variation(rng_));
    
    // 湿度の時間的変化
    current.humidity = previous.humidity + humidity_variation(rng_);
    current.humidity = std::max(0, std::min(100, current.humidity));
    
    // 降水量は急激に変化する可能性がある
    std::uniform_real_distribution<double> precip_change(0.0, 1.0);
    if (precip_change(rng_) < 0.8) {
        // 80%の確率で前の値の近く
        std::normal_distribution<double> precip_variation(0.0, 2.0);
        current.precipitation = std::max(0.0, previous.precipitation + precip_variation(rng_));
    }
    // 20%の確率で新しい降水イベント
}

bool TestDataGenerator::is_coastal_area(double latitude, double longitude) {
    // 簡単な海岸判定（実際の地理データは使用しない）
    // 島国や半島の特定のパターンをシミュレート
    
    // 日本の場合の簡単なモデル
    if (latitude >= 24.0 && latitude <= 46.0 && 
        longitude >= 123.0 && longitude <= 146.0) {
        // 内陸部の条件（大まかな近似）
        bool is_inland = (latitude >= 35.0 && latitude <= 37.0 && 
                         longitude >= 138.0 && longitude <= 140.0);
        return !is_inland;
    }
    
    return false;
}

std::string TestDataGenerator::format_query_template(const std::string& template_str) {
    std::string result = template_str;
    
    // プレースホルダーを置換
    size_t pos = 0;
    while ((pos = result.find("{}", pos)) != std::string::npos) {
        std::string replacement;
        
        // コンテキストに応じて適切な値を生成
        if (result.find("area_code") != std::string::npos) {
            replacement = std::to_string(generate_japan_area_code());
        } else if (result.find("temperature") != std::string::npos) {
            replacement = std::to_string(generate_weather_data().temperature);
        } else if (result.find("timestamp") != std::string::npos || 
                   result.find("date") != std::string::npos) {
            replacement = "'2024-08-17'";  // 固定日付
        } else if (result.find("prefecture") != std::string::npos) {
            replacement = "'東京都'";  // 固定県名
        } else {
            // デフォルト値
            replacement = std::to_string(generate_area_code());
        }
        
        result.replace(pos, 2, replacement);
        pos += replacement.length();
    }
    
    return result;
}

uint16_t TestDataGenerator::calculate_simple_checksum(const std::vector<uint8_t>& data) {
    uint32_t sum = 0;
    for (uint8_t byte : data) {
        sum += byte;
    }
    return static_cast<uint16_t>(sum & 0xFFFF);
}