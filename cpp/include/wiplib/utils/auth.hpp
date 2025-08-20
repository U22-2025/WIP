#pragma once

#include <string>
#include <vector>
#include <unordered_map>
#include <chrono>
#include <memory>
#include <mutex>
#include <atomic>
#include <optional>
#include <functional>
#include "wiplib/packet/packet.hpp"

namespace wiplib::utils {

enum class HashAlgorithm {
    MD5,
    SHA1,
    SHA256
};

/**
 * @brief 認証レベル
 */
enum class AuthLevel {
    None = 0,
    Basic = 1,
    Standard = 2,
    Advanced = 3,
    Maximum = 4
};

/**
 * @brief 認証結果
 */
struct AuthResult {
    bool success = false;
    std::string token{};
    std::chrono::seconds expires_in{0};
    AuthLevel level = AuthLevel::None;
    std::string error_message{};
    std::unordered_map<std::string, std::string> metadata{};
};

/**
 * @brief 認証トークン情報
 */
struct TokenInfo {
    std::string token;
    std::string user_id;
    AuthLevel level = AuthLevel::None;
    std::chrono::steady_clock::time_point created_time;
    std::chrono::seconds expires_in{3600};
    std::unordered_map<std::string, std::string> claims{};
    bool is_renewable = true;
    
    /**
     * @brief トークンが有効かチェック
     */
    bool is_valid() const {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = now - created_time;
        return elapsed < expires_in;
    }
    
    /**
     * @brief トークンの残り有効時間を取得
     */
    std::chrono::seconds remaining_time() const {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - created_time);
        return expires_in > elapsed ? expires_in - elapsed : std::chrono::seconds{0};
    }
};

/**
 * @brief セキュリティポリシー
 */
struct SecurityPolicy {
    AuthLevel minimum_auth_level = AuthLevel::Basic;
    std::chrono::seconds token_lifetime{3600};
    std::chrono::seconds token_refresh_threshold{300};  // 5分前にリフレッシュ
    uint32_t max_login_attempts = 5;
    std::chrono::seconds lockout_duration{300};
    bool require_token_renewal = true;
    bool enable_audit_logging = true;
    std::vector<std::string> allowed_hosts{};
    std::vector<std::string> blocked_hosts{};
};

/**
 * @brief WIP認証管理クラス
 */
class WIPAuth {
public:
    /**
     * @brief コンストラクタ
     * @param policy セキュリティポリシー
     */
    explicit WIPAuth(const SecurityPolicy& policy = SecurityPolicy{});
    
    ~WIPAuth();
    
    /**
     * @brief パスフレーズベース認証
     * @param passphrase パスフレーズ
     * @param user_id ユーザーID（オプション）
     * @return 認証結果
     */
    AuthResult authenticate_with_passphrase(
        const std::string& passphrase,
        const std::string& user_id = ""
    );
    
    /**
     * @brief トークンベース認証
     * @param token 認証トークン
     * @return 認証結果
     */
    AuthResult authenticate_with_token(const std::string& token);
    
    /**
     * @brief APIキーベース認証
     * @param api_key APIキー
     * @param secret_key シークレットキー（オプション）
     * @return 認証結果
     */
    AuthResult authenticate_with_api_key(
        const std::string& api_key,
        const std::string& secret_key = ""
    );
    
    /**
     * @brief 証明書ベース認証
     * @param cert_path 証明書ファイルパス
     * @param key_path 秘密鍵ファイルパス
     * @return 認証結果
     */
    AuthResult authenticate_with_certificate(
        const std::string& cert_path,
        const std::string& key_path
    );
    
    /**
     * @brief トークンを更新
     * @param old_token 古いトークン
     * @return 新しい認証結果
     */
    AuthResult refresh_token(const std::string& old_token);
    
    /**
     * @brief トークンを無効化
     * @param token 無効化するトークン
     * @return 成功時true
     */
    bool invalidate_token(const std::string& token);
    
    /**
     * @brief 全トークンを無効化
     * @return 無効化されたトークン数
     */
    size_t invalidate_all_tokens();
    
    /**
     * @brief トークンの有効性を検証
     * @param token 検証するトークン
     * @return 有効な場合トークン情報
     */
    std::optional<TokenInfo> validate_token(const std::string& token) const;
    
    /**
     * @brief ユーザーの認証レベルを取得
     * @param user_id ユーザーID
     * @return 認証レベル
     */
    AuthLevel get_user_auth_level(const std::string& user_id) const;
    
    /**
     * @brief 操作に必要な認証レベルをチェック
     * @param required_level 必要なレベル
     * @param user_token ユーザートークン
     * @return 認証通過時true
     */
    bool check_auth_level(AuthLevel required_level, const std::string& user_token) const;
    
