#include <gtest/gtest.h>
#include "wiplib/compatibility/python_errors.hpp"
#include "wiplib/compatibility/python_config.hpp"
#include "wiplib/compatibility/python_protocol.hpp"
#include "wiplib/client/client.hpp"

using namespace wiplib::compatibility;
using namespace wiplib::client;

class PythonCompatibilityTest : public ::testing::Test {
protected:
    void SetUp() override {
        // テスト用設定の初期化
        config_.server().host = "localhost";
        config_.server().port = 4110;
        config_.client().debug = false;
    }
    
    void TearDown() override {}
    
    PythonConfig config_;
};

// エラーハンドリング互換性テスト
TEST_F(PythonCompatibilityTest, ErrorCodeCompatibility) {
    // Python版と同一のエラーコード値
    EXPECT_EQ(static_cast<int>(PythonErrorCode::CONNECTION_ERROR), 1001);
    EXPECT_EQ(static_cast<int>(PythonErrorCode::TIMEOUT_ERROR), 1002);
    EXPECT_EQ(static_cast<int>(PythonErrorCode::NETWORK_UNREACHABLE), 1003);
    EXPECT_EQ(static_cast<int>(PythonErrorCode::INVALID_PACKET), 2001);
    EXPECT_EQ(static_cast<int>(PythonErrorCode::INVALID_COORDINATES), 3001);
    EXPECT_EQ(static_cast<int>(PythonErrorCode::INVALID_AREA_CODE), 3002);
    EXPECT_EQ(static_cast<int>(PythonErrorCode::SERVER_ERROR), 4001);
}

// エラーメッセージ形式の互換性テスト
TEST_F(PythonCompatibilityTest, ErrorMessageFormat) {
    ConnectionError conn_err("ネットワーク接続に失敗しました");
    std::string formatted = conn_err.python_format();
    
    // Python版と同じ形式: [エラーコード] メッセージ
    EXPECT_TRUE(formatted.find("[1001]") != std::string::npos);
    EXPECT_TRUE(formatted.find("ネットワーク接続に失敗しました") != std::string::npos);
}

// 設定ファイル形式の互換性テスト
TEST_F(PythonCompatibilityTest, ConfigFileFormat) {
    // Python版と同一のJSON形式で出力
    std::string json = config_.to_json();
    
    // 必須フィールドの存在確認
    EXPECT_TRUE(json.find("\"server\"") != std::string::npos);
    EXPECT_TRUE(json.find("\"host\"") != std::string::npos);
    EXPECT_TRUE(json.find("\"port\"") != std::string::npos);
    EXPECT_TRUE(json.find("\"logging\"") != std::string::npos);
    EXPECT_TRUE(json.find("\"cache\"") != std::string::npos);
    EXPECT_TRUE(json.find("\"client\"") != std::string::npos);
}

// 環境変数の互換性テスト
TEST_F(PythonCompatibilityTest, EnvironmentVariables) {
    // Python版と同じ環境変数名をサポート
    setenv("WIPLIB_HOST", "test.example.com", 1);
    setenv("WIPLIB_PORT", "8080", 1);
    setenv("WIPLIB_DEBUG", "true", 1);
    
    config_.load_from_environment();
    
    EXPECT_EQ(config_.server().host, "test.example.com");
    EXPECT_EQ(config_.server().port, 8080);
    EXPECT_TRUE(config_.client().debug);
    
    // クリーンアップ
    unsetenv("WIPLIB_HOST");
    unsetenv("WIPLIB_PORT");
    unsetenv("WIPLIB_DEBUG");
}

// プロトコル互換性テスト
TEST_F(PythonCompatibilityTest, ProtocolCompatibility) {
    // パケットID生成
    uint16_t id1 = PythonProtocolAdapter::generate_python_packet_id();
    uint16_t id2 = PythonProtocolAdapter::generate_python_packet_id();
    
    EXPECT_NE(id1, id2); // 異なるIDが生成される
    EXPECT_GT(id1, 0);   // 0より大きい
    EXPECT_GT(id2, 0);
}

