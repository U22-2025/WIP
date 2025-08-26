use std::fs::{self, File};
use std::io::{Read, Write, BufReader, BufWriter};
use std::path::{Path, PathBuf};
use std::time::{SystemTime, UNIX_EPOCH, Duration};
use std::collections::HashMap;
use serde::{Serialize, Deserialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileCacheEntry { pub key: String, pub data: Vec<u8>, pub expires_at: u64, pub created_at: u64, pub access_count: u64, pub last_accessed: u64 }
impl FileCacheEntry {
    pub fn new(key: String, data: Vec<u8>, ttl: Duration) -> Self {
        let now = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs();
        Self { key, data, expires_at: now + ttl.as_secs(), created_at: now, access_count: 0, last_accessed: now }
    }
    pub fn is_expired(&self) -> bool { SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs() > self.expires_at }
    pub fn touch(&mut self) { self.access_count += 1; self.last_accessed = SystemTime::now().duration_since(UNIX_EPOCH).unwrap_or_default().as_secs(); }
}

pub struct FileCache {
    cache_dir: PathBuf,
    default_ttl: Duration,
    max_file_size: u64,
    max_cache_size: u64,
    metadata: HashMap<String, FileCacheEntry>,
}
impl FileCache {
    pub fn new<P: AsRef<Path>>(cache_dir: P) -> Result<Self, String> { Self::with_options(cache_dir, Duration::from_secs(3600), 10*1024*1024, 100*1024*1024) }
    pub fn with_options<P: AsRef<Path>>(cache_dir: P, default_ttl: Duration, max_file_size: u64, max_cache_size: u64) -> Result<Self, String> {
        let cache_dir = cache_dir.as_ref().to_path_buf();
        if !cache_dir.exists() { fs::create_dir_all(&cache_dir).map_err(|e| format!("Failed to create cache directory: {}", e))?; }
        let mut cache = Self { cache_dir, default_ttl, max_file_size, max_cache_size, metadata: HashMap::new() };
        cache.load_metadata()?; cache.cleanup_expired()?; Ok(cache)
    }
    pub fn set(&mut self, key: &str, data: &[u8]) -> Result<(), String> { self.set_with_ttl(key, data, None) }
    pub fn set_with_ttl(&mut self, key: &str, data: &[u8], ttl: Option<Duration>) -> Result<(), String> {
        if data.len() as u64 > self.max_file_size { return Err(format!("Data size {} exceeds maximum file size {}", data.len(), self.max_file_size)); }
        let ttl = ttl.unwrap_or(self.default_ttl);
        let entry = FileCacheEntry::new(key.to_string(), data.to_vec(), ttl);
        self.ensure_space_available(data.len() as u64)?;
        let file_path = self.get_cache_file_path(key);
        let mut file = File::create(&file_path).map_err(|e| format!("Failed to create cache file: {}", e))?;
        file.write_all(data).map_err(|e| format!("Failed to write cache data: {}", e))?;
        self.metadata.insert(key.to_string(), entry);
        self.save_metadata()?; Ok(())
    }
    pub fn get(&mut self, key: &str) -> Result<Option<Vec<u8>>, String> {
        if let Some(entry) = self.metadata.get_mut(key) {
            if entry.is_expired() { self.delete(key)?; return Ok(None); }
            entry.touch();
            let file_path = self.get_cache_file_path(key);
            if !file_path.exists() { self.metadata.remove(key); self.save_metadata()?; return Ok(None); }
            let mut file = File::open(&file_path).map_err(|e| format!("Failed to open cache file: {}", e))?;
            let mut data = Vec::new(); file.read_to_end(&mut data).map_err(|e| format!("Failed to read cache data: {}", e))?;
            self.save_metadata()?; Ok(Some(data))
        } else { Ok(None) }
    }
    pub fn contains_key(&self, key: &str) -> bool { self.metadata.get(key).map_or(false, |e| !e.is_expired() && self.get_cache_file_path(key).exists()) }
    pub fn delete(&mut self, key: &str) -> Result<bool, String> {
        if let Some(_) = self.metadata.remove(key) {
            let file_path = self.get_cache_file_path(key);
            if file_path.exists() { fs::remove_file(&file_path).map_err(|e| format!("Failed to delete cache file: {}", e))?; }
            self.save_metadata()?; Ok(true)
        } else { Ok(false) }
    }
    pub fn clear(&mut self) -> Result<(), String> {
        for entry in self.metadata.values() { let p = self.get_cache_file_path(&entry.key); if p.exists() { fs::remove_file(&p).map_err(|e| format!("Failed to delete cache file: {}", e))?; } }
        self.metadata.clear(); self.save_metadata()?; Ok(())
    }
    pub fn cleanup_expired(&mut self) -> Result<usize, String> { let keys: Vec<_> = self.metadata.iter().filter(|(_, e)| e.is_expired()).map(|(k, _)| k.clone()).collect(); let count = keys.len(); for k in keys { self.delete(&k)?; } Ok(count) }
    pub fn get_stats(&self) -> FileCacheStats { let mut total_size=0; let mut expired=0; let mut total_access=0; for e in self.metadata.values(){ total_size += e.data.len() as u64; total_access+=e.access_count; if e.is_expired(){expired+=1;} } FileCacheStats{ total_entries:self.metadata.len(), expired_entries:expired, total_size, total_access_count:total_access, max_cache_size:self.max_cache_size, cache_dir:self.cache_dir.clone() } }
    pub fn keys(&self) -> Vec<String> { self.metadata.keys().filter(|k| !self.metadata[*k].is_expired()).cloned().collect() }
    fn get_cache_file_path(&self, key: &str) -> PathBuf { let safe = self.safe_filename(key); self.cache_dir.join(format!("{}.cache", safe)) }
    fn get_metadata_path(&self) -> PathBuf { self.cache_dir.join("metadata.json") }
    fn safe_filename(&self, key: &str) -> String { use std::collections::hash_map::DefaultHasher; use std::hash::{Hash, Hasher}; let mut h = DefaultHasher::new(); key.hash(&mut h); format!("{:x}", h.finish()) }
    fn load_metadata(&mut self) -> Result<(), String> { let p = self.get_metadata_path(); if !p.exists() { return Ok(());} let f=File::open(&p).map_err(|e| format!("Failed to open metadata file: {}", e))?; let r=BufReader::new(f); self.metadata = serde_json::from_reader(r).map_err(|e| format!("Failed to parse metadata: {}", e))?; Ok(()) }
    fn save_metadata(&self) -> Result<(), String> { let p=self.get_metadata_path(); let f=File::create(&p).map_err(|e| format!("Failed to create metadata file: {}", e))?; let w=BufWriter::new(f); serde_json::to_writer_pretty(w, &self.metadata).map_err(|e| format!("Failed to write metadata: {}", e))?; Ok(()) }
    fn ensure_space_available(&mut self, needed: u64) -> Result<(), String> { let current=self.get_current_cache_size(); if current+needed <= self.max_cache_size { return Ok(());} let mut ents:Vec<_>=self.metadata.values().collect(); ents.sort_by_key(|e| e.last_accessed); let mut freed=0; let mut rm=Vec::new(); for e in ents { if current+needed - freed <= self.max_cache_size { break; } freed += e.data.len() as u64; rm.push(e.key.clone()); } for k in rm { self.delete(&k)?; } Ok(()) }
    fn get_current_cache_size(&self) -> u64 { self.metadata.values().map(|e| e.data.len() as u64).sum() }
}

#[derive(Debug, Clone)]
pub struct FileCacheStats { pub total_entries: usize, pub expired_entries: usize, pub total_size: u64, pub total_access_count: u64, pub max_cache_size: u64, pub cache_dir: PathBuf }

