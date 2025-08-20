#pragma once

#include <string>
#include <memory>
#include <unordered_map>
#include <fstream>
#include <mutex>
#include <atomic>
#include <chrono>
#include <filesystem>
#include <optional>
#include <functional>
#include <thread>

namespace wiplib::utils {

/**
 * @brief ファイルキャッシュエントリ
 */
struct FileCacheEntry {
    std::string key;
    std::string file_path;
    std::chrono::steady_clock::time_point created_time;
    std::chrono::steady_clock::time_point last_accessed_time;
    std::chrono::seconds ttl;
    size_t file_size = 0;
    std::string content_hash;
    
    /**
     * @brief エントリが期限切れかチェック
     */
    bool is_expired() const {
        if (ttl.count() <= 0) return false;  // 無制限TTL
        auto now = std::chrono::steady_clock::now();
        auto elapsed = now - created_time;
        return elapsed > ttl;
    }
    
    /**
     * @brief ファイルが存在するかチェック
     */
    bool file_exists() const {
        return std::filesystem::exists(file_path);
    }
    
    /**
     * @brief ファイルサイズを取得
     */
    size_t get_file_size() const {
        if (!file_exists()) return 0;
        return std::filesystem::file_size(file_path);
    }
};

/**
 * @brief ファイルキャッシュ統計
 */
struct FileCacheStats {
    std::atomic<uint64_t> hits{0};
    std::atomic<uint64_t> misses{0};
    std::atomic<uint64_t> writes{0};
    std::atomic<uint64_t> deletes{0};
    std::atomic<uint64_t> expirations{0};
    std::atomic<uint64_t> disk_reads{0};
    std::atomic<uint64_t> disk_writes{0};
    std::atomic<size_t> total_entries{0};
    std::atomic<size_t> total_disk_usage{0};
    std::chrono::steady_clock::time_point start_time{std::chrono::steady_clock::now()};
    FileCacheStats() = default;
    FileCacheStats(const FileCacheStats& o) {
        hits.store(o.hits.load()); misses.store(o.misses.load()); writes.store(o.writes.load()); deletes.store(o.deletes.load()); expirations.store(o.expirations.load()); disk_reads.store(o.disk_reads.load()); disk_writes.store(o.disk_writes.load()); total_entries.store(o.total_entries.load()); total_disk_usage.store(o.total_disk_usage.load()); start_time = o.start_time;
    }
    FileCacheStats& operator=(const FileCacheStats& o) {
        if (this!=&o) { hits.store(o.hits.load()); misses.store(o.misses.load()); writes.store(o.writes.load()); deletes.store(o.deletes.load()); expirations.store(o.expirations.load()); disk_reads.store(o.disk_reads.load()); disk_writes.store(o.disk_writes.load()); total_entries.store(o.total_entries.load()); total_disk_usage.store(o.total_disk_usage.load()); start_time = o.start_time; }
        return *this;
    }
    
    /**
     * @brief ヒット率を計算
     */
    double hit_ratio() const {
        uint64_t total = hits.load() + misses.load();
        return total > 0 ? static_cast<double>(hits.load()) / total : 0.0;
    }
};

/**
 * @brief ファイルシステムキャッシュクラス
 */
class FileCache {
public:
    /**
     * @brief コンストラクタ
     * @param cache_dir キャッシュディレクトリ
     * @param max_size 最大サイズ（バイト）
     * @param default_ttl デフォルトTTL
     */
    explicit FileCache(
        const std::string& cache_dir = "./cache",
        size_t max_size = 1024 * 1024 * 100,  // 100MB
        std::chrono::seconds default_ttl = std::chrono::seconds{3600}
    );
    
    ~FileCache();
    
    /**
     * @brief データを格納
     * @param key キー
     * @param data データ
     * @param ttl TTL（nulloptでデフォルト）
     * @return 成功時true
     */
    bool put(const std::string& key, const std::vector<uint8_t>& data, 
             std::optional<std::chrono::seconds> ttl = std::nullopt);
    
    /**
     * @brief 文字列データを格納
     * @param key キー
     * @param data 文字列データ
     * @param ttl TTL（nulloptでデフォルト）
     * @return 成功時true
     */
    bool put_string(const std::string& key, const std::string& data, 
                   std::optional<std::chrono::seconds> ttl = std::nullopt);
    
