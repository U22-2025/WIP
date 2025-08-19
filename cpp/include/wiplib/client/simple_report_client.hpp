#pragma once

#include <string>
#include <optional>
#include <vector>
#include <unordered_map>
#include <future>
#include <any>
#include <memory>
#include <cstdint>

#include "wiplib/expected.hpp"
#include "wiplib/error.hpp"
#include "wiplib/packet/report_packet_compat.hpp"
#include "wiplib/packet/debug/debug_logger.hpp"
#include "wiplib/utils/network.hpp"

namespace wiplib::client {

/**
 * @brief レポート送信結果
 */
struct ReportResult {
    std::string type;                           // "report_ack" or "error"
    bool success = false;                       // 成功フラグ
    std::optional<std::string> area_code{};     // レスポンスのエリアコード
    std::optional<uint16_t> packet_id{};        // パケットID
    std::optional<uint64_t> timestamp{};        // タイムスタンプ
    std::optional<uint16_t> error_code{};       // エラーコード (error時)
    double response_time_ms = 0.0;              // レスポンス時間
    std::unordered_map<std::string, std::string> summary{}; // 追加情報
};

/**
 * @brief Python版ReportClient互換のシンプルなReportClient
 * 
 * Python版ReportClientと完全互換のAPIを提供する
 * IoT機器からサーバーへのセンサーデータレポート送信に特化
 */
class SimpleReportClient {
public:
    /**
     * @brief コンストラクタ（Python版互換）
     * @param host Report Serverのホスト名
     * @param port Report Serverのポート番号
     * @param debug デバッグモードフラグ
     */
    SimpleReportClient(std::string host = "localhost", uint16_t port = 4112, bool debug = false);
    
    /**
     * @brief デストラクタ
     */
    ~SimpleReportClient();
    
    // Python互換データ設定API
    
    /**
     * @brief センサーデータを一括設定（Python版set_sensor_data()互換）
     * @param area_code エリアコード（6桁文字列）
     * @param weather_code 天気コード（オプション）
     * @param temperature 気温（摂氏、オプション）
     * @param precipitation_prob 降水確率（0-100%、オプション）
     * @param alert 警報情報リスト（オプション）
     * @param disaster 災害情報リスト（オプション）
     */
    void set_sensor_data(const std::string& area_code, 
                        std::optional<int> weather_code = {},
                        std::optional<float> temperature = {},
                        std::optional<int> precipitation_prob = {},
                        std::optional<std::vector<std::string>> alert = {},
                        std::optional<std::vector<std::string>> disaster = {});
    
    /**
     * @brief エリアコードを設定（Python版set_area_code()互換）
     * @param area_code エリアコード
     */
    void set_area_code(const std::string& area_code);
    
    /**
     * @brief 天気コードを設定（Python版set_weather_code()互換）
     * @param weather_code 天気コード
     */
    void set_weather_code(int weather_code);
    
    /**
     * @brief 気温を設定（Python版set_temperature()互換）
     * @param temperature 気温（摂氏）
     */
    void set_temperature(float temperature);
    
    /**
     * @brief 降水確率を設定（Python版set_precipitation_prob()互換）
     * @param precipitation_prob 降水確率（0-100%）
     */
    void set_precipitation_prob(int precipitation_prob);
    
    /**
     * @brief 警報情報を設定（Python版set_alert()互換）
     * @param alert 警報情報リスト
     */
    void set_alert(const std::vector<std::string>& alert);

    /**
     * @brief 災害情報を設定（Python版set_disaster()互換）
     * @param disaster 災害情報リスト
     */
    void set_disaster(const std::vector<std::string>& disaster);

    /**
     * @brief 接続先サーバーを再設定
     * @param host ホスト名
     * @param port ポート番号
     */
    void set_server(const std::string& host, uint16_t port);

    /**
     * @brief 接続先サーバーを再設定（ポートは保持）
     * @param host ホスト名
     */
    void set_server(const std::string& host);
    
    // Python互換送信API
    
    /**
     * @brief レポートデータを送信（Python版send_report_data()互換）
     * @return 送信結果
     */
    Result<ReportResult> send_report_data();
    
    /**
     * @brief レポートデータを非同期送信（Python版send_report_data_async()互換）
     * @return 送信結果のfuture
     */
    std::future<Result<ReportResult>> send_report_data_async();
    
