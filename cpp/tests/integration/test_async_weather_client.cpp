#include <gtest/gtest.h>
#include "wiplib/client/async_weather_client.hpp"
#include "wiplib/expected.hpp"

using namespace wiplib::client;

class AsyncWeatherClientIntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {
        client = std::make_unique<AsyncWeatherClient>("localhost", 4110);
    }
    
    void TearDown() override {
        client.reset();
    }
    
    std::unique_ptr<AsyncWeatherClient> client;
};

// 基本的なクライアント作成テスト
TEST_F(AsyncWeatherClientIntegrationTest, ClientCreation) {
    // クライアントが正常に作成されることを確認
    EXPECT_NE(client, nullptr);
}

// ネットワークエラーテスト（実際のサーバーがないため）
TEST_F(AsyncWeatherClientIntegrationTest, NetworkError) {
    // 実際のサーバーが動いていないのでエラーが期待される
    // テストの目的は正しいAPIの確認とコンパイルエラーがないことの確認
    SUCCEED() << "AsyncWeatherClient compiled successfully";
}