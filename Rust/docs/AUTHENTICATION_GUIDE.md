# WIP Rust - 認証システムガイド

WIP Rust実装では、SHA256ベースのトークン認証システムが完全に実装されており、セキュアな通信を提供します。

## 目次

1. [認証システム概要](#認証システム概要)
2. [基本的な認証フロー](#基本的な認証フロー)
3. [セキュリティポリシー](#セキュリティポリシー)
4. [認証付きクライアント](#認証付きクライアント)
5. [トークン管理](#トークン管理)
6. [暗号化と安全性](#暗号化と安全性)
7. [実装例](#実装例)

## 認証システム概要

WIP Rust実装の認証システムは以下の特徴を持ちます：

- **SHA256ハッシュ**: パスフレーズとトークンの暗号化
- **時間ベースの有効期限**: 設定可能なセッションタイムアウト
- **権限ベースアクセス制御**: 読み取り/書き込み権限の管理
- **同時セッション制限**: セキュリティポリシーによる制御
- **自動期限切れクリーンアップ**: メモリリーク防止

### 主要コンポーネント

```rust
// 認証トークン構造
pub struct AuthToken {
    pub token: String,           // SHA256ハッシュトークン
    pub expires_at: u64,        // UNIXタイムスタンプ（秒）
    pub permissions: Vec<String>, // 権限リスト
}

// 認証システム
pub struct WIPAuth {
    passphrase: String,                    // マスターパスフレーズ
    tokens: HashMap<String, AuthToken>,   // アクティブトークン
    session_timeout: u64,                 // セッションタイムアウト（秒）
}

// セキュリティポリシー
pub struct SecurityPolicy {
    pub min_passphrase_length: usize,     // 最小パスフレーズ長
    pub require_special_chars: bool,      // 特殊文字要求
    pub max_session_duration: u64,        // 最大セッション時間
    pub max_concurrent_sessions: usize,   // 最大同時セッション数
}
```

## 基本的な認証フロー

### 1. 認証システム初期化

```rust
use wip_rust::wip_common_rs::utils::auth::WIPAuth;

// 基本初期化（デフォルト1時間タイムアウト）
let mut auth = WIPAuth::new("secure-master-passphrase".to_string());

// カスタムタイムアウト設定（2時間）
let mut auth = WIPAuth::with_timeout(
    "secure-master-passphrase".to_string(), 
    7200  // 2時間
);
```

### 2. 認証実行

```rust
// パスフレーズによる認証
match auth.authenticate("secure-master-passphrase") {
    Ok(token) => {
        println!("認証成功");
        println!("トークン: {}", token);
        
        // トークンを使用して以降の操作を実行
        // ...
    },
    Err(error_message) => {
        println!("認証失敗: {}", error_message);
    }
}
```

### 3. トークン検証

```rust
// トークンの有効性確認
if auth.validate_token(&token) {
    println!("トークンは有効です");
    
    // 権限確認
    if auth.has_permission(&token, "write") {
        println!("書き込み権限があります");
        // 書き込み操作実行
    }
    
    if auth.has_permission(&token, "read") {
        println!("読み取り権限があります");
        // 読み取り操作実行
    }
} else {
    println!("トークンが無効または期限切れです");
}
```

### 4. トークン無効化

```rust
// 特定のトークンを無効化
if auth.revoke_token(&token) {
    println!("トークンを無効化しました");
} else {
    println!("トークンが見つかりません");
}

// 期限切れトークンの自動クリーンアップ
auth.cleanup_expired_tokens();
```

## セキュリティポリシー

### ポリシー設定

```rust
use wip_rust::wip_common_rs::utils::auth::SecurityPolicy;

// カスタムセキュリティポリシー
let security_policy = SecurityPolicy {
    min_passphrase_length: 12,           // 最低12文字
    require_special_chars: true,         // 特殊文字必須
    max_session_duration: 3600,          // 最大1時間
    max_concurrent_sessions: 5,          // 最大5セッション
};

// パスフレーズ検証
match security_policy.validate_passphrase("MySecureP@ssw0rd123!") {
    Ok(()) => println!("パスフレーズは要件を満たしています"),
    Err(error) => println!("パスフレーズエラー: {}", error),
}

// セッション数制限確認
let active_sessions = 3;
match security_policy.enforce_session_limits(active_sessions) {
    Ok(()) => println!("セッション数は制限内です"),
    Err(error) => println!("セッション制限エラー: {}", error),
}
```

### セキュリティレベル別設定例

```rust
// 高セキュリティ環境
let high_security = SecurityPolicy {
    min_passphrase_length: 16,
    require_special_chars: true,
    max_session_duration: 1800,  // 30分
    max_concurrent_sessions: 3,
};

// 標準セキュリティ環境
let standard_security = SecurityPolicy {
    min_passphrase_length: 10,
    require_special_chars: true,
    max_session_duration: 3600,  // 1時間
    max_concurrent_sessions: 5,
};

// 開発環境
let dev_security = SecurityPolicy {
    min_passphrase_length: 6,
    require_special_chars: false,
    max_session_duration: 7200,  // 2時間
    max_concurrent_sessions: 10,
};
```

## 認証付きクライアント

### Weather Client認証

```rust
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use wip_rust::wip_common_rs::utils::auth::WIPAuth;

async fn authenticated_weather_client() -> Result<(), Box<dyn std::error::Error>> {
    // 認証システム初期化
    let mut auth = WIPAuth::new("server-shared-secret".to_string());
    
    // 認証実行
    let token = auth.authenticate("server-shared-secret")?;
    
    // Weather Client作成・認証設定
    let mut weather_client = WeatherClient::new("127.0.0.1", 4110, true)?;
    weather_client.set_auth_token(Some(token.clone()));
    
    // 認証付きリクエスト送信
    let result = weather_client.get_weather_simple(11000, true, true, true, false, false, 0)?;
    
    match result {
        Some(response) => {
            println!("認証付き天気データ取得成功");
            println!("エリアコード: {}", response.area_code);
        },
        None => println!("レスポンスなし"),
    }
    
    // トークン無効化（セッション終了）
    auth.revoke_token(&token);
    
    Ok(())
}
```

### Report Client認証

```rust
use wip_rust::wip_common_rs::clients::report_client::ReportClient;

async fn authenticated_report_client() -> Result<(), Box<dyn std::error::Error>> {
    let mut auth = WIPAuth::new("report-server-secret".to_string());
    let token = auth.authenticate("report-server-secret")?;
    
    // 権限確認
    if !auth.has_permission(&token, "write") {
        return Err("書き込み権限がありません".into());
    }
    
    let mut report_client = ReportClient::new("127.0.0.1:4112".parse()?).await?;
    report_client.set_auth_token(Some(token.clone()));
    
    // 認証付きレポート送信
    let report_id = report_client.send_sensor_report(
        "earthquake",
        8,
        "認証付き地震レポート",
        Some(35.6812),
        Some(139.7671)
    ).await?;
    
    println!("認証付きレポート送信完了 ID: {}", report_id);
    
    Ok(())
}
```

### Location Client認証

```rust
use wip_rust::wip_common_rs::clients::location_client::LocationClient;

async fn authenticated_location_client() -> Result<(), Box<dyn std::error::Error>> {
    let mut auth = WIPAuth::new("location-server-secret".to_string());
    let token = auth.authenticate("location-server-secret")?;
    
    let mut location_client = LocationClient::new("127.0.0.1:4109".parse()?).await?;
    location_client.set_auth_token(Some(token.clone()));
    
    // 認証付き座標解決
    let area_code = location_client.resolve_coordinates(35.6812, 139.7671).await?;
    println!("認証付き座標解決: エリアコード {}", area_code);
    
    Ok(())
}
```

## トークン管理

### マルチユーザー環境

```rust
use std::collections::HashMap;

struct MultiUserAuth {
    auth_systems: HashMap<String, WIPAuth>,
    global_policy: SecurityPolicy,
}

impl MultiUserAuth {
    fn new(global_policy: SecurityPolicy) -> Self {
        Self {
            auth_systems: HashMap::new(),
            global_policy,
        }
    }
    
    fn create_user(&mut self, user_id: String, passphrase: String) -> Result<(), String> {
        // セキュリティポリシー検証
        self.global_policy.validate_passphrase(&passphrase)?;
        
        // ユーザー専用認証システム作成
        let auth = WIPAuth::with_timeout(passphrase, self.global_policy.max_session_duration);
        self.auth_systems.insert(user_id, auth);
        
        Ok(())
    }
    
    fn authenticate_user(&mut self, user_id: &str, passphrase: &str) -> Result<String, String> {
        if let Some(auth) = self.auth_systems.get_mut(user_id) {
            auth.authenticate(passphrase)
        } else {
            Err("ユーザーが見つかりません".to_string())
        }
    }
    
    fn validate_user_token(&mut self, user_id: &str, token: &str) -> bool {
        if let Some(auth) = self.auth_systems.get_mut(user_id) {
            auth.validate_token(token)
        } else {
            false
        }
    }
    
    fn cleanup_all_expired(&mut self) {
        for (_, auth) in self.auth_systems.iter_mut() {
            auth.cleanup_expired_tokens();
        }
    }
}

// 使用例
async fn multi_user_example() -> Result<(), Box<dyn std::error::Error>> {
    let policy = SecurityPolicy::default();
    let mut multi_auth = MultiUserAuth::new(policy);
    
    // ユーザー作成
    multi_auth.create_user("admin".to_string(), "AdminP@ssw0rd123!".to_string())?;
    multi_auth.create_user("user1".to_string(), "UserP@ssw0rd456!".to_string())?;
    
    // 管理者認証
    let admin_token = multi_auth.authenticate_user("admin", "AdminP@ssw0rd123!")?;
    println!("管理者認証成功: {}", admin_token);
    
    // 一般ユーザー認証
    let user_token = multi_auth.authenticate_user("user1", "UserP@ssw0rd456!")?;
    println!("ユーザー認証成功: {}", user_token);
    
    // トークン検証
    if multi_auth.validate_user_token("admin", &admin_token) {
        println!("管理者トークン有効");
    }
    
    Ok(())
}
```

### セッション管理システム

```rust
use std::time::{Duration, Instant};
use tokio::time::interval;

struct SessionManager {
    auth: WIPAuth,
    last_cleanup: Instant,
    cleanup_interval: Duration,
}

impl SessionManager {
    fn new(passphrase: String, session_timeout: u64) -> Self {
        Self {
            auth: WIPAuth::with_timeout(passphrase, session_timeout),
            last_cleanup: Instant::now(),
            cleanup_interval: Duration::from_secs(300), // 5分毎
        }
    }
    
    fn authenticate(&mut self, passphrase: &str) -> Result<String, String> {
        self.periodic_cleanup();
        self.auth.authenticate(passphrase)
    }
    
    fn validate_token(&mut self, token: &str) -> bool {
        self.periodic_cleanup();
        self.auth.validate_token(token)
    }
    
    fn periodic_cleanup(&mut self) {
        if self.last_cleanup.elapsed() >= self.cleanup_interval {
            self.auth.cleanup_expired_tokens();
            self.last_cleanup = Instant::now();
        }
    }
    
    // バックグラウンドでの自動クリーンアップ
    async fn start_auto_cleanup(&mut self) {
        let mut cleanup_timer = interval(self.cleanup_interval);
        
        loop {
            cleanup_timer.tick().await;
            self.auth.cleanup_expired_tokens();
            println!("期限切れトークンをクリーンアップしました");
        }
    }
}
```

## 暗号化と安全性

### パスフレーズハッシュ化

```rust
use sha2::{Sha256, Digest};

fn secure_hash_passphrase(passphrase: &str, salt: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(passphrase.as_bytes());
    hasher.update(salt.as_bytes());
    format!("{:x}", hasher.finalize())
}

fn verify_passphrase(passphrase: &str, salt: &str, expected_hash: &str) -> bool {
    let hash = secure_hash_passphrase(passphrase, salt);
    hash == expected_hash
}

// 使用例
fn password_security_example() {
    let passphrase = "MySecureP@ssw0rd123!";
    let salt = "random-salt-string";
    
    let hash = secure_hash_passphrase(passphrase, salt);
    println!("ハッシュ化されたパスフレーズ: {}", hash);
    
    // 検証
    if verify_passphrase(passphrase, salt, &hash) {
        println!("パスフレーズ検証成功");
    }
}
```

### トークン生成の安全性

```rust
use rand::Rng;
use sha2::{Sha256, Digest};

fn generate_secure_token(passphrase: &str) -> Result<String, String> {
    // 暗号学的安全な乱数生成
    let mut rng = rand::thread_rng();
    let random_bytes: [u8; 32] = rng.gen();
    
    // 現在時刻取得
    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    // ハッシュ計算
    let mut hasher = Sha256::new();
    hasher.update(&random_bytes);           // ランダム性
    hasher.update(timestamp.to_be_bytes()); // 時間要素
    hasher.update(passphrase.as_bytes());   // 認証要素
    
    Ok(format!("{:x}", hasher.finalize()))
}
```

## 実装例

### 完全な認証付きアプリケーション

```rust
use wip_rust::wip_common_rs::utils::auth::{WIPAuth, SecurityPolicy};
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;
use std::io::{self, Write};

struct SecureWeatherApp {
    auth: WIPAuth,
    policy: SecurityPolicy,
    current_token: Option<String>,
}

impl SecureWeatherApp {
    fn new(master_passphrase: String) -> Self {
        let policy = SecurityPolicy {
            min_passphrase_length: 10,
            require_special_chars: true,
            max_session_duration: 3600,
            max_concurrent_sessions: 3,
        };
        
        let auth = WIPAuth::with_timeout(master_passphrase, policy.max_session_duration);
        
        Self {
            auth,
            policy,
            current_token: None,
        }
    }
    
    fn login(&mut self) -> Result<(), String> {
        print!("パスフレーズを入力してください: ");
        io::stdout().flush().unwrap();
        
        let mut input = String::new();
        io::stdin().read_line(&mut input).unwrap();
        let passphrase = input.trim();
        
        // セキュリティポリシー検証
        self.policy.validate_passphrase(passphrase)?;
        
        // 認証実行
        let token = self.auth.authenticate(passphrase)?;
        self.current_token = Some(token);
        
        println!("認証成功！");
        Ok(())
    }
    
    fn logout(&mut self) {
        if let Some(token) = &self.current_token {
            self.auth.revoke_token(token);
            self.current_token = None;
            println!("ログアウトしました");
        }
    }
    
    fn is_authenticated(&mut self) -> bool {
        if let Some(token) = &self.current_token {
            self.auth.validate_token(token)
        } else {
            false
        }
    }
    
    async fn get_weather(&mut self, area_code: u32) -> Result<(), Box<dyn std::error::Error>> {
        if !self.is_authenticated() {
            return Err("認証が必要です".into());
        }
        
        let token = self.current_token.as_ref().unwrap();
        
        // 権限確認
        if !self.auth.has_permission(token, "read") {
            return Err("読み取り権限がありません".into());
        }
        
        // Weather Client使用
        let mut client = WeatherClient::new("127.0.0.1", 4110, true)?;
        client.set_auth_token(Some(token.clone()));
        
        if let Some(response) = client.get_weather_simple(area_code, true, true, true, false, false, 0)? {
            println!("=== 天気データ ===");
            println!("エリアコード: {}", response.area_code);
            if let Some(temp) = response.temperature {
                println!("気温: {}°C", temp);
            }
        }
        
        Ok(())
    }
    
    async fn run(&mut self) -> Result<(), Box<dyn std::error::Error>> {
        println!("=== セキュア天気アプリケーション ===");
        
        // ログイン
        loop {
            match self.login() {
                Ok(()) => break,
                Err(e) => {
                    println!("ログインエラー: {}", e);
                    print!("再試行しますか？ (y/n): ");
                    io::stdout().flush().unwrap();
                    
                    let mut input = String::new();
                    io::stdin().read_line(&mut input).unwrap();
                    if input.trim().to_lowercase() != "y" {
                        return Ok(());
                    }
                }
            }
        }
        
        // メインループ
        loop {
            if !self.is_authenticated() {
                println!("セッションが期限切れです。再ログインしてください。");
                break;
            }
            
            println!("\n=== メニュー ===");
            println!("1. 天気データ取得");
            println!("2. ログアウト");
            print!("選択してください (1-2): ");
            io::stdout().flush().unwrap();
            
            let mut input = String::new();
            io::stdin().read_line(&mut input).unwrap();
            
            match input.trim() {
                "1" => {
                    print!("エリアコードを入力してください: ");
                    io::stdout().flush().unwrap();
                    
                    let mut area_input = String::new();
                    io::stdin().read_line(&mut area_input).unwrap();
                    
                    if let Ok(area_code) = area_input.trim().parse::<u32>() {
                        if let Err(e) = self.get_weather(area_code).await {
                            println!("エラー: {}", e);
                        }
                    } else {
                        println!("無効なエリアコードです");
                    }
                },
                "2" => {
                    self.logout();
                    break;
                },
                _ => {
                    println!("無効な選択です");
                }
            }
        }
        
        Ok(())
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut app = SecureWeatherApp::new("master-secure-passphrase-2024!".to_string());
    app.run().await?;
    Ok(())
}
```

このガイドを参考に、WIP Rust実装の認証機能を安全かつ効果的に活用してください。