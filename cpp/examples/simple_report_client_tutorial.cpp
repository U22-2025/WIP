/**
 * @file simple_report_client_tutorial.cpp
 * @brief Python版ReportClient互換のC++版SimpleReportClient使用例
 * 
 * Python版ReportClientと完全互換のAPIを使用した
 * センサーデータレポート送信のチュートリアル
 */

#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <thread>

#include "wiplib/client/simple_report_client.hpp"

void print_separator(const std::string& title) {
    std::cout << "\n=== " << title << " ===" << std::endl;
}

void print_result(const wiplib::Result<wiplib::client::ReportResult>& result) {
    if (result.has_value()) {
        auto& r = result.value();
        std::cout << "✅ 送信成功!" << std::endl;
        std::cout << "   タイプ: " << r.type << std::endl;
        std::cout << "   パケットID: " << (r.packet_id ? std::to_string(*r.packet_id) : "N/A") << std::endl;
        std::cout << "   レスポンス時間: " << r.response_time_ms << "ms" << std::endl;
        if (r.timestamp) {
            std::cout << "   タイムスタンプ: " << *r.timestamp << std::endl;
        }
    } else {
        std::cout << "❌ 送信失敗: " << static_cast<int>(result.error()) << std::endl;
    }
}

/**
 * @brief 基本的な使用例（Python版と同等）
 * 
 * Python版コード例:
 * ```python
 * from report_client import ReportClient
 * 
 * client = ReportClient("127.0.0.1", 4112, debug=True)
 * client.set_sensor_data("123456", weather_code=1, temperature=25.5, precipitation_prob=30)
 * result = client.send_report_data()
 * client.close()
 * ```
 */
void basic_usage_example() {
    print_separator("基本的な使用例（Python版互換）");
    
    try {
        // Python版ReportClient("127.0.0.1", 4112, debug=True)と同等
        wiplib::client::SimpleReportClient client("127.0.0.1", 4112, true);
        
        // Python版set_sensor_data()と同等の呼び出し
        client.set_sensor_data(
            "123456",                    // area_code
            1,                          // weather_code
            25.5f,                      // temperature
            30                          // precipitation_prob
        );
        
        // Python版send_report_data()と同等の呼び出し
        auto result = client.send_report_data();
        print_result(result);
        
        // Python版close()と同等の呼び出し
        client.close();
        
    } catch (const std::exception& e) {
        std::cout << "❌ エラー: " << e.what() << std::endl;
    }
}

/**
 * @brief 個別設定メソッドの使用例（Python版と同等）
 * 
 * Python版コード例:
 * ```python
 * client = ReportClient()
 * client.set_area_code("654321")
 * client.set_weather_code(2)
 * client.set_temperature(18.3)
 * client.set_precipitation_prob(75)
 * client.set_alert(["大雨", "雷"])
 * client.set_disaster(["竜巻"])
 * result = client.send_report_data()
 * ```
 */
void individual_setter_example() {
    print_separator("個別設定メソッドの使用例（Python版互換）");
    
    try {
        wiplib::client::SimpleReportClient client("127.0.0.1", 4112, true);
        
        // Python版の個別設定メソッドと同等の呼び出し
        client.set_area_code("654321");
        client.set_weather_code(2);
        client.set_temperature(18.3f);
        client.set_precipitation_prob(75);
        client.set_alert({"大雨", "雷"});
        client.set_disaster({"竜巻"});
        
        // Python版get_current_data()と同等の確認
        auto current_data = client.get_current_data();
        std::cout << "設定されているデータ数: " << current_data.size() << std::endl;
        
        auto result = client.send_report_data();
        print_result(result);
        
    } catch (const std::exception& e) {
        std::cout << "❌ エラー: " << e.what() << std::endl;
    }
}

/**
 * @brief 警報・災害情報を含む使用例（Python版と同等）
 * 
 * Python版コード例:
 * ```python
 * client = ReportClient("127.0.0.1", 4112, debug=True)
 * client.set_sensor_data(
 *     "789012",
 *     weather_code=3,
 *     temperature=12.8,
 *     precipitation_prob=85,
 *     alert=["地震", "津波", "大雨"],
 *     disaster=["台風", "洪水", "土砂災害"]
 * )
 * result = client.send_report_data()
 * ```
 */
