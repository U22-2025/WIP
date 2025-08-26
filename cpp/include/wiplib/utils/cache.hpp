#pragma once

#include <unordered_map>
#include <list>
#include <memory>
#include <mutex>
#include <atomic>
#include <chrono>
#include <functional>
#include <optional>
#include <thread>
#include <condition_variable>

namespace wiplib::utils {

/**
 * @brief キャッシュエントリ
 */
template<typename T>
struct CacheEntry {
    T value;
    std::chrono::steady_clock::time_point created_time;
    std::chrono::steady_clock::time_point last_accessed_time;
    std::chrono::seconds ttl;
    uint64_t access_count = 0;
    
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
     * @brief 残り有効時間を取得
     */
    std::chrono::seconds remaining_ttl() const {
        if (ttl.count() <= 0) return std::chrono::seconds::max();
        auto now = std::chrono::steady_clock::now();
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(now - created_time);
        return ttl > elapsed ? ttl - elapsed : std::chrono::seconds{0};
    }
    
    /**
     * @brief アクセス情報を更新
     */
    void update_access() {
        last_accessed_time = std::chrono::steady_clock::now();
        access_count++;
    }
};

/**
 * @brief キャッシュ統計情報
 */
struct CacheStats {
    std::atomic<uint64_t> hits{0};
    std::atomic<uint64_t> misses{0};
    std::atomic<uint64_t> evictions{0};
    std::atomic<uint64_t> expirations{0};
    std::atomic<uint64_t> puts{0};
    std::atomic<uint64_t> removes{0};
    std::atomic<size_t> current_size{0};
    std::chrono::steady_clock::time_point start_time{std::chrono::steady_clock::now()};
    
    /**
     * @brief ヒット率を計算
     */
    double hit_ratio() const {
        uint64_t total = hits.load() + misses.load();
        return total > 0 ? static_cast<double>(hits.load()) / total : 0.0;
    }
};

/**
 * @brief キャッシュポリシー
 */
enum class EvictionPolicy {
    LRU,    // Least Recently Used
    LFU,    // Least Frequently Used
    FIFO,   // First In First Out
    Random  // Random eviction
};

/**
 * @brief インメモリキャッシュクラス
 */
template<typename K, typename V>
class InMemoryCache {
public:
    /**
     * @brief コンストラクタ
     * @param max_size 最大サイズ
     * @param default_ttl デフォルトTTL（0で無制限）
     * @param policy 削除ポリシー
     */
    explicit InMemoryCache(
        size_t max_size = 1000,
        std::chrono::seconds default_ttl = std::chrono::seconds{300},
        EvictionPolicy policy = EvictionPolicy::LRU
    ) : max_size_(max_size), default_ttl_(default_ttl), eviction_policy_(policy) {
        cleanup_thread_ = std::make_unique<std::thread>(&InMemoryCache::cleanup_loop, this);
    }
    
    ~InMemoryCache() {
        running_ = false;
        cleanup_cv_.notify_all();
        if (cleanup_thread_ && cleanup_thread_->joinable()) {
            cleanup_thread_->join();
        }
    }
    
    /**
     * @brief 値を格納
     * @param key キー
     * @param value 値
     * @param ttl TTL（nulloptでデフォルト）
     */
    void put(const K& key, const V& value, std::optional<std::chrono::seconds> ttl = std::nullopt) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto effective_ttl = ttl.value_or(default_ttl_);
        auto now = std::chrono::steady_clock::now();
        
        auto it = cache_.find(key);
        if (it != cache_.end()) {
            // 既存エントリを更新
            it->second.value = value;
            it->second.created_time = now;
            it->second.last_accessed_time = now;
            it->second.ttl = effective_ttl;
            it->second.access_count = 1;
            
            // LRUリストを更新
            if (eviction_policy_ == EvictionPolicy::LRU) {
                auto lru_it = std::find(lru_list_.begin(), lru_list_.end(), key);
                if (lru_it != lru_list_.end()) {
                    lru_list_.erase(lru_it);
                }
                lru_list_.push_front(key);
            }
        } else {
            // 新しいエントリを追加
            if (cache_.size() >= max_size_) {
                evict_one();
            }
            
            CacheEntry<V> entry{value, now, now, effective_ttl, 1};
            cache_.emplace(key, std::move(entry));
            
            if (eviction_policy_ == EvictionPolicy::LRU) {
                lru_list_.push_front(key);
            } else if (eviction_policy_ == EvictionPolicy::FIFO) {
                fifo_list_.push_back(key);
            }
            
            stats_.current_size = cache_.size();
        }
        
