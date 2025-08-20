#include <gtest/gtest.h>
#include <fstream>
#include <filesystem>
#include "wiplib/utils/config_loader.hpp"

using namespace wiplib::utils;

class ConfigLoaderTest : public ::testing::Test {
protected:
    void SetUp() override {
        // テスト用ディレクトリの作成
        test_dir = std::filesystem::temp_directory_path() / "config_test";
        std::filesystem::create_directories(test_dir);
    }
    
    void TearDown() override {
        // テスト用ファイルのクリーンアップ
        if (std::filesystem::exists(test_dir)) {
            std::filesystem::remove_all(test_dir);
        }
    }
    
    void createTestConfigFile(const std::string& filename, const std::string& content) {
        std::filesystem::path filepath = test_dir / filename;
        std::ofstream file(filepath);
        file << content;
        file.close();
    }
    
    std::filesystem::path test_dir;
};

// 基本的な設定ファイル読み込みテスト
TEST_F(ConfigLoaderTest, BasicConfigLoading) {
    std::string config_content = R"({
        "server": {
            "host": "localhost",
            "port": 8080
        },
        "client": {
            "timeout": 30,
            "retries": 3
        }
    })";
    
    createTestConfigFile("basic_config.json", config_content);
    
    ConfigLoader loader;
    std::filesystem::path config_path = test_dir / "basic_config.json";
    auto result = loader.load_config(config_path.string());
    
    ASSERT_TRUE(result.has_value());
    auto& config = result.value();
    
    EXPECT_EQ(config.get_string("server.host"), "localhost");
    EXPECT_EQ(config.get_int("server.port"), 8080);
    EXPECT_EQ(config.get_int("client.timeout"), 30);
    EXPECT_EQ(config.get_int("client.retries"), 3);
}

// 存在しないファイルのテスト
TEST_F(ConfigLoaderTest, NonExistentFile) {
    ConfigLoader loader;
    auto result = loader.load_config("nonexistent_config.json");
    
    EXPECT_FALSE(result.has_value());
}

// 不正なJSONファイルのテスト
TEST_F(ConfigLoaderTest, InvalidJSON) {
    std::string invalid_content = R"({
        "server": {
            "host": "localhost",
            "port": 8080,
        }  // 不正なカンマ
    })";
    
    createTestConfigFile("invalid_config.json", invalid_content);
    
    ConfigLoader loader;
    std::filesystem::path config_path = test_dir / "invalid_config.json";
    auto result = loader.load_config(config_path.string());
    
    EXPECT_FALSE(result.has_value());
}

// 環境変数サポートのテスト
TEST_F(ConfigLoaderTest, EnvironmentVariableSupport) {
    // 環境変数を設定
    setenv("TEST_HOST", "env_host", 1);
    setenv("TEST_PORT", "9090", 1);
    
    std::string config_content = R"({
        "server": {
            "host": "${TEST_HOST}",
            "port": "${TEST_PORT}"
        }
    })";
    
    createTestConfigFile("env_config.json", config_content);
    
    ConfigLoader loader;
    std::filesystem::path config_path = test_dir / "env_config.json";
    auto result = loader.load_config(config_path.string());
    
    ASSERT_TRUE(result.has_value());
    auto& config = result.value();
    
    EXPECT_EQ(config.get_string("server.host"), "env_host");
    EXPECT_EQ(config.get_string("server.port"), "9090");
    
    // 環境変数をクリーンアップ
    unsetenv("TEST_HOST");
    unsetenv("TEST_PORT");
}

// 未定義の環境変数のテスト
TEST_F(ConfigLoaderTest, UndefinedEnvironmentVariable) {
    std::string config_content = R"({
        "server": {
            "host": "${UNDEFINED_HOST}",
            "port": 8080
        }
    })";
    
    createTestConfigFile("undef_env_config.json", config_content);
    
    ConfigLoader loader;
    std::filesystem::path config_path = test_dir / "undef_env_config.json";
    auto result = loader.load_config(config_path.string());
    
    ASSERT_TRUE(result.has_value());
    auto& config = result.value();
    
    // 未定義の環境変数はそのまま残るか空文字列になる（実装依存）
    std::string host = config.get_string("server.host");
    EXPECT_TRUE(host == "${UNDEFINED_HOST}" || host == "");
}

// 設定バリデーションのテスト
TEST_F(ConfigLoaderTest, ConfigValidation) {
    std::string config_content = R"({
        "server": {
            "host": "localhost",
            "port": 8080
        },
        "client": {
            "timeout": 30
        }
    })";
    
    createTestConfigFile("valid_config.json", config_content);
    
    ConfigLoader loader;
    std::filesystem::path config_path = test_dir / "valid_config.json";
    auto result = loader.load_config(config_path.string());
    
    ASSERT_TRUE(result.has_value());
    auto& config = result.value();
    
    // バリデーション
    EXPECT_TRUE(config.validate());
    
    // 必須フィールドの存在確認
    EXPECT_TRUE(config.has_key("server.host"));
    EXPECT_TRUE(config.has_key("server.port"));
    EXPECT_TRUE(config.has_key("client.timeout"));
}

