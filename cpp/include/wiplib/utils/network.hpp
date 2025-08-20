#pragma once

#include <string>
#include <vector>
#include <optional>
#include <chrono>
#include <unordered_map>
#include <memory>
#include <atomic>
#include <mutex>
#include <functional>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <iphlpapi.h>
#else
    #include <sys/socket.h>
    #include <netinet/in.h>
#endif
#include <future>
#include <thread>

namespace wiplib::utils {

/**
 * @brief ネットワークインターフェース情報
 */
struct NetworkInterface {
    std::string name;
    std::string ip_address;
    std::string netmask;
    std::string broadcast;
    std::string mac_address;
    bool is_up = false;
    bool is_loopback = false;
    uint64_t bytes_sent = 0;
    uint64_t bytes_received = 0;
    uint32_t mtu = 0;
};

/**
 * @brief IPv4アドレス解決結果
 */
struct IPv4Resolution {
    std::string hostname;
    std::vector<std::string> ip_addresses;
    std::chrono::steady_clock::time_point resolved_time;
    std::chrono::seconds ttl{300};
    
    /**
     * @brief 解決結果が有効かチェック
     */
    bool is_valid() const {
        auto now = std::chrono::steady_clock::now();
        auto elapsed = now - resolved_time;
        return elapsed < ttl && !ip_addresses.empty();
    }
};

/**
 * @brief ネットワーク統計情報
 */
struct NetworkStats {
    std::atomic<uint64_t> dns_queries{0};
    std::atomic<uint64_t> dns_cache_hits{0};
    std::atomic<uint64_t> dns_failures{0};
    std::atomic<uint64_t> connection_attempts{0};
    std::atomic<uint64_t> successful_connections{0};
    std::atomic<uint64_t> failed_connections{0};
    std::atomic<uint64_t> bytes_sent{0};
    std::atomic<uint64_t> bytes_received{0};
    std::chrono::steady_clock::time_point start_time{std::chrono::steady_clock::now()};
    NetworkStats() = default;
    NetworkStats(const NetworkStats& o) {
        dns_queries.store(o.dns_queries.load()); dns_cache_hits.store(o.dns_cache_hits.load()); dns_failures.store(o.dns_failures.load()); connection_attempts.store(o.connection_attempts.load()); successful_connections.store(o.successful_connections.load()); failed_connections.store(o.failed_connections.load()); bytes_sent.store(o.bytes_sent.load()); bytes_received.store(o.bytes_received.load()); start_time = o.start_time;
    }
    NetworkStats& operator=(const NetworkStats& o) { if (this!=&o) { dns_queries.store(o.dns_queries.load()); dns_cache_hits.store(o.dns_cache_hits.load()); dns_failures.store(o.dns_failures.load()); connection_attempts.store(o.connection_attempts.load()); successful_connections.store(o.successful_connections.load()); failed_connections.store(o.failed_connections.load()); bytes_sent.store(o.bytes_sent.load()); bytes_received.store(o.bytes_received.load()); start_time = o.start_time; } return *this; }
    
    /**
     * @brief DNS成功率を計算
     */
    double get_dns_success_rate() const {
        uint64_t total = dns_queries.load();
        return total > 0 ? static_cast<double>(total - dns_failures.load()) / total : 0.0;
    }
    
    /**
     * @brief 接続成功率を計算
     */
    double get_connection_success_rate() const {
        uint64_t total = connection_attempts.load();
        return total > 0 ? static_cast<double>(successful_connections.load()) / total : 0.0;
    }
};

/**
 * @brief ネットワーク診断結果
 */
struct NetworkDiagnostics {
    bool internet_connectivity = false;
    bool dns_resolution = false;
    bool local_network = false;
    std::chrono::milliseconds ping_latency{0};
    double packet_loss_rate = 0.0;
    std::string primary_dns_server;
    std::vector<std::string> available_interfaces;
    std::string default_gateway;
    std::unordered_map<std::string, std::string> diagnostic_details;
};

/**
 * @brief IPv4名前解決クラス
 */
class IPv4Resolver {
public:
    /**
     * @brief コンストラクタ
     * @param cache_size DNSキャッシュサイズ
     * @param cache_ttl デフォルトキャッシュTTL
     */
    explicit IPv4Resolver(size_t cache_size = 1000, std::chrono::seconds cache_ttl = std::chrono::seconds{300});
    
