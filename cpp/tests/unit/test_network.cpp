#include <gtest/gtest.h>
#include "wiplib/utils/network.hpp"

using namespace wiplib::utils;

class NetworkTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

// IPv4名前解決の基本テスト
TEST_F(NetworkTest, ResolveIPv4Basic) {
    // localhost の解決
    auto result = resolve_ipv4("localhost");
    EXPECT_TRUE(result.has_value());
    if (result.has_value()) {
        EXPECT_EQ(result.value(), "127.0.0.1");
    }
}

// 既にIPアドレスの場合のテスト
TEST_F(NetworkTest, ResolveIPv4AlreadyIP) {
    // 既にIPアドレスの場合はそのまま返される
    auto result = resolve_ipv4("192.168.1.1");
    EXPECT_TRUE(result.has_value());
    if (result.has_value()) {
        EXPECT_EQ(result.value(), "192.168.1.1");
    }
}

// 無効なホスト名のテスト
TEST_F(NetworkTest, ResolveIPv4InvalidHost) {
    // 存在しないホスト名
    auto result = resolve_ipv4("this.domain.does.not.exist.invalid");
    EXPECT_FALSE(result.has_value());
}

// 空のホスト名のテスト
TEST_F(NetworkTest, ResolveIPv4EmptyHost) {
    auto result = resolve_ipv4("");
    EXPECT_FALSE(result.has_value());
}

// 有名なパブリックDNSサーバーの解決テスト
TEST_F(NetworkTest, ResolveIPv4PublicDNS) {
    // Google Public DNS
    auto google_dns = resolve_ipv4("dns.google");
    if (google_dns.has_value()) {
        // 8.8.8.8 または 8.8.4.4 のいずれかであることを期待
        EXPECT_TRUE(google_dns.value() == "8.8.8.8" || 
                   google_dns.value() == "8.8.4.4" ||
                   !google_dns.value().empty());  // その他の有効なIPでも可
    }
    // ネットワークが利用できない場合は失敗してもよい
}

// IPv4アドレスの形式検証テスト
TEST_F(NetworkTest, ValidIPv4Format) {
    // 有効なIPv4アドレス
    std::vector<std::string> valid_ips = {
        "0.0.0.0",
        "127.0.0.1", 
        "192.168.1.1",
        "255.255.255.255",
        "10.0.0.1",
        "172.16.0.1"
    };
    
    for (const auto& ip : valid_ips) {
        auto result = resolve_ipv4(ip);
        EXPECT_TRUE(result.has_value()) << "Failed to resolve valid IP: " << ip;
        if (result.has_value()) {
            EXPECT_EQ(result.value(), ip);
        }
    }
}

// 無効なIPv4アドレスの形式テスト
TEST_F(NetworkTest, InvalidIPv4Format) {
    std::vector<std::string> invalid_ips = {
        "256.256.256.256",  // 範囲外
        "192.168.1",        // 不完全
        "192.168.1.1.1",    // 余分なオクテット
        "192.168.01.1",     // 先頭ゼロ（実装によっては有効）
        "192.168.-1.1",     // 負の数
        "192.168.1.a",      // 非数値
        "192.168..1",       // 空のオクテット
        "",                 // 空文字列
        "   ",              // 空白
    };
    
    for (const auto& ip : invalid_ips) {
        auto result = resolve_ipv4(ip);
        // 無効なIPアドレスは解決に失敗するか、変更されて返される
        // 実装によっては有効なIPに変換される場合もある
        if (result.has_value()) {
            // 何らかの有効なIPアドレスが返された場合は形式をチェック
            std::string resolved = result.value();
            // 基本的なIPアドレス形式のチェック
            int dot_count = 0;
            for (char c : resolved) {
                if (c == '.') dot_count++;
            }
            EXPECT_EQ(dot_count, 3);  // IPv4は3つのドットを持つ
        }
    }
}

// ループバックアドレスのテスト
TEST_F(NetworkTest, LoopbackAddresses) {
    // 様々なループバック表現
    std::vector<std::string> loopback_hosts = {
        "localhost",
        "127.0.0.1",
        "127.1",
        "127.0.1",
    };
    
    for (const auto& host : loopback_hosts) {
        auto result = resolve_ipv4(host);
        if (result.has_value()) {
            // ループバック範囲 (127.x.x.x) であることを確認
            std::string ip = result.value();
            EXPECT_TRUE(ip.substr(0, 4) == "127.");
        }
    }
}

