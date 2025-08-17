/**
 * @file wip_packet_analyzer.cpp
 * @brief WIPパケット解析ツール
 * 
 * パケットの内容を詳細に解析し、可読性の高い形式で表示します。
 * Python版のパケット解析ツールと同等の機能を提供します。
 */

#include <iostream>
#include <fstream>
#include <iomanip>
#include <vector>
#include <string>
#include <sstream>
#include <cstring>

#include "wiplib/packet/codec.hpp"
#include "wiplib/packet/checksum.hpp"
#include "wiplib/compatibility/python_protocol.hpp"

using namespace wiplib::proto;
using namespace wiplib::compatibility;

class PacketAnalyzer {
public:
    struct AnalysisOptions {
        bool verbose = false;
        bool show_hex_dump = true;
        bool validate_checksum = true;
        bool python_compatible = true;
        bool show_extended_fields = true;
        std::string output_format = "text"; // text, json, csv
    };

    static void print_usage(const char* program_name) {
        std::cout << "WIPパケット解析ツール\n";
        std::cout << "使用方法: " << program_name << " [オプション] <入力ファイル|パケットデータ>\n\n";
        std::cout << "オプション:\n";
        std::cout << "  -v, --verbose           詳細な解析結果を表示\n";
        std::cout << "  -h, --hex-dump          16進ダンプを表示\n";
        std::cout << "  -c, --check-checksum    チェックサムを検証\n";
        std::cout << "  -p, --python-compat     Python互換性をチェック\n";
        std::cout << "  -e, --extended-fields   拡張フィールドを解析\n";
        std::cout << "  -f, --format FORMAT     出力形式 (text|json|csv)\n";
        std::cout << "  -i, --input-file FILE   ファイルからパケットデータを読み込み\n";
        std::cout << "  -o, --output-file FILE  結果をファイルに出力\n";
        std::cout << "  --help                  このヘルプを表示\n\n";
        std::cout << "例:\n";
        std::cout << "  " << program_name << " -v packet.bin\n";
        std::cout << "  " << program_name << " --hex-dump --format json packet_data.hex\n";
        std::cout << "  echo '010023040102...' | " << program_name << " --python-compat\n";
    }

    static std::vector<uint8_t> read_packet_from_file(const std::string& filename) {
        std::ifstream file(filename, std::ios::binary);
        if (!file) {
            throw std::runtime_error("ファイルを開けません: " + filename);
        }

        std::vector<uint8_t> data;
        file.seekg(0, std::ios::end);
        size_t size = file.tellg();
        file.seekg(0, std::ios::beg);

        data.resize(size);
        file.read(reinterpret_cast<char*>(data.data()), size);

        return data;
    }

    static std::vector<uint8_t> parse_hex_string(const std::string& hex_str) {
        std::vector<uint8_t> data;
        std::string clean_hex;
        
        // 空白や区切り文字を除去
        for (char c : hex_str) {
            if (std::isxdigit(c)) {
                clean_hex += c;
            }
        }

        if (clean_hex.length() % 2 != 0) {
            throw std::runtime_error("16進文字列の長さが奇数です");
        }

        for (size_t i = 0; i < clean_hex.length(); i += 2) {
            std::string byte_str = clean_hex.substr(i, 2);
            uint8_t byte = static_cast<uint8_t>(std::stoul(byte_str, nullptr, 16));
            data.push_back(byte);
        }

        return data;
    }

    static void print_hex_dump(const std::vector<uint8_t>& data, std::ostream& out = std::cout) {
        out << "\n=== 16進ダンプ ===\n";
        
        for (size_t i = 0; i < data.size(); i += 16) {
            // アドレス表示
            out << std::setfill('0') << std::setw(8) << std::hex << i << ": ";
            
            // 16進表示
            for (size_t j = 0; j < 16; ++j) {
                if (i + j < data.size()) {
                    out << std::setfill('0') << std::setw(2) << std::hex 
                        << static_cast<int>(data[i + j]) << " ";
                } else {
                    out << "   ";
                }
                
                if (j == 7) out << " ";
            }
            
            out << " |";
            
            // ASCII表示
            for (size_t j = 0; j < 16 && i + j < data.size(); ++j) {
                char c = static_cast<char>(data[i + j]);
                out << (std::isprint(c) ? c : '.');
            }
            
            out << "|\n";
        }
        out << std::dec << std::setfill(' ');
    }

