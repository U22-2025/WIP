/**
 * @file wip_performance_test.cpp
 * @brief WIPライブラリパフォーマンス測定ツール
 * 
 * C++版のパフォーマンスをPython版と比較測定し、ベンチマーク結果を出力します。
 */

#include <iostream>
#include <chrono>
#include <vector>
#include <thread>
#include <future>
#include <random>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <algorithm>

#include "wiplib/client/client.hpp"
#include "wiplib/client/weather_client.hpp"
#include "wiplib/packet/codec.hpp"
#include "wiplib/packet/checksum.hpp"
#include "wiplib/compatibility/python_protocol.hpp"

using namespace wiplib::client;
using namespace wiplib::proto;
using namespace wiplib::compatibility;

class PerformanceTester {
public:
    struct BenchmarkResult {
        std::string test_name;
        size_t iterations;
        double total_time_ms;
        double average_time_ms;
        double min_time_ms;
        double max_time_ms;
        double median_time_ms;
        double std_deviation_ms;
        double throughput_ops_per_sec;
        
        void calculate_statistics(const std::vector<double>& times) {
            total_time_ms = std::accumulate(times.begin(), times.end(), 0.0);
            average_time_ms = total_time_ms / times.size();
            
            auto minmax = std::minmax_element(times.begin(), times.end());
            min_time_ms = *minmax.first;
            max_time_ms = *minmax.second;
            
            std::vector<double> sorted_times = times;
            std::sort(sorted_times.begin(), sorted_times.end());
            size_t mid = sorted_times.size() / 2;
            if (sorted_times.size() % 2 == 0) {
                median_time_ms = (sorted_times[mid - 1] + sorted_times[mid]) / 2.0;
            } else {
                median_time_ms = sorted_times[mid];
            }
            
            double variance = 0.0;
            for (double time : times) {
                variance += (time - average_time_ms) * (time - average_time_ms);
            }
            variance /= times.size();
            std_deviation_ms = std::sqrt(variance);
            
            throughput_ops_per_sec = 1000.0 / average_time_ms;
        }
    };

    struct TestOptions {
        size_t iterations = 1000;
        size_t concurrent_threads = 1;
        bool warmup = true;
        size_t warmup_iterations = 100;
        bool measure_memory = false;
        std::string output_format = "text"; // text, json, csv
        bool compare_python = false;
        bool detailed_stats = false;
    };

    static void print_usage(const char* program_name) {
        std::cout << "WIPライブラリパフォーマンス測定ツール\n";
        std::cout << "使用方法: " << program_name << " [オプション] [テスト名]\n\n";
        std::cout << "テスト名:\n";
        std::cout << "  packet-encode       パケットエンコードのベンチマーク\n";
        std::cout << "  packet-decode       パケットデコードのベンチマーク\n";
        std::cout << "  checksum            チェックサム計算のベンチマーク\n";
        std::cout << "  client-creation     クライアント作成のベンチマーク\n";
        std::cout << "  network-simulation  ネットワーク通信シミュレーション\n";
        std::cout << "  all                 全てのテストを実行\n\n";
        std::cout << "オプション:\n";
        std::cout << "  -i, --iterations N  テストの実行回数 (デフォルト: 1000)\n";
        std::cout << "  -t, --threads N     並行スレッド数 (デフォルト: 1)\n";
        std::cout << "  -w, --warmup        ウォームアップを実行 (デフォルト: 有効)\n";
        std::cout << "  -m, --memory        メモリ使用量を測定\n";
        std::cout << "  -p, --python-compare Python版との比較\n";
        std::cout << "  -d, --detailed      詳細統計を表示\n";
        std::cout << "  --format FORMAT     出力形式 (text|json|csv)\n";
        std::cout << "  -o, --output FILE   結果をファイルに出力\n";
        std::cout << "  --help              このヘルプを表示\n\n";
        std::cout << "例:\n";
        std::cout << "  " << program_name << " packet-encode\n";
        std::cout << "  " << program_name << " -i 10000 -t 4 all\n";
        std::cout << "  " << program_name << " --format json --output results.json\n";
    }

private:
    static Header create_test_header() {
        Header h{};
        h.version = 1;
        h.packet_id = 12345;
        h.type = PacketType::WeatherRequest;
        h.flags.weather = true;
        h.flags.temperature = true;
        h.day = 0;
        h.timestamp = PythonProtocolAdapter::generate_python_timestamp();
        h.area_code = 130010;
        h.checksum = 0; // 後で計算
        return h;
    }

