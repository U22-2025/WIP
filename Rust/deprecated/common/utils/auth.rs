use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Deserialize, Serialize};
use sha2::{Sha256, Digest};
use rand::Rng;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthToken {
    pub token: String,
    pub expires_at: u64,
    pub permissions: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct WIPAuth {
    passphrase: String,
    tokens: HashMap<String, AuthToken>,
    session_timeout: u64,
}

impl WIPAuth {
    pub fn new(passphrase: String) -> Self {
        Self {
            passphrase,
            tokens: HashMap::new(),
            session_timeout: 3600, // 1時間
        }
    }

    pub fn with_timeout(passphrase: String, timeout_seconds: u64) -> Self {
        Self {
            passphrase,
            tokens: HashMap::new(),
            session_timeout: timeout_seconds,
        }
    }

    pub fn authenticate(&mut self, provided_passphrase: &str) -> Result<String, String> {
        if self.validate_passphrase(provided_passphrase) {
            let token = self.generate_token()?;
            let auth_token = AuthToken {
                token: token.clone(),
                expires_at: self.current_timestamp() + self.session_timeout,
                permissions: vec!["read".to_string(), "write".to_string()],
            };
            self.tokens.insert(token.clone(), auth_token);
            Ok(token)
        } else {
            Err("Invalid passphrase".to_string())
        }
    }

    pub fn validate_token(&mut self, token: &str) -> bool {
        if let Some(auth_token) = self.tokens.get(token) {
            if auth_token.expires_at > self.current_timestamp() {
                true
            } else {
                self.tokens.remove(token);
                false
            }
        } else {
            false
        }
    }

    pub fn revoke_token(&mut self, token: &str) -> bool {
        self.tokens.remove(token).is_some()
    }

    pub fn cleanup_expired_tokens(&mut self) {
        let current_time = self.current_timestamp();
        self.tokens.retain(|_, token| token.expires_at > current_time);
    }

    pub fn get_token_permissions(&self, token: &str) -> Option<&Vec<String>> {
        self.tokens.get(token).map(|t| &t.permissions)
    }

    pub fn has_permission(&self, token: &str, permission: &str) -> bool {
        if let Some(auth_token) = self.tokens.get(token) {
            auth_token.permissions.contains(&permission.to_string())
        } else {
            false
        }
    }

    fn validate_passphrase(&self, provided: &str) -> bool {
        self.hash_passphrase(provided) == self.hash_passphrase(&self.passphrase)
    }

    fn hash_passphrase(&self, passphrase: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(passphrase.as_bytes());
        format!("{:x}", hasher.finalize())
    }

    fn generate_token(&self) -> Result<String, String> {
        let mut rng = rand::thread_rng();
        let random_bytes: [u8; 32] = rng.gen();
        let timestamp = self.current_timestamp();
        
        let mut hasher = Sha256::new();
        hasher.update(&random_bytes);
        hasher.update(timestamp.to_be_bytes());
        hasher.update(self.passphrase.as_bytes());
        
        Ok(format!("{:x}", hasher.finalize()))
    }

    fn current_timestamp(&self) -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs()
    }
}

#[derive(Debug, Clone)]
pub struct SecurityPolicy {
    pub min_passphrase_length: usize,
    pub require_special_chars: bool,
    pub max_session_duration: u64,
    pub max_concurrent_sessions: usize,
}

impl Default for SecurityPolicy {
    fn default() -> Self {
        Self {
            min_passphrase_length: 8,
            require_special_chars: true,
            max_session_duration: 3600,
            max_concurrent_sessions: 5,
        }
    }
}

impl SecurityPolicy {
    pub fn validate_passphrase(&self, passphrase: &str) -> Result<(), String> {
        if passphrase.len() < self.min_passphrase_length {
            return Err(format!("Passphrase must be at least {} characters", self.min_passphrase_length));
        }

        if self.require_special_chars && !passphrase.chars().any(|c| !c.is_alphanumeric()) {
            return Err("Passphrase must contain special characters".to_string());
        }

        Ok(())
    }

    pub fn enforce_session_limits(&self, active_sessions: usize) -> Result<(), String> {
        if active_sessions >= self.max_concurrent_sessions {
            Err("Maximum concurrent sessions exceeded".to_string())
        } else {
            Ok(())
        }
    }
}