    static void analyze_header(const Header& header, const AnalysisOptions& options, std::ostream& out = std::cout) {
        out << "\n=== ヘッダー解析 ===\n";
        out << "プロトコルバージョン: " << static_cast<int>(header.version) << "\n";
        out << "パケットID: 0x" << std::hex << header.packet_id << std::dec << " (" << header.packet_id << ")\n";
        
        // パケットタイプの詳細表示
        out << "パケットタイプ: ";
        switch (header.type) {
            case PacketType::WeatherRequest:
                out << "WeatherRequest (天気リクエスト)";
                break;
            case PacketType::WeatherResponse:
                out << "WeatherResponse (天気レスポンス)";
                break;
            default:
                out << "Unknown (" << static_cast<int>(header.type) << ")";
                break;
        }
        out << "\n";

        // フラグの詳細表示
        out << "フラグ:\n";
        out << "  天気: " << (header.flags.weather ? "有効" : "無効") << "\n";
        out << "  気温: " << (header.flags.temperature ? "有効" : "無効") << "\n";
        out << "  降水確率: " << (header.flags.precipitation_prob ? "有効" : "無効") << "\n";
        out << "  警報: " << (header.flags.alert ? "有効" : "無効") << "\n";
        out << "  災害情報: " << (header.flags.disaster ? "有効" : "無効") << "\n";

        out << "対象日: " << static_cast<int>(header.day) << "日後\n";
        
        // タイムスタンプの詳細表示
        out << "タイムスタンプ: 0x" << std::hex << header.timestamp << std::dec;
        if (options.verbose) {
            // Unix時間として解釈
            time_t unix_time = header.timestamp / 1000000; // マイクロ秒から秒に変換
            out << " (" << std::ctime(&unix_time);
            out.seekp(-1, std::ios_base::cur); // 改行を削除
            out << ")";
        }
        out << "\n";
        
        out << "エリアコード: " << header.area_code << "\n";
        out << "チェックサム: 0x" << std::hex << header.checksum << std::dec << "\n";
    }

