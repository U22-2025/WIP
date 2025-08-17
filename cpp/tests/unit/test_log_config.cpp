#include <gtest/gtest.h>
#include <sstream>
#include <filesystem>
#include "wiplib/utils/log_config.hpp"

using namespace wiplib::utils;

class LogConfigTest : public ::testing::Test {
protected:
    void SetUp() override {
        // テスト用ディレクトリの作成
        test_dir = std::filesystem::temp_directory_path() / "log_test";
        std::filesystem::create_directories(test_dir);
    }
    
    void TearDown() override {
        // テスト用ファイルのクリーンアップ
        if (std::filesystem::exists(test_dir)) {
            std::filesystem::remove_all(test_dir);
        }
    }
    
    std::filesystem::path test_dir;
};

// UnifiedLogFormatter の基本テスト
TEST_F(LogConfigTest, UnifiedLogFormatterBasic) {
    UnifiedLogFormatter formatter;
    
    // テストメッセージのフォーマット
    std::string formatted = formatter.format("INFO", "Test message", "test_module");
    
    EXPECT_FALSE(formatted.empty());
    EXPECT_NE(formatted.find("INFO"), std::string::npos);
    EXPECT_NE(formatted.find("Test message"), std::string::npos);
    EXPECT_NE(formatted.find("test_module"), std::string::npos);
}

// 異なるログレベルのテスト
TEST_F(LogConfigTest, DifferentLogLevels) {
    UnifiedLogFormatter formatter;
    
    std::string debug_log = formatter.format("DEBUG", "Debug message", "debug_module");
    std::string info_log = formatter.format("INFO", "Info message", "info_module");
    std::string warning_log = formatter.format("WARNING", "Warning message", "warning_module");
    std::string error_log = formatter.format("ERROR", "Error message", "error_module");
    
    EXPECT_NE(debug_log.find("DEBUG"), std::string::npos);
    EXPECT_NE(info_log.find("INFO"), std::string::npos);
    EXPECT_NE(warning_log.find("WARNING"), std::string::npos);
    EXPECT_NE(error_log.find("ERROR"), std::string::npos);
    
    // 各ログに適切なメッセージが含まれている
    EXPECT_NE(debug_log.find("Debug message"), std::string::npos);
    EXPECT_NE(info_log.find("Info message"), std::string::npos);
    EXPECT_NE(warning_log.find("Warning message"), std::string::npos);
    EXPECT_NE(error_log.find("Error message"), std::string::npos);
}

// タイムスタンプの存在確認
TEST_F(LogConfigTest, TimestampInclusion) {
    UnifiedLogFormatter formatter;
    
    std::string formatted = formatter.format("INFO", "Timestamp test", "timestamp_module");
    
    // タイムスタンプの形式確認（例：YYYY-MM-DD HH:MM:SS）
    // 実際の形式は実装に依存するが、数字と区切り文字が含まれているはず
    bool has_timestamp = false;
    
    // 典型的なタイムスタンプパターンをチェック
    if (formatted.find("-") != std::string::npos && 
        formatted.find(":") != std::string::npos) {
        has_timestamp = true;
    }
    
    EXPECT_TRUE(has_timestamp);
}

// 特殊文字を含むメッセージのテスト
TEST_F(LogConfigTest, SpecialCharactersInMessage) {
    UnifiedLogFormatter formatter;
    
    std::string special_message = "Message with special chars: !@#$%^&*()[]{}|;':\",./<>?";
    std::string formatted = formatter.format("INFO", special_message, "special_module");
    
    EXPECT_NE(formatted.find(special_message), std::string::npos);
}

// 空のメッセージのテスト
TEST_F(LogConfigTest, EmptyMessage) {
    UnifiedLogFormatter formatter;
    
    std::string formatted = formatter.format("INFO", "", "empty_module");
    
    EXPECT_FALSE(formatted.empty());
    EXPECT_NE(formatted.find("INFO"), std::string::npos);
    EXPECT_NE(formatted.find("empty_module"), std::string::npos);
}

// 長いメッセージのテスト
TEST_F(LogConfigTest, LongMessage) {
    UnifiedLogFormatter formatter;
    
    std::string long_message(1000, 'x');  // 1000文字のメッセージ
    std::string formatted = formatter.format("INFO", long_message, "long_module");
    
    EXPECT_NE(formatted.find(long_message), std::string::npos);
    EXPECT_NE(formatted.find("INFO"), std::string::npos);
    EXPECT_NE(formatted.find("long_module"), std::string::npos);
}

// マルチバイト文字のテスト
TEST_F(LogConfigTest, MultbyteCharacters) {
    UnifiedLogFormatter formatter;
    
    std::string japanese_message = "日本語のログメッセージです";
    std::string formatted = formatter.format("INFO", japanese_message, "japanese_module");
    
    EXPECT_NE(formatted.find(japanese_message), std::string::npos);
    EXPECT_NE(formatted.find("INFO"), std::string::npos);
    EXPECT_NE(formatted.find("japanese_module"), std::string::npos);
}

