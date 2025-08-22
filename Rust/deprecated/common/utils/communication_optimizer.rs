use std::collections::{HashMap, VecDeque};
use std::sync::{Arc, Mutex, RwLock};
use std::time::{Duration, Instant};
use tokio::sync::{Semaphore, SemaphorePermit};
use tokio::time::{sleep, timeout};
use crate::common::utils::memory_pool::{ThreadSafeBufferPool, get_buffer, return_buffer};

#[derive(Debug, Clone)]
pub struct CompressionStats {
    pub total_compressed: u64,
    pub total_uncompressed: u64,
    pub compression_ratio: f64,
    pub compression_time: Duration,
    pub decompression_time: Duration,
}

impl CompressionStats {
    pub fn new() -> Self {
        Self {
            total_compressed: 0,
            total_uncompressed: 0,
            compression_ratio: 1.0,
            compression_time: Duration::ZERO,
            decompression_time: Duration::ZERO,
        }
    }

    pub fn update_compression(&mut self, original_size: usize, compressed_size: usize, time: Duration) {
        self.total_uncompressed += original_size as u64;
        self.total_compressed += compressed_size as u64;
        self.compression_time += time;
        
        if self.total_uncompressed > 0 {
            self.compression_ratio = self.total_compressed as f64 / self.total_uncompressed as f64;
        }
    }

    pub fn update_decompression(&mut self, time: Duration) {
        self.decompression_time += time;
    }

    pub fn space_saved(&self) -> u64 {
        self.total_uncompressed.saturating_sub(self.total_compressed)
    }

    pub fn space_saved_percentage(&self) -> f64 {
        if self.total_uncompressed > 0 {
            (self.space_saved() as f64 / self.total_uncompressed as f64) * 100.0
        } else {
            0.0
        }
    }
}

pub struct PacketCompressor {
    compression_threshold: usize,
    stats: Arc<Mutex<CompressionStats>>,
}

impl PacketCompressor {
    pub fn new(compression_threshold: usize) -> Self {
        Self {
            compression_threshold,
            stats: Arc::new(Mutex::new(CompressionStats::new())),
        }
    }

    pub fn compress(&self, data: &[u8]) -> Result<Vec<u8>, String> {
        if data.len() < self.compression_threshold {
            return Ok(data.to_vec());
        }

        let start = Instant::now();
        let compressed = self.simple_compress(data)?;
        let compression_time = start.elapsed();

        if let Ok(mut stats) = self.stats.lock() {
            stats.update_compression(data.len(), compressed.len(), compression_time);
        }

        Ok(compressed)
    }

    pub fn decompress(&self, data: &[u8]) -> Result<Vec<u8>, String> {
        let start = Instant::now();
        let decompressed = self.simple_decompress(data)?;
        let decompression_time = start.elapsed();

        if let Ok(mut stats) = self.stats.lock() {
            stats.update_decompression(decompression_time);
        }

        Ok(decompressed)
    }

    pub fn get_stats(&self) -> CompressionStats {
        self.stats.lock().unwrap().clone()
    }

    // Simple RLE compression for demonstration
    // In production, you'd use a proper compression library like zstd or lz4
    fn simple_compress(&self, data: &[u8]) -> Result<Vec<u8>, String> {
        let mut compressed = Vec::new();
        let mut i = 0;
        
        while i < data.len() {
            let current = data[i];
            let mut count = 1;
            
            // Count consecutive bytes
            while i + count < data.len() && data[i + count] == current && count < 255 {
                count += 1;
            }
            
            if count >= 3 {
                // Use RLE for runs of 3 or more
                compressed.push(0xFF); // Escape marker
                compressed.push(count as u8);
                compressed.push(current);
            } else {
                // Copy literal bytes
                for j in 0..count {
                    compressed.push(data[i + j]);
                }
            }
            
            i += count;
        }
        
        Ok(compressed)
    }

    fn simple_decompress(&self, data: &[u8]) -> Result<Vec<u8>, String> {
        let mut decompressed = Vec::new();
        let mut i = 0;
        
        while i < data.len() {
            if data[i] == 0xFF && i + 2 < data.len() {
                // RLE sequence
                let count = data[i + 1] as usize;
                let value = data[i + 2];
                
                for _ in 0..count {
                    decompressed.push(value);
                }
                
                i += 3;
            } else {
                // Literal byte
                decompressed.push(data[i]);
                i += 1;
            }
        }
        
        Ok(decompressed)
    }
}

#[derive(Debug, Clone)]
pub struct BatchingConfig {
    pub max_batch_size: usize,
    pub max_batch_delay: Duration,
    pub max_pending_batches: usize,
}

impl Default for BatchingConfig {
    fn default() -> Self {
        Self {
            max_batch_size: 10,
            max_batch_delay: Duration::from_millis(100),
            max_pending_batches: 5,
        }
    }
}