    /**
     * @brief パスフレーズを設定
     * @param passphrase パスフレーズ
     * @param auth_level 認証レベル
     */
    void set_passphrase(const std::string& passphrase, AuthLevel auth_level = AuthLevel::Standard);
    
    /**
     * @brief APIキーを設定
     * @param api_key APIキー
     * @param secret_key シークレットキー
     * @param auth_level 認証レベル
     */
    void set_api_key(const std::string& api_key, const std::string& secret_key, AuthLevel auth_level = AuthLevel::Standard);
    
    /**
     * @brief ユーザーを追加
     * @param user_id ユーザーID
     * @param credentials 認証情報
     * @param auth_level 認証レベル
     */
    void add_user(const std::string& user_id, const std::string& credentials, AuthLevel auth_level = AuthLevel::Basic);
    
    /**
     * @brief ユーザーを削除
     * @param user_id ユーザーID
     * @return 削除された場合true
     */
    bool remove_user(const std::string& user_id);
    
    /**
     * @brief セキュリティポリシーを更新
     * @param new_policy 新しいポリシー
     */
    void update_security_policy(const SecurityPolicy& new_policy);
    
    /**
     * @brief セキュリティポリシーを取得
     * @return 現在のポリシー
     */
    SecurityPolicy get_security_policy() const;
    
    /**
     * @brief ホストアクセス許可をチェック
     * @param host_address ホストアドレス
     * @return 許可された場合true
     */
    bool is_host_allowed(const std::string& host_address) const;
    
    /**
     * @brief 認証統計を取得
     * @return 統計情報マップ
     */
    std::unordered_map<std::string, uint64_t> get_auth_statistics() const;
    
    /**
     * @brief アクティブなトークン数を取得
     * @return アクティブトークン数
     */
    size_t get_active_token_count() const;
    
    /**
     * @brief 期限切れトークンをクリーンアップ
     * @return クリーンアップされたトークン数
     */
    size_t cleanup_expired_tokens();
    
    /**
     * @brief 監査ログを有効化/無効化
     * @param enabled 有効フラグ
     */
    void set_audit_logging_enabled(bool enabled);
    
    /**
     * @brief デバッグモードを設定
     * @param enabled デバッグ有効フラグ
     */
    void set_debug_enabled(bool enabled);

    // Python WIP compatibility helpers (HMAC-SHA256 based)
    static std::vector<uint8_t> calculate_auth_hash(
        uint16_t packet_id,
        uint64_t timestamp,
        const std::string& passphrase,
        HashAlgorithm algo = HashAlgorithm::SHA256);

    static bool verify_auth_hash(
        uint16_t packet_id,
        uint64_t timestamp,
        const std::string& passphrase,
        const std::vector<uint8_t>& received_hash,
        HashAlgorithm algo = HashAlgorithm::SHA256);

    // Convenience overloads with algorithm name ("md5", "sha1", "sha256")
    static std::vector<uint8_t> calculate_auth_hash(
        uint16_t packet_id,
        uint64_t timestamp,
        const std::string& passphrase,
        const std::string& algo_name);

    static bool verify_auth_hash(
        uint16_t packet_id,
        uint64_t timestamp,
        const std::string& passphrase,
        const std::vector<uint8_t>& received_hash,
        const std::string& algo_name);

    /**
     * @brief パケットに Python 互換の認証ハッシュを付与
     * @details AUTH_SPEC に基づき、HMAC-SHA256 を hex 文字列化して拡張フィールド(ID=4)へ格納し、
     *          header.flags.extended を立てます。
     * @param packet 対象パケット（packet_id, timestamp を設定済みであること）
     * @param passphrase 共有パスフレーズ（空の場合は何もせず false）
     * @return 付与に成功した場合 true
     */
    static bool attach_auth_hash(wiplib::proto::Packet& packet, const std::string& passphrase);

    // Helpers
    static HashAlgorithm parse_hash_algorithm(const std::string& name);
    static HashAlgorithm get_default_hash_algorithm_from_env();

private:
    struct UserInfo {
        std::string user_id;
        std::string credentials_hash;
        AuthLevel auth_level;
        uint32_t failed_attempts = 0;
        std::chrono::steady_clock::time_point last_attempt_time{};
        std::chrono::steady_clock::time_point locked_until{};
        bool is_locked = false;
    };
    
    SecurityPolicy policy_;
    