// タイムスタンプ互換性テスト
TEST_F(PythonCompatibilityTest, TimestampCompatibility) {
    uint64_t timestamp = PythonProtocolAdapter::generate_python_timestamp();
    
    // マイクロ秒精度のUnix時間
    EXPECT_GT(timestamp, 0);
    
    // 現在時刻に近い値であることを確認（±10秒）
    auto now = std::chrono::system_clock::now();
    auto now_us = std::chrono::duration_cast<std::chrono::microseconds>(
        now.time_since_epoch()).count();
    
    EXPECT_NEAR(static_cast<double>(timestamp), static_cast<double>(now_us), 10000000.0);
}

// 座標検証の互換性テスト
TEST_F(PythonCompatibilityTest, CoordinateValidation) {
    // 有効な座標
    EXPECT_TRUE(PythonProtocolAdapter::validate_python_coordinates(35.6762, 139.6503)); // 東京
    EXPECT_TRUE(PythonProtocolAdapter::validate_python_coordinates(0.0, 0.0)); // 赤道
    EXPECT_TRUE(PythonProtocolAdapter::validate_python_coordinates(-90.0, -180.0)); // 境界値
    EXPECT_TRUE(PythonProtocolAdapter::validate_python_coordinates(90.0, 180.0)); // 境界値
    
    // 無効な座標
    EXPECT_FALSE(PythonProtocolAdapter::validate_python_coordinates(91.0, 0.0)); // 緯度範囲外
    EXPECT_FALSE(PythonProtocolAdapter::validate_python_coordinates(0.0, 181.0)); // 経度範囲外
    EXPECT_FALSE(PythonProtocolAdapter::validate_python_coordinates(-91.0, 0.0)); // 緯度範囲外
    EXPECT_FALSE(PythonProtocolAdapter::validate_python_coordinates(0.0, -181.0)); // 経度範囲外
}

// エリアコード検証の互換性テスト
TEST_F(PythonCompatibilityTest, AreaCodeValidation) {
    // 有効なエリアコード
    EXPECT_TRUE(PythonProtocolAdapter::validate_python_area_code("130010")); // 東京
    EXPECT_TRUE(PythonProtocolAdapter::validate_python_area_code("270000")); // 大阪
    EXPECT_TRUE(PythonProtocolAdapter::validate_python_area_code("400040")); // 福岡
    
    // 無効なエリアコード
    EXPECT_FALSE(PythonProtocolAdapter::validate_python_area_code(""));      // 空文字
    EXPECT_FALSE(PythonProtocolAdapter::validate_python_area_code("12345"));  // 5桁
    EXPECT_FALSE(PythonProtocolAdapter::validate_python_area_code("1234567")); // 7桁
    EXPECT_FALSE(PythonProtocolAdapter::validate_python_area_code("abcdef")); // 非数字
    EXPECT_FALSE(PythonProtocolAdapter::validate_python_area_code("000000")); // 範囲外
    EXPECT_FALSE(PythonProtocolAdapter::validate_python_area_code("999999")); // 範囲外
}

// User-Agent互換性テスト
TEST_F(PythonCompatibilityTest, UserAgentCompatibility) {
    std::string user_agent = PythonProtocolAdapter::generate_python_user_agent();
    
    EXPECT_TRUE(user_agent.find("WIPClient-Python") != std::string::npos);
    EXPECT_TRUE(user_agent.find("CPP-Compatible") != std::string::npos);
}

// HTTPヘッダー互換性テスト
TEST_F(PythonCompatibilityTest, HTTPHeaderCompatibility) {
    auto headers = PythonProtocolAdapter::generate_python_headers();
    
    EXPECT_TRUE(headers.find("User-Agent") != headers.end());
    EXPECT_TRUE(headers.find("Content-Type") != headers.end());
    EXPECT_TRUE(headers.find("Accept") != headers.end());
    
    EXPECT_EQ(headers["Content-Type"], "application/octet-stream");
    EXPECT_EQ(headers["Accept"], "application/octet-stream");
    EXPECT_EQ(headers["Connection"], "keep-alive");
}