    /**
     * @brief ファイルをキャッシュにコピー
     * @param key キー
     * @param source_file_path コピー元ファイルパス
     * @param ttl TTL（nulloptでデフォルト）
     * @return 成功時true
     */
    bool put_file(const std::string& key, const std::string& source_file_path,
                 std::optional<std::chrono::seconds> ttl = std::nullopt);
    
    /**
     * @brief データを取得
     * @param key キー
     * @return データ（見つからない場合nullopt）
     */
    std::optional<std::vector<uint8_t>> get(const std::string& key);
    
    /**
     * @brief 文字列データを取得
     * @param key キー
     * @return 文字列データ（見つからない場合nullopt）
     */
    std::optional<std::string> get_string(const std::string& key);
    
    /**
     * @brief ファイルパスを取得
     * @param key キー
     * @return ファイルパス（見つからない場合nullopt）
     */
    std::optional<std::string> get_file_path(const std::string& key);
    
    /**
     * @brief キャッシュファイルをコピー
     * @param key キー
     * @param destination_path コピー先パス
     * @return 成功時true
     */
    bool copy_to_file(const std::string& key, const std::string& destination_path);
    
    /**
     * @brief エントリを削除
     * @param key キー
     * @return 削除された場合true
     */
    bool remove(const std::string& key);
    
    /**
     * @brief キーの存在チェック
     * @param key キー
     * @return 存在する場合true
     */
    bool contains(const std::string& key) const;
    
    /**
     * @brief エントリ数を取得
     * @return エントリ数
     */
    size_t size() const;
    
    /**
     * @brief キャッシュが空かチェック
     * @return 空の場合true
     */
    bool empty() const;
    
    /**
     * @brief 全キャッシュをクリア
     */
    void clear();
    
    /**
     * @brief 期限切れエントリをクリーンアップ
     * @return クリーンアップされたエントリ数
     */
    size_t cleanup_expired();
    
    /**
     * @brief 古いエントリを削除してサイズを制限
     * @return 削除されたエントリ数
     */
    size_t enforce_size_limit();
    
    /**
     * @brief 統計情報を取得
     * @return 統計情報
     */
    FileCacheStats get_stats() const;
    
    /**
     * @brief 統計情報をリセット
     */
    void reset_stats();
    
    /**
     * @brief 現在のディスク使用量を取得
     * @return ディスク使用量（バイト）
     */
    size_t get_disk_usage() const;
    
    /**
     * @brief 最大サイズを変更
     * @param new_max_size 新しい最大サイズ
     */
    void set_max_size(size_t new_max_size);
    
    /**
     * @brief デフォルトTTLを変更
     * @param new_default_ttl 新しいデフォルトTTL
     */
    void set_default_ttl(std::chrono::seconds new_default_ttl);
    
    /**
     * @brief キャッシュディレクトリを取得
     * @return キャッシュディレクトリパス
     */
    std::string get_cache_directory() const;
    
    /**
     * @brief 全キーを取得
     * @return キー一覧
     */
    std::vector<std::string> get_all_keys() const;
    
    /**
     * @brief エントリ情報を取得
     * @param key キー
     * @return エントリ情報（見つからない場合nullopt）
     */
    std::optional<FileCacheEntry> get_entry_info(const std::string& key) const;
    
    /**
     * @brief キャッシュの整合性をチェック
     * @return 問題のあるエントリ数
     */
    size_t verify_integrity();
    
    /**
     * @brief インデックスファイルを保存
     * @return 成功時true
     */
    bool save_index();
    
    /**
     * @brief インデックスファイルを読み込み
     * @return 成功時true
     */
    bool load_index();
    
    /**
     * @brief 自動クリーンアップを有効化/無効化
     * @param enabled 有効フラグ
     * @param interval クリーンアップ間隔
     */
    void set_auto_cleanup(bool enabled, std::chrono::seconds interval = std::chrono::seconds{300});

private:
    std::string cache_dir_;
    size_t max_size_;
    std::chrono::seconds default_ttl_;
    
    // エントリ管理
    mutable std::mutex entries_mutex_;
    std::unordered_map<std::string, FileCacheEntry> entries_;
    
    // 統計
    mutable FileCacheStats stats_;
    
    // 自動クリーンアップ
    std::atomic<bool> auto_cleanup_enabled_{false};
    std::atomic<bool> running_{true};
    std::chrono::seconds cleanup_interval_{300};
    std::unique_ptr<std::thread> cleanup_thread_;
    