void alert_disaster_example() {
    print_separator("警報・災害情報を含む使用例（Python版互換）");
    
    try {
        wiplib::client::SimpleReportClient client("127.0.0.1", 4112, true);
        
        // Python版と同等の警報・災害情報設定
        std::vector<std::string> alert = {"地震", "津波", "大雨"};
        std::vector<std::string> disaster = {"台風", "洪水", "土砂災害"};
        
        client.set_sensor_data(
            "789012",                   // area_code
            3,                          // weather_code
            12.8f,                      // temperature
            85,                         // precipitation_prob
            alert,                      // alert
            disaster                    // disaster
        );
        
        auto result = client.send_report_data();
        print_result(result);
        
    } catch (const std::exception& e) {
        std::cout << "❌ エラー: " << e.what() << std::endl;
    }
}

/**
 * @brief 非同期送信の使用例（Python版と同等）
 * 
 * Python版コード例:
 * ```python
 * import asyncio
 * 
 * async def async_example():
 *     client = ReportClient("127.0.0.1", 4112, debug=True)
 *     client.set_sensor_data("111222", weather_code=4, temperature=28.9)
 *     result = await client.send_report_data_async()
 *     return result
 * 
 * result = asyncio.run(async_example())
 * ```
 */
void async_usage_example() {
    print_separator("非同期送信の使用例（Python版互換）");
    
    try {
        wiplib::client::SimpleReportClient client("127.0.0.1", 4112, true);
        
        client.set_sensor_data("111222", 4, 28.9f);
        
        // Python版send_report_data_async()と同等の非同期呼び出し
        auto future_result = client.send_report_data_async();
        
        std::cout << "非同期送信を開始しました..." << std::endl;
        
        // 結果を待機（Python版awaitと同等）
        auto result = future_result.get();
        print_result(result);
        
    } catch (const std::exception& e) {
        std::cout << "❌ エラー: " << e.what() << std::endl;
    }
}

/**
 * @brief データクリア機能の使用例（Python版と同等）
 * 
 * Python版コード例:
 * ```python
 * client = ReportClient()
 * client.set_sensor_data("333444", weather_code=5)
 * data_before = client.get_current_data()
 * client.clear_data()
 * data_after = client.get_current_data()
 * ```
 */
void data_management_example() {
    print_separator("データ管理機能の使用例（Python版互換）");
    
    try {
        wiplib::client::SimpleReportClient client("127.0.0.1", 4110, true);
        
        // データ設定
        client.set_sensor_data("333444", 5, 22.1f, 45);
        
        // Python版get_current_data()と同等
        auto data_before = client.get_current_data();
        std::cout << "設定前のデータ数: " << data_before.size() << std::endl;
        
        // Python版clear_data()と同等
        client.clear_data();
        
        auto data_after = client.get_current_data();
        std::cout << "クリア後のデータ数: " << data_after.size() << std::endl;
        
    } catch (const std::exception& e) {
        std::cout << "❌ エラー: " << e.what() << std::endl;
    }
}

/**
 * @brief 便利関数の使用例（Python版と同等）
 * 
 * Python版コード例:
 * ```python
 * from report_client import send_sensor_report
 * 
 * result = send_sensor_report(
 *     "555666",
 *     weather_code=6,
 *     temperature=31.2,
 *     precipitation_prob=10,
 *     host="127.0.0.1",
 *     port=4112,
 *     debug=True
 * )
 * ```
 */
void utility_function_example() {
    print_separator("便利関数の使用例（Python版互換）");
    
    // Python版send_sensor_report()と同等の一括送信関数
    auto result = wiplib::client::utils::send_sensor_report(
        "555666",                       // area_code
        6,                              // weather_code
        31.2f,                          // temperature
        10,                             // precipitation_prob
        {},                             // alert (空)
        {},                             // disaster (空)
        "127.0.0.1",                    // host
        4112,                           // port
        true                            // debug
    );
    
    print_result(result);
}

/**
 * @brief 後方互換性メソッドの使用例（Python版と同等）
 * 
 * Python版コード例:
 * ```python
 * client = ReportClient()
 * client.set_area_code("777888")
 * 
 * # 後方互換性メソッド
 * result1 = client.send_report()
 * result2 = client.send_current_data() 
 * result3 = client.send_data_simple()
 * ```
 */