    ~IPv4Resolver();
    
    /**
     * @brief ホスト名をIPアドレスに解決（同期）
     * @param hostname ホスト名
     * @param timeout タイムアウト時間
     * @return 解決結果
     */
    std::optional<IPv4Resolution> resolve_sync(
        const std::string& hostname,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{5000}
    );
    
    /**
     * @brief ホスト名をIPアドレスに解決（非同期）
     * @param hostname ホスト名
     * @param timeout タイムアウト時間
     * @return 解決結果のFuture
     */
    std::future<std::optional<IPv4Resolution>> resolve_async(
        const std::string& hostname,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{5000}
    );
    
    /**
     * @brief 複数ホスト名を一括解決
     * @param hostnames ホスト名リスト
     * @param timeout タイムアウト時間
     * @return 解決結果マップ
     */
    std::unordered_map<std::string, std::optional<IPv4Resolution>> resolve_multiple(
        const std::vector<std::string>& hostnames,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{5000}
    );
    
    /**
     * @brief IPアドレスを逆引き
     * @param ip_address IPアドレス
     * @param timeout タイムアウト時間
     * @return ホスト名
     */
    std::optional<std::string> reverse_lookup(
        const std::string& ip_address,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{5000}
    );
    
    /**
     * @brief DNSキャッシュをクリア
     */
    void clear_cache();
    
    /**
     * @brief キャッシュエントリを追加/更新
     * @param hostname ホスト名
     * @param resolution 解決結果
     */
    void cache_resolution(const std::string& hostname, const IPv4Resolution& resolution);
    
    /**
     * @brief キャッシュから解決結果を取得
     * @param hostname ホスト名
     * @return 解決結果（キャッシュにない場合nullopt）
     */
    std::optional<IPv4Resolution> get_cached_resolution(const std::string& hostname) const;
    
    /**
     * @brief DNSサーバーを設定
     * @param dns_servers DNSサーバーリスト
     */
    void set_dns_servers(const std::vector<std::string>& dns_servers);
    
    /**
     * @brief DNSサーバーを取得
     * @return DNSサーバーリスト
     */
    std::vector<std::string> get_dns_servers() const;
    
    /**
     * @brief 統計情報を取得
     * @return 統計情報
     */
    NetworkStats get_statistics() const;
    
    /**
     * @brief キャッシュ統計を取得
     * @return キャッシュ統計マップ
     */
    std::unordered_map<std::string, uint64_t> get_cache_statistics() const;

private:
    size_t cache_size_;
    std::chrono::seconds cache_ttl_;
    
    // DNSキャッシュ
    mutable std::mutex cache_mutex_;
    std::unordered_map<std::string, IPv4Resolution> dns_cache_;
    
    // DNS設定
    std::vector<std::string> dns_servers_;
    
    // 統計
    mutable NetworkStats stats_;
    
    // プライベートメソッド
    std::optional<IPv4Resolution> resolve_with_system_dns(const std::string& hostname);
    std::optional<IPv4Resolution> resolve_with_custom_dns(const std::string& hostname, const std::string& dns_server);
    void cleanup_expired_cache_entries();
    std::vector<std::string> get_system_dns_servers() const;
    bool is_valid_hostname(const std::string& hostname) const;
    bool is_valid_ip_address(const std::string& ip_address) const;
};

/**
 * @brief ネットワーク状態チェッククラス
 */
class NetworkStateChecker {
public:
    /**
     * @brief コンストラクタ
     */
    NetworkStateChecker();
    
