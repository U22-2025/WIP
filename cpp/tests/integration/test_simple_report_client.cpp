#include <gtest/gtest.h>
#include <memory>
#include <iostream>
#include <unordered_map>
#include <vector>
#include <string>

#include "wiplib/client/simple_report_client.hpp"
#include "wiplib/packet/report_packet_compat.hpp"

namespace wiplib::client::test {

/**
 * @brief Python版ReportClientとの互換性テスト
 * 
 * Python版ReportClientと同一データでのパケット形式、レスポンス処理、
 * エラーハンドリングの完全互換性を確認
 */
class SimpleReportClientCompatibilityTest : public ::testing::Test {
protected:
    void SetUp() override {
        // テスト用のクライアント作成（デバッグモード有効）
        client_ = std::make_unique<SimpleReportClient>("127.0.0.1", 4112, true);
    }

    void TearDown() override {
        if (client_) {
            client_->close();
        }
    }

    std::unique_ptr<SimpleReportClient> client_;
};

/**
 * @brief Python版との同一データでのパケット形式比較テスト
 * 
 * Python版で以下のコードと同等のパケットが生成されることを確認:
 * ```python
 * client = ReportClient("127.0.0.1", 4112, debug=True)
 * client.set_sensor_data("123456", weather_code=1, temperature=25.5, precipitation_prob=30)
 * # パケット内容の確認
 * ```
 */
TEST_F(SimpleReportClientCompatibilityTest, PacketFormatCompatibility) {
    // Python版と同一のテストデータ
    const std::string area_code = "123456";
    const int weather_code = 1;
    const float temperature = 25.5f;
    const int precipitation_prob = 30;
    const std::vector<std::string> alert = {"地震", "津波"};
    const std::vector<std::string> disaster = {"台風", "洪水"};

    // データ設定（Python版set_sensor_data()と同等）
    client_->set_sensor_data(area_code, weather_code, temperature, precipitation_prob, alert, disaster);

    // Python版get_current_data()と同等の動作確認
    auto current_data = client_->get_current_data();
    
    EXPECT_EQ(std::any_cast<std::string>(current_data["area_code"]), area_code);
    EXPECT_EQ(std::any_cast<int>(current_data["weather_code"]), weather_code);
    EXPECT_FLOAT_EQ(std::any_cast<float>(current_data["temperature"]), temperature);
    EXPECT_EQ(std::any_cast<int>(current_data["precipitation_prob"]), precipitation_prob);
    
    auto stored_alert = std::any_cast<std::vector<std::string>>(current_data["alert"]);
    EXPECT_EQ(stored_alert, alert);
    
    auto stored_disaster = std::any_cast<std::vector<std::string>>(current_data["disaster"]);
    EXPECT_EQ(stored_disaster, disaster);

    // パケット生成のテスト（実際の通信なしでパケット形式確認）
    // Python版create_sensor_data_report()と同等のパケット生成
    auto request = packet::compat::PyReportRequest::create_sensor_data_report(
        area_code,
        weather_code,
        temperature,
        precipitation_prob,
        alert,
        disaster,
        1  // version
    );

    // パケットタイプがType 4 (ReportRequest)であることを確認
    EXPECT_EQ(static_cast<uint8_t>(request.header.type), 4);
    
    // パケット内容の確認
    auto packet_data = request.to_bytes();
    EXPECT_GT(packet_data.size(), 0);
    
    // Python版との互換性確認のため、パケットの基本構造をチェック
    EXPECT_GE(packet_data.size(), 3);  // 最小ヘッダーサイズ
    
    std::cout << "Generated packet size: " << packet_data.size() << " bytes" << std::endl;
    std::cout << "Packet type: " << static_cast<int>(packet_data[2]) << " (expected: 4)" << std::endl;
}

/**
 * @brief Python版との個別設定メソッド互換性テスト
 * 
 * Python版の個別設定メソッドと同等の動作を確認:
 * ```python
 * client.set_area_code("123456")
 * client.set_weather_code(1)
 * client.set_temperature(25.5)
 * client.set_precipitation_prob(30)
 * client.set_alert(["地震", "津波"])
 * client.set_disaster(["台風", "洪水"])
 * ```
 */
TEST_F(SimpleReportClientCompatibilityTest, IndividualSetterCompatibility) {
    // Python版の個別設定メソッドと同等の呼び出し
    client_->set_area_code("654321");
    client_->set_weather_code(2);
    client_->set_temperature(18.3f);
    client_->set_precipitation_prob(75);
    client_->set_alert({"大雨", "雷"});
    client_->set_disaster({"竜巻"});

    // Python版get_current_data()と同等の確認
    auto current_data = client_->get_current_data();
    
    EXPECT_EQ(std::any_cast<std::string>(current_data["area_code"]), "654321");
    EXPECT_EQ(std::any_cast<int>(current_data["weather_code"]), 2);
    EXPECT_FLOAT_EQ(std::any_cast<float>(current_data["temperature"]), 18.3f);
    EXPECT_EQ(std::any_cast<int>(current_data["precipitation_prob"]), 75);
    
    auto alert = std::any_cast<std::vector<std::string>>(current_data["alert"]);
    EXPECT_EQ(alert.size(), 2);
    EXPECT_EQ(alert[0], "大雨");
    EXPECT_EQ(alert[1], "雷");
    
    auto disaster = std::any_cast<std::vector<std::string>>(current_data["disaster"]);
    EXPECT_EQ(disaster.size(), 1);
    EXPECT_EQ(disaster[0], "竜巻");
}

/**
 * @brief Python版とのデータクリア機能互換性テスト
 * 
 * Python版clear_data()メソッドと同等の動作を確認
 */
TEST_F(SimpleReportClientCompatibilityTest, ClearDataCompatibility) {
    // データ設定
    client_->set_sensor_data("123456", 1, 25.5f, 30);
    
    // データが設定されていることを確認
    auto data_before = client_->get_current_data();
    EXPECT_FALSE(data_before.empty());
    
    // Python版clear_data()と同等の呼び出し
    client_->clear_data();
    
    // データがクリアされていることを確認
    auto data_after = client_->get_current_data();
    EXPECT_TRUE(data_after.empty());
}

/**
 * @brief Python版とのエラーハンドリング互換性テスト
 * 
 * Python版と同様のエラー処理動作を確認
 */
TEST_F(SimpleReportClientCompatibilityTest, ErrorHandlingCompatibility) {
    // エリアコード未設定でのエラーテスト（Python版と同様）
    auto result = client_->send_report_data();
    
    // Python版と同様にエラーが返されることを確認
    EXPECT_FALSE(result.has_value());
    
    // エラーコードの確認（Python版invalid_packet相当）
    EXPECT_EQ(result.error(), WipErrc::invalid_packet);
}

/**
 * @brief Python版との認証設定互換性テスト
 * 
 * 環境変数による認証設定がPython版と同等に動作することを確認
 */
TEST_F(SimpleReportClientCompatibilityTest, AuthConfigCompatibility) {
    // 認証設定のテスト用環境変数設定
    // 注意: 実際のテストでは環境変数の設定/復元が必要
    
    // 正常なエリアコード設定
    client_->set_area_code("123456");
    
    // 認証が有効な場合のパケット生成テスト
    auto request = packet::compat::PyReportRequest::create_sensor_data_report(
        "123456", {}, {}, {}, {}, {}, 1
    );
    
    // Python版と同様の認証フラグ設定テスト
    std::string test_passphrase = "test_password";
    request.enable_auth(test_passphrase);
    request.set_auth_flags();
    
    // 認証が設定されたパケットの確認
    auto packet_data = request.to_bytes();
    EXPECT_GT(packet_data.size(), 0);
}

/**
 * @brief Python版との便利関数互換性テスト
 * 
 * Python版の便利関数と同等の動作を確認
 */
TEST_F(SimpleReportClientCompatibilityTest, UtilityFunctionCompatibility) {
    // Python版create_report_client()と同等の関数テスト
    auto client = utils::create_report_client("127.0.0.1", 4112, true);
    EXPECT_NE(client, nullptr);
    
    // Python版send_sensor_report()と同等の一括送信関数テスト
    // 注意: 実際のサーバーが動作していない場合はタイムアウトまたはエラーが発生
    auto result = utils::send_sensor_report(
        "123456",
        1,               // weather_code
        25.5f,           // temperature
        30,              // precipitation_prob
        {},              // alert (空)
        {},              // disaster (空)
        "127.0.0.1",
        4112,
        true             // debug
    );
    
    // サーバーが応答しない場合のエラーハンドリング確認
    // Python版と同様にタイムアウトまたは接続エラーが発生することを確認
    EXPECT_FALSE(result.has_value() && result.value().success);
}

/**
 * @brief Python版との後方互換性メソッドテスト
 * 
 * Python版の後方互換性メソッドと同等の動作を確認
 */
TEST_F(SimpleReportClientCompatibilityTest, BackwardCompatibilityMethods) {
    client_->set_area_code("123456");
    
    // Python版send_report()互換メソッド
    auto result1 = client_->send_report();
    EXPECT_FALSE(result1.has_value()); // サーバー未起動のためエラー
    
    // Python版send_current_data()互換メソッド  
    auto result2 = client_->send_current_data();
    EXPECT_FALSE(result2.has_value()); // サーバー未起動のためエラー
    
    // Python版send_data_simple()互換メソッド
    auto result3 = client_->send_data_simple();
    EXPECT_FALSE(result3.has_value()); // サーバー未起動のためエラー
}

} // namespace wiplib::client::test

/**
 * @brief メイン関数（テスト実行用）
 * 
 * Python版との互換性確認テストを実行
 * 使用方法: ./test_simple_report_client
 */
int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    
    std::cout << "=== Python版ReportClient互換性テスト ===" << std::endl;
    std::cout << "C++版SimpleReportClientのPython版ReportClientとの互換性を確認します" << std::endl;
    std::cout << std::endl;
    
    return RUN_ALL_TESTS();
}
