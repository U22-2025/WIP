#pragma once

#include <cstdint>
#include <vector>
#include <string>
#include <optional>
#include <unordered_map>
#include <span>
#include <chrono>
#include <mutex>

#include "wiplib/packet/packet.hpp"
#include "wiplib/packet/extended_field.hpp"
#include "wiplib/expected.hpp"

namespace wiplib::packet::compat {

/**
 * @brief Python互換センサーデータ構造体
 * 
 * Python版ReportClientと完全互換のセンサーデータ構造
 * 全フィールドがオプショナルで、Python版と同様の動作を実現
 */
struct PySensorData {
    std::optional<std::string> area_code{};               // エリアコード（6桁文字列）
    std::optional<int> weather_code{};                    // 天気コード（センサー観測値）
    std::optional<float> temperature{};                   // 気温（摂氏）
    std::optional<int> precipitation_prob{};              // 降水確率（0-100%）
    std::optional<std::vector<std::string>> alert{};      // 警報情報
    std::optional<std::vector<std::string>> disaster{};   // 災害情報
    
    /**
     * @brief エリアコードを6桁文字列に正規化
     * @param area_code エリアコード（文字列または数値）
     * @return 正規化された6桁文字列
     */
    static std::string normalize_area_code(const std::string& area_code);
    static std::string normalize_area_code(int area_code);
    
    /**
     * @brief 設定されているデータの辞書を取得（Python版get_current_data()互換）
     * @return データ辞書
     */
    std::unordered_map<std::string, std::string> to_dict() const;
    
    /**
     * @brief データがすべて空かチェック
     * @return すべて空の場合true
     */
    bool is_empty() const;
    
    /**
     * @brief データをクリア（Python版clear_data()互換）
     */
    void clear();
};

/**
 * @brief Python互換レポートリクエスト（Type 4）
 * 
 * Python版 ReportRequest.create_sensor_data_report() と完全互換
 */
struct PyReportRequest {
    proto::Header header{};
    PySensorData sensor_data{};
    
    // 認証関連（Python版互換）
    bool auth_enabled = false;
    std::string auth_passphrase{};
    
    /**
     * @brief センサーデータレポートリクエストを作成（Python版互換）
     * @param area_code エリアコード
     * @param weather_code 天気コード（オプション）
     * @param temperature 気温（オプション）
     * @param precipitation_prob 降水確率（オプション）
     * @param alert 警報情報（オプション）
     * @param disaster 災害情報（オプション）
     * @param version プロトコルバージョン
     * @return 作成されたリクエスト
     */
    static PyReportRequest create_sensor_data_report(
        const std::string& area_code,
        std::optional<int> weather_code = {},
        std::optional<float> temperature = {},
        std::optional<int> precipitation_prob = {},
        std::optional<std::vector<std::string>> alert = {},
        std::optional<std::vector<std::string>> disaster = {},
        uint8_t version = 1
    );
    
    /**
     * @brief 認証を有効化（Python版enable_auth()互換）
     * @param passphrase パスフレーズ
     */
    void enable_auth(const std::string& passphrase);
    
    /**
     * @brief 認証フラグを設定（Python版set_auth_flags()互換）
     */
    void set_auth_flags();
    
    /**
     * @brief パケットをバイナリデータにエンコード（Python版to_bytes()互換）
     * @return エンコードされたバイナリデータ
     */
    std::vector<uint8_t> to_bytes() const;
    
    /**
     * @brief バイナリデータからパケットをデコード（Python版from_bytes()互換）
     * @param data バイナリデータ
     * @return デコードされたパケット
     */
    static wiplib::Result<PyReportRequest> from_bytes(std::span<const uint8_t> data);
    
    /**
     * @brief パケットの検証
     * @return 検証成功時true
     */
    bool validate() const;

private:
    /**
     * @brief フラグを計算（データが設定されているかで判定）
     */
    void calculate_flags();
    
    /**
     * @brief 拡張フィールドを構築
     * @return 拡張フィールド
     */
    std::vector<proto::ExtendedField> build_extended_fields() const;
};

/**
 * @brief Python互換レポートレスポンス（Type 5）
 * 
 * Python版 ReportResponse と完全互換
 */
struct PyReportResponse {
    proto::Header header{};
    proto::ResponseFields response_fields{};
    
