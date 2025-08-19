#include <gtest/gtest.h>
#include "wiplib/client/client.hpp"
#include "wiplib/expected.hpp"

using namespace wiplib::client;

class ClientIntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {
        // テスト用クライアント作成（デフォルト設定）
        client = std::make_unique<Client>();
        client->set_coordinates(35.6762, 139.6503);  // 東京
    }
    
    void TearDown() override {
        if (client) {
            client->close();
        }
        client.reset();
    }
    
    std::unique_ptr<Client> client;
};

// 基本的なクライアント作成テスト
TEST_F(ClientIntegrationTest, ClientCreation) {
    // プロパティアクセスのテスト
    auto lat = client->latitude();
    auto lon = client->longitude();
    
    EXPECT_TRUE(lat.has_value());
    EXPECT_TRUE(lon.has_value());
    EXPECT_DOUBLE_EQ(lat.value(), 35.6762);
    EXPECT_DOUBLE_EQ(lon.value(), 139.6503);
}

// 座標設定のテスト
TEST_F(ClientIntegrationTest, SetCoordinates) {
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

// サーバー設定のテスト
TEST_F(ClientIntegrationTest, SetServer) {
    // デフォルトホストでのサーバー設定
    client->set_server("localhost");
    
    // ポート指定でのサーバー設定
    client->set_server("localhost", 4110);
    
    // 設定の変更が成功することを確認（例外が発生しない）
    SUCCEED();
}

// 天気データ取得テスト（ネットワークエラーが期待される）
TEST_F(ClientIntegrationTest, GetWeatherNetworkError) {
    // 実際のサーバーが動いていないのでネットワークエラーが期待される
    auto result = client->get_weather();
    
    // エラーが返ることを確認
    EXPECT_FALSE(result.has_value());
}

// 座標による天気データ取得テスト
TEST_F(ClientIntegrationTest, GetWeatherByCoordinates) {
    double test_lat = 34.0522;   // ロサンゼルス
    double test_lon = -118.2437;
    
    // 実際のサーバーが動いていないのでネットワークエラーが期待される
    auto result = client->get_weather_by_coordinates(test_lat, test_lon);
    
    // エラーが返ることを確認
    EXPECT_FALSE(result.has_value());
}

// エリアコードによる天気データ取得テスト
TEST_F(ClientIntegrationTest, GetWeatherByAreaCode) {
    std::string test_area_code = "130010";  // 東京
    
    // 実際のサーバーが動いていないのでネットワークエラーが期待される
    auto result = client->get_weather_by_area_code(test_area_code);
    
    // エラーが返ることを確認
    EXPECT_FALSE(result.has_value());
}

// オプション引数のテスト
TEST_F(ClientIntegrationTest, WeatherOptionsTest) {
    // 各オプションを設定してリクエスト
    auto result = client->get_weather(
        true,   // weather
        true,   // temperature
        false,  // precipitation_prob
        false,  // alert
        false,  // disaster
        0,      // day
        false   // proxy
    );
    
    // 実際のサーバーが動いていないのでエラーが期待される
    EXPECT_FALSE(result.has_value());
}

// クライアント状態取得のテスト
TEST_F(ClientIntegrationTest, GetState) {
    auto state = client->get_state();
    
    // 状態の基本フィールドが設定されていることを確認
    EXPECT_TRUE(state.latitude.has_value());
    EXPECT_TRUE(state.longitude.has_value());
    EXPECT_DOUBLE_EQ(state.latitude.value(), 35.6762);
    EXPECT_DOUBLE_EQ(state.longitude.value(), 139.6503);
}

// 無効な座標のテスト
TEST_F(ClientIntegrationTest, InvalidCoordinates) {
    // 範囲外の座標を設定
    client->set_coordinates(200.0, 200.0);  // 無効な座標
    
    auto result = client->get_weather();
    
    // エラーが返ることを確認
    EXPECT_FALSE(result.has_value());
}

// クライアントのクローズ機能テスト
TEST_F(ClientIntegrationTest, CloseConnection) {
    // クローズ前の状態確認
    auto state_before = client->get_state();
    EXPECT_TRUE(state_before.latitude.has_value());
    
    // 接続をクローズ
    client->close();
    
    // クローズ後も状態は保持される
    auto state_after = client->get_state();
    EXPECT_TRUE(state_after.latitude.has_value());
    EXPECT_DOUBLE_EQ(state_after.latitude.value(), state_before.latitude.value());
}

// RAII サポートのテスト
TEST_F(ClientIntegrationTest, RAIISupport) {
    // operator() のテスト
    auto& client_ref = (*client)();
    EXPECT_EQ(&client_ref, client.get());
    
    // release() のテスト（close()の別名）
    client->release();
    
    // release後も基本的な操作は可能
    auto state = client->get_state();
    EXPECT_TRUE(state.latitude.has_value());
}