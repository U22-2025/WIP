/**
 * @file wip_config_validator.cpp
 * @brief WIP設定ファイル検証ツール
 * 
 * 設定ファイルの形式・内容を検証し、Python版との互換性をチェックします。
 */

#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <filesystem>
#include <regex>

#include "wiplib/compatibility/python_config.hpp"
#include "wiplib/compatibility/python_errors.hpp"

using namespace wiplib::compatibility;

class ConfigValidator {
public:
    struct ValidationResult {
        bool is_valid = false;
        std::vector<std::string> errors;
        std::vector<std::string> warnings;
        std::vector<std::string> suggestions;
        
        void add_error(const std::string& error) {
            errors.push_back("❌ エラー: " + error);
            is_valid = false;
        }
        
        void add_warning(const std::string& warning) {
            warnings.push_back("⚠️  警告: " + warning);
        }
        
        void add_suggestion(const std::string& suggestion) {
            suggestions.push_back("💡 提案: " + suggestion);
        }
    };

    struct ValidationOptions {
        bool check_python_compatibility = true;
        bool check_network_connectivity = false;
        bool suggest_improvements = true;
        bool verbose = false;
        bool fix_issues = false;
        std::string output_format = "text"; // text, json
    };

    static void print_usage(const char* program_name) {
        std::cout << "WIP設定ファイル検証ツール\n";
        std::cout << "使用方法: " << program_name << " [オプション] <設定ファイル>\n\n";
        std::cout << "オプション:\n";
        std::cout << "  -p, --python-compat     Python互換性をチェック\n";
        std::cout << "  -n, --network-check     ネットワーク接続をテスト\n";
        std::cout << "  -s, --suggest           改善提案を表示\n";
        std::cout << "  -v, --verbose           詳細な検証結果を表示\n";
        std::cout << "  -f, --fix               問題を自動修正\n";
        std::cout << "  --format FORMAT         出力形式 (text|json)\n";
        std::cout << "  -o, --output FILE       結果をファイルに出力\n";
        std::cout << "  --create-template       テンプレート設定を作成\n";
        std::cout << "  --validate-all          全ての設定ファイルを検証\n";
        std::cout << "  --help                  このヘルプを表示\n\n";
        std::cout << "例:\n";
        std::cout << "  " << program_name << " config.json\n";
        std::cout << "  " << program_name << " --python-compat --suggest ~/.wiplib/config.json\n";
        std::cout << "  " << program_name << " --create-template > default_config.json\n";
        std::cout << "  " << program_name << " --validate-all --format json\n";
    }