    // プライベートメソッド
    std::string generate_file_path(const std::string& key) const;
    std::string calculate_hash(const std::vector<uint8_t>& data) const;
    std::string sanitize_key(const std::string& key) const;
    bool ensure_cache_directory() const;
    bool write_data_to_file(const std::string& file_path, const std::vector<uint8_t>& data);
    std::optional<std::vector<uint8_t>> read_data_from_file(const std::string& file_path);
    void update_access_time(const std::string& key);
    void cleanup_loop();
    size_t calculate_total_disk_usage() const;
    std::vector<std::string> get_oldest_keys(size_t count) const;
    bool remove_file_safe(const std::string& file_path);
    std::string get_index_file_path() const;
};

/**
 * @brief 永続化データ管理クラス
 */
class PersistentStorage {
public:
    /**
     * @brief コンストラクタ
     * @param storage_dir ストレージディレクトリ
     */
    explicit PersistentStorage(const std::string& storage_dir = "./storage");
    
    ~PersistentStorage();
    
    /**
     * @brief データを保存
     * @param key キー
     * @param data データ
     * @param metadata メタデータ
     * @return 成功時true
     */
    bool store(const std::string& key, const std::vector<uint8_t>& data,
              const std::unordered_map<std::string, std::string>& metadata = {});
    
    /**
     * @brief データを読み込み
     * @param key キー
     * @return データ（見つからない場合nullopt）
     */
    std::optional<std::vector<uint8_t>> load(const std::string& key);
    
    /**
     * @brief メタデータを取得
     * @param key キー
     * @return メタデータ（見つからない場合nullopt）
     */
    std::optional<std::unordered_map<std::string, std::string>> get_metadata(const std::string& key);
    
    /**
     * @brief データを削除
     * @param key キー
     * @return 削除された場合true
     */
    bool remove(const std::string& key);
    
    /**
     * @brief キーの存在チェック
     * @param key キー
     * @return 存在する場合true
     */
    bool exists(const std::string& key);
    
    /**
     * @brief 全キーを取得
     * @return キー一覧
     */
    std::vector<std::string> list_keys() const;
    
    /**
     * @brief ストレージサイズを取得
     * @return ストレージサイズ（バイト）
     */
    size_t get_storage_size() const;
    
    /**
     * @brief 圧縮を有効化/無効化
     * @param enabled 圧縮有効フラグ
     */
    void set_compression_enabled(bool enabled);
    
    /**
     * @brief 暗号化を有効化/無効化
     * @param enabled 暗号化有効フラグ
     * @param encryption_key 暗号化キー
     */
    void set_encryption_enabled(bool enabled, const std::string& encryption_key = "");

private:
    std::string storage_dir_;
    std::atomic<bool> compression_enabled_{false};
    std::atomic<bool> encryption_enabled_{false};
    std::string encryption_key_;
    
    mutable std::mutex storage_mutex_;
    
    // プライベートメソッド
    std::string get_data_file_path(const std::string& key) const;
    std::string get_metadata_file_path(const std::string& key) const;
    bool ensure_storage_directory() const;
    std::vector<uint8_t> compress_data(const std::vector<uint8_t>& data) const;
    std::vector<uint8_t> decompress_data(const std::vector<uint8_t>& compressed_data) const;
    std::vector<uint8_t> encrypt_data(const std::vector<uint8_t>& data) const;
    std::vector<uint8_t> decrypt_data(const std::vector<uint8_t>& encrypted_data) const;
};

/**
 * @brief キャッシュユーティリティ
 */
namespace cache_utils {
    /**
     * @brief キーを正規化
     * @param key 元のキー
     * @return 正規化されたキー
     */
    std::string normalize_key(const std::string& key);
    
    /**
     * @brief ディスク使用量を取得
     * @param directory ディレクトリパス
     * @return 使用量（バイト）
     */
    size_t get_directory_size(const std::string& directory);
    
    /**
     * @brief ディレクトリを再帰的に削除
     * @param directory ディレクトリパス
     * @return 成功時true
     */
    bool remove_directory_recursive(const std::string& directory);
    
    /**
     * @brief 一時ファイルを作成
     * @param prefix ファイル名プレフィックス
     * @return 一時ファイルパス
     */
    std::string create_temp_file(const std::string& prefix = "wiplib_cache_");
}

} // namespace wiplib::utils
