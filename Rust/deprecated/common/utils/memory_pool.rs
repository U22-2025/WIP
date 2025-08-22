use std::collections::{VecDeque, HashMap};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicUsize, Ordering};

#[derive(Debug, Clone)]
pub struct MemoryStats {
    pub total_allocated: usize,
    pub total_deallocated: usize,
    pub current_usage: usize,
    pub peak_usage: usize,
    pub allocation_count: usize,
    pub deallocation_count: usize,
    pub pool_hits: usize,
    pub pool_misses: usize,
}

impl MemoryStats {
    pub fn new() -> Self {
        Self {
            total_allocated: 0,
            total_deallocated: 0,
            current_usage: 0,
            peak_usage: 0,
            allocation_count: 0,
            deallocation_count: 0,
            pool_hits: 0,
            pool_misses: 0,
        }
    }

    pub fn record_allocation(&mut self, size: usize) {
        self.total_allocated += size;
        self.current_usage += size;
        self.allocation_count += 1;
        
        if self.current_usage > self.peak_usage {
            self.peak_usage = self.current_usage;
        }
    }

    pub fn record_deallocation(&mut self, size: usize) {
        self.total_deallocated += size;
        self.current_usage = self.current_usage.saturating_sub(size);
        self.deallocation_count += 1;
    }

    pub fn record_pool_hit(&mut self) {
        self.pool_hits += 1;
    }

    pub fn record_pool_miss(&mut self) {
        self.pool_misses += 1;
    }

    pub fn pool_hit_rate(&self) -> f64 {
        let total_requests = self.pool_hits + self.pool_misses;
        if total_requests == 0 {
            0.0
        } else {
            self.pool_hits as f64 / total_requests as f64
        }
    }
}

pub struct BufferPool {
    pools: HashMap<usize, VecDeque<Vec<u8>>>,
    max_buffers_per_size: usize,
    stats: MemoryStats,
    last_cleanup: Instant,
    cleanup_interval: Duration,
}

impl BufferPool {
    pub fn new(max_buffers_per_size: usize) -> Self {
        Self {
            pools: HashMap::new(),
            max_buffers_per_size,
            stats: MemoryStats::new(),
            last_cleanup: Instant::now(),
            cleanup_interval: Duration::from_secs(300), // 5 minutes
        }
    }

    pub fn get_buffer(&mut self, size: usize) -> Vec<u8> {
        self.cleanup_if_needed();
        
        let pool_size = self.round_up_to_power_of_two(size);
        
        if let Some(pool) = self.pools.get_mut(&pool_size) {
            if let Some(mut buffer) = pool.pop_front() {
                buffer.clear();
                buffer.reserve(size);
                self.stats.record_pool_hit();
                return buffer;
            }
        }

        self.stats.record_pool_miss();
        self.stats.record_allocation(pool_size);
        
        let mut buffer = Vec::with_capacity(pool_size);
        buffer.reserve(size);
        buffer
    }

    pub fn return_buffer(&mut self, buffer: Vec<u8>) {
        let capacity = buffer.capacity();
        let pool_size = self.round_up_to_power_of_two(capacity);
        
        if capacity > 0 && capacity <= 1024 * 1024 { // Only pool buffers up to 1MB
            let pool = self.pools.entry(pool_size).or_insert_with(VecDeque::new);
            
            if pool.len() < self.max_buffers_per_size {
                pool.push_back(buffer);
                return;
            }
        }
        
        // Buffer is dropped here, record deallocation
        self.stats.record_deallocation(capacity);
    }

    pub fn get_stats(&self) -> &MemoryStats {
        &self.stats
    }

    pub fn clear(&mut self) {
        for (size, pool) in &self.pools {
            let count = pool.len();
            self.stats.record_deallocation(size * count);
        }
        self.pools.clear();
    }

    fn cleanup_if_needed(&mut self) {
        if self.last_cleanup.elapsed() >= self.cleanup_interval {
            self.cleanup_old_buffers();
            self.last_cleanup = Instant::now();
        }
    }

    fn cleanup_old_buffers(&mut self) {
        // Remove half the buffers from each pool to prevent indefinite growth
        for pool in self.pools.values_mut() {
            let remove_count = pool.len() / 2;
            for _ in 0..remove_count {
                if let Some(buffer) = pool.pop_back() {
                    self.stats.record_deallocation(buffer.capacity());
                }
            }
        }
    }

    fn round_up_to_power_of_two(&self, size: usize) -> usize {
        if size == 0 {
            return 8; // Minimum buffer size
        }
        size.next_power_of_two().max(8)
    }
}

// Thread-safe wrapper for BufferPool
pub struct ThreadSafeBufferPool {
    inner: Arc<Mutex<BufferPool>>,
}

impl ThreadSafeBufferPool {
    pub fn new(max_buffers_per_size: usize) -> Self {
        Self {
            inner: Arc::new(Mutex::new(BufferPool::new(max_buffers_per_size))),
        }
    }

    pub fn get_buffer(&self, size: usize) -> Vec<u8> {
        self.inner.lock().unwrap().get_buffer(size)
    }

    pub fn return_buffer(&self, buffer: Vec<u8>) {
        self.inner.lock().unwrap().return_buffer(buffer);
    }

    pub fn get_stats(&self) -> MemoryStats {
        self.inner.lock().unwrap().get_stats().clone()
    }

    pub fn clear(&self) {
        self.inner.lock().unwrap().clear();
    }
}