void backward_compatibility_example() {
    print_separator("後方互換性メソッドの使用例（Python版互換）");
    
    try {
        wiplib::client::SimpleReportClient client("127.0.0.1", 4112, true);
        
        client.set_area_code("777888");
        client.set_weather_code(7);
        
        // Python版後方互換性メソッドと同等
        std::cout << "send_report()を呼び出し中..." << std::endl;
        auto result1 = client.send_report();
        print_result(result1);
        
        std::cout << "send_current_data()を呼び出し中..." << std::endl;
        auto result2 = client.send_current_data();
        print_result(result2);
        
        std::cout << "send_data_simple()を呼び出し中..." << std::endl;
        auto result3 = client.send_data_simple();
        print_result(result3);
        
    } catch (const std::exception& e) {
        std::cout << "❌ エラー: " << e.what() << std::endl;
    }
}

/**
 * @brief 環境変数を使用した設定例（Python版と同等）
 * 
 * Python版では以下の環境変数が使用される:
 * - REPORT_SERVER_HOST
 * - REPORT_SERVER_PORT  
 * - REPORT_SERVER_REQUEST_AUTH_ENABLED
 * - REPORT_SERVER_PASSPHRASE
 */
void environment_config_example() {
    print_separator("環境変数設定の使用例（Python版互換）");
    
    std::cout << "環境変数の設定状況:" << std::endl;
    std::cout << "REPORT_SERVER_HOST: " << (getenv("REPORT_SERVER_HOST") ? getenv("REPORT_SERVER_HOST") : "未設定") << std::endl;
    std::cout << "REPORT_SERVER_PORT: " << (getenv("REPORT_SERVER_PORT") ? getenv("REPORT_SERVER_PORT") : "未設定") << std::endl;
    std::cout << "REPORT_SERVER_REQUEST_AUTH_ENABLED: " << (getenv("REPORT_SERVER_REQUEST_AUTH_ENABLED") ? getenv("REPORT_SERVER_REQUEST_AUTH_ENABLED") : "未設定") << std::endl;
    std::cout << "REPORT_SERVER_PASSPHRASE: " << (getenv("REPORT_SERVER_PASSPHRASE") ? "設定済み" : "未設定") << std::endl;
    
    try {
        // Python版と同様に環境変数から設定を自動読み込み
        wiplib::client::SimpleReportClient client("localhost", 4112, true);
        
        client.set_sensor_data("999000", 8, 15.7f, 60);
        auto result = client.send_report_data();
        print_result(result);
        
    } catch (const std::exception& e) {
        std::cout << "❌ エラー: " << e.what() << std::endl;
    }
}

/**
 * @brief メイン関数 - 全ての使用例を実行
 */
int main() {
    std::cout << "C++ SimpleReportClient チュートリアル" << std::endl;
    std::cout << "Python版ReportClientと完全互換のAPIを使用したサンプル" << std::endl;
    std::cout << "\n注意: 実際にサーバーが動作していない場合、送信はタイムアウトエラーになります" << std::endl;

    // 基本的な使用例
    basic_usage_example();
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // 個別設定メソッドの使用例
    individual_setter_example();
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // 警報・災害情報を含む使用例
    alert_disaster_example();
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // 非同期送信の使用例
    async_usage_example();
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // データ管理機能の使用例
    data_management_example();
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // 便利関数の使用例
    utility_function_example();
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // 後方互換性メソッドの使用例
    backward_compatibility_example();
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    // 環境変数設定の使用例
    environment_config_example();

    print_separator("チュートリアル完了");
    std::cout << "✅ 全ての使用例の実行が完了しました" << std::endl;
    std::cout << "\nPython版から移植する際の手順:" << std::endl;
    std::cout << "1. #include \"wiplib/client/simple_report_client.hpp\" を追加" << std::endl;
    std::cout << "2. Python版のReportClientをSimpleReportClientに置換" << std::endl;
    std::cout << "3. 型指定（std::optional<int>など）を適切に設定" << std::endl;
    std::cout << "4. エラーハンドリングをResult<T>型に対応" << std::endl;

    return 0;
}