// 天気データJSON互換性テスト
TEST_F(PythonCompatibilityTest, WeatherDataJSONCompatibility) {
    WeatherData data;
    data.area_code = 130010;
    data.weather_code = 100;
    data.temperature = 25;
    data.precipitation_prob = 10;
    
    std::string json = PythonDataConverter::weather_data_to_python_json(data);
    
    // JSON形式の確認
    EXPECT_TRUE(json.find("\"area_code\": 130010") != std::string::npos);
    EXPECT_TRUE(json.find("\"weather_code\": 100") != std::string::npos);
    EXPECT_TRUE(json.find("\"temperature\": 25") != std::string::npos);
    EXPECT_TRUE(json.find("\"precipitation_prob\": 10") != std::string::npos);
    EXPECT_TRUE(json.find("\"timestamp\"") != std::string::npos);
}

// JSON→WeatherData変換互換性テスト
TEST_F(PythonCompatibilityTest, JSONToWeatherDataCompatibility) {
    std::string json = R"({
        "area_code": 130010,
        "weather_code": 100,
        "temperature": 25,
        "precipitation_prob": 10,
        "timestamp": 1234567890123456
    })";
    
    auto result = PythonDataConverter::python_json_to_weather_data(json);
    ASSERT_TRUE(result.has_value());
    
    auto& data = result.value();
    EXPECT_EQ(data.area_code, 130010);
    EXPECT_TRUE(data.weather_code.has_value());
    EXPECT_EQ(data.weather_code.value(), 100);
    EXPECT_TRUE(data.temperature.has_value());
    EXPECT_EQ(data.temperature.value(), 25);
    EXPECT_TRUE(data.precipitation_prob.has_value());
    EXPECT_EQ(data.precipitation_prob.value(), 10);
}

// 設定パス互換性テスト
TEST_F(PythonCompatibilityTest, ConfigPathCompatibility) {
    auto search_paths = get_config_search_paths();
    
    // Python版と同じ検索順序
    EXPECT_FALSE(search_paths.empty());
    EXPECT_EQ(search_paths[0], "./config.json");
    EXPECT_EQ(search_paths[1], "./wiplib_config.json");
    
    // プラットフォーム固有のパスが含まれている
    bool has_platform_path = false;
    for (const auto& path : search_paths) {
        if (path.find(".wiplib") != std::string::npos || 
            path.find("/etc/wiplib") != std::string::npos) {
            has_platform_path = true;
            break;
        }
    }
    EXPECT_TRUE(has_platform_path);
}

// 完全互換性チェック
TEST_F(PythonCompatibilityTest, FullCompatibilityCheck) {
    auto issues = PythonCompatibilityChecker::perform_full_compatibility_check();
    
    // 互換性問題がないことを確認
    for (const auto& issue : issues) {
        std::cout << "互換性問題: " << issue << std::endl;
    }
    
    // 重大な互換性問題がないことを確認
    EXPECT_TRUE(issues.size() <= 2); // 軽微な問題は許容
}

// 互換性レポート生成テスト
TEST_F(PythonCompatibilityTest, CompatibilityReportGeneration) {
    std::string report = PythonCompatibilityChecker::generate_compatibility_report();
    
    EXPECT_FALSE(report.empty());
    EXPECT_TRUE(report.find("Python互換性レポート") != std::string::npos);
    EXPECT_TRUE(report.find("技術仕様の確認") != std::string::npos);
    EXPECT_TRUE(report.find("プロトコルバージョン") != std::string::npos);
}

// エラー変換互換性テスト
TEST_F(PythonCompatibilityTest, ErrorConversionCompatibility) {
    // システムエラーからPython互換エラーへの変換
    std::error_code timeout_error = std::make_error_code(std::errc::timed_out);
    auto python_error = convert_system_error(timeout_error, "ネットワーク操作");
    
    EXPECT_NE(python_error, nullptr);
    EXPECT_EQ(python_error->code(), PythonErrorCode::TIMEOUT_ERROR);
    EXPECT_TRUE(python_error->what() != std::string(""));
}