pub struct PacketBatcher<T> {
    config: BatchingConfig,
    pending_batch: Arc<Mutex<Vec<T>>>,
    batch_start_time: Arc<Mutex<Option<Instant>>>,
    buffer_pool: ThreadSafeBufferPool,
}

impl<T: Clone + Send + 'static> PacketBatcher<T> {
    pub fn new(config: BatchingConfig, buffer_pool: ThreadSafeBufferPool) -> Self {
        Self {
            config,
            pending_batch: Arc::new(Mutex::new(Vec::new())),
            batch_start_time: Arc::new(Mutex::new(None)),
            buffer_pool,
        }
    }

    pub async fn add_packet(&self, packet: T) -> Option<Vec<T>> {
        let mut batch = self.pending_batch.lock().unwrap();
        let mut start_time = self.batch_start_time.lock().unwrap();
        
        if batch.is_empty() {
            *start_time = Some(Instant::now());
        }
        
        batch.push(packet);
        
        // Check if we should flush the batch
        let should_flush = batch.len() >= self.config.max_batch_size ||
            start_time.map(|t| t.elapsed() >= self.config.max_batch_delay).unwrap_or(false);
        
        if should_flush {
            let result = batch.clone();
            batch.clear();
            *start_time = None;
            Some(result)
        } else {
            None
        }
    }

    pub async fn flush(&self) -> Option<Vec<T>> {
        let mut batch = self.pending_batch.lock().unwrap();
        let mut start_time = self.batch_start_time.lock().unwrap();
        
        if !batch.is_empty() {
            let result = batch.clone();
            batch.clear();
            *start_time = None;
            Some(result)
        } else {
            None
        }
    }

    pub fn pending_count(&self) -> usize {
        self.pending_batch.lock().unwrap().len()
    }
}

#[derive(Debug, Clone)]
pub struct ConcurrencyConfig {
    pub max_concurrent_requests: usize,
    pub request_timeout: Duration,
    pub connection_pool_size: usize,
    pub backpressure_threshold: usize,
}

impl Default for ConcurrencyConfig {
    fn default() -> Self {
        Self {
            max_concurrent_requests: 100,
            request_timeout: Duration::from_secs(30),
            connection_pool_size: 10,
            backpressure_threshold: 200,
        }
    }
}

pub struct ConcurrencyManager {
    config: ConcurrencyConfig,
    semaphore: Arc<Semaphore>,
    active_requests: Arc<RwLock<HashMap<u64, Instant>>>,
    request_counter: Arc<Mutex<u64>>,
}

impl ConcurrencyManager {
    pub fn new(config: ConcurrencyConfig) -> Self {
        Self {
            semaphore: Arc::new(Semaphore::new(config.max_concurrent_requests)),
            config,
            active_requests: Arc::new(RwLock::new(HashMap::new())),
            request_counter: Arc::new(Mutex::new(0)),
        }
    }

    pub async fn acquire_request_slot(&self) -> Result<RequestGuard<'_>, String> {
        // Check backpressure
        if self.active_request_count() >= self.config.backpressure_threshold {
            return Err("Too many active requests (backpressure)".to_string());
        }

        let permit = self.semaphore.acquire().await
            .map_err(|_| "Failed to acquire semaphore permit")?;

        let request_id = {
            let mut counter = self.request_counter.lock().unwrap();
            *counter += 1;
            *counter
        };

        // Track request start time
        {
            let mut active = self.active_requests.write().unwrap();
            active.insert(request_id, Instant::now());
        }

        Ok(RequestGuard {
            request_id,
            _permit: permit,
            active_requests: Arc::clone(&self.active_requests),
        })
    }

    pub fn active_request_count(&self) -> usize {
        self.active_requests.read().unwrap().len()
    }

    pub fn get_request_stats(&self) -> RequestStats {
        let active = self.active_requests.read().unwrap();
        let now = Instant::now();
        
        let mut total_duration = Duration::ZERO;
        let mut min_duration = Duration::MAX;
        let mut max_duration = Duration::ZERO;
        
        for &start_time in active.values() {
            let duration = now.duration_since(start_time);
            total_duration += duration;
            min_duration = min_duration.min(duration);
            max_duration = max_duration.max(duration);
        }
        
        let count = active.len();
        let avg_duration = if count > 0 {
            total_duration / count as u32
        } else {
            Duration::ZERO
        };

        RequestStats {
            active_requests: count,
            avg_request_duration: avg_duration,
            min_request_duration: if count > 0 { min_duration } else { Duration::ZERO },
            max_request_duration: max_duration,
        }
    }

    pub async fn cleanup_timed_out_requests(&self) {
        let mut active = self.active_requests.write().unwrap();
        let now = Instant::now();
        
        active.retain(|_, &mut start_time| {
            now.duration_since(start_time) < self.config.request_timeout
        });
    }
}