    static std::vector<uint8_t> create_test_packet_data() {
        Header header = create_test_header();
        auto encoded = encode_header(header);
        if (encoded.has_value()) {
            return std::vector<uint8_t>(encoded.value().begin(), encoded.value().end());
        }
        return std::vector<uint8_t>(16, 0x00); // フォールバック
    }

public:
    static BenchmarkResult benchmark_packet_encode(const TestOptions& options) {
        BenchmarkResult result;
        result.test_name = "パケットエンコード";
        result.iterations = options.iterations;

        Header test_header = create_test_header();
        std::vector<double> times;
        times.reserve(options.iterations);

        // ウォームアップ
        if (options.warmup) {
            for (size_t i = 0; i < options.warmup_iterations; ++i) {
                auto encoded = encode_header(test_header);
                (void)encoded; // 結果を使用
            }
        }

        // 実際の測定
        for (size_t i = 0; i < options.iterations; ++i) {
            auto start = std::chrono::high_resolution_clock::now();
            
            auto encoded = encode_header(test_header);
            
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);
            times.push_back(duration.count() / 1000000.0); // ナノ秒をミリ秒に変換
        }

        result.calculate_statistics(times);
        return result;
    }

    static BenchmarkResult benchmark_packet_decode(const TestOptions& options) {
        BenchmarkResult result;
        result.test_name = "パケットデコード";
        result.iterations = options.iterations;

        std::vector<uint8_t> test_data = create_test_packet_data();
        std::vector<double> times;
        times.reserve(options.iterations);

        // ウォームアップ
        if (options.warmup) {
            for (size_t i = 0; i < options.warmup_iterations; ++i) {
                auto decoded = decode_header(test_data);
                (void)decoded;
            }
        }

        // 実際の測定
        for (size_t i = 0; i < options.iterations; ++i) {
            auto start = std::chrono::high_resolution_clock::now();
            
            auto decoded = decode_header(test_data);
            
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);
            times.push_back(duration.count() / 1000000.0);
        }

        result.calculate_statistics(times);
        return result;
    }

    static BenchmarkResult benchmark_checksum(const TestOptions& options) {
        BenchmarkResult result;
        result.test_name = "チェックサム計算";
        result.iterations = options.iterations;

        // テストデータの生成（様々なサイズ）
        std::vector<std::vector<uint8_t>> test_data_sets;
        std::random_device rd;
        std::mt19937 gen(rd());
        std::uniform_int_distribution<uint8_t> byte_dis(0, 255);

        for (size_t size : {16, 64, 256, 1024}) {
            std::vector<uint8_t> data(size);
            for (auto& byte : data) {
                byte = byte_dis(gen);
            }
            test_data_sets.push_back(data);
        }

        std::vector<double> times;
        times.reserve(options.iterations);

        // ウォームアップ
        if (options.warmup) {
            for (size_t i = 0; i < options.warmup_iterations; ++i) {
                for (const auto& data : test_data_sets) {
                    uint16_t checksum = wiplib::packet::calc_checksum12(data);
                    (void)checksum;
                }
            }
        }

        // 実際の測定
        size_t data_set_index = 0;
        for (size_t i = 0; i < options.iterations; ++i) {
            const auto& data = test_data_sets[data_set_index % test_data_sets.size()];
            data_set_index++;

            auto start = std::chrono::high_resolution_clock::now();
            
            uint16_t checksum = wiplib::packet::calc_checksum12(data);
            
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);
            times.push_back(duration.count() / 1000000.0);
        }

        result.calculate_statistics(times);
        return result;
    }

    static BenchmarkResult benchmark_client_creation(const TestOptions& options) {
        BenchmarkResult result;
        result.test_name = "クライアント作成";
        result.iterations = options.iterations;

        std::vector<double> times;
        times.reserve(options.iterations);

        // ウォームアップ
        if (options.warmup) {
            for (size_t i = 0; i < options.warmup_iterations; ++i) {
                Client client;
                (void)client;
            }
        }

        // 実際の測定
        for (size_t i = 0; i < options.iterations; ++i) {
            auto start = std::chrono::high_resolution_clock::now();
            
            Client client;
            client.set_coordinates(35.6762, 139.6503);
            
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);
            times.push_back(duration.count() / 1000000.0);
        }

        result.calculate_statistics(times);
        return result;
    }

    static BenchmarkResult benchmark_network_simulation(const TestOptions& options) {
        BenchmarkResult result;
        result.test_name = "ネットワーク通信シミュレーション";
        result.iterations = options.iterations;

        std::vector<double> times;
        times.reserve(options.iterations);

        // 実際の測定（ネットワーク処理をシミュレート）
        for (size_t i = 0; i < options.iterations; ++i) {
            auto start = std::chrono::high_resolution_clock::now();
            
            // パケット作成
            Header header = create_test_header();
            header.packet_id = static_cast<uint16_t>(i);
            
            // エンコード
            auto encoded = encode_header(header);
            if (!encoded.has_value()) continue;
            
            // ネットワーク遅延シミュレーション（1-10ms）
            std::random_device rd;
            std::mt19937 gen(rd());
            std::uniform_int_distribution<int> delay_dis(1, 10);
            std::this_thread::sleep_for(std::chrono::microseconds(delay_dis(gen) * 100));
            
            // デコード
            auto decoded = decode_header(encoded.value());
            
            auto end = std::chrono::high_resolution_clock::now();
            auto duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end - start);
            times.push_back(duration.count() / 1000000.0);
        }

        result.calculate_statistics(times);
        return result;
    }

    static BenchmarkResult benchmark_concurrent_operations(const TestOptions& options) {
        BenchmarkResult result;
        result.test_name = "並行処理";
        result.iterations = options.iterations;

        std::vector<double> times;
        times.reserve(options.iterations);

        size_t iterations_per_thread = options.iterations / options.concurrent_threads;

        auto start_total = std::chrono::high_resolution_clock::now();

        // 並行タスクを実行
        std::vector<std::future<void>> futures;
        for (size_t t = 0; t < options.concurrent_threads; ++t) {
            futures.push_back(std::async(std::launch::async, [iterations_per_thread]() {
                for (size_t i = 0; i < iterations_per_thread; ++i) {
                    Header header = create_test_header();
                    header.packet_id = static_cast<uint16_t>(i);
                    
                    auto encoded = encode_header(header);
                    if (encoded.has_value()) {
                        auto decoded = decode_header(encoded.value());
                        (void)decoded;
                    }
                }
            }));
        }

        // 全てのタスクの完了を待機
        for (auto& future : futures) {
            future.wait();
        }

        auto end_total = std::chrono::high_resolution_clock::now();
        auto total_duration = std::chrono::duration_cast<std::chrono::nanoseconds>(end_total - start_total);
        
        result.total_time_ms = total_duration.count() / 1000000.0;
        result.average_time_ms = result.total_time_ms / options.iterations;
        result.throughput_ops_per_sec = options.iterations / (result.total_time_ms / 1000.0);

        return result;
    }

    static void print_benchmark_result(const BenchmarkResult& result, const TestOptions& options, std::ostream& out = std::cout) {
        if (options.output_format == "json") {
            print_json_result(result, out);
            return;
        } else if (options.output_format == "csv") {
            print_csv_result(result, out);
            return;
        }

        out << "\n=== " << result.test_name << " ベンチマーク結果 ===\n";
        out << std::fixed << std::setprecision(3);
        out << "実行回数: " << result.iterations << "\n";
        out << "総実行時間: " << result.total_time_ms << " ms\n";
        out << "平均実行時間: " << result.average_time_ms << " ms\n";
        out << "最小実行時間: " << result.min_time_ms << " ms\n";
        out << "最大実行時間: " << result.max_time_ms << " ms\n";
        out << "中央値: " << result.median_time_ms << " ms\n";
        
        if (options.detailed_stats) {
            out << "標準偏差: " << result.std_deviation_ms << " ms\n";
        }
        
        out << "スループット: " << std::setprecision(1) << result.throughput_ops_per_sec << " ops/sec\n";

        // パフォーマンス評価
        if (result.average_time_ms < 0.1) {
            out << "評価: 🚀 優秀";
        } else if (result.average_time_ms < 1.0) {
            out << "評価: ✅ 良好";
        } else if (result.average_time_ms < 10.0) {
            out << "評価: ⚠️  普通";
        } else {
            out << "評価: 🐌 要改善";
        }
        out << "\n";
    }