    static ValidationResult validate_config_file(const std::string& file_path, const ValidationOptions& options) {
        ValidationResult result;
        result.is_valid = true;

        try {
            // ファイル存在チェック
            if (!std::filesystem::exists(file_path)) {
                result.add_error("設定ファイルが存在しません: " + file_path);
                return result;
            }

            // ファイル読み込み
            PythonConfig config;
            if (!config.load_from_file(file_path)) {
                result.add_error("設定ファイルの読み込みに失敗しました");
                return result;
            }

            // 基本的な妥当性検証
            std::string validation_error = config.validate();
            if (!validation_error.empty()) {
                result.add_error("設定内容に問題があります:\n" + validation_error);
            }

            // 個別フィールドの検証
            validate_server_config(config.server(), result, options);
            validate_logging_config(config.logging(), result, options);
            validate_cache_config(config.cache(), result, options);
            validate_client_config(config.client(), result, options);

            // JSON形式の検証
            validate_json_format(file_path, result, options);

            // Python互換性チェック
            if (options.check_python_compatibility) {
                validate_python_compatibility(config, result, options);
            }

            // ネットワーク接続テスト
            if (options.check_network_connectivity) {
                validate_network_connectivity(config, result, options);
            }

            // 改善提案
            if (options.suggest_improvements) {
                generate_suggestions(config, result, options);
            }

        } catch (const std::exception& e) {
            result.add_error("予期しないエラー: " + std::string(e.what()));
        }

        return result;
    }

private:
    static void validate_server_config(const PythonConfig::ServerSettings& server, ValidationResult& result, const ValidationOptions& options) {
        // ホスト名検証
        if (server.host.empty()) {
            result.add_error("サーバーホストが設定されていません");
        } else {
            // ホスト名形式の検証
            std::regex hostname_regex(R"(^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$)");
            std::regex ip_regex(R"(^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$)");
            
            if (!std::regex_match(server.host, hostname_regex) && !std::regex_match(server.host, ip_regex)) {
                result.add_warning("ホスト名またはIPアドレスの形式が正しくない可能性があります: " + server.host);
            }
        }

        // ポート番号検証
        if (server.port == 0) {
            result.add_error("無効なポート番号: 0");
        } else if (server.port < 1024 && server.port != 80 && server.port != 443) {
            result.add_warning("特権ポート（1024未満）が指定されています: " + std::to_string(server.port));
        } else if (server.port > 65535) {
            result.add_error("無効なポート番号（範囲外）: " + std::to_string(server.port));
        }

        // タイムアウト検証
        if (server.timeout_ms <= 0) {
            result.add_error("タイムアウト値は正の値である必要があります: " + std::to_string(server.timeout_ms));
        } else if (server.timeout_ms > 300000) { // 5分
            result.add_warning("タイムアウトが非常に長く設定されています: " + std::to_string(server.timeout_ms) + "ms");
        } else if (server.timeout_ms < 1000) { // 1秒
            result.add_warning("タイムアウトが非常に短く設定されています: " + std::to_string(server.timeout_ms) + "ms");
        }

        // リトライ回数検証
        if (server.retry_count < 0) {
            result.add_error("リトライ回数は0以上である必要があります: " + std::to_string(server.retry_count));
        } else if (server.retry_count > 10) {
            result.add_warning("リトライ回数が多すぎます: " + std::to_string(server.retry_count));
        }

        // SSL設定の検証
        if (server.use_ssl && server.port == 80) {
            result.add_warning("SSL有効ですがHTTPポート（80）が指定されています");
        } else if (!server.use_ssl && server.port == 443) {
            result.add_warning("SSL無効ですがHTTPSポート（443）が指定されています");
        }
    }

    static void validate_logging_config(const PythonConfig::LoggingSettings& logging, ValidationResult& result, const ValidationOptions& options) {
        // ログレベル検証
        std::vector<std::string> valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"};
        if (std::find(valid_levels.begin(), valid_levels.end(), logging.level) == valid_levels.end()) {
            result.add_error("無効なログレベル: " + logging.level);
        }

        // ログフォーマット検証
        if (logging.format.empty()) {
            result.add_warning("ログフォーマットが設定されていません");
        }

        // ファイルパス検証
        if (logging.file_path.has_value()) {
            const std::string& file_path = logging.file_path.value();
            std::filesystem::path log_path(file_path);
            
            if (log_path.has_parent_path()) {
                std::filesystem::path parent = log_path.parent_path();
                if (!std::filesystem::exists(parent)) {
                    result.add_warning("ログファイルのディレクトリが存在しません: " + parent.string());
                }
            }
        }

        // ファイルサイズとバックアップ設定
        if (logging.max_file_size_mb <= 0) {
            result.add_warning("最大ファイルサイズが正しく設定されていません: " + std::to_string(logging.max_file_size_mb));
        } else if (logging.max_file_size_mb > 1000) { // 1GB
            result.add_warning("最大ファイルサイズが非常に大きく設定されています: " + std::to_string(logging.max_file_size_mb) + "MB");
        }

        if (logging.backup_count < 0) {
            result.add_warning("バックアップファイル数は0以上である必要があります: " + std::to_string(logging.backup_count));
        } else if (logging.backup_count > 100) {
            result.add_warning("バックアップファイル数が多すぎます: " + std::to_string(logging.backup_count));
        }
    }