pub struct RequestGuard<'a> {
    request_id: u64,
    _permit: SemaphorePermit<'a>,
    active_requests: Arc<RwLock<HashMap<u64, Instant>>>,
}

impl<'a> Drop for RequestGuard<'a> {
    fn drop(&mut self) {
        let mut active = self.active_requests.write().unwrap();
        active.remove(&self.request_id);
    }
}

#[derive(Debug, Clone)]
pub struct RequestStats {
    pub active_requests: usize,
    pub avg_request_duration: Duration,
    pub min_request_duration: Duration,
    pub max_request_duration: Duration,
}

pub struct AdaptiveConcurrencyController {
    base_concurrency: usize,
    current_concurrency: Arc<Mutex<usize>>,
    success_rate_window: Arc<Mutex<VecDeque<bool>>>,
    window_size: usize,
    target_success_rate: f64,
    adjustment_factor: f64,
}

impl AdaptiveConcurrencyController {
    pub fn new(base_concurrency: usize, target_success_rate: f64) -> Self {
        Self {
            base_concurrency,
            current_concurrency: Arc::new(Mutex::new(base_concurrency)),
            success_rate_window: Arc::new(Mutex::new(VecDeque::new())),
            window_size: 100,
            target_success_rate,
            adjustment_factor: 0.1,
        }
    }

    pub fn record_result(&self, success: bool) {
        let mut window = self.success_rate_window.lock().unwrap();
        window.push_back(success);
        
        if window.len() > self.window_size {
            window.pop_front();
        }

        // Adjust concurrency based on success rate
        if window.len() >= self.window_size {
            let success_count = window.iter().filter(|&&s| s).count();
            let success_rate = success_count as f64 / window.len() as f64;
            
            let mut current = self.current_concurrency.lock().unwrap();
            
            if success_rate < self.target_success_rate {
                // Decrease concurrency
                let new_concurrency = (*current as f64 * (1.0 - self.adjustment_factor)).max(1.0) as usize;
                *current = new_concurrency;
            } else if success_rate > self.target_success_rate + 0.05 {
                // Increase concurrency (with some hysteresis)
                let new_concurrency = (*current as f64 * (1.0 + self.adjustment_factor)) as usize;
                *current = new_concurrency.min(self.base_concurrency * 2);
            }
        }
    }

    pub fn get_current_concurrency(&self) -> usize {
        *self.current_concurrency.lock().unwrap()
    }

    pub fn get_success_rate(&self) -> f64 {
        let window = self.success_rate_window.lock().unwrap();
        if window.is_empty() {
            return 1.0;
        }

        let success_count = window.iter().filter(|&&s| s).count();
        success_count as f64 / window.len() as f64
    }
}

#[derive(Debug, Clone)]
pub struct CommunicationStats {
    pub compression_stats: CompressionStats,
    pub request_stats: RequestStats,
    pub batching_efficiency: f64,
    pub adaptive_concurrency: usize,
    pub success_rate: f64,
}

pub struct CommunicationOptimizer {
    compressor: PacketCompressor,
    concurrency_manager: ConcurrencyManager,
    adaptive_controller: AdaptiveConcurrencyController,
    buffer_pool: ThreadSafeBufferPool,
}

impl CommunicationOptimizer {
    pub fn new(
        compression_threshold: usize,
        concurrency_config: ConcurrencyConfig,
        target_success_rate: f64,
        buffer_pool: ThreadSafeBufferPool,
    ) -> Self {
        Self {
            compressor: PacketCompressor::new(compression_threshold),
            concurrency_manager: ConcurrencyManager::new(concurrency_config.clone()),
            adaptive_controller: AdaptiveConcurrencyController::new(
                concurrency_config.max_concurrent_requests,
                target_success_rate,
            ),
            buffer_pool,
        }
    }

    pub async fn optimize_request(&self, data: &[u8]) -> Result<(Vec<u8>, RequestGuard<'_>), String> {
        // Acquire concurrency slot
        let guard = self.concurrency_manager.acquire_request_slot().await?;
        
        // Compress data if beneficial
        let optimized_data = self.compressor.compress(data)?;
        
        Ok((optimized_data, guard))
    }

    pub fn optimize_response(&self, data: &[u8]) -> Result<Vec<u8>, String> {
        // Decompress response data
        self.compressor.decompress(data)
    }

    pub fn record_request_result(&self, success: bool) {
        self.adaptive_controller.record_result(success);
    }

    pub fn get_communication_stats(&self) -> CommunicationStats {
        CommunicationStats {
            compression_stats: self.compressor.get_stats(),
            request_stats: self.concurrency_manager.get_request_stats(),
            batching_efficiency: 0.0, // Would be calculated from batcher stats
            adaptive_concurrency: self.adaptive_controller.get_current_concurrency(),
            success_rate: self.adaptive_controller.get_success_rate(),
        }
    }

    pub async fn cleanup(&self) {
        self.concurrency_manager.cleanup_timed_out_requests().await;
    }
}