private:
    static void print_json_result(const BenchmarkResult& result, std::ostream& out) {
        out << "{\n";
        out << "  \"test_name\": \"" << result.test_name << "\",\n";
        out << "  \"iterations\": " << result.iterations << ",\n";
        out << "  \"total_time_ms\": " << result.total_time_ms << ",\n";
        out << "  \"average_time_ms\": " << result.average_time_ms << ",\n";
        out << "  \"min_time_ms\": " << result.min_time_ms << ",\n";
        out << "  \"max_time_ms\": " << result.max_time_ms << ",\n";
        out << "  \"median_time_ms\": " << result.median_time_ms << ",\n";
        out << "  \"std_deviation_ms\": " << result.std_deviation_ms << ",\n";
        out << "  \"throughput_ops_per_sec\": " << result.throughput_ops_per_sec << ",\n";
        out << "  \"timestamp\": " << PythonProtocolAdapter::generate_python_timestamp() << "\n";
        out << "}\n";
    }

    static void print_csv_result(const BenchmarkResult& result, std::ostream& out) {
        out << result.test_name << ","
            << result.iterations << ","
            << result.total_time_ms << ","
            << result.average_time_ms << ","
            << result.min_time_ms << ","
            << result.max_time_ms << ","
            << result.median_time_ms << ","
            << result.std_deviation_ms << ","
            << result.throughput_ops_per_sec << "\n";
    }

