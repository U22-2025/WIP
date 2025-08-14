use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};

pub struct Cache<T: Clone> {
    store: Mutex<HashMap<String, (T, Instant)>>,
    default_ttl: Duration,
}

impl<T: Clone> Cache<T> {
    pub fn new(default_ttl: Duration) -> Self {
        Self {
            store: Mutex::new(HashMap::new()),
            default_ttl,
        }
    }

    pub fn set(&self, key: &str, value: T, ttl: Option<Duration>) {
        let mut map = self.store.lock().unwrap();
        let expire = Instant::now() + ttl.unwrap_or(self.default_ttl);
        map.insert(key.to_string(), (value, expire));
    }

    pub fn get(&self, key: &str) -> Option<T> {
        let mut map = self.store.lock().unwrap();
        if let Some((val, exp)) = map.get(key) {
            if Instant::now() <= *exp {
                return Some(val.clone());
            } else {
                map.remove(key);
            }
        }
        None
    }

    pub fn delete(&self, key: &str) {
        self.store.lock().unwrap().remove(key);
    }

    pub fn clear(&self) {
        self.store.lock().unwrap().clear();
    }

    pub fn size(&self) -> usize {
        self.store.lock().unwrap().len()
    }
}