    /**
     * @brief 現在のデータでレポートを送信（Python版send_data_simple()互換）
     * @return 送信結果
     */
    Result<ReportResult> send_data_simple();
    
    // Python互換データ管理API
    
    /**
     * @brief 現在設定されているデータを取得（Python版get_current_data()互換）
     * @return データ辞書
     */
    std::unordered_map<std::string, std::any> get_current_data() const;
    
    /**
     * @brief 設定されているデータをクリア（Python版clear_data()互換）
     */
    void clear_data();
    
    /**
     * @brief ソケットを閉じる（Python版close()互換）
     */
    void close();
    
    // 後方互換性メソッド（Python版と同様）
    
    /**
     * @brief 後方互換性のため（Python版send_report()互換）
     * @return 送信結果
     */
    Result<ReportResult> send_report();
    
    /**
     * @brief 後方互換性のため（Python版send_current_data()互換）
     * @return 送信結果
     */
    Result<ReportResult> send_current_data();

private:
    // 設定
    std::string host_;
    uint16_t port_;
    bool debug_;
    
    // ネットワーク
    int socket_fd_;
    bool socket_closed_;
    
    // デバッグ（将来の拡張用）
    // std::unique_ptr<packet::debug::PacketDebugLogger> debug_logger_;
    
    // パケットIDジェネレーター
    std::unique_ptr<packet::compat::PyPacketIDGenerator> pid_generator_;
    
    // センサーデータ（Python版と同様にメンバ変数で保持）
    std::optional<std::string> area_code_{};
    std::optional<int> weather_code_{};
    std::optional<float> temperature_{};
    std::optional<int> precipitation_prob_{};
    std::optional<std::vector<std::string>> alert_{};
    std::optional<std::vector<std::string>> disaster_{};
    
    // 認証設定（Python版互換）
    bool auth_enabled_;
    std::string auth_passphrase_;
    
    /**
     * @brief 環境変数から認証設定を初期化（Python版_init_auth_config()互換）
     */
    void init_auth_config();
    
    /**
     * @brief UDPソケットを初期化
     * @return 成功時true
     */
    bool init_socket();
    
    /**
     * @brief レポートリクエストを作成
     * @return 作成されたリクエスト
     */
    Result<packet::compat::PyReportRequest> create_request();
    
    /**
     * @brief レスポンスを受信・解析
     * @param packet_id 期待するパケットID
     * @param timeout_ms タイムアウト（ミリ秒）
     * @return レスポンス解析結果
     */
    Result<ReportResult> receive_response(uint16_t packet_id, int timeout_ms = 10000);
    
    /**
     * @brief エラーレスポンスを処理
     * @param data 受信データ
     * @return エラー結果
     */
    ReportResult handle_error_response(const std::vector<uint8_t>& data);
    
    /**
     * @brief パケットタイプを取得
     * @param data パケットデータ
     * @return パケットタイプ
     */
    static uint8_t get_packet_type(const std::vector<uint8_t>& data);
};

} // namespace wiplib::client

// Python版互換の便利関数

namespace wiplib::client::utils {

/**
 * @brief SimpleReportClientインスタンスを作成する便利関数（Python版create_report_client()互換）
 * @param host ホスト名
 * @param port ポート番号
 * @param debug デバッグモード
 * @return クライアントインスタンス
 */
std::unique_ptr<SimpleReportClient> create_report_client(
    const std::string& host = "localhost", 
    uint16_t port = 4112, 
    bool debug = false
);

/**
 * @brief センサーレポートを一回の呼び出しで送信する便利関数（Python版send_sensor_report()互換）
 * @param area_code エリアコード
 * @param weather_code 天気コード（オプション）
 * @param temperature 気温（オプション）
 * @param precipitation_prob 降水確率（オプション）
 * @param alert 警報情報（オプション）
 * @param disaster 災害情報（オプション）
 * @param host ホスト名
 * @param port ポート番号
 * @param debug デバッグモード
 * @return 送信結果
 */
Result<ReportResult> send_sensor_report(
    const std::string& area_code,
    std::optional<int> weather_code = {},
    std::optional<float> temperature = {},
    std::optional<int> precipitation_prob = {},
    std::optional<std::vector<std::string>> alert = {},
    std::optional<std::vector<std::string>> disaster = {},
    const std::string& host = "localhost",
    uint16_t port = 4112,
    bool debug = false
);

} // namespace wiplib::client::utils