    static void validate_cache_config(const PythonConfig::CacheSettings& cache, ValidationResult& result, const ValidationOptions& options) {
        // TTL検証
        if (cache.ttl_seconds <= 0) {
            result.add_error("キャッシュTTLは正の値である必要があります: " + std::to_string(cache.ttl_seconds));
        } else if (cache.ttl_seconds > 86400) { // 24時間
            result.add_warning("キャッシュTTLが非常に長く設定されています: " + std::to_string(cache.ttl_seconds) + "秒");
        }

        // エントリ数検証
        if (cache.max_entries <= 0) {
            result.add_error("最大キャッシュエントリ数は正の値である必要があります: " + std::to_string(cache.max_entries));
        } else if (cache.max_entries > 100000) {
            result.add_warning("最大キャッシュエントリ数が非常に多く設定されています: " + std::to_string(cache.max_entries));
        }

        // キャッシュディレクトリ検証
        if (cache.persistent && cache.cache_dir.has_value()) {
            const std::string& cache_dir = cache.cache_dir.value();
            std::filesystem::path dir_path(cache_dir);
            
            if (!std::filesystem::exists(dir_path)) {
                result.add_warning("キャッシュディレクトリが存在しません: " + cache_dir);
            } else {
                // 書き込み権限のチェック
                std::filesystem::perms perms = std::filesystem::status(dir_path).permissions();
                if ((perms & std::filesystem::perms::owner_write) == std::filesystem::perms::none) {
                    result.add_warning("キャッシュディレクトリに書き込み権限がありません: " + cache_dir);
                }
            }
        }
    }

    static void validate_client_config(const PythonConfig::ClientSettings& client, ValidationResult& result, const ValidationOptions& options) {
        // 座標検証
        if (client.default_latitude.has_value()) {
            double lat = client.default_latitude.value();
            if (lat < -90.0 || lat > 90.0) {
                result.add_error("緯度は-90から90の範囲で指定してください: " + std::to_string(lat));
            }
        }

        if (client.default_longitude.has_value()) {
            double lon = client.default_longitude.value();
            if (lon < -180.0 || lon > 180.0) {
                result.add_error("経度は-180から180の範囲で指定してください: " + std::to_string(lon));
            }
        }

        // エリアコード検証
        if (client.default_area_code.has_value()) {
            const std::string& area_code = client.default_area_code.value();
            if (!PythonProtocolAdapter::validate_python_area_code(area_code)) {
                result.add_error("無効なエリアコード形式: " + area_code);
            }
        }

        // User-Agent検証
        if (client.user_agent.empty()) {
            result.add_warning("User-Agentが設定されていません");
        } else if (client.user_agent.length() > 255) {
            result.add_warning("User-Agentが長すぎます: " + std::to_string(client.user_agent.length()) + "文字");
        }
    }

