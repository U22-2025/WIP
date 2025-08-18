use clap::{Parser, Subcommand};
use std::error::Error;
use wip_rust::wip_common_rs::utils::auth::{WIPAuth, SecurityPolicy};
use std::io::{self, Write};

#[derive(Parser)]
#[command(name = "wip-auth")]
#[command(about = "WIP Authentication Manager - 認証管理ツール")]
#[command(version = "0.1.0")]
struct Cli {
    /// デバッグモード
    #[arg(short, long)]
    debug: bool,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// 認証トークンを生成
    GenerateToken {
        /// パスフレーズ（指定しない場合は入力を求める）
        #[arg(short, long)]
        passphrase: Option<String>,

        /// トークン有効期限（秒）
        #[arg(short, long, default_value = "3600")]
        expires: u64,
    },
    /// トークンを検証
    VerifyToken {
        /// 認証トークン
        token: String,

        /// パスフレーズ
        #[arg(short, long)]
        passphrase: Option<String>,
    },
    /// セキュリティポリシーを表示
    ShowPolicy,
    /// パスフレーズのテスト
    TestPassphrase {
        /// テストするパスフレーズ
        passphrase: String,
    },
}

fn read_passphrase(prompt: &str) -> Result<String, Box<dyn Error>> {
    print!("{}", prompt);
    io::stdout().flush()?;
    
    // 簡易的なパスフレーズ入力（実際のプロダクションではrpasswordクレートなどを使用）
    let mut passphrase = String::new();
    io::stdin().read_line(&mut passphrase)?;
    Ok(passphrase.trim().to_string())
}

fn format_security_policy(policy: &SecurityPolicy) {
    println!("=== セキュリティポリシー ===");
    println!("最小パスフレーズ長: {}", policy.min_passphrase_length);
    println!("特殊文字要求: {}", if policy.require_special_chars { "有効" } else { "無効" });
    println!("セッション有効期限: {}秒", policy.max_session_duration);
    println!("最大同時セッション数: {}", policy.max_concurrent_sessions);
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let cli = Cli::parse();

    if cli.debug {
        env_logger::init();
    }

    match cli.command {
        Commands::GenerateToken { passphrase, expires } => {
            println!("🎫 認証トークンを生成中...");
            
            let passphrase = if let Some(p) = passphrase {
                p
            } else {
                read_passphrase("パスフレーズを入力してください: ")?
            };
            
            let mut auth = WIPAuth::with_timeout(passphrase.clone(), expires);
            
            match auth.authenticate(&passphrase) {
                Ok(token) => {
                    println!("✅ 認証トークンが生成されました");
                    println!("🎫 トークン: {}", token);
                    println!("⏰ 有効期限: {}秒", expires);
                    println!();
                    println!("💡 使用例:");
                    println!("  cargo run --bin wip-weather -- --auth-token {} get 11000 --weather", token);
                }
                Err(e) => {
                    println!("❌ トークン生成失敗: {}", e);
                }
            }
        }

        Commands::VerifyToken { token, passphrase } => {
            println!("🔍 トークンを検証中...");
            
            let passphrase = if let Some(p) = passphrase {
                p
            } else {
                read_passphrase("パスフレーズを入力してください: ")?
            };
            
            let mut auth = WIPAuth::new(passphrase);
            
            if auth.validate_token(&token) {
                println!("✅ トークンは有効です");
                
                if let Some(permissions) = auth.get_token_permissions(&token) {
                    println!("🔐 権限: {:?}", permissions);
                }
            } else {
                println!("❌ トークンは無効または期限切れです");
            }
        }

        Commands::ShowPolicy => {
            let policy = SecurityPolicy::default();
            format_security_policy(&policy);
        }

        Commands::TestPassphrase { passphrase } => {
            println!("🔍 パスフレーズをテスト中...");
            
            let policy = SecurityPolicy::default();
            
            match policy.validate_passphrase(&passphrase) {
                Ok(()) => {
                    println!("✅ パスフレーズは有効です");
                    println!("長さ: {} 文字", passphrase.len());
                    println!("特殊文字含有: {}", if passphrase.chars().any(|c| !c.is_alphanumeric()) { "あり" } else { "なし" });
                }
                Err(e) => {
                    println!("❌ パスフレーズは無効です: {}", e);
                    println!("💡 要件:");
                    println!("  - 最小 {} 文字", policy.min_passphrase_length);
                    if policy.require_special_chars {
                        println!("  - 特殊文字を含む");
                    }
                }
            }
        }
    }

    Ok(())
}