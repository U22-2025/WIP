#include <gtest/gtest.h>
#include <thread>
#include <chrono>
#include "wiplib/utils/cache.hpp"

using namespace wiplib::utils;

class CacheTest : public ::testing::Test {
protected:
    void SetUp() override {
        cache.clear();
    }
    void TearDown() override {
        cache.clear();
    }
    
    Cache<std::string, std::string> cache;
};

// 基本的なキャッシュ操作テスト
TEST_F(CacheTest, BasicOperations) {
    // 空の状態
    EXPECT_FALSE(cache.has("key1"));
    
    // データの追加
    cache.put("key1", "value1");
    EXPECT_TRUE(cache.has("key1"));
    
    // データの取得
    auto value = cache.get("key1");
    ASSERT_TRUE(value.has_value());
    EXPECT_EQ(*value, "value1");
}

// 複数のキー/値のテスト
TEST_F(CacheTest, MultipleEntries) {
    cache.put("key1", "value1");
    cache.put("key2", "value2");
    cache.put("key3", "value3");
    
    EXPECT_TRUE(cache.has("key1"));
    EXPECT_TRUE(cache.has("key2"));
    EXPECT_TRUE(cache.has("key3"));
    EXPECT_FALSE(cache.has("key4"));
    
    auto value1 = cache.get("key1");
    auto value2 = cache.get("key2");
    auto value3 = cache.get("key3");
    auto value4 = cache.get("key4");
    
    ASSERT_TRUE(value1.has_value());
    ASSERT_TRUE(value2.has_value());
    ASSERT_TRUE(value3.has_value());
    ASSERT_FALSE(value4.has_value());
    
    EXPECT_EQ(*value1, "value1");
    EXPECT_EQ(*value2, "value2");
    EXPECT_EQ(*value3, "value3");
}

// 値の更新テスト
TEST_F(CacheTest, ValueUpdate) {
    cache.put("key1", "initial_value");
    
    auto initial = cache.get("key1");
    ASSERT_TRUE(initial.has_value());
    EXPECT_EQ(*initial, "initial_value");
    
    // 同じキーで値を更新
    cache.put("key1", "updated_value");
    
    auto updated = cache.get("key1");
    ASSERT_TRUE(updated.has_value());
    EXPECT_EQ(*updated, "updated_value");
}

// キャッシュクリアテスト
TEST_F(CacheTest, CacheClear) {
    cache.put("key1", "value1");
    cache.put("key2", "value2");
    
    EXPECT_TRUE(cache.has("key1"));
    EXPECT_TRUE(cache.has("key2"));
    
    cache.clear();
    
    EXPECT_FALSE(cache.has("key1"));
    EXPECT_FALSE(cache.has("key2"));
}

// TTL (Time To Live) テスト
TEST_F(CacheTest, TTLFunctionality) {
    // 短いTTLでキャッシュエントリを作成
    cache.put_with_ttl("ttl_key", "ttl_value", std::chrono::milliseconds(100));
    
    // 直後は存在する
    EXPECT_TRUE(cache.has("ttl_key"));
    auto value = cache.get("ttl_key");
    ASSERT_TRUE(value.has_value());
    EXPECT_EQ(*value, "ttl_value");
    
    // TTL経過後は存在しない
    std::this_thread::sleep_for(std::chrono::milliseconds(150));
    EXPECT_FALSE(cache.has("ttl_key"));
    auto expired_value = cache.get("ttl_key");
    EXPECT_FALSE(expired_value.has_value());
}

// TTLなしのエントリが影響を受けないことを確認
TEST_F(CacheTest, TTLMixedEntries) {
    cache.put("permanent_key", "permanent_value");
    cache.put_with_ttl("temporary_key", "temporary_value", std::chrono::milliseconds(100));
    
    // 両方とも存在
    EXPECT_TRUE(cache.has("permanent_key"));
    EXPECT_TRUE(cache.has("temporary_key"));
    
    // TTL経過後
    std::this_thread::sleep_for(std::chrono::milliseconds(150));
    
    // 永続エントリは残り、TTLエントリは削除される
    EXPECT_TRUE(cache.has("permanent_key"));
    EXPECT_FALSE(cache.has("temporary_key"));
}

// 異なるTTLのテスト
TEST_F(CacheTest, DifferentTTLValues) {
    cache.put_with_ttl("short_ttl", "short_value", std::chrono::milliseconds(50));
    cache.put_with_ttl("long_ttl", "long_value", std::chrono::milliseconds(200));
    
    EXPECT_TRUE(cache.has("short_ttl"));
    EXPECT_TRUE(cache.has("long_ttl"));
    
    // 短いTTL経過後
    std::this_thread::sleep_for(std::chrono::milliseconds(75));
    EXPECT_FALSE(cache.has("short_ttl"));
    EXPECT_TRUE(cache.has("long_ttl"));
    
    // 長いTTL経過後
    std::this_thread::sleep_for(std::chrono::milliseconds(150));
    EXPECT_FALSE(cache.has("short_ttl"));
    EXPECT_FALSE(cache.has("long_ttl"));
}