    ~NetworkStateChecker();
    
    /**
     * @brief インターネット接続をチェック
     * @param test_hosts テスト用ホストリスト
     * @param timeout タイムアウト時間
     * @return 接続可能な場合true
     */
    bool check_internet_connectivity(
        const std::vector<std::string>& test_hosts = {"8.8.8.8", "1.1.1.1", "google.com"},
        std::chrono::milliseconds timeout = std::chrono::milliseconds{5000}
    );
    
    /**
     * @brief DNS解決をチェック
     * @param test_hostname テスト用ホスト名
     * @param timeout タイムアウト時間
     * @return 解決可能な場合true
     */
    bool check_dns_resolution(
        const std::string& test_hostname = "google.com",
        std::chrono::milliseconds timeout = std::chrono::milliseconds{5000}
    );
    
    /**
     * @brief 特定ホストの疎通をチェック
     * @param host ホスト
     * @param port ポート
     * @param timeout タイムアウト時間
     * @return 疎通可能な場合true
     */
    bool check_host_reachability(
        const std::string& host,
        uint16_t port,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{3000}
    );
    
    /**
     * @brief ネットワーク遅延を測定
     * @param host ホスト
     * @param port ポート
     * @param timeout タイムアウト時間
     * @return 遅延時間（接続できない場合nullopt）
     */
    std::optional<std::chrono::milliseconds> measure_latency(
        const std::string& host,
        uint16_t port,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{3000}
    );
    
    /**
     * @brief 利用可能なネットワークインターフェースを取得
     * @return インターフェース一覧
     */
    std::vector<NetworkInterface> get_network_interfaces();
    
    /**
     * @brief デフォルトゲートウェイを取得
     * @return デフォルトゲートウェイIP
     */
    std::optional<std::string> get_default_gateway();
    
    /**
     * @brief 包括的ネットワーク診断を実行
     * @return 診断結果
     */
    NetworkDiagnostics run_comprehensive_diagnostics();
    
    /**
     * @brief 帯域幅を測定
     * @param test_server テストサーバー
     * @param test_size テストデータサイズ（バイト）
     * @return 帯域幅（bps）
     */
    std::optional<double> measure_bandwidth(
        const std::string& test_server = "speedtest.net",
        size_t test_size = 1024 * 1024
    );
    
    /**
     * @brief パケット損失率を測定
     * @param host ホスト
     * @param packet_count パケット数
     * @param timeout タイムアウト時間
     * @return 損失率（0.0-1.0）
     */
    double measure_packet_loss(
        const std::string& host,
        size_t packet_count = 10,
        std::chrono::milliseconds timeout = std::chrono::milliseconds{1000}
    );
    
    /**
     * @brief ネットワーク品質スコアを計算
     * @param host ホスト
     * @param port ポート
     * @return 品質スコア（0.0-1.0）
     */
    double calculate_network_quality_score(const std::string& host, uint16_t port);
    
    /**
     * @brief 継続監視を開始
     * @param interval 監視間隔
     * @param callback 状態変化コールバック
     */
    void start_monitoring(
        std::chrono::seconds interval = std::chrono::seconds{30},
        std::function<void(const NetworkDiagnostics&)> callback = nullptr
    );
    
    /**
     * @brief 継続監視を停止
     */
    void stop_monitoring();

private:
    std::atomic<bool> monitoring_enabled_{false};
    std::unique_ptr<std::thread> monitoring_thread_;
    std::function<void(const NetworkDiagnostics&)> monitoring_callback_;
    