impl Clone for ThreadSafeBufferPool {
    fn clone(&self) -> Self {
        Self {
            inner: Arc::clone(&self.inner),
        }
    }
}

// Zero-copy buffer management for packet processing
pub struct ZeroCopyBuffer {
    data: Vec<u8>,
    start: usize,
    len: usize,
}

impl ZeroCopyBuffer {
    pub fn new(data: Vec<u8>) -> Self {
        let len = data.len();
        Self {
            data,
            start: 0,
            len,
        }
    }

    pub fn from_slice(slice: &[u8]) -> Self {
        Self::new(slice.to_vec())
    }

    pub fn slice(&self, start: usize, len: usize) -> Option<ZeroCopyBuffer> {
        if start + len <= self.len {
            Some(ZeroCopyBuffer {
                data: self.data.clone(), // This could be optimized with Rc<Vec<u8>>
                start: self.start + start,
                len,
            })
        } else {
            None
        }
    }

    pub fn as_slice(&self) -> &[u8] {
        &self.data[self.start..self.start + self.len]
    }

    pub fn len(&self) -> usize {
        self.len
    }

    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    pub fn advance(&mut self, n: usize) {
        let advance = n.min(self.len);
        self.start += advance;
        self.len -= advance;
    }

    pub fn remaining(&self) -> usize {
        self.len
    }
}

// Memory leak detection for debugging
pub struct MemoryTracker {
    allocations: Arc<Mutex<HashMap<usize, (usize, Instant, String)>>>,
    total_allocated: AtomicUsize,
    total_deallocated: AtomicUsize,
    enabled: bool,
}

impl MemoryTracker {
    pub fn new(enabled: bool) -> Self {
        Self {
            allocations: Arc::new(Mutex::new(HashMap::new())),
            total_allocated: AtomicUsize::new(0),
            total_deallocated: AtomicUsize::new(0),
            enabled,
        }
    }

    pub fn track_allocation(&self, ptr: usize, size: usize, location: String) {
        if !self.enabled {
            return;
        }

        self.total_allocated.fetch_add(size, Ordering::Relaxed);
        
        if let Ok(mut allocs) = self.allocations.lock() {
            allocs.insert(ptr, (size, Instant::now(), location));
        }
    }

    pub fn track_deallocation(&self, ptr: usize) -> Option<usize> {
        if !self.enabled {
            return None;
        }

        if let Ok(mut allocs) = self.allocations.lock() {
            if let Some((size, _, _)) = allocs.remove(&ptr) {
                self.total_deallocated.fetch_add(size, Ordering::Relaxed);
                return Some(size);
            }
        }
        None
    }

    pub fn get_current_usage(&self) -> usize {
        self.total_allocated.load(Ordering::Relaxed) - 
        self.total_deallocated.load(Ordering::Relaxed)
    }

    pub fn get_leak_report(&self) -> Vec<(usize, usize, Duration, String)> {
        if !self.enabled {
            return Vec::new();
        }

        let now = Instant::now();
        if let Ok(allocs) = self.allocations.lock() {
            allocs.iter()
                .map(|(ptr, (size, time, location))| {
                    (*ptr, *size, now.duration_since(*time), location.clone())
                })
                .collect()
        } else {
            Vec::new()
        }
    }

    pub fn clear(&self) {
        if let Ok(mut allocs) = self.allocations.lock() {
            allocs.clear();
        }
        self.total_allocated.store(0, Ordering::Relaxed);
        self.total_deallocated.store(0, Ordering::Relaxed);
    }
}

// Global memory pool instance
lazy_static::lazy_static! {
    pub static ref GLOBAL_BUFFER_POOL: ThreadSafeBufferPool = 
        ThreadSafeBufferPool::new(10); // Max 10 buffers per size class

    pub static ref GLOBAL_MEMORY_TRACKER: MemoryTracker = 
        MemoryTracker::new(cfg!(debug_assertions));
}

// Convenience functions
pub fn get_buffer(size: usize) -> Vec<u8> {
    GLOBAL_BUFFER_POOL.get_buffer(size)
}

pub fn return_buffer(buffer: Vec<u8>) {
    GLOBAL_BUFFER_POOL.return_buffer(buffer);
}

pub fn get_memory_stats() -> MemoryStats {
    GLOBAL_BUFFER_POOL.get_stats()
}

// RAII buffer wrapper that automatically returns to pool
pub struct PooledBuffer {
    buffer: Option<Vec<u8>>,
    pool: ThreadSafeBufferPool,
}

impl PooledBuffer {
    pub fn new(size: usize, pool: ThreadSafeBufferPool) -> Self {
        let buffer = pool.get_buffer(size);
        Self {
            buffer: Some(buffer),
            pool,
        }
    }

    pub fn as_mut(&mut self) -> Option<&mut Vec<u8>> {
        self.buffer.as_mut()
    }

    pub fn as_slice(&self) -> Option<&[u8]> {
        self.buffer.as_ref().map(|b| b.as_slice())
    }

    pub fn len(&self) -> usize {
        self.buffer.as_ref().map(|b| b.len()).unwrap_or(0)
    }

    pub fn capacity(&self) -> usize {
        self.buffer.as_ref().map(|b| b.capacity()).unwrap_or(0)
    }
}

impl Drop for PooledBuffer {
    fn drop(&mut self) {
        if let Some(buffer) = self.buffer.take() {
            self.pool.return_buffer(buffer);
        }
    }
}