    static void analyze_packet(const std::vector<uint8_t>& packet_data, const AnalysisOptions& options, std::ostream& out = std::cout) {
        out << "=== WIPパケット解析結果 ===\n";
        out << "パケットサイズ: " << packet_data.size() << " bytes\n";

        if (options.show_hex_dump) {
            print_hex_dump(packet_data, out);
        }

        // ヘッダーのデコード
        if (packet_data.size() < 16) {
            out << "\nエラー: パケットサイズが小さすぎます (最低16バイト必要)\n";
            return;
        }

        auto header_result = decode_header(packet_data);
        if (!header_result.has_value()) {
            out << "\nエラー: ヘッダーのデコードに失敗しました\n";
            return;
        }

        const Header& header = header_result.value();
        analyze_header(header, options, out);

        // チェックサム検証
        if (options.validate_checksum) {
            out << "\n=== チェックサム検証 ===\n";
            
            // ヘッダーのチェックサム検証
            std::vector<uint8_t> header_data(packet_data.begin(), packet_data.begin() + 16);
            uint16_t calculated_checksum = PythonProtocolAdapter::calculate_python_checksum(header_data);
            
            out << "計算されたチェックサム: 0x" << std::hex << calculated_checksum << std::dec << "\n";
            out << "パケット内チェックサム: 0x" << std::hex << header.checksum << std::dec << "\n";
            
            if (calculated_checksum == header.checksum) {
                out << "✅ チェックサム検証: 正常\n";
            } else {
                out << "❌ チェックサム検証: 失敗\n";
            }
        }

        // 拡張フィールドの解析
        if (options.show_extended_fields && packet_data.size() > 16) {
            out << "\n=== 拡張フィールド解析 ===\n";
            
            auto packet_result = decode_packet(packet_data);
            if (packet_result.has_value()) {
                const Packet& packet = packet_result.value();
                
                if (packet.extensions.empty()) {
                    out << "拡張フィールドなし\n";
                } else {
                    out << "拡張フィールド数: " << packet.extensions.size() << "\n";
                    
                    for (size_t i = 0; i < packet.extensions.size(); ++i) {
                        const ExtendedField& field = packet.extensions[i];
                        out << "\nフィールド " << (i + 1) << ":\n";
                        out << "  データタイプ: 0x" << std::hex << static_cast<int>(field.data_type) << std::dec << "\n";
                        out << "  データサイズ: " << field.data.size() << " bytes\n";
                        
                        if (options.verbose && !field.data.empty()) {
                            out << "  データ: ";
                            for (uint8_t byte : field.data) {
                                out << std::hex << std::setfill('0') << std::setw(2) << static_cast<int>(byte) << " ";
                            }
                            out << std::dec << "\n";
                        }
                    }
                }
            } else {
                out << "拡張フィールドのデコードに失敗しました\n";
            }
        }

        // Python互換性チェック
        if (options.python_compatible) {
            out << "\n=== Python互換性チェック ===\n";
            
            bool is_compatible = PythonCompatibilityChecker::check_packet_format_compatibility(packet_data);
            out << "Python互換性: " << (is_compatible ? "✅ 互換" : "❌ 非互換") << "\n";
            
            if (options.verbose) {
                if (PythonCompatibilityChecker::check_protocol_compatibility(header.version)) {
                    out << "プロトコルバージョン: ✅ 互換\n";
                } else {
                    out << "プロトコルバージョン: ❌ 非互換 (バージョン " << static_cast<int>(header.version) << ")\n";
                }
            }
        }

        // 統計情報
        if (options.verbose) {
            out << "\n=== 統計情報 ===\n";
            out << "ヘッダーサイズ: 16 bytes\n";
            out << "ペイロードサイズ: " << (packet_data.size() - 16) << " bytes\n";
            out << "総パケットサイズ: " << packet_data.size() << " bytes\n";
            
            // データ分布
            std::vector<int> byte_freq(256, 0);
            for (uint8_t byte : packet_data) {
                byte_freq[byte]++;
            }
            
            int non_zero_bytes = 0;
            for (int freq : byte_freq) {
                if (freq > 0) non_zero_bytes++;
            }
            
            out << "使用されているバイト値の種類: " << non_zero_bytes << "/256\n";
        }
    }

    static void output_json_format(const std::vector<uint8_t>& packet_data, const AnalysisOptions& options, std::ostream& out = std::cout) {
        out << "{\n";
        out << "  \"packet_size\": " << packet_data.size() << ",\n";
        
        if (packet_data.size() >= 16) {
            auto header_result = decode_header(packet_data);
            if (header_result.has_value()) {
                const Header& header = header_result.value();
                
                out << "  \"header\": {\n";
                out << "    \"version\": " << static_cast<int>(header.version) << ",\n";
                out << "    \"packet_id\": " << header.packet_id << ",\n";
                out << "    \"type\": " << static_cast<int>(header.type) << ",\n";
                out << "    \"flags\": {\n";
                out << "      \"weather\": " << (header.flags.weather ? "true" : "false") << ",\n";
                out << "      \"temperature\": " << (header.flags.temperature ? "true" : "false") << ",\n";
                out << "      \"precipitation_prob\": " << (header.flags.precipitation_prob ? "true" : "false") << ",\n";
                out << "      \"alert\": " << (header.flags.alert ? "true" : "false") << ",\n";
                out << "      \"disaster\": " << (header.flags.disaster ? "true" : "false") << "\n";
                out << "    },\n";
                out << "    \"day\": " << static_cast<int>(header.day) << ",\n";
                out << "    \"timestamp\": " << header.timestamp << ",\n";
                out << "    \"area_code\": " << header.area_code << ",\n";
                out << "    \"checksum\": " << header.checksum << "\n";
                out << "  },\n";
            }
        }
        
        if (options.python_compatible) {
            bool is_compatible = PythonCompatibilityChecker::check_packet_format_compatibility(packet_data);
            out << "  \"python_compatible\": " << (is_compatible ? "true" : "false") << ",\n";
        }
        
        out << "  \"analysis_timestamp\": " << PythonProtocolAdapter::generate_python_timestamp() << "\n";
        out << "}\n";
    }
};

