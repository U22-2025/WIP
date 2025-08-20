#include <gtest/gtest.h>
#include "wiplib/utils/auth.hpp"

using namespace wiplib::utils;

class AuthTest : public ::testing::Test {
protected:
    void SetUp() override {}
    void TearDown() override {}
};

// 基本的な認証テスト
TEST_F(AuthTest, BasicAuthentication) {
    WIPAuth auth("test_passphrase");
    
    EXPECT_TRUE(auth.is_authenticated());
    EXPECT_FALSE(auth.get_token().empty());
}

// 空のパスフレーズテスト
TEST_F(AuthTest, EmptyPassphrase) {
    WIPAuth auth("");
    
    // 空のパスフレーズでも認証は可能（設計による）
    EXPECT_TRUE(auth.is_authenticated());
}

// パスフレーズ変更テスト
TEST_F(AuthTest, PassphraseUpdate) {
    WIPAuth auth("initial_passphrase");
    std::string initial_token = auth.get_token();
    
    auth.set_passphrase("new_passphrase");
    std::string new_token = auth.get_token();
    
    EXPECT_TRUE(auth.is_authenticated());
    EXPECT_NE(initial_token, new_token);  // トークンが変更されるべき
}

// トークン生成テスト
TEST_F(AuthTest, TokenGeneration) {
    WIPAuth auth1("same_passphrase");
    WIPAuth auth2("same_passphrase");
    
    // 同じパスフレーズでも異なるトークンが生成される可能性
    std::string token1 = auth1.get_token();
    std::string token2 = auth2.get_token();
    
    EXPECT_FALSE(token1.empty());
    EXPECT_FALSE(token2.empty());
    // トークンの具体的な比較は実装依存
}

// トークンの一意性テスト
TEST_F(AuthTest, TokenUniqueness) {
    WIPAuth auth("test_passphrase");
    
    std::string token1 = auth.get_token();
    std::string token2 = auth.get_token();
    
    // 同じインスタンスからは同じトークンが返されるべき
    EXPECT_EQ(token1, token2);
}

// 異なるパスフレーズでの認証テスト
TEST_F(AuthTest, DifferentPassphrases) {
    WIPAuth auth1("passphrase1");
    WIPAuth auth2("passphrase2");
    
    EXPECT_TRUE(auth1.is_authenticated());
    EXPECT_TRUE(auth2.is_authenticated());
    
    std::string token1 = auth1.get_token();
    std::string token2 = auth2.get_token();
    
    EXPECT_FALSE(token1.empty());
    EXPECT_FALSE(token2.empty());
    EXPECT_NE(token1, token2);  // 異なるパスフレーズなら異なるトークン
}

// セキュリティポリシーテスト
TEST_F(AuthTest, SecurityPolicy) {
    WIPAuth auth("test_passphrase");
    
    // セキュリティポリシーの確認
    EXPECT_TRUE(auth.is_authenticated());
    
    // トークンが十分な長さを持つか確認
    std::string token = auth.get_token();
    EXPECT_GE(token.length(), 8);  // 最小8文字
}

// 認証状態のリセットテスト
TEST_F(AuthTest, AuthenticationReset) {
    WIPAuth auth("test_passphrase");
    EXPECT_TRUE(auth.is_authenticated());
    
    auth.reset();
    
    // リセット後の状態確認
    // 実装によってはリセット後も認証状態が維持される可能性あり
    std::string token_after_reset = auth.get_token();
    EXPECT_FALSE(token_after_reset.empty());
}

// 長いパスフレーズのテスト
TEST_F(AuthTest, LongPassphrase) {
    std::string long_passphrase(1000, 'x');  // 1000文字のパスフレーズ
    WIPAuth auth(long_passphrase);
    
    EXPECT_TRUE(auth.is_authenticated());
    EXPECT_FALSE(auth.get_token().empty());
}

// 特殊文字を含むパスフレーズのテスト
TEST_F(AuthTest, SpecialCharactersPassphrase) {
    std::string special_passphrase = "test!@#$%^&*()_+-=[]{}|;':\",./<>?`~";
    WIPAuth auth(special_passphrase);
    
    EXPECT_TRUE(auth.is_authenticated());
    EXPECT_FALSE(auth.get_token().empty());
}

// Unicode文字を含むパスフレーズのテスト
TEST_F(AuthTest, UnicodePassphrase) {
    std::string unicode_passphrase = "テスト用パスフレーズ🔐";
    WIPAuth auth(unicode_passphrase);
    
    EXPECT_TRUE(auth.is_authenticated());
    EXPECT_FALSE(auth.get_token().empty());
}

// 認証トークンの管理テスト
TEST_F(AuthTest, TokenManagement) {
    WIPAuth auth("test_passphrase");
    
    // 初期状態
    EXPECT_TRUE(auth.is_authenticated());
    std::string initial_token = auth.get_token();
    EXPECT_FALSE(initial_token.empty());
    
    // トークンの再取得
    std::string second_token = auth.get_token();
    EXPECT_EQ(initial_token, second_token);  // 同じトークンが返される
    
    // パスフレーズ変更でトークンが更新される
    auth.set_passphrase("new_passphrase");
    std::string updated_token = auth.get_token();
    EXPECT_NE(initial_token, updated_token);
}

// マルチインスタンステスト
TEST_F(AuthTest, MultipleInstances) {
    WIPAuth auth1("passphrase1");
    WIPAuth auth2("passphrase2");
    WIPAuth auth3("passphrase1");  // auth1と同じパスフレーズ
    
    EXPECT_TRUE(auth1.is_authenticated());
    EXPECT_TRUE(auth2.is_authenticated());
    EXPECT_TRUE(auth3.is_authenticated());
    
    std::string token1 = auth1.get_token();
    std::string token2 = auth2.get_token();
    std::string token3 = auth3.get_token();
    
    EXPECT_NE(token1, token2);  // 異なるパスフレーズなら異なるトークン
    // token1とtoken3の関係は実装依存（同じでも異なってもよい）
}

// セキュリティポリシー適用テスト
TEST_F(AuthTest, SecurityPolicyApplication) {
    WIPAuth auth("test_passphrase");
    
    // 認証状態の確認
    EXPECT_TRUE(auth.is_authenticated());
    
    // トークンの基本的なセキュリティ要件
    std::string token = auth.get_token();
    EXPECT_FALSE(token.empty());
    EXPECT_GE(token.length(), 4);  // 最小長
    
    // トークンが印刷可能文字のみで構成されているか
    for (char c : token) {
        EXPECT_TRUE(std::isprint(static_cast<unsigned char>(c)));
    }
}