// 型変換テスト
TEST_F(ConfigLoaderTest, TypeConversion) {
    std::string config_content = R"({
        "numbers": {
            "integer": 42,
            "float": 3.14,
            "string_number": "123"
        },
        "booleans": {
            "true_value": true,
            "false_value": false
        },
        "arrays": {
            "numbers": [1, 2, 3, 4, 5],
            "strings": ["a", "b", "c"]
        }
    })";
    
    createTestConfigFile("types_config.json", config_content);
    
    ConfigLoader loader;
    std::filesystem::path config_path = test_dir / "types_config.json";
    auto result = loader.load_config(config_path.string());
    
    ASSERT_TRUE(result.has_value());
    auto& config = result.value();
    
    // 数値型
    EXPECT_EQ(config.get_int("numbers.integer"), 42);
    EXPECT_DOUBLE_EQ(config.get_double("numbers.float"), 3.14);
    EXPECT_EQ(config.get_int("numbers.string_number"), 123);
    
    // ブール型
    EXPECT_TRUE(config.get_bool("booleans.true_value"));
    EXPECT_FALSE(config.get_bool("booleans.false_value"));
    
    // 配列（実装されている場合）
    if (config.has_key("arrays.numbers")) {
        auto numbers = config.get_array<int>("arrays.numbers");
        if (numbers.has_value()) {
            EXPECT_EQ(numbers->size(), 5);
            EXPECT_EQ((*numbers)[0], 1);
            EXPECT_EQ((*numbers)[4], 5);
        }
    }
}

// デフォルト値のテスト
TEST_F(ConfigLoaderTest, DefaultValues) {
    std::string config_content = R"({
        "server": {
            "host": "localhost"
        }
    })";
    
    createTestConfigFile("partial_config.json", config_content);
    
    ConfigLoader loader;
    std::filesystem::path config_path = test_dir / "partial_config.json";
    auto result = loader.load_config(config_path.string());
    
    ASSERT_TRUE(result.has_value());
    auto& config = result.value();
    
    // 存在するキー
    EXPECT_EQ(config.get_string("server.host"), "localhost");
    
    // 存在しないキーにデフォルト値を使用
    EXPECT_EQ(config.get_string("server.port", "8080"), "8080");
    EXPECT_EQ(config.get_int("client.timeout", 30), 30);
    EXPECT_TRUE(config.get_bool("client.debug", true));
}

// ネストした設定のテスト
TEST_F(ConfigLoaderTest, NestedConfiguration) {
    std::string config_content = R"({
        "database": {
            "primary": {
                "host": "db1.example.com",
                "port": 5432,
                "credentials": {
                    "username": "user1",
                    "password": "pass1"
                }
            },
            "replica": {
                "host": "db2.example.com",
                "port": 5433,
                "credentials": {
                    "username": "user2",
                    "password": "pass2"
                }
            }
        }
    })";
    
    createTestConfigFile("nested_config.json", config_content);
    
    ConfigLoader loader;
    std::filesystem::path config_path = test_dir / "nested_config.json";
    auto result = loader.load_config(config_path.string());
    
    ASSERT_TRUE(result.has_value());
    auto& config = result.value();
    
    // ネストしたキーへのアクセス
    EXPECT_EQ(config.get_string("database.primary.host"), "db1.example.com");
    EXPECT_EQ(config.get_int("database.primary.port"), 5432);
    EXPECT_EQ(config.get_string("database.primary.credentials.username"), "user1");
    EXPECT_EQ(config.get_string("database.primary.credentials.password"), "pass1");
    
    EXPECT_EQ(config.get_string("database.replica.host"), "db2.example.com");
    EXPECT_EQ(config.get_int("database.replica.port"), 5433);
    EXPECT_EQ(config.get_string("database.replica.credentials.username"), "user2");
    EXPECT_EQ(config.get_string("database.replica.credentials.password"), "pass2");
}

// 大きな設定ファイルのテスト
TEST_F(ConfigLoaderTest, LargeConfigFile) {
    std::string config_content = R"({
        "application": {
            "name": "WIP Client",
            "version": "1.0.0",
            "debug": true
        },
        "server": {
            "weather": {
                "host": "weather.example.com",
                "port": 8080,
                "timeout": 30,
                "retries": 3
            },
            "location": {
                "host": "location.example.com",
                "port": 8081,
                "timeout": 15,
                "retries": 2
            },
            "query": {
                "host": "query.example.com",
                "port": 8082,
                "timeout": 45,
                "retries": 5
            }
        },
        "cache": {
            "enabled": true,
            "ttl": 3600,
            "max_size": 1000
        },
        "logging": {
            "level": "INFO",
            "file": "/var/log/wip_client.log",
            "rotation": {
                "enabled": true,
                "max_size": "100MB",
                "max_files": 10
            }
        }
    })";
    
    createTestConfigFile("large_config.json", config_content);
    
    ConfigLoader loader;
    std::filesystem::path config_path = test_dir / "large_config.json";
    auto result = loader.load_config(config_path.string());
    
    ASSERT_TRUE(result.has_value());
    auto& config = result.value();
    
    // アプリケーション設定
    EXPECT_EQ(config.get_string("application.name"), "WIP Client");
    EXPECT_EQ(config.get_string("application.version"), "1.0.0");
    EXPECT_TRUE(config.get_bool("application.debug"));
    
    // サーバー設定
    EXPECT_EQ(config.get_string("server.weather.host"), "weather.example.com");
    EXPECT_EQ(config.get_int("server.weather.port"), 8080);
    EXPECT_EQ(config.get_string("server.location.host"), "location.example.com");
    EXPECT_EQ(config.get_int("server.location.port"), 8081);
    
    // キャッシュ設定
    EXPECT_TRUE(config.get_bool("cache.enabled"));
    EXPECT_EQ(config.get_int("cache.ttl"), 3600);
    EXPECT_EQ(config.get_int("cache.max_size"), 1000);
    
    // ログ設定
    EXPECT_EQ(config.get_string("logging.level"), "INFO");
    EXPECT_EQ(config.get_string("logging.file"), "/var/log/wip_client.log");
    EXPECT_TRUE(config.get_bool("logging.rotation.enabled"));
}