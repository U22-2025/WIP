#include "wiplib/client/client.hpp"
#include "wiplib/error.hpp"
#include <stdexcept>
#include <utility>

namespace wiplib::client {

Client::Client(
    std::optional<std::string> host,
    std::optional<uint16_t> port,
    std::optional<ServerConfig> server_config,
    bool debug,
    std::optional<double> latitude,
    std::optional<double> longitude,
    std::optional<std::string> area_code
) : debug_(debug) {
    // サーバー設定の初期化
    config_ = server_config.value_or(ServerConfig{});
    if (host.has_value()) {
        config_.host = host.value();
    }
    if (port.has_value()) {
        config_.port = port.value();
    }

    // 状態の初期化
    state_.latitude = latitude;
    state_.longitude = longitude;
    state_.area_code = area_code;

    // ポート番号の検証
    validate_port();

    try {
        initialize_wip_client();
    } catch (const std::exception& e) {
        throw std::runtime_error("111: クライアント初期化失敗 - " + std::string(e.what()));
    }

    // デバッグログ出力
    if (debug_) {
        // TODO: ログフォーマッター実装後に有効化
        // auto init_log = UnifiedLogFormatter::format_communication_log(
        //     "WIPClient", "connected to", config_.host, config_.port, 0, 
        //     {{"Initial State", state_.to_string()}}
        // );
        // logger.debug(init_log);
    }
}

std::optional<double> Client::latitude() const noexcept {
    return state_.latitude;
}

std::optional<double> Client::longitude() const noexcept {
    return state_.longitude;
}

std::optional<std::string> Client::area_code() const noexcept {
    return state_.area_code;
}

void Client::set_coordinates(double lat, double lon) {
    state_.latitude = lat;
    state_.longitude = lon;
    if (wip_client_) {
        wip_client_->set_coordinates(lat, lon);
    }
}

void Client::set_area_code(std::string area_code) {
    state_.area_code = area_code;
    if (wip_client_) {
        wip_client_->set_area_code(std::move(area_code));
    }
}

void Client::set_server(const std::string& host) {
    config_.host = host;
    // クライアントの再初期化が必要
    initialize_wip_client();
}

void Client::set_server(const std::string& host, uint16_t port) {
    config_.host = host;
    config_.port = port;
    validate_port();
    // クライアントの再初期化が必要
    initialize_wip_client();
}

void Client::close() {
    if (wip_client_) {
        wip_client_->close();
        wip_client_.reset();
    }
}

ClientSnapshot Client::get_state() const noexcept {
    ClientSnapshot snapshot;
    snapshot.latitude = state_.latitude;
    snapshot.longitude = state_.longitude;
    snapshot.area_code = state_.area_code;
    snapshot.host = config_.host;
    snapshot.port = config_.port;
    return snapshot;
}

Result<WeatherData> Client::get_weather(
    bool weather, bool temperature, bool precipitation_prob,
    bool alert, bool disaster, uint8_t day, bool proxy
) {
    // 座標が設定されているかチェック
    if (!state_.latitude.has_value() || !state_.longitude.has_value()) {
        if (!state_.area_code.has_value()) {
            return Result<WeatherData>(make_error_code(WipErrc::invalid_packet));
        }
        // エリアコードで取得
        auto options = build_options(weather, temperature, precipitation_prob, alert, disaster, day);
        return wip_client_->get_weather_by_area_code(state_.area_code.value(), options, proxy);
    }
    
    // 座標で取得
    auto options = build_options(weather, temperature, precipitation_prob, alert, disaster, day);
    return wip_client_->get_weather_by_coordinates(
        state_.latitude.value(), state_.longitude.value(), options, proxy
    );
}

Result<WeatherData> Client::get_weather_by_coordinates(
    double lat, double lon,
    bool weather, bool temperature, bool precipitation_prob,
    bool alert, bool disaster, uint8_t day, bool proxy
) {
    auto options = build_options(weather, temperature, precipitation_prob, alert, disaster, day);
    return wip_client_->get_weather_by_coordinates(lat, lon, options, proxy);
}

Result<WeatherData> Client::get_weather_by_area_code(
    std::string_view area_code,
    bool weather, bool temperature, bool precipitation_prob,
    bool alert, bool disaster, uint8_t day, bool proxy
) {
    auto options = build_options(weather, temperature, precipitation_prob, alert, disaster, day);
    return wip_client_->get_weather_by_area_code(area_code, options, proxy);
}

WeatherOptions Client::build_options(bool weather, bool temperature, bool precipitation_prob, 
                                    bool alert, bool disaster, uint8_t day) const {
    WeatherOptions options;
    options.weather = weather;
    options.temperature = temperature;
    options.precipitation_prob = precipitation_prob;
    options.alert = alert;
    options.disaster = disaster;
    options.day = day;
    return options;
}

void Client::validate_port() const {
    if (config_.port < 1 || config_.port > 65535) {
        throw std::invalid_argument("112: 無効なポート番号");
    }
}

void Client::initialize_wip_client() {
    wip_client_ = std::make_unique<WipClient>(config_, debug_);
    // 既存の状態を同期
    if (state_.latitude.has_value() && state_.longitude.has_value()) {
        wip_client_->set_coordinates(state_.latitude.value(), state_.longitude.value());
    }
    if (state_.area_code.has_value()) {
        wip_client_->set_area_code(state_.area_code.value());
    }
}

} // namespace wiplib::client