public:
    static void print_csv_header(std::ostream& out) {
        out << "test_name,iterations,total_time_ms,average_time_ms,min_time_ms,max_time_ms,median_time_ms,std_deviation_ms,throughput_ops_per_sec\n";
    }

    static void run_all_benchmarks(const TestOptions& options, std::ostream& out = std::cout) {
        std::vector<BenchmarkResult> results;

        out << "🏁 WIPライブラリ パフォーマンステスト開始\n";
        out << "設定: " << options.iterations << " 回実行, " << options.concurrent_threads << " スレッド\n\n";

        if (options.output_format == "csv") {
            print_csv_header(out);
        }

        // 各ベンチマークを実行
        std::cout << "⏱️  パケットエンコード測定中...\n";
        results.push_back(benchmark_packet_encode(options));

        std::cout << "⏱️  パケットデコード測定中...\n";
        results.push_back(benchmark_packet_decode(options));

        std::cout << "⏱️  チェックサム計算測定中...\n";
        results.push_back(benchmark_checksum(options));

        std::cout << "⏱️  クライアント作成測定中...\n";
        results.push_back(benchmark_client_creation(options));

        if (options.concurrent_threads > 1) {
            std::cout << "⏱️  並行処理測定中...\n";
            results.push_back(benchmark_concurrent_operations(options));
        }

        std::cout << "⏱️  ネットワーク通信シミュレーション測定中...\n";
        results.push_back(benchmark_network_simulation(options));

        // 結果の表示
        for (const auto& result : results) {
            print_benchmark_result(result, options, out);
        }

        // 総合評価
        if (options.output_format == "text") {
            print_summary(results, options, out);
        }
    }

private:
    static void print_summary(const std::vector<BenchmarkResult>& results, const TestOptions& options, std::ostream& out) {
        out << "\n=== 総合パフォーマンス評価 ===\n";
        
        double total_throughput = 0.0;
        double fastest_operation = std::numeric_limits<double>::max();
        double slowest_operation = 0.0;
        
        for (const auto& result : results) {
            total_throughput += result.throughput_ops_per_sec;
            fastest_operation = std::min(fastest_operation, result.average_time_ms);
            slowest_operation = std::max(slowest_operation, result.average_time_ms);
        }

        out << std::fixed << std::setprecision(3);
        out << "総合スループット: " << std::setprecision(1) << total_throughput << " ops/sec\n";
        out << "最速操作: " << std::setprecision(3) << fastest_operation << " ms\n";
        out << "最遅操作: " << slowest_operation << " ms\n";
        out << "パフォーマンス比率: " << std::setprecision(1) << (fastest_operation / slowest_operation * 100) << "%\n";

        // Python版との比較（参考値）
        if (options.compare_python) {
            out << "\n📊 Python版との推定比較:\n";
            out << "C++版は概ね5-50倍高速と推定されます\n";
            out << "（実際の比較にはPython版での同等測定が必要）\n";
        }

        // ハードウェア情報
        out << "\n💻 測定環境:\n";
        out << "CPU: " << std::thread::hardware_concurrency() << " コア\n";
        out << "測定時刻: " << PythonDataConverter::format_python_datetime(
            PythonProtocolAdapter::generate_python_timestamp()
        ) << "\n";
    }
};