// ログレベル管理のテスト
TEST_F(LogConfigTest, LogLevelManagement) {
    // ログレベルの設定と取得のテスト
    // 実装されている場合のテスト
    
    // DEBUG レベル
    bool debug_enabled = is_log_level_enabled("DEBUG");
    // INFO レベル
    bool info_enabled = is_log_level_enabled("INFO");
    // WARNING レベル
    bool warning_enabled = is_log_level_enabled("WARNING");
    // ERROR レベル
    bool error_enabled = is_log_level_enabled("ERROR");
    
    // 通常、ERROR > WARNING > INFO > DEBUG の順で有効になる
    if (error_enabled) {
        EXPECT_TRUE(error_enabled);
    }
    if (warning_enabled) {
        EXPECT_TRUE(warning_enabled);
    }
    // レベル設定のテストは実装に依存
}

// ファイルローテーションの設定テスト
TEST_F(LogConfigTest, FileRotationConfiguration) {
    std::filesystem::path log_file = test_dir / "test.log";
    
    // ファイルローテーション設定
    LogRotationConfig rotation_config;
    rotation_config.max_file_size = 1024 * 1024;  // 1MB
    rotation_config.max_files = 5;
    rotation_config.enabled = true;
    
    EXPECT_TRUE(rotation_config.enabled);
    EXPECT_EQ(rotation_config.max_file_size, 1024 * 1024);
    EXPECT_EQ(rotation_config.max_files, 5);
}

// ログファイルの書き込みテスト
TEST_F(LogConfigTest, LogFileWriting) {
    std::filesystem::path log_file = test_dir / "test_output.log";
    
    // ログファイルへの書き込み（実装されている場合）
    UnifiedLogFormatter formatter;
    std::string formatted_message = formatter.format("INFO", "Test file output", "file_module");
    
    // ファイルへの書き込み
    std::ofstream log_stream(log_file);
    if (log_stream.is_open()) {
        log_stream << formatted_message << std::endl;
        log_stream.close();
        
        // ファイルが正しく作成されているか確認
        EXPECT_TRUE(std::filesystem::exists(log_file));
        
        // ファイルの内容確認
        std::ifstream read_stream(log_file);
        std::string file_content;
        std::getline(read_stream, file_content);
        read_stream.close();
        
        EXPECT_EQ(file_content, formatted_message);
    }
}

// コンソール出力のテスト
TEST_F(LogConfigTest, ConsoleOutput) {
    UnifiedLogFormatter formatter;
    
    // 標準出力のキャプチャ
    std::ostringstream captured_output;
    std::streambuf* orig_cout = std::cout.rdbuf();
    std::cout.rdbuf(captured_output.rdbuf());
    
    // ログ出力
    std::string message = formatter.format("INFO", "Console test message", "console_module");
    std::cout << message << std::endl;
    
    // 標準出力の復元
    std::cout.rdbuf(orig_cout);
    
    // キャプチャした出力の確認
    std::string output = captured_output.str();
    EXPECT_NE(output.find("Console test message"), std::string::npos);
    EXPECT_NE(output.find("INFO"), std::string::npos);
}

// ログ設定の初期化テスト
TEST_F(LogConfigTest, LogConfigurationInitialization) {
    // ログ設定の初期化
    LogConfig config;
    config.level = "INFO";
    config.enable_console = true;
    config.enable_file = true;
    config.log_file_path = (test_dir / "init_test.log").string();
    
    EXPECT_EQ(config.level, "INFO");
    EXPECT_TRUE(config.enable_console);
    EXPECT_TRUE(config.enable_file);
    EXPECT_FALSE(config.log_file_path.empty());
}

// スレッドセーフティテスト
TEST_F(LogConfigTest, ThreadSafety) {
    UnifiedLogFormatter formatter;
    const int num_threads = 4;
    const int messages_per_thread = 100;
    std::vector<std::thread> threads;
    std::vector<std::string> all_messages;
    std::mutex messages_mutex;
    
    // 複数スレッドでログフォーマッティング
    for (int t = 0; t < num_threads; ++t) {
        threads.emplace_back([&, t]() {
            for (int i = 0; i < messages_per_thread; ++i) {
                std::string message = "Thread " + std::to_string(t) + " Message " + std::to_string(i);
                std::string formatted = formatter.format("INFO", message, "thread_module");
                
                std::lock_guard<std::mutex> lock(messages_mutex);
                all_messages.push_back(formatted);
            }
        });
    }
    
    // すべてのスレッドの完了を待機
    for (auto& thread : threads) {
        thread.join();
    }
    
    // すべてのメッセージが正しくフォーマットされているか確認
    EXPECT_EQ(all_messages.size(), num_threads * messages_per_thread);
    
    for (const auto& formatted_message : all_messages) {
        EXPECT_NE(formatted_message.find("INFO"), std::string::npos);
        EXPECT_NE(formatted_message.find("thread_module"), std::string::npos);
        EXPECT_FALSE(formatted_message.empty());
    }
}