    // プライベートメソッド
    bool ping_host(const std::string& host, std::chrono::milliseconds timeout);
    bool tcp_connect_test(const std::string& host, uint16_t port, std::chrono::milliseconds timeout);
    std::chrono::milliseconds measure_tcp_connect_time(const std::string& host, uint16_t port, std::chrono::milliseconds timeout);
    std::vector<std::string> get_system_dns_servers();
    void monitoring_loop(std::chrono::seconds interval);
    NetworkInterface parse_interface_info(const std::string& interface_name);
    std::string execute_system_command(const std::string& command);
};

/**
 * @brief ネットワークユーティリティ関数
 */
namespace network_utils {
    /**
     * @brief sockaddr_inを文字列に変換
     * @param addr sockaddr_in構造体
     * @return "IP:PORT"形式の文字列
     */
    std::string sockaddr_to_string(const struct sockaddr_in& addr);
    
    /**
     * @brief 文字列からsockaddr_inを作成
     * @param addr_str "IP:PORT"形式の文字列
     * @return sockaddr_in構造体
     */
    std::optional<struct sockaddr_in> string_to_sockaddr(const std::string& addr_str);
    
    /**
     * @brief IPアドレスの有効性をチェック
     * @param ip_address IPアドレス文字列
     * @return 有効な場合true
     */
    bool is_valid_ipv4_address(const std::string& ip_address);
    
    /**
     * @brief プライベートIPアドレスかチェック
     * @param ip_address IPアドレス文字列
     * @return プライベートIPの場合true
     */
    bool is_private_ipv4_address(const std::string& ip_address);
    
    /**
     * @brief ローカルIPアドレスかチェック
     * @param ip_address IPアドレス文字列
     * @return ローカルIPの場合true
     */
    bool is_loopback_ipv4_address(const std::string& ip_address);
    
    /**
     * @brief ネットワークアドレスを計算
     * @param ip_address IPアドレス
     * @param netmask ネットマスク
     * @return ネットワークアドレス
     */
    std::string calculate_network_address(const std::string& ip_address, const std::string& netmask);
    
    /**
     * @brief ブロードキャストアドレスを計算
     * @param ip_address IPアドレス
     * @param netmask ネットマスク
     * @return ブロードキャストアドレス
     */
    std::string calculate_broadcast_address(const std::string& ip_address, const std::string& netmask);
    
    /**
     * @brief CIDR表記をネットマスクに変換
     * @param cidr CIDR値（例：24）
     * @return ネットマスク文字列
     */
    std::string cidr_to_netmask(int cidr);
    
    /**
     * @brief ネットマスクをCIDR表記に変換
     * @param netmask ネットマスク文字列
     * @return CIDR値
     */
    int netmask_to_cidr(const std::string& netmask);
    
    /**
     * @brief MACアドレスの正規化
     * @param mac_address MACアドレス文字列
     * @return 正規化されたMACアドレス
     */
    std::string normalize_mac_address(const std::string& mac_address);
    
    /**
     * @brief ポート番号の有効性をチェック
     * @param port ポート番号
     * @return 有効な場合true
     */
    bool is_valid_port(uint16_t port);
    
    /**
     * @brief 利用可能なポートを検索
     * @param start_port 開始ポート
     * @param end_port 終了ポート
     * @return 利用可能なポート（見つからない場合nullopt）
     */
    std::optional<uint16_t> find_available_port(uint16_t start_port = 49152, uint16_t end_port = 65535);
    
    /**
     * @brief ホスト名の正規化
     * @param hostname ホスト名
     * @return 正規化されたホスト名
     */
    std::string normalize_hostname(const std::string& hostname);
}

/**
 * @brief ネットワークファクトリー
 */
class NetworkFactory {
public:
    /**
     * @brief 基本的なIPv4リゾルバーを作成
     */
    static std::unique_ptr<IPv4Resolver> create_basic_resolver();
    
    /**
     * @brief 高性能IPv4リゾルバーを作成
     */
    static std::unique_ptr<IPv4Resolver> create_high_performance_resolver();
    
    /**
     * @brief ネットワーク状態チェッカーを作成
     */
    static std::unique_ptr<NetworkStateChecker> create_network_checker();
};

} // namespace wiplib::utils