    // 認証情報管理
    std::unordered_map<std::string, std::string> passphrases_;  // passphrase -> hash
    std::unordered_map<std::string, std::pair<std::string, std::string>> api_keys_;  // api_key -> (secret_hash, level)
    std::unordered_map<std::string, UserInfo> users_;  // user_id -> UserInfo
    
    // トークン管理
    std::unordered_map<std::string, TokenInfo> active_tokens_;  // token -> TokenInfo
    mutable std::mutex tokens_mutex_;
    
    // 統計
    mutable std::mutex stats_mutex_;
    std::unordered_map<std::string, std::atomic<uint64_t>> statistics_;
    
    // 設定
    std::atomic<bool> audit_logging_enabled_{true};
    std::atomic<bool> debug_enabled_{false};
    
    // プライベートメソッド
    std::string generate_token();
    std::string hash_string(const std::string& input) const;
    bool verify_hash(const std::string& input, const std::string& hash) const;
    bool is_user_locked(const std::string& user_id) const;
    void record_failed_attempt(const std::string& user_id);
    void reset_failed_attempts(const std::string& user_id);
    void log_auth_event(const std::string& event, const std::string& user_id, bool success) const;
    void log_debug(const std::string& message) const;
    void increment_stat(const std::string& key);
    AuthLevel string_to_auth_level(const std::string& level_str) const;
    std::string auth_level_to_string(AuthLevel level) const;
    bool is_token_near_expiry(const TokenInfo& token_info) const;
};

/**
 * @brief 暗号化ユーティリティ
 */
namespace crypto {
    /**
     * @brief SHA-256ハッシュ計算
     * @param input 入力文字列
     * @return ハッシュ値（16進数文字列）
     */
    std::string sha256(const std::string& input);
    std::vector<uint8_t> sha256_bytes(const std::vector<uint8_t>& data);
    std::vector<uint8_t> sha1_bytes(const std::vector<uint8_t>& data);
    std::vector<uint8_t> md5_bytes(const std::vector<uint8_t>& data);
    
    /**
     * @brief HMAC-SHA256計算
     * @param key キー
     * @param message メッセージ
     * @return HMAC値（16進数文字列）
     */
    std::string hmac_sha256(const std::string& key, const std::string& message);
    std::vector<uint8_t> hmac_sha256_bytes(const std::vector<uint8_t>& key, const std::vector<uint8_t>& message);
    std::vector<uint8_t> hmac_sha1_bytes(const std::vector<uint8_t>& key, const std::vector<uint8_t>& message);
    std::vector<uint8_t> hmac_md5_bytes(const std::vector<uint8_t>& key, const std::vector<uint8_t>& message);
    
    /**
     * @brief ランダムソルト生成
     * @param length ソルト長（バイト）
     * @return ランダムソルト（16進数文字列）
     */
    std::string generate_salt(size_t length = 16);
    
    /**
     * @brief パスワードハッシュ生成（PBKDF2）
     * @param password パスワード
     * @param salt ソルト
     * @param iterations 反復回数
     * @return ハッシュ値
     */
    std::string pbkdf2_hash(const std::string& password, const std::string& salt, int iterations = 10000);
    
    /**
     * @brief AES-256-GCM暗号化
     * @param plaintext 平文
     * @param key 暗号化キー（32バイト）
     * @return 暗号化データ（Base64）
     */
    std::string aes_encrypt(const std::string& plaintext, const std::string& key);
    
    /**
     * @brief AES-256-GCM復号化
     * @param ciphertext 暗号文（Base64）
     * @param key 復号化キー（32バイト）
     * @return 復号化データ
     */
    std::string aes_decrypt(const std::string& ciphertext, const std::string& key);
    
    /**
     * @brief Base64エンコード
     * @param input 入力データ
     * @return Base64文字列
     */
    std::string base64_encode(const std::vector<uint8_t>& input);
    
    /**
     * @brief Base64デコード
     * @param input Base64文字列
     * @return デコードされたデータ
     */
    std::vector<uint8_t> base64_decode(const std::string& input);
}

/**
 * @brief 認証ファクトリー
 */
class AuthFactory {
public:
    /**
     * @brief 基本認証システムを作成
     */
    static std::unique_ptr<WIPAuth> create_basic_auth();
    
    /**
     * @brief 高セキュリティ認証システムを作成
     */
    static std::unique_ptr<WIPAuth> create_high_security_auth();
    
    /**
     * @brief 開発用認証システムを作成
     */
    static std::unique_ptr<WIPAuth> create_development_auth();
    
    /**
     * @brief カスタム認証システムを作成
     */
    static std::unique_ptr<WIPAuth> create_custom_auth(const SecurityPolicy& policy);
};

} // namespace wiplib::utils
