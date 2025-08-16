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
    pub fn new(default_ttl: Duration) -> Self { Self::with_options(default_ttl, 1000, Duration::from_secs(60)) }
    pub fn with_options(default_ttl: Duration, max_size: usize, cleanup_interval: Duration) -> Self {
        let cache = Self { store: Arc::new(Mutex::new(HashMap::new())), default_ttl, max_size, cleanup_interval };
        cache.start_cleanup_thread();
        cache
    }
    pub fn set(&self, key: &str, value: T) { self.set_with_ttl(key, value, None); }
    pub fn set_with_ttl(&self, key: &str, value: T, ttl: Option<Duration>) {
        let mut map = self.store.lock().unwrap();
        let now = Instant::now();
        let expire = now + ttl.unwrap_or(self.default_ttl);
        let entry = CacheEntry { value, expires_at: expire, hit_count: 0, last_accessed: now };
        if map.len() >= self.max_size && !map.contains_key(key) { self.evict_lru(&mut map); }
        map.insert(key.to_string(), entry);
    }
    pub fn get(&self, key: &str) -> Option<T> {
        let mut map = self.store.lock().unwrap();
        if let Some(entry) = map.get_mut(key) {
            let now = Instant::now();
            if now <= entry.expires_at { entry.hit_count += 1; entry.last_accessed = now; return Some(entry.value.clone()); } else { map.remove(key); }
        }
        None
    }
    pub fn get_with_stats(&self, key: &str) -> Option<(T, u64, Instant)> {
        let mut map = self.store.lock().unwrap();
        if let Some(entry) = map.get_mut(key) {
            let now = Instant::now();
            if now <= entry.expires_at { entry.hit_count += 1; entry.last_accessed = now; return Some((entry.value.clone(), entry.hit_count, entry.last_accessed)); } else { map.remove(key); }
        }
        None
    }
    pub fn contains_key(&self, key: &str) -> bool {
        let mut map = self.store.lock().unwrap();
        if let Some(entry) = map.get(key) { if Instant::now() <= entry.expires_at { true } else { false } } else { false }
    }
    fn start_cleanup_thread(&self) {
        let store = self.store.clone();
        let interval = self.cleanup_interval;
        thread::spawn(move || loop {
            thread::sleep(interval);
            let mut map = store.lock().unwrap();
            let now = Instant::now();
            map.retain(|_, e| now <= e.expires_at);
        });
    }
    fn evict_lru(&self, map: &mut HashMap<String, CacheEntry<T>>) {
        if let Some((lru_key, _)) = map.iter().min_by_key(|(_, e)| e.last_accessed).map(|(k, v)| (k.clone(), v.last_accessed)) {
            map.remove(&lru_key);
        }
    }
}

pub type ThreadSafeCache<T> = Arc<Cache<T>>;
pub fn create_shared_cache<T: Clone + Send + 'static>(default_ttl: Duration, max_size: usize) -> ThreadSafeCache<T> {
    Arc::new(Cache::with_options(default_ttl, max_size, Duration::from_secs(60)))
}