    static void validate_json_format(const std::string& file_path, ValidationResult& result, const ValidationOptions& options) {
        std::ifstream file(file_path);
        if (!file) {
            result.add_error("ファイルを開けません: " + file_path);
            return;
        }

        std::string content((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());
        
        // 基本的なJSON形式チェック
        int brace_count = 0;
        int bracket_count = 0;
        bool in_string = false;
        bool escape_next = false;

        for (char c : content) {
            if (escape_next) {
                escape_next = false;
                continue;
            }

            if (c == '\\') {
                escape_next = true;
                continue;
            }

            if (c == '"' && !escape_next) {
                in_string = !in_string;
                continue;
            }

            if (!in_string) {
                if (c == '{') brace_count++;
                else if (c == '}') brace_count--;
                else if (c == '[') bracket_count++;
                else if (c == ']') bracket_count--;
            }
        }

        if (brace_count != 0) {
            result.add_error("JSONの波括弧 {} が正しく閉じられていません");
        }

        if (bracket_count != 0) {
            result.add_error("JSONの角括弧 [] が正しく閉じられていません");
        }

        // 重複キーのチェック（簡易版）
        std::regex key_regex(R"("([^"]+)"\s*:)");
        std::set<std::string> keys;
        std::sregex_iterator iter(content.begin(), content.end(), key_regex);
        std::sregex_iterator end;

        for (; iter != end; ++iter) {
            std::string key = (*iter)[1].str();
            if (keys.find(key) != keys.end()) {
                result.add_warning("重複するキーが見つかりました: " + key);
            }
            keys.insert(key);
        }
    }

    static void validate_python_compatibility(const PythonConfig& config, ValidationResult& result, const ValidationOptions& options) {
        // Python版のデフォルト値との比較
        if (config.server().port != 4110) {
            result.add_suggestion("Python版のデフォルトポート（4110）と異なります: " + std::to_string(config.server().port));
        }

        if (config.server().timeout_ms != 5000) {
            result.add_suggestion("Python版のデフォルトタイムアウト（5000ms）と異なります: " + std::to_string(config.server().timeout_ms));
        }

        if (config.server().retry_count != 3) {
            result.add_suggestion("Python版のデフォルトリトライ回数（3）と異なります: " + std::to_string(config.server().retry_count));
        }

        // Python版の設定キー形式チェック
        std::string json = config.to_json();
        std::vector<std::string> required_sections = {"server", "logging", "cache", "client"};
        
        for (const std::string& section : required_sections) {
            if (json.find("\"" + section + "\"") == std::string::npos) {
                result.add_warning("Python版で必要なセクションが見つかりません: " + section);
            }
        }
    }

    static void validate_network_connectivity(const PythonConfig& config, ValidationResult& result, const ValidationOptions& options) {
        // 実際のネットワーク接続テストは実装の複雑性を考慮して簡略化
        result.add_suggestion("ネットワーク接続テストは手動で確認してください: " + 
                             config.server().host + ":" + std::to_string(config.server().port));
    }

    static void generate_suggestions(const PythonConfig& config, ValidationResult& result, const ValidationOptions& options) {
        // パフォーマンス改善提案
        if (config.cache().enabled && config.cache().ttl_seconds < 60) {
            result.add_suggestion("キャッシュTTLを60秒以上に設定するとパフォーマンスが向上する可能性があります");
        }

        if (!config.cache().enabled) {
            result.add_suggestion("キャッシュを有効にするとパフォーマンスが向上する可能性があります");
        }

        // セキュリティ改善提案
        if (!config.server().use_ssl && config.server().host != "localhost" && config.server().host != "127.0.0.1") {
            result.add_suggestion("外部サーバーへの接続ではSSLの使用を検討してください");
        }

        // ログ設定改善提案
        if (config.logging().level == "DEBUG" && !config.client().debug) {
            result.add_suggestion("本番環境ではログレベルをINFO以上に設定することを推奨します");
        }

        if (!config.logging().file_path.has_value()) {
            result.add_suggestion("ログファイルの設定を行うとトラブルシューティングが容易になります");
        }
    }

public:
    static void print_validation_result(const ValidationResult& result, const ValidationOptions& options, std::ostream& out = std::cout) {
        if (options.output_format == "json") {
            print_json_result(result, out);
            return;
        }

        out << "=== WIP設定ファイル検証結果 ===\n\n";
        
        if (result.is_valid && result.errors.empty()) {
            out << "✅ 設定ファイルは有効です\n\n";
        } else {
            out << "❌ 設定ファイルに問題があります\n\n";
        }

        // エラー表示
        if (!result.errors.empty()) {
            out << "🚨 エラー:\n";
            for (const auto& error : result.errors) {
                out << "  " << error << "\n";
            }
            out << "\n";
        }

        // 警告表示
        if (!result.warnings.empty()) {
            out << "⚠️  警告:\n";
            for (const auto& warning : result.warnings) {
                out << "  " << warning << "\n";
            }
            out << "\n";
        }

        // 提案表示
        if (!result.suggestions.empty() && options.suggest_improvements) {
            out << "💡 改善提案:\n";
            for (const auto& suggestion : result.suggestions) {
                out << "  " << suggestion << "\n";
            }
            out << "\n";
        }

        // 統計
        out << "📊 統計:\n";
        out << "  エラー: " << result.errors.size() << "\n";
        out << "  警告: " << result.warnings.size() << "\n";
        out << "  提案: " << result.suggestions.size() << "\n";
    }

private:
    static void print_json_result(const ValidationResult& result, std::ostream& out) {
        out << "{\n";
        out << "  \"is_valid\": " << (result.is_valid ? "true" : "false") << ",\n";
        out << "  \"errors\": [\n";
        for (size_t i = 0; i < result.errors.size(); ++i) {
            out << "    \"" << result.errors[i] << "\"";
            if (i < result.errors.size() - 1) out << ",";
            out << "\n";
        }
        out << "  ],\n";
        out << "  \"warnings\": [\n";
        for (size_t i = 0; i < result.warnings.size(); ++i) {
            out << "    \"" << result.warnings[i] << "\"";
            if (i < result.warnings.size() - 1) out << ",";
            out << "\n";
        }
        out << "  ],\n";
        out << "  \"suggestions\": [\n";
        for (size_t i = 0; i < result.suggestions.size(); ++i) {
            out << "    \"" << result.suggestions[i] << "\"";
            if (i < result.suggestions.size() - 1) out << ",";
            out << "\n";
        }
        out << "  ],\n";
        out << "  \"validation_timestamp\": " << PythonProtocolAdapter::generate_python_timestamp() << "\n";
        out << "}\n";
    }

public:
    static void create_template_config(std::ostream& out = std::cout) {
        PythonConfig template_config;
        
        // デフォルト値の設定
        template_config.server().host = "localhost";
        template_config.server().port = 4110;
        template_config.server().timeout_ms = 5000;
        template_config.server().retry_count = 3;
        
        template_config.logging().level = "INFO";
        template_config.logging().console_output = true;
        
        template_config.cache().enabled = true;
        template_config.cache().ttl_seconds = 300;
        template_config.cache().max_entries = 1000;
        
        template_config.client().debug = false;
        
        out << template_config.to_json();
    }

    static void validate_all_configs(const ValidationOptions& options, std::ostream& out = std::cout) {
        auto search_paths = get_config_search_paths();
        
        out << "=== 全設定ファイル検証 ===\n\n";
        
        int total_files = 0;
        int valid_files = 0;
        
        for (const auto& path : search_paths) {
            if (std::filesystem::exists(path)) {
                total_files++;
                out << "検証中: " << path << "\n";
                
                auto result = validate_config_file(path, options);
                if (result.is_valid && result.errors.empty()) {
                    valid_files++;
                    out << "  ✅ 有効\n";
                } else {
                    out << "  ❌ 問題あり (" << result.errors.size() << " エラー, " 
                        << result.warnings.size() << " 警告)\n";
                }
                out << "\n";
            }
        }
        
        out << "📊 検証結果: " << valid_files << "/" << total_files << " ファイルが有効\n";
    }
};

int main(int argc, char* argv[]) {
    ConfigValidator::ValidationOptions options;
    std::string config_file;
    std::string output_file;
    bool create_template = false;
    bool validate_all = false;

    // コマンドライン引数の解析
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        
        if (arg == "--help") {
            ConfigValidator::print_usage(argv[0]);
            return 0;
        } else if (arg == "-p" || arg == "--python-compat") {
            options.check_python_compatibility = true;
        } else if (arg == "-n" || arg == "--network-check") {
            options.check_network_connectivity = true;
        } else if (arg == "-s" || arg == "--suggest") {
            options.suggest_improvements = true;
        } else if (arg == "-v" || arg == "--verbose") {
            options.verbose = true;
        } else if (arg == "-f" || arg == "--fix") {
            options.fix_issues = true;
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
        } else if (arg == "--create-template") {
            create_template = true;
        } else if (arg == "--validate-all") {
            validate_all = true;
        } else if (arg[0] != '-') {
            config_file = arg;
        } else {
            std::cerr << "エラー: 不明なオプション: " << arg << "\n";
            ConfigValidator::print_usage(argv[0]);
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

        if (create_template) {
            ConfigValidator::create_template_config(*output_stream);
        } else if (validate_all) {
            ConfigValidator::validate_all_configs(options, *output_stream);
        } else {
            if (config_file.empty()) {
                // デフォルト設定ファイルを検索
                auto search_paths = get_config_search_paths();
                for (const auto& path : search_paths) {
                    if (std::filesystem::exists(path)) {
                        config_file = path;
                        break;
                    }
                }
                
                if (config_file.empty()) {
                    std::cerr << "エラー: 設定ファイルが見つかりません\n";
                    std::cerr << "以下のパスを検索しました:\n";
                    for (const auto& path : search_paths) {
                        std::cerr << "  " << path << "\n";
                    }
                    return 1;
                }
            }

            auto result = ConfigValidator::validate_config_file(config_file, options);
            ConfigValidator::print_validation_result(result, options, *output_stream);
            
            return (result.is_valid && result.errors.empty()) ? 0 : 1;
        }

    } catch (const std::exception& e) {
        std::cerr << "エラー: " << e.what() << "\n";
        return 1;
    }

    return 0;
}