    // レスポンス固有データ
    std::optional<std::tuple<std::string, int>> source_info{}; // (ip, port)
    
    /**
     * @brief ACKレスポンスを作成（Python版create_ack_response()互換）
     * @param request 元のリクエスト
     * @param version プロトコルバージョン
     * @return 作成されたレスポンス
     */
    static PyReportResponse create_ack_response(
        const PyReportRequest& request,
        uint8_t version = 1
    );
    
    /**
     * @brief データ付きレスポンスを作成（Python版create_data_response()互換）
     * @param request 元のリクエスト
     * @param sensor_data サーバーで処理されたセンサーデータ
     * @param version プロトコルバージョン
     * @return 作成されたレスポンス
     */
    static PyReportResponse create_data_response(
        const PyReportRequest& request,
        const std::unordered_map<std::string, std::string>& sensor_data,
        uint8_t version = 1
    );
    
    /**
     * @brief パケットをバイナリデータにエンコード（Python版to_bytes()互換）
     * @return エンコードされたバイナリデータ
     */
    std::vector<uint8_t> to_bytes() const;
    
    /**
     * @brief バイナリデータからパケットをデコード（Python版from_bytes()互換）
     * @param data バイナリデータ
     * @return デコードされたパケット
     */
    static wiplib::Result<PyReportResponse> from_bytes(std::span<const uint8_t> data);
    
    /**
     * @brief 送信元情報を取得（Python版get_source_info()互換）
     * @return 送信元情報 (ip, port) またはnullopt
     */
    std::optional<std::tuple<std::string, int>> get_source_info() const;
    
    /**
     * @brief レスポンスが成功かどうかを判定（Python版is_success()互換）
     * @return 成功の場合true
     */
    bool is_success() const;
    
    /**
     * @brief レスポンスの要約情報を取得（Python版get_response_summary()互換）
     * @return レスポンスの要約辞書
     */
    std::unordered_map<std::string, std::string> get_response_summary() const;
    
    /**
     * @brief パケットの検証
     * @return 検証成功時true
     */
    bool validate() const;

private:
    /**
     * @brief 拡張フィールドを構築
     * @return 拡張フィールド
     */
    std::vector<proto::ExtendedField> build_extended_fields() const;
    
    /**
     * @brief 拡張フィールドから送信元情報を抽出
     * @param extensions 拡張フィールド
     * @return 送信元情報
     */
    static std::optional<std::tuple<std::string, int>> extract_source_info(
        const std::vector<proto::ExtendedField>& extensions
    );
};

/**
 * @brief パケットIDジェネレーター（Python版互換）
 * 
 * Python版 PacketIDGenerator12Bit と完全互換
 */
class PyPacketIDGenerator {
public:
    PyPacketIDGenerator();
    
    /**
     * @brief 次のパケットIDを生成
     * @return 12ビットパケットID（0-4095）
     */
    uint16_t next_id();
    
private:
    std::mutex mutex_;
    uint16_t current_;
    static constexpr uint16_t MAX_ID = 4096; // 2^12
};

/**
 * @brief Python互換ユーティリティ関数
 */
namespace py_utils {
    /**
     * @brief 気温を摂氏から内部表現に変換（Python版互換）
     * @param celsius 摂氏温度
     * @return 内部表現（+100オフセット）
     */
    inline int8_t celsius_to_internal(float celsius) {
        return static_cast<int8_t>(static_cast<int>(celsius) + 100);
    }
    
    /**
     * @brief 気温を内部表現から摂氏に変換（Python版互換）
     * @param internal 内部表現
     * @return 摂氏温度
     */
    inline float internal_to_celsius(int8_t internal) {
        return static_cast<float>(internal - 100);
    }
    
    /**
     * @brief パケットタイプからタイプ名を取得（デバッグ用）
     * @param type パケットタイプ
     * @return タイプ名
     */
    std::string packet_type_to_string(uint8_t type);
    
    /**
     * @brief 現在のUNIXタイムスタンプを取得（Python版互換）
     * @return UNIXタイムスタンプ
     */
    uint64_t current_unix_timestamp();
}

} // namespace wiplib::packet::compat