// 数値型のキャッシュテスト
TEST_F(CacheTest, NumericCache) {
    Cache<int, double> numeric_cache;
    
    numeric_cache.put(1, 1.5);
    numeric_cache.put(2, 2.7);
    numeric_cache.put(3, 3.14159);
    
    EXPECT_TRUE(numeric_cache.has(1));
    EXPECT_TRUE(numeric_cache.has(2));
    EXPECT_TRUE(numeric_cache.has(3));
    EXPECT_FALSE(numeric_cache.has(4));
    
    auto val1 = numeric_cache.get(1);
    auto val2 = numeric_cache.get(2);
    auto val3 = numeric_cache.get(3);
    
    ASSERT_TRUE(val1.has_value());
    ASSERT_TRUE(val2.has_value());
    ASSERT_TRUE(val3.has_value());
    
    EXPECT_DOUBLE_EQ(*val1, 1.5);
    EXPECT_DOUBLE_EQ(*val2, 2.7);
    EXPECT_DOUBLE_EQ(*val3, 3.14159);
}

// 大量データのテスト
TEST_F(CacheTest, LargeDataSet) {
    const int num_entries = 1000;
    
    // 大量のエントリを追加
    for (int i = 0; i < num_entries; ++i) {
        cache.put("key" + std::to_string(i), "value" + std::to_string(i));
    }
    
    // すべてのエントリが存在することを確認
    for (int i = 0; i < num_entries; ++i) {
        std::string key = "key" + std::to_string(i);
        std::string expected_value = "value" + std::to_string(i);
        
        EXPECT_TRUE(cache.has(key));
        auto value = cache.get(key);
        ASSERT_TRUE(value.has_value());
        EXPECT_EQ(*value, expected_value);
    }
}

// キーの型としてカスタム構造体を使用
struct CustomKey {
    int id;
    std::string name;
    
    bool operator<(const CustomKey& other) const {
        if (id != other.id) return id < other.id;
        return name < other.name;
    }
    
    bool operator==(const CustomKey& other) const {
        return id == other.id && name == other.name;
    }
};

TEST_F(CacheTest, CustomKeyType) {
    Cache<CustomKey, std::string> custom_cache;
    
    CustomKey key1{1, "first"};
    CustomKey key2{2, "second"};
    CustomKey key3{1, "third"};  // 同じidだが異なるname
    
    custom_cache.put(key1, "value1");
    custom_cache.put(key2, "value2");
    custom_cache.put(key3, "value3");
    
    EXPECT_TRUE(custom_cache.has(key1));
    EXPECT_TRUE(custom_cache.has(key2));
    EXPECT_TRUE(custom_cache.has(key3));
    
    auto val1 = custom_cache.get(key1);
    auto val2 = custom_cache.get(key2);
    auto val3 = custom_cache.get(key3);
    
    ASSERT_TRUE(val1.has_value());
    ASSERT_TRUE(val2.has_value());
    ASSERT_TRUE(val3.has_value());
    
    EXPECT_EQ(*val1, "value1");
    EXPECT_EQ(*val2, "value2");
    EXPECT_EQ(*val3, "value3");
}

// スレッドセーフティテスト（基本的な同時アクセス）
TEST_F(CacheTest, ConcurrentAccess) {
    const int num_threads = 4;
    const int entries_per_thread = 100;
    std::vector<std::thread> threads;
    
    // 複数スレッドでキャッシュにデータを追加
    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back([this, t, entries_per_thread]() {
            for (int i = 0; i < entries_per_thread; ++i) {
                std::string key = "thread" + std::to_string(t) + "_key" + std::to_string(i);
                std::string value = "thread" + std::to_string(t) + "_value" + std::to_string(i);
                cache.put(key, value);
            }
        });
    }
    
    // すべてのスレッドの完了を待機
    for (auto& thread : threads) {
        thread.join();
    }
    
    // すべてのエントリが正しく保存されていることを確認
    for (int t = 0; t < num_threads; ++t) {
        for (int i = 0; i < entries_per_thread; ++i) {
            std::string key = "thread" + std::to_string(t) + "_key" + std::to_string(i);
            std::string expected_value = "thread" + std::to_string(t) + "_value" + std::to_string(i);
            
            EXPECT_TRUE(cache.has(key));
            auto value = cache.get(key);
            ASSERT_TRUE(value.has_value());
            EXPECT_EQ(*value, expected_value);
        }
    }
}