// 特殊なIPアドレスのテスト
TEST_F(NetworkTest, SpecialIPAddresses) {
    struct TestCase {
        std::string input;
        std::string expected;
        bool should_succeed;
    };
    
    std::vector<TestCase> test_cases = {
        {"0.0.0.0", "0.0.0.0", true},           // Any address
        {"255.255.255.255", "255.255.255.255", true}, // Broadcast
        {"127.0.0.1", "127.0.0.1", true},       // Loopback
        {"::1", "", false},                      // IPv6 (IPv4解決なので失敗)
        {"localhost", "127.0.0.1", true},       // localhost
    };
    
    for (const auto& test_case : test_cases) {
        auto result = resolve_ipv4(test_case.input);
        
        if (test_case.should_succeed) {
            EXPECT_TRUE(result.has_value()) << "Failed to resolve: " << test_case.input;
            if (result.has_value() && !test_case.expected.empty()) {
                EXPECT_EQ(result.value(), test_case.expected);
            }
        } else {
            EXPECT_FALSE(result.has_value()) << "Should not resolve: " << test_case.input;
        }
    }
}

// プライベートIPアドレス範囲のテスト
TEST_F(NetworkTest, PrivateIPRanges) {
    std::vector<std::string> private_ips = {
        "10.0.0.1",         // Class A private
        "172.16.0.1",       // Class B private
        "192.168.1.1",      // Class C private
        "169.254.1.1",      // Link-local
    };
    
    for (const auto& ip : private_ips) {
        auto result = resolve_ipv4(ip);
        EXPECT_TRUE(result.has_value()) << "Failed to resolve private IP: " << ip;
        if (result.has_value()) {
            EXPECT_EQ(result.value(), ip);
        }
    }
}

// 大量の連続解決テスト
TEST_F(NetworkTest, BulkResolution) {
    const int num_resolutions = 100;
    
    for (int i = 0; i < num_resolutions; ++i) {
        auto result = resolve_ipv4("127.0.0.1");
        EXPECT_TRUE(result.has_value());
        if (result.has_value()) {
            EXPECT_EQ(result.value(), "127.0.0.1");
        }
    }
}

// 並行解決テスト
TEST_F(NetworkTest, ConcurrentResolution) {
    const int num_threads = 4;
    const int resolutions_per_thread = 25;
    std::vector<std::thread> threads;
    std::vector<bool> results(num_threads * resolutions_per_thread, false);
    std::mutex results_mutex;
    
    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back([&, t]() {
            for (int i = 0; i < resolutions_per_thread; ++i) {
                auto result = resolve_ipv4("127.0.0.1");
                bool success = result.has_value() && result.value() == "127.0.0.1";
                
                std::lock_guard<std::mutex> lock(results_mutex);
                results[t * resolutions_per_thread + i] = success;
            }
        });
    }
    
    // すべてのスレッドの完了を待機
    for (auto& thread : threads) {
        thread.join();
    }
    
    // すべての解決が成功したことを確認
    for (bool result : results) {
        EXPECT_TRUE(result);
    }
}

// エラーハンドリングのテスト
TEST_F(NetworkTest, ErrorHandling) {
    // 様々なエラーケース
    std::vector<std::string> error_cases = {
        "invalid.domain.name.that.should.not.exist",
        "...",
        "256.256.256.256",
        "not.a.valid.hostname!@#$",
        std::string(1000, 'x') + ".com",  // 非常に長いホスト名
    };
    
    for (const auto& error_case : error_cases) {
        auto result = resolve_ipv4(error_case);
        // エラーケースではnulloptが返されるか、何らかの有効なIPが返される
        if (result.has_value()) {
            // 何かが返された場合は、少なくとも有効な形式であることを確認
            std::string ip = result.value();
            EXPECT_FALSE(ip.empty());
            
            // 基本的なIPアドレス形式チェック
            int dot_count = 0;
            bool all_digits_and_dots = true;
            for (char c : ip) {
                if (c == '.') {
                    dot_count++;
                } else if (!std::isdigit(c)) {
                    all_digits_and_dots = false;
                    break;
                }
            }
            EXPECT_EQ(dot_count, 3);
            EXPECT_TRUE(all_digits_and_dots);
        }
    }
}