int main(int argc, char* argv[]) {
    PerformanceTester::TestOptions options;
    std::string test_name = "all";
    std::string output_file;

    // コマンドライン引数の解析
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        
        if (arg == "--help") {
            PerformanceTester::print_usage(argv[0]);
            return 0;
        } else if (arg == "-i" || arg == "--iterations") {
            if (i + 1 < argc) {
                options.iterations = std::stoul(argv[++i]);
            } else {
                std::cerr << "エラー: --iterations オプションには引数が必要です\n";
                return 1;
            }
        } else if (arg == "-t" || arg == "--threads") {
            if (i + 1 < argc) {
                options.concurrent_threads = std::stoul(argv[++i]);
            } else {
                std::cerr << "エラー: --threads オプションには引数が必要です\n";
                return 1;
            }
        } else if (arg == "-w" || arg == "--warmup") {
            options.warmup = true;
        } else if (arg == "-m" || arg == "--memory") {
            options.measure_memory = true;
        } else if (arg == "-p" || arg == "--python-compare") {
            options.compare_python = true;
        } else if (arg == "-d" || arg == "--detailed") {
            options.detailed_stats = true;
        } else if (arg == "--format") {
            if (i + 1 < argc) {
                options.output_format = argv[++i];
            } else {
                std::cerr << "エラー: --format オプションには引数が必要です\n";
                return 1;
            }
        } else if (arg == "-o" || arg == "--output") {
            if (i + 1 < argc) {
                output_file = argv[++i];
            } else {
                std::cerr << "エラー: --output オプションには引数が必要です\n";
                return 1;
            }
        } else if (arg[0] != '-') {
            test_name = arg;
        } else {
            std::cerr << "エラー: 不明なオプション: " << arg << "\n";
            PerformanceTester::print_usage(argv[0]);
            return 1;
        }
    }

    try {
        std::ofstream output_file_stream;
        std::ostream* output_stream = &std::cout;

        if (!output_file.empty()) {
            output_file_stream.open(output_file);
            if (!output_file_stream) {
                throw std::runtime_error("出力ファイルを開けません: " + output_file);
            }
            output_stream = &output_file_stream;
        }

        if (test_name == "all") {
            PerformanceTester::run_all_benchmarks(options, *output_stream);
        } else if (test_name == "packet-encode") {
            auto result = PerformanceTester::benchmark_packet_encode(options);
            PerformanceTester::print_benchmark_result(result, options, *output_stream);
        } else if (test_name == "packet-decode") {
            auto result = PerformanceTester::benchmark_packet_decode(options);
            PerformanceTester::print_benchmark_result(result, options, *output_stream);
        } else if (test_name == "checksum") {
            auto result = PerformanceTester::benchmark_checksum(options);
            PerformanceTester::print_benchmark_result(result, options, *output_stream);
        } else if (test_name == "client-creation") {
            auto result = PerformanceTester::benchmark_client_creation(options);
            PerformanceTester::print_benchmark_result(result, options, *output_stream);
        } else if (test_name == "network-simulation") {
            auto result = PerformanceTester::benchmark_network_simulation(options);
            PerformanceTester::print_benchmark_result(result, options, *output_stream);
        } else {
            std::cerr << "エラー: 不明なテスト名: " << test_name << "\n";
            PerformanceTester::print_usage(argv[0]);
            return 1;
        }

    } catch (const std::exception& e) {
        std::cerr << "エラー: " << e.what() << "\n";
        return 1;
    }

    return 0;
}