        stats_.puts++;
    }
    
    /**
     * @brief 値を取得
     * @param key キー
     * @return 値（見つからない場合nullopt）
     */
    std::optional<V> get(const K& key) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto it = cache_.find(key);
        if (it == cache_.end()) {
            stats_.misses++;
            return std::nullopt;
        }
        
        auto& entry = it->second;
        if (entry.is_expired()) {
            cache_.erase(it);
            remove_from_lists(key);
            stats_.current_size = cache_.size();
            stats_.expirations++;
            stats_.misses++;
            return std::nullopt;
        }
        
        // アクセス情報更新
        entry.update_access();
        
        // LRUリストを更新
        if (eviction_policy_ == EvictionPolicy::LRU) {
            auto lru_it = std::find(lru_list_.begin(), lru_list_.end(), key);
            if (lru_it != lru_list_.end()) {
                lru_list_.erase(lru_it);
            }
            lru_list_.push_front(key);
        }
        
        stats_.hits++;
        return entry.value;
    }
    
    /**
     * @brief 値を削除
     * @param key キー
     * @return 削除された場合true
     */
    bool remove(const K& key) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto it = cache_.find(key);
        if (it == cache_.end()) {
            return false;
        }
        
        cache_.erase(it);
        remove_from_lists(key);
        stats_.current_size = cache_.size();
        stats_.removes++;
        return true;
    }
    
    /**
     * @brief キーの存在チェック
     * @param key キー
     * @return 存在する場合true
     */
    bool contains(const K& key) const {
        std::lock_guard<std::mutex> lock(mutex_);
        
        auto it = cache_.find(key);
        if (it == cache_.end()) {
            return false;
        }
        
        return !it->second.is_expired();
    }
    
    /**
     * @brief キャッシュサイズを取得
     * @return 現在のサイズ
     */
    size_t size() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return cache_.size();
    }
    
    /**
     * @brief キャッシュが空かチェック
     * @return 空の場合true
     */
    bool empty() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return cache_.empty();
    }
    
    /**
     * @brief キャッシュをクリア
     */
    void clear() {
        std::lock_guard<std::mutex> lock(mutex_);
        cache_.clear();
        lru_list_.clear();
        fifo_list_.clear();
        stats_.current_size = 0;
    }
    
    /**
     * @brief 期限切れエントリをクリーンアップ
     * @return クリーンアップされたエントリ数
     */
    size_t cleanup_expired() {
        std::lock_guard<std::mutex> lock(mutex_);
        
        size_t removed_count = 0;
        auto it = cache_.begin();
        while (it != cache_.end()) {
            if (it->second.is_expired()) {
                remove_from_lists(it->first);
                it = cache_.erase(it);
                removed_count++;
                stats_.expirations++;
            } else {
                ++it;
            }
        }
        
        stats_.current_size = cache_.size();
        return removed_count;
    }
    
    /**
     * @brief 統計情報を取得
     * @return 統計情報
     */
    CacheStats get_stats() const {
        return stats_;
    }
    
    /**
     * @brief 統計情報をリセット
     */
    void reset_stats() {
        stats_.hits = 0;
        stats_.misses = 0;
        stats_.evictions = 0;
        stats_.expirations = 0;
        stats_.puts = 0;
        stats_.removes = 0;
        stats_.start_time = std::chrono::steady_clock::now();
    }
    
    /**
     * @brief 最大サイズを変更
     * @param new_max_size 新しい最大サイズ
     */
    void resize(size_t new_max_size) {
        std::lock_guard<std::mutex> lock(mutex_);
        max_size_ = new_max_size;
        
        // サイズ超過の場合は削除
        while (cache_.size() > max_size_) {
            evict_one();
        }
    }
    
    /**
     * @brief デフォルトTTLを変更
     * @param new_default_ttl 新しいデフォルトTTL
     */
    void set_default_ttl(std::chrono::seconds new_default_ttl) {
        default_ttl_ = new_default_ttl;
    }
    
    /**
     * @brief 全キーを取得
     * @return キー一覧
     */
    std::vector<K> get_all_keys() const {
        std::lock_guard<std::mutex> lock(mutex_);
        
        std::vector<K> keys;
        keys.reserve(cache_.size());
        
        for (const auto& pair : cache_) {
            if (!pair.second.is_expired()) {
                keys.push_back(pair.first);
            }
        }
        
        return keys;
    }

