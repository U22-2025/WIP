#pragma once

#include <future>
#include <mutex>
#include <optional>
#include <string>
#include <string_view>

#include "wiplib/client/wip_client.hpp"
#include "wiplib/client/client.hpp" // for ClientSnapshot

namespace wiplib::client {

/**
 * @brief 非同期WIPクライアント（Python ClientAsyncに対応）
 */
class ClientAsync {
public:
    /**
     * @brief コンストラクタ
     * @param host サーバーホスト（nulloptの場合デフォルト）
     * @param port サーバーポート（nulloptの場合デフォルト）
     * @param server_config サーバー設定（nulloptの場合デフォルト）
     * @param debug デバッグ有効
     * @param latitude 初期緯度
     * @param longitude 初期経度  
     * @param area_code 初期エリアコード
     */
    explicit ClientAsync(
        std::optional<std::string> host = std::nullopt,
        std::optional<uint16_t> port = std::nullopt,
        std::optional<ServerConfig> server_config = std::nullopt,
        bool debug = false,
        std::optional<double> latitude = std::nullopt,
        std::optional<double> longitude = std::nullopt,
        std::optional<std::string> area_code = std::nullopt
    );

    // プロパティアクセス（Python互換）
    std::optional<double> latitude() const noexcept;
    std::optional<double> longitude() const noexcept;
    std::optional<std::string> area_code() const noexcept;

    // 座標設定
    void set_coordinates(double lat, double lon);

    // エリアコード設定
    void set_area_code(std::string area_code);

    // 非同期天気データ取得
    std::future<Result<WeatherData>> get_weather(
        bool weather = true,
        bool temperature = true,
        bool precipitation_prob = true,
        bool alert = false,
        bool disaster = false,
        uint8_t day = 0,
        bool proxy = false
    );

    std::future<Result<WeatherData>> get_weather_by_coordinates(
        double lat, double lon,
        bool weather = true,
        bool temperature = true,
        bool precipitation_prob = true,
        bool alert = false,
        bool disaster = false,
        uint8_t day = 0,
        bool proxy = false
    );

    std::future<Result<WeatherData>> get_weather_by_area_code(
        std::string_view area_code,
        bool weather = true,
        bool temperature = true,
        bool precipitation_prob = true,
        bool alert = false,
        bool disaster = false,
        uint8_t day = 0,
        bool proxy = false
    );

    // 状態管理
    ClientSnapshot get_state() const;
    void set_server(const std::string& host);
    void set_server(const std::string& host, uint16_t port);
    void close();

    // RAII サポート（Python async with相当）
    ClientAsync& operator()() { return *this; } // __aenter__ equivalent
    void release() { close(); } // __aexit__ equivalent

private:
    ServerConfig config_;
    ClientState state_;
    bool debug_;
    
    // 非同期操作用のmutex（Python asyncio.Lock相当）
    mutable std::mutex async_mutex_;
    
    // 内部クライアント（WipClientを使用）
    std::unique_ptr<WipClient> wip_client_;
    
    // ヘルパーメソッド
    WeatherOptions build_options(bool weather, bool temperature, bool precipitation_prob, 
                                bool alert, bool disaster, uint8_t day) const;
    void validate_port() const;
    void initialize_wip_client();
};

} // namespace wiplib::client
