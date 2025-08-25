use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use std::thread;

#[derive(Clone)]
pub struct CacheEntry<T> {
    pub value: T,
    pub expires_at: Instant,
    pub hit_count: u64,
    pub last_accessed: Instant,
}

pub struct Cache<T: Clone + Send + 'static> {
    store: Arc<Mutex<HashMap<String, CacheEntry<T>>>>,
    default_ttl: Duration,
    max_size: usize,
    cleanup_interval: Duration,
}

impl<T: Clone + Send + 'static> Cache<T> {
    pub fn new(default_ttl: Duration) -> Self {
        Self::with_options(default_ttl, 1000, Duration::from_secs(60))
    }

    pub fn with_options(default_ttl: Duration, max_size: usize, cleanup_interval: Duration) -> Self {
        let cache = Self {
            store: Arc::new(Mutex::new(HashMap::new())),
            default_ttl,
            max_size,
            cleanup_interval,
        };

        // Start cleanup thread
        cache.start_cleanup_thread();
        cache
    }

    pub fn set(&self, key: &str, value: T) {
        self.set_with_ttl(key, value, None);
    }

    pub fn set_with_ttl(&self, key: &str, value: T, ttl: Option<Duration>) {
        let mut map = self.store.lock().unwrap();
        let now = Instant::now();
        let expire = now + ttl.unwrap_or(self.default_ttl);
        
        let entry = CacheEntry {
            value,
            expires_at: expire,
            hit_count: 0,
            last_accessed: now,
        };

        // Check if we need to evict entries to make space
        if map.len() >= self.max_size && !map.contains_key(key) {
            self.evict_lru(&mut map);
        }

        map.insert(key.to_string(), entry);
    }

    pub fn get(&self, key: &str) -> Option<T> {
        let mut map = self.store.lock().unwrap();
        if let Some(entry) = map.get_mut(key) {
            let now = Instant::now();
            if now <= entry.expires_at {
                entry.hit_count += 1;
                entry.last_accessed = now;
                return Some(entry.value.clone());
            } else {
                map.remove(key);
            }
        }
        None
    }

    pub fn get_with_stats(&self, key: &str) -> Option<(T, u64, Instant)> {
        let mut map = self.store.lock().unwrap();
        if let Some(entry) = map.get_mut(key) {
            let now = Instant::now();
            if now <= entry.expires_at {
                entry.hit_count += 1;
                entry.last_accessed = now;
                return Some((entry.value.clone(), entry.hit_count, entry.last_accessed));
            } else {
                map.remove(key);
            }
        }
        None
    }

    pub fn contains_key(&self, key: &str) -> bool {
        let mut map = self.store.lock().unwrap();
        if let Some(entry) = map.get(key) {
            if Instant::now() <= entry.expires_at {
                true
            } else {
                map.remove(key);
                false
            }
        } else {
            false
        }
    }

    pub fn delete(&self, key: &str) -> bool {
        self.store.lock().unwrap().remove(key).is_some()
    }

    pub fn clear(&self) {
        self.store.lock().unwrap().clear();
    }

    pub fn size(&self) -> usize {
        self.store.lock().unwrap().len()
    }

    pub fn keys(&self) -> Vec<String> {
        let map = self.store.lock().unwrap();
        map.keys().cloned().collect()
    }

    pub fn cleanup_expired(&self) -> usize {
        let mut map = self.store.lock().unwrap();
        let now = Instant::now();
        let initial_size = map.len();
        
        map.retain(|_, entry| entry.expires_at > now);
        
        initial_size - map.len()
    }

    pub fn get_stats(&self) -> CacheStats {
        let map = self.store.lock().unwrap();
        let now = Instant::now();
        
        let mut total_hits = 0;
        let mut expired_count = 0;
        
        for entry in map.values() {
            total_hits += entry.hit_count;
            if entry.expires_at <= now {
                expired_count += 1;
            }
        }

        CacheStats {
            total_entries: map.len(),
            expired_entries: expired_count,
            total_hits,
            max_size: self.max_size,
        }
    }

    fn evict_lru(&self, map: &mut HashMap<String, CacheEntry<T>>) {
        if map.is_empty() {
            return;
        }

        // Find the least recently used entry
        let mut oldest_key = String::new();
        let mut oldest_time = Instant::now();

        for (key, entry) in map.iter() {
            if entry.last_accessed < oldest_time {
                oldest_time = entry.last_accessed;
                oldest_key = key.clone();
            }
        }

        map.remove(&oldest_key);
    }

    fn start_cleanup_thread(&self) {
        let store = Arc::clone(&self.store);
        let interval = self.cleanup_interval;

        thread::spawn(move || {
            loop {
                thread::sleep(interval);
                
                if let Ok(mut map) = store.lock() {
                    let now = Instant::now();
                    map.retain(|_, entry| entry.expires_at > now);
                }
            }
        });
    }
}

#[derive(Debug, Clone)]
pub struct CacheStats {
    pub total_entries: usize,
    pub expired_entries: usize,
    pub total_hits: u64,
    pub max_size: usize,
}

// Thread-safe cache wrapper for easier usage
pub type ThreadSafeCache<T> = Arc<Cache<T>>;

pub fn create_shared_cache<T: Clone + Send + 'static>(
    default_ttl: Duration,
    max_size: usize,
) -> ThreadSafeCache<T> {
    Arc::new(Cache::with_options(
        default_ttl,
        max_size,
        Duration::from_secs(60),
    ))
}
