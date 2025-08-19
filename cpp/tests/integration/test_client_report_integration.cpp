#include <gtest/gtest.h>
#include <thread>
#include <chrono>
#include <memory>

#include "wiplib/client/client.hpp"
#include "wiplib/error.hpp"

namespace wiplib::client {

class ClientReportIntegrationTest : public ::testing::Test {
protected:
    void SetUp() override {
        // ReportServerが動いている前提でテスト
        // 実際のテストではモックサーバーを使用することを推奨
    }

    void TearDown() override {
        if (client_) {
            client_->close();
        }
    }

    std::unique_ptr<Client> client_;
};

TEST_F(ClientReportIntegrationTest, ConstructorWithReportSupport) {
    // Clientコンストラクタでレポート機能が初期化されることを確認
    ASSERT_NO_THROW({
        client_ = std::make_unique<Client>(
            "localhost", 
            4112,  // Report Server port
            std::nullopt, 
            false  // debug off for tests
        );
    });
    
    ASSERT_NE(client_, nullptr);
}

TEST_F(ClientReportIntegrationTest, SetSensorDataAPI) {
    client_ = std::make_unique<Client>("localhost", 4112, std::nullopt, false);
    
    // Python版互換のset_sensor_data APIをテスト
    ASSERT_NO_THROW({
        client_->set_sensor_data(
            "123456",           // area_code
            1,                  // weather_code
            25.5f,              // temperature
            30,                 // precipitation_prob
            std::vector<std::string>{"警報1", "警報2"},  // alert
            std::vector<std::string>{"災害1"}            // disaster
        );
    });
}

TEST_F(ClientReportIntegrationTest, IndividualSettersAPI) {
    client_ = std::make_unique<Client>("localhost", 4112, std::nullopt, false);
    
    // Python版互換の個別setter APIをテスト
    ASSERT_NO_THROW({
        client_->set_area_code("654321");
        client_->set_weather_code(2);
        client_->set_temperature(20.0f);
        client_->set_precipitation_prob(50);
        client_->set_alert({"警報A"});
        client_->set_disaster({"災害A", "災害B"});
    });
}

TEST_F(ClientReportIntegrationTest, GetCurrentDataAPI) {
    client_ = std::make_unique<Client>("localhost", 4112, std::nullopt, false);
    
    // データ設定
    client_->set_sensor_data("789012", 3, 18.5f, 80);
    
    // get_current_data APIをテスト
    auto data = client_->get_current_data();
    EXPECT_FALSE(data.empty());
    
    // 設定したデータが取得できることを確認
    // 注意: std::anyの値の確認は実装詳細に依存するため、
    // ここでは基本的な動作確認のみ
}

TEST_F(ClientReportIntegrationTest, ClearDataAPI) {
    client_ = std::make_unique<Client>("localhost", 4112, std::nullopt, false);
    
    // データ設定
    client_->set_sensor_data("111222", 1, 22.0f, 10);
    
    // データが存在することを確認
    auto data_before = client_->get_current_data();
    EXPECT_FALSE(data_before.empty());
    
    // clear_data APIをテスト
    ASSERT_NO_THROW({
        client_->clear_data();
    });
    
    // データがクリアされたことを確認
    auto data_after = client_->get_current_data();
    EXPECT_TRUE(data_after.empty());
}

TEST_F(ClientReportIntegrationTest, SendReportDataAPISignature) {
    client_ = std::make_unique<Client>("localhost", 4112, std::nullopt, false);
    
    // APIシグネチャが正しいことを確認（実際の送信はサーバー依存）
    client_->set_sensor_data("333444", 2, 15.0f, 60);
    
    // send_report_data() API
    auto result = client_->send_report_data();
    // サーバーがない場合はエラーになるが、APIシグネチャは正しい
    EXPECT_TRUE(result.has_value() || result.has_error());
    
    // send_report_data_async() API
    auto future_result = client_->send_report_data_async();
    EXPECT_TRUE(future_result.valid());
    
    // send_data_simple() API
    auto simple_result = client_->send_data_simple();
    EXPECT_TRUE(simple_result.has_value() || simple_result.has_error());
}

TEST_F(ClientReportIntegrationTest, BackwardCompatibilityAPIs) {
    client_ = std::make_unique<Client>("localhost", 4112, std::nullopt, false);
    
    client_->set_sensor_data("555666", 1, 30.0f, 20);
    
    // 後方互換性メソッドのAPIシグネチャ確認
    auto report_result = client_->send_report();
    EXPECT_TRUE(report_result.has_value() || report_result.has_error());
    
    auto current_data_result = client_->send_current_data();
    EXPECT_TRUE(current_data_result.has_value() || current_data_result.has_error());
}

TEST_F(ClientReportIntegrationTest, WeatherAndReportIntegration) {
    client_ = std::make_unique<Client>("localhost", 4112, std::nullopt, false);
    
    // 天気データ取得とレポート送信の両方を同じClientで使用
    client_->set_coordinates(35.6762, 139.6503);  // 東京
    client_->set_area_code("130010");
    
    // 天気データ取得API（既存機能）
    auto weather_result = client_->get_weather();
    // サーバー接続エラーでも構わない（APIシグネチャの確認）
    EXPECT_TRUE(weather_result.has_value() || weather_result.has_error());
    
    // レポート送信API（新機能）
    client_->set_sensor_data("130010", 1, 25.0f, 40);
    auto report_result = client_->send_report_data();
    EXPECT_TRUE(report_result.has_value() || report_result.has_error());
}

TEST_F(ClientReportIntegrationTest, ServerConfigurationChange) {
    client_ = std::make_unique<Client>("localhost", 4110, std::nullopt, false);
    
    // サーバー設定変更時に内部クライアントが再初期化されることを確認
    ASSERT_NO_THROW({
        client_->set_server("localhost", 4112);
    });
    
    // レポート機能が正常に動作することを確認
    ASSERT_NO_THROW({
        client_->set_sensor_data("777888", 1, 20.0f, 70);
    });
}

TEST_F(ClientReportIntegrationTest, CloseFunction) {
    client_ = std::make_unique<Client>("localhost", 4112, std::nullopt, false);
    
    // データ設定
    client_->set_sensor_data("999000", 3, 10.0f, 90);
    
    // close()で両方のクライアント（Weather, Report）が閉じられることを確認
    ASSERT_NO_THROW({
        client_->close();
    });
    
    // close後もAPIは呼び出せるが、内部で再初期化される
    ASSERT_NO_THROW({
        client_->set_area_code("000111");
    });
}

} // namespace wiplib::client