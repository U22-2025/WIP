#include <gtest/gtest.h>
#include "wiplib/client/weather_client.hpp"
#include "wiplib/expected.hpp"

using namespace wiplib::client;

class WeatherClientIntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {
        // テスト用クライアント作成
        client = std::make_unique<WeatherClient>("localhost", 4110);
    }
    
    void TearDown() override {
        client.reset();
    }
    
    std::unique_ptr<WeatherClient> client;
};

// 基本的な座標による天気データ取得テスト
TEST_F(WeatherClientIntegrationTest, WeatherDataByCoordinates) {
    double latitude = 35.6762;
    double longitude = 139.6503;  // 東京の座標
    
    QueryOptions options;
    options.weather = true;
    options.temperature = true;
    
    // 実際のサーバーがないのでエラーが期待される
    auto result = client->get_weather_by_coordinates(latitude, longitude, options);
    
    // ネットワークエラーでfalseが返ることを確認
    EXPECT_FALSE(result.has_value());
}

// 基本的なエリアコードによる天気データ取得テスト
TEST_F(WeatherClientIntegrationTest, WeatherDataByAreaCode) {
    QueryOptions options;
    options.weather = true;
    options.temperature = true;
    
    // 実際のサーバーがないのでエラーが期待される
    auto result = client->get_weather_by_area_code("130010", options);
    
    // ネットワークエラーでfalseが返ることを確認
    EXPECT_FALSE(result.has_value());
}

// QueryOptionsの設定テスト
TEST_F(WeatherClientIntegrationTest, QueryOptionsConfiguration) {
    QueryOptions options;
    
    // デフォルト値の確認
    EXPECT_TRUE(options.weather);
    EXPECT_TRUE(options.temperature);
    EXPECT_FALSE(options.precipitation_prob);
    EXPECT_FALSE(options.alerts);
    EXPECT_FALSE(options.disaster);
    EXPECT_EQ(options.day, 0);
    
    // オプション設定
    options.precipitation_prob = true;
    options.alerts = true;
    options.day = 1;
    
    EXPECT_TRUE(options.precipitation_prob);
    EXPECT_TRUE(options.alerts);
    EXPECT_EQ(options.day, 1);
}

// WeatherResultの構造テスト
TEST_F(WeatherClientIntegrationTest, WeatherResultStructure) {
    WeatherResult result;
    
    // デフォルト値の確認
    EXPECT_EQ(result.area_code, 0);
    EXPECT_FALSE(result.weather_code.has_value());
    EXPECT_FALSE(result.temperature.has_value());
    EXPECT_FALSE(result.precipitation_prob.has_value());
    
    // 値の設定
    result.area_code = 130010;
    result.weather_code = 100;
    result.temperature = 25;
    result.precipitation_prob = 10;
    
    EXPECT_EQ(result.area_code, 130010);
    EXPECT_TRUE(result.weather_code.has_value());
    EXPECT_EQ(result.weather_code.value(), 100);
    EXPECT_TRUE(result.temperature.has_value());
    EXPECT_EQ(result.temperature.value(), 25);
    EXPECT_TRUE(result.precipitation_prob.has_value());
    EXPECT_EQ(result.precipitation_prob.value(), 10);
}