int main(int argc, char* argv[]) {
    PacketAnalyzer::AnalysisOptions options;
    std::string input_file;
    std::string output_file;
    std::string packet_hex;

    // コマンドライン引数の解析
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        
        if (arg == "--help") {
            PacketAnalyzer::print_usage(argv[0]);
            return 0;
        } else if (arg == "-v" || arg == "--verbose") {
            options.verbose = true;
        } else if (arg == "-h" || arg == "--hex-dump") {
            options.show_hex_dump = true;
        } else if (arg == "-c" || arg == "--check-checksum") {
            options.validate_checksum = true;
        } else if (arg == "-p" || arg == "--python-compat") {
            options.python_compatible = true;
        } else if (arg == "-e" || arg == "--extended-fields") {
            options.show_extended_fields = true;
        } else if (arg == "-f" || arg == "--format") {
            if (i + 1 < argc) {
                options.output_format = argv[++i];
            } else {
                std::cerr << "エラー: --format オプションには引数が必要です\n";
                return 1;
            }
        } else if (arg == "-i" || arg == "--input-file") {
            if (i + 1 < argc) {
                input_file = argv[++i];
            } else {
                std::cerr << "エラー: --input-file オプションには引数が必要です\n";
                return 1;
            }
        } else if (arg == "-o" || arg == "--output-file") {
            if (i + 1 < argc) {
                output_file = argv[++i];
            } else {
                std::cerr << "エラー: --output-file オプションには引数が必要です\n";
                return 1;
            }
        } else if (arg[0] != '-') {
            if (input_file.empty()) {
                input_file = arg;
            } else {
                packet_hex = arg;
            }
        } else {
            std::cerr << "エラー: 不明なオプション: " << arg << "\n";
            PacketAnalyzer::print_usage(argv[0]);
            return 1;
        }
    }

    try {
        std::vector<uint8_t> packet_data;

        // データの読み込み
        if (!input_file.empty()) {
            packet_data = PacketAnalyzer::read_packet_from_file(input_file);
        } else if (!packet_hex.empty()) {
            packet_data = PacketAnalyzer::parse_hex_string(packet_hex);
        } else {
            // 標準入力から読み込み
            std::string line;
            std::getline(std::cin, line);
            if (line.empty()) {
                std::cerr << "エラー: パケットデータが指定されていません\n";
                PacketAnalyzer::print_usage(argv[0]);
                return 1;
            }
            packet_data = PacketAnalyzer::parse_hex_string(line);
        }

        // 出力
        std::ofstream output_file_stream;
        std::ostream* output_stream = &std::cout;

        if (!output_file.empty()) {
            output_file_stream.open(output_file);
            if (!output_file_stream) {
                throw std::runtime_error("出力ファイルを開けません: " + output_file);
            }
            output_stream = &output_file_stream;
        }

        // 解析と出力
        if (options.output_format == "json") {
            PacketAnalyzer::output_json_format(packet_data, options, *output_stream);
        } else {
            PacketAnalyzer::analyze_packet(packet_data, options, *output_stream);
        }

    } catch (const std::exception& e) {
        std::cerr << "エラー: " << e.what() << "\n";
        return 1;
    }

    return 0;
}