private:
    mutable std::mutex mutex_;
    std::unordered_map<K, CacheEntry<V>> cache_;
    
    // 削除ポリシー用データ構造
    std::list<K> lru_list_;   // LRU用
    std::list<K> fifo_list_;  // FIFO用
    
    size_t max_size_;
    std::chrono::seconds default_ttl_;
    EvictionPolicy eviction_policy_;
    
    // バックグラウンドクリーンアップ
    std::atomic<bool> running_{true};
    std::unique_ptr<std::thread> cleanup_thread_;
    std::condition_variable cleanup_cv_;
    
    // 統計
    mutable CacheStats stats_;
    
    /**
     * @brief エントリを1つ削除
     */
    void evict_one() {
        if (cache_.empty()) return;
        
        K key_to_remove;
        bool found = false;
        
        switch (eviction_policy_) {
            case EvictionPolicy::LRU:
                if (!lru_list_.empty()) {
                    key_to_remove = lru_list_.back();
                    lru_list_.pop_back();
                    found = true;
                }
                break;
                
            case EvictionPolicy::FIFO:
                if (!fifo_list_.empty()) {
                    key_to_remove = fifo_list_.front();
                    fifo_list_.pop_front();
                    found = true;
                }
                break;
                
            case EvictionPolicy::LFU: {
                auto min_it = std::min_element(cache_.begin(), cache_.end(),
                    [](const auto& a, const auto& b) {
                        return a.second.access_count < b.second.access_count;
                    });
                if (min_it != cache_.end()) {
                    key_to_remove = min_it->first;
                    found = true;
                }
                break;
            }
            
            case EvictionPolicy::Random:
                if (!cache_.empty()) {
                    auto it = cache_.begin();
                    std::advance(it, rand() % cache_.size());
                    key_to_remove = it->first;
                    found = true;
                }
                break;
        }
        
        if (found) {
            cache_.erase(key_to_remove);
            remove_from_lists(key_to_remove);
            stats_.evictions++;
            stats_.current_size = cache_.size();
        }
    }
    
    /**
     * @brief 各種リストからキーを削除
     */
    void remove_from_lists(const K& key) {
        // LRUリストから削除
        auto lru_it = std::find(lru_list_.begin(), lru_list_.end(), key);
        if (lru_it != lru_list_.end()) {
            lru_list_.erase(lru_it);
        }
        
        // FIFOリストから削除
        auto fifo_it = std::find(fifo_list_.begin(), fifo_list_.end(), key);
        if (fifo_it != fifo_list_.end()) {
            fifo_list_.erase(fifo_it);
        }
    }
    
    /**
     * @brief バックグラウンドクリーンアップループ
     */
    void cleanup_loop() {
        while (running_) {
            std::unique_lock<std::mutex> lock(mutex_);
            cleanup_cv_.wait_for(lock, std::chrono::seconds{60}, [this] { return !running_; });
            
            if (!running_) break;
            
            cleanup_expired();
        }
    }
};

/**
 * @brief キャッシュファクトリー
 */
class CacheFactory {
public:
    /**
     * @brief LRUキャッシュを作成
     */
    template<typename K, typename V>
    static std::unique_ptr<InMemoryCache<K, V>> create_lru_cache(
        size_t max_size = 1000,
        std::chrono::seconds default_ttl = std::chrono::seconds{300}
    ) {
        return std::make_unique<InMemoryCache<K, V>>(max_size, default_ttl, EvictionPolicy::LRU);
    }
    
    /**
     * @brief LFUキャッシュを作成
     */
    template<typename K, typename V>
    static std::unique_ptr<InMemoryCache<K, V>> create_lfu_cache(
        size_t max_size = 1000,
        std::chrono::seconds default_ttl = std::chrono::seconds{300}
    ) {
        return std::make_unique<InMemoryCache<K, V>>(max_size, default_ttl, EvictionPolicy::LFU);
    }
    
    /**
     * @brief FIFOキャッシュを作成
     */
    template<typename K, typename V>
    static std::unique_ptr<InMemoryCache<K, V>> create_fifo_cache(
        size_t max_size = 1000,
        std::chrono::seconds default_ttl = std::chrono::seconds{300}
    ) {
        return std::make_unique<InMemoryCache<K, V>>(max_size, default_ttl, EvictionPolicy::FIFO);
    }
};

} // namespace wiplib::utils