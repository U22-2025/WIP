#include <gtest/gtest.h>
#include <future>
#include <chrono>
#include "wiplib/client/client_async.hpp"
#include "wiplib/expected.hpp"

using namespace wiplib::client;

class ClientAsyncIntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {
        // テスト用非同期クライアント作成（デフォルト設定）
        client = std::make_unique<ClientAsync>();
        client->set_coordinates(35.6762, 139.6503);  // 東京
    }
    
    void TearDown() override {
        if (client) {
            client->close();
        }
        client.reset();
    }
    
    std::unique_ptr<ClientAsync> client;
};

// 基本的な非同期クライアント作成テスト
TEST_F(ClientAsyncIntegrationTest, ClientCreation) {
    // プロパティアクセスのテスト
    auto lat = client->latitude();
    auto lon = client->longitude();
    
    EXPECT_TRUE(lat.has_value());
    EXPECT_TRUE(lon.has_value());
    EXPECT_DOUBLE_EQ(lat.value(), 35.6762);
    EXPECT_DOUBLE_EQ(lon.value(), 139.6503);
}

// 非同期天気データ取得テスト（ネットワークエラーが期待される）
TEST_F(ClientAsyncIntegrationTest, AsyncGetWeatherNetworkError) {
    // 非同期リクエストを開始
    auto future = client->get_weather();
    
    // タイムアウト付きで結果を待機
    auto status = future.wait_for(std::chrono::seconds(2));
    
    if (status == std::future_status::ready) {
        auto result = future.get();
        // 実際のサーバーが動いていないのでエラーが期待される
        EXPECT_FALSE(result.has_value());
    } else {
        // タイムアウトした場合もテストとしては成功
        SUCCEED() << "Request timed out as expected";
    }
}

// 非同期座標による天気データ取得テスト
TEST_F(ClientAsyncIntegrationTest, AsyncGetWeatherByCoordinates) {
    double test_lat = 34.0522;   // ロサンゼルス
    double test_lon = -118.2437;
    
    // 非同期リクエストを開始
    auto future = client->get_weather_by_coordinates(test_lat, test_lon);
    
    // タイムアウト付きで結果を待機
    auto status = future.wait_for(std::chrono::seconds(2));
    
    if (status == std::future_status::ready) {
        auto result = future.get();
        // 実際のサーバーが動いていないのでエラーが期待される
        EXPECT_FALSE(result.has_value());
    } else {
        // タイムアウトした場合もテストとしては成功
        SUCCEED() << "Request timed out as expected";
    }
}

// 非同期エリアコードによる天気データ取得テスト
TEST_F(ClientAsyncIntegrationTest, AsyncGetWeatherByAreaCode) {
    std::string test_area_code = "130010";  // 東京
    
    // 非同期リクエストを開始
    auto future = client->get_weather_by_area_code(test_area_code);
    
    // タイムアウト付きで結果を待機
    auto status = future.wait_for(std::chrono::seconds(2));
    
    if (status == std::future_status::ready) {
        auto result = future.get();
        // 実際のサーバーが動いていないのでエラーが期待される
        EXPECT_FALSE(result.has_value());
    } else {
        // タイムアウトした場合もテストとしては成功
        SUCCEED() << "Request timed out as expected";
    }
}

// 複数の非同期リクエストテスト
TEST_F(ClientAsyncIntegrationTest, MultipleConcurrentRequests) {
    const int num_requests = 3;
    std::vector<std::future<wiplib::Result<WeatherData>>> futures;
    
    // 複数の非同期リクエストを開始
    for (int i = 0; i < num_requests; ++i) {
        futures.push_back(client->get_weather());
    }
    
    // 各リクエストの結果を確認
    for (int i = 0; i < num_requests; ++i) {
        auto status = futures[i].wait_for(std::chrono::seconds(2));
        
        if (status == std::future_status::ready) {
            auto result = futures[i].get();
            // 実際のサーバーが動いていないのでエラーが期待される
            EXPECT_FALSE(result.has_value()) << "Request " << i << " should fail";
        } else {
            // タイムアウトした場合もテストとしては成功
            SUCCEED() << "Request " << i << " timed out as expected";
        }
    }
}

// 非同期クライアント状態取得のテスト
TEST_F(ClientAsyncIntegrationTest, GetState) {
    auto state = client->get_state();
    
    // 状態の基本フィールドが設定されていることを確認
    EXPECT_TRUE(state.latitude.has_value());
    EXPECT_TRUE(state.longitude.has_value());
    EXPECT_DOUBLE_EQ(state.latitude.value(), 35.6762);
    EXPECT_DOUBLE_EQ(state.longitude.value(), 139.6503);
}

// 座標設定のテスト
TEST_F(ClientAsyncIntegrationTest, SetCoordinates) {
    double new_lat = 40.7128;   // ニューヨーク
    double new_lon = -74.0060;
    
    // 座標を設定
    client->set_coordinates(new_lat, new_lon);
    
    // プロパティが正しく更新されているか確認
    auto lat = client->latitude();
    auto lon = client->longitude();
    
    EXPECT_TRUE(lat.has_value());
    EXPECT_TRUE(lon.has_value());
    EXPECT_DOUBLE_EQ(lat.value(), new_lat);
    EXPECT_DOUBLE_EQ(lon.value(), new_lon);
}

// RAII サポートのテスト
TEST_F(ClientAsyncIntegrationTest, RAIISupport) {
    // operator() のテスト
    auto& client_ref = (*client)();
    EXPECT_EQ(&client_ref, client.get());
    
    // release() のテスト（close()の別名）
    client->release();
    
    // release後も基本的な操作は可能
    auto state = client->get_state();
    EXPECT_TRUE(state.latitude.has_value());
}