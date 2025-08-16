use std::collections::{HashMap, VecDeque};
use std::sync::{Arc, Mutex, RwLock};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use serde::{Serialize, Deserialize};
use tokio::time::interval;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TimingMetric {
    pub count: u64,
    pub total_duration: Duration,
    pub min_duration: Duration,
    pub max_duration: Duration,
    pub avg_duration: Duration,
    pub p50: Duration,
    pub p95: Duration,
    pub p99: Duration,
}

impl TimingMetric {
    pub fn new() -> Self {
        Self {
            count: 0,
            total_duration: Duration::ZERO,
            min_duration: Duration::MAX,
            max_duration: Duration::ZERO,
            avg_duration: Duration::ZERO,
            p50: Duration::ZERO,
            p95: Duration::ZERO,
            p99: Duration::ZERO,
        }
    }

    pub fn record(&mut self, duration: Duration) {
        self.count += 1;
        self.total_duration += duration;
        self.min_duration = self.min_duration.min(duration);
        self.max_duration = self.max_duration.max(duration);
        
        if self.count > 0 {
            self.avg_duration = self.total_duration / self.count as u32;
        }
    }

    pub fn calculate_percentiles(&mut self, durations: &[Duration]) {
        if durations.is_empty() {
            return;
        }

        let mut sorted = durations.to_vec();
        sorted.sort();

        let len = sorted.len();
        self.p50 = sorted[len * 50 / 100];
        self.p95 = sorted[len * 95 / 100];
        self.p99 = sorted[len * 99 / 100];
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CounterMetric {
    pub value: u64,
    pub rate: f64, // per second
    pub last_update: u64,
}

impl CounterMetric {
    pub fn new() -> Self {
        Self {
            value: 0,
            rate: 0.0,
            last_update: Self::current_timestamp(),
        }
    }

    pub fn increment(&mut self) {
        self.increment_by(1);
    }

    pub fn increment_by(&mut self, amount: u64) {
        let now = Self::current_timestamp();
        let time_diff = now.saturating_sub(self.last_update);
        
        if time_diff > 0 {
            self.rate = amount as f64 / (time_diff as f64 / 1000.0);
        }
        
        self.value += amount;
        self.last_update = now;
    }

    pub fn reset(&mut self) {
        self.value = 0;
        self.rate = 0.0;
        self.last_update = Self::current_timestamp();
    }

    fn current_timestamp() -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GaugeMetric {
    pub value: f64,
    pub min_value: f64,
    pub max_value: f64,
    pub last_update: u64,
}

impl GaugeMetric {
    pub fn new() -> Self {
        Self {
            value: 0.0,
            min_value: f64::MAX,
            max_value: f64::MIN,
            last_update: Self::current_timestamp(),
        }
    }

    pub fn set(&mut self, value: f64) {
        self.value = value;
        self.min_value = self.min_value.min(value);
        self.max_value = self.max_value.max(value);
        self.last_update = Self::current_timestamp();
    }

    pub fn add(&mut self, delta: f64) {
        self.set(self.value + delta);
    }

    pub fn subtract(&mut self, delta: f64) {
        self.set(self.value - delta);
    }

    fn current_timestamp() -> u64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistogramMetric {
    pub buckets: HashMap<String, u64>, // bucket_name -> count
    pub total_count: u64,
    pub sum: f64,
}

impl HistogramMetric {
    pub fn new(bucket_boundaries: Vec<f64>) -> Self {
        let mut buckets = HashMap::new();
        
        for boundary in bucket_boundaries {
            buckets.insert(format!("le_{}", boundary), 0);
        }
        buckets.insert("le_inf".to_string(), 0);

        Self {
            buckets,
            total_count: 0,
            sum: 0.0,
        }
    }

    pub fn observe(&mut self, value: f64) {
        self.total_count += 1;
        self.sum += value;

        // Find appropriate buckets
        let bucket_keys: Vec<String> = self.buckets.keys()
            .filter(|k| k.starts_with("le_"))
            .cloned()
            .collect();
        let mut sorted_keys = bucket_keys;
        sorted_keys.sort();

        for bucket_key in sorted_keys {
            if bucket_key == "le_inf" {
                *self.buckets.get_mut(&bucket_key).unwrap() += 1;
                break;
            }

            if let Some(boundary_str) = bucket_key.strip_prefix("le_") {
                if let Ok(boundary) = boundary_str.parse::<f64>() {
                    if value <= boundary {
                        *self.buckets.get_mut(&bucket_key).unwrap() += 1;
                        break;
                    }
                }
            }
        }
    }

    pub fn average(&self) -> f64 {
        if self.total_count > 0 {
            self.sum / self.total_count as f64
        } else {
            0.0
        }
    }
}

#[derive(Debug, Clone)]
pub struct MetricsSnapshot {
    pub timestamp: u64,
    pub counters: HashMap<String, CounterMetric>,
    pub gauges: HashMap<String, GaugeMetric>,
    pub timings: HashMap<String, TimingMetric>,
    pub histograms: HashMap<String, HistogramMetric>,
}

impl MetricsSnapshot {
    pub fn new() -> Self {
        Self {
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis() as u64,
            counters: HashMap::new(),
            gauges: HashMap::new(),
            timings: HashMap::new(),
            histograms: HashMap::new(),
        }
    }
}

pub struct MetricsCollector {
    counters: Arc<RwLock<HashMap<String, CounterMetric>>>,
    gauges: Arc<RwLock<HashMap<String, GaugeMetric>>>,
    timings: Arc<RwLock<HashMap<String, TimingMetric>>>,
    histograms: Arc<RwLock<HashMap<String, HistogramMetric>>>,
    timing_samples: Arc<Mutex<HashMap<String, VecDeque<Duration>>>>,
    max_samples: usize,
}

impl MetricsCollector {
    pub fn new(max_samples: usize) -> Self {
        Self {
            counters: Arc::new(RwLock::new(HashMap::new())),
            gauges: Arc::new(RwLock::new(HashMap::new())),
            timings: Arc::new(RwLock::new(HashMap::new())),
            histograms: Arc::new(RwLock::new(HashMap::new())),
            timing_samples: Arc::new(Mutex::new(HashMap::new())),
            max_samples,
        }
    }

    pub fn increment_counter(&self, name: &str) {
        self.increment_counter_by(name, 1);
    }

    pub fn increment_counter_by(&self, name: &str, amount: u64) {
        let mut counters = self.counters.write().unwrap();
        let counter = counters.entry(name.to_string()).or_insert_with(CounterMetric::new);
        counter.increment_by(amount);
    }

    pub fn set_gauge(&self, name: &str, value: f64) {
        let mut gauges = self.gauges.write().unwrap();
        let gauge = gauges.entry(name.to_string()).or_insert_with(GaugeMetric::new);
        gauge.set(value);
    }

    pub fn add_to_gauge(&self, name: &str, delta: f64) {
        let mut gauges = self.gauges.write().unwrap();
        let gauge = gauges.entry(name.to_string()).or_insert_with(GaugeMetric::new);
        gauge.add(delta);
    }

    pub fn record_timing(&self, name: &str, duration: Duration) {
        // Update timing metric
        {
            let mut timings = self.timings.write().unwrap();
            let timing = timings.entry(name.to_string()).or_insert_with(TimingMetric::new);
            timing.record(duration);
        }

        // Store sample for percentile calculation
        {
            let mut samples = self.timing_samples.lock().unwrap();
            let sample_list = samples.entry(name.to_string()).or_insert_with(VecDeque::new);
            
            sample_list.push_back(duration);
            if sample_list.len() > self.max_samples {
                sample_list.pop_front();
            }
        }
    }

    pub fn observe_histogram(&self, name: &str, value: f64) {
        let mut histograms = self.histograms.write().unwrap();
        if let Some(histogram) = histograms.get_mut(name) {
            histogram.observe(value);
        }
    }

    pub fn create_histogram(&self, name: &str, bucket_boundaries: Vec<f64>) {
        let mut histograms = self.histograms.write().unwrap();
        histograms.insert(name.to_string(), HistogramMetric::new(bucket_boundaries));
    }

    pub fn get_snapshot(&self) -> MetricsSnapshot {
        // Calculate percentiles before snapshot
        self.calculate_percentiles();

        let counters = self.counters.read().unwrap().clone();
        let gauges = self.gauges.read().unwrap().clone();
        let timings = self.timings.read().unwrap().clone();
        let histograms = self.histograms.read().unwrap().clone();

        MetricsSnapshot {
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis() as u64,
            counters,
            gauges,
            timings,
            histograms,
        }
    }

    pub fn reset_all(&self) {
        self.counters.write().unwrap().clear();
        self.gauges.write().unwrap().clear();
        self.timings.write().unwrap().clear();
        self.histograms.write().unwrap().clear();
        self.timing_samples.lock().unwrap().clear();
    }

    pub fn reset_metric(&self, name: &str) {
        self.counters.write().unwrap().remove(name);
        self.gauges.write().unwrap().remove(name);
        self.timings.write().unwrap().remove(name);
        self.histograms.write().unwrap().remove(name);
        self.timing_samples.lock().unwrap().remove(name);
    }

    fn calculate_percentiles(&self) {
        let samples = self.timing_samples.lock().unwrap();
        let mut timings = self.timings.write().unwrap();

        for (name, sample_list) in samples.iter() {
            if let Some(timing) = timings.get_mut(name) {
                let durations: Vec<Duration> = sample_list.iter().cloned().collect();
                timing.calculate_percentiles(&durations);
            }
        }
    }
}

// Python版WIPクライアントに基づく通信メトリクス
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommunicationMetrics {
    pub requests_total: u64,
    pub requests_successful: u64,
    pub requests_failed: u64,
    pub bytes_sent: u64,
    pub bytes_received: u64,
    pub response_time: TimingMetric,
    pub connection_time: TimingMetric,
    pub cache_hits: u64,
    pub cache_misses: u64,
    pub retry_attempts: u64,
    pub circuit_breaker_opens: u64,
}

impl CommunicationMetrics {
    pub fn new() -> Self {
        Self {
            requests_total: 0,
            requests_successful: 0,
            requests_failed: 0,
            bytes_sent: 0,
            bytes_received: 0,
            response_time: TimingMetric::new(),
            connection_time: TimingMetric::new(),
            cache_hits: 0,
            cache_misses: 0,
            retry_attempts: 0,
            circuit_breaker_opens: 0,
        }
    }

    pub fn success_rate(&self) -> f64 {
        if self.requests_total > 0 {
            self.requests_successful as f64 / self.requests_total as f64
        } else {
            1.0
        }
    }

    pub fn cache_hit_rate(&self) -> f64 {
        let total_cache_requests = self.cache_hits + self.cache_misses;
        if total_cache_requests > 0 {
            self.cache_hits as f64 / total_cache_requests as f64
        } else {
            0.0
        }
    }

    pub fn average_retry_rate(&self) -> f64 {
        if self.requests_total > 0 {
            self.retry_attempts as f64 / self.requests_total as f64
        } else {
            0.0
        }
    }
}

pub struct CommunicationMetricsCollector {
    metrics: Arc<Mutex<CommunicationMetrics>>,
    response_times: Arc<Mutex<VecDeque<Duration>>>,
    connection_times: Arc<Mutex<VecDeque<Duration>>>,
    max_samples: usize,
}

impl CommunicationMetricsCollector {
    pub fn new(max_samples: usize) -> Self {
        Self {
            metrics: Arc::new(Mutex::new(CommunicationMetrics::new())),
            response_times: Arc::new(Mutex::new(VecDeque::new())),
            connection_times: Arc::new(Mutex::new(VecDeque::new())),
            max_samples,
        }
    }

    pub fn record_request(&self, success: bool, bytes_sent: u64, bytes_received: u64) {
        let mut metrics = self.metrics.lock().unwrap();
        metrics.requests_total += 1;
        metrics.bytes_sent += bytes_sent;
        metrics.bytes_received += bytes_received;

        if success {
            metrics.requests_successful += 1;
        } else {
            metrics.requests_failed += 1;
        }
    }

    pub fn record_response_time(&self, duration: Duration) {
        let mut metrics = self.metrics.lock().unwrap();
        metrics.response_time.record(duration);

        let mut times = self.response_times.lock().unwrap();
        times.push_back(duration);
        if times.len() > self.max_samples {
            times.pop_front();
        }

        // Calculate percentiles
        let durations: Vec<Duration> = times.iter().cloned().collect();
        metrics.response_time.calculate_percentiles(&durations);
    }

    pub fn record_connection_time(&self, duration: Duration) {
        let mut metrics = self.metrics.lock().unwrap();
        metrics.connection_time.record(duration);

        let mut times = self.connection_times.lock().unwrap();
        times.push_back(duration);
        if times.len() > self.max_samples {
            times.pop_front();
        }

        let durations: Vec<Duration> = times.iter().cloned().collect();
        metrics.connection_time.calculate_percentiles(&durations);
    }

    pub fn record_cache_hit(&self) {
        let mut metrics = self.metrics.lock().unwrap();
        metrics.cache_hits += 1;
    }

    pub fn record_cache_miss(&self) {
        let mut metrics = self.metrics.lock().unwrap();
        metrics.cache_misses += 1;
    }

    pub fn record_retry(&self) {
        let mut metrics = self.metrics.lock().unwrap();
        metrics.retry_attempts += 1;
    }

    pub fn record_circuit_breaker_open(&self) {
        let mut metrics = self.metrics.lock().unwrap();
        metrics.circuit_breaker_opens += 1;
    }

    pub fn get_metrics(&self) -> CommunicationMetrics {
        self.metrics.lock().unwrap().clone()
    }

    pub fn reset(&self) {
        *self.metrics.lock().unwrap() = CommunicationMetrics::new();
        self.response_times.lock().unwrap().clear();
        self.connection_times.lock().unwrap().clear();
    }
}

// メトリクスエクスポーター（Prometheusフォーマット）
pub struct PrometheusExporter {
    metrics_collector: Arc<MetricsCollector>,
    communication_metrics: Arc<CommunicationMetricsCollector>,
}

impl PrometheusExporter {
    pub fn new(
        metrics_collector: Arc<MetricsCollector>,
        communication_metrics: Arc<CommunicationMetricsCollector>,
    ) -> Self {
        Self {
            metrics_collector,
            communication_metrics,
        }
    }

    pub fn export(&self) -> String {
        let mut output = Vec::new();
        let snapshot = self.metrics_collector.get_snapshot();
        let comm_metrics = self.communication_metrics.get_metrics();

        // Export counters
        for (name, counter) in &snapshot.counters {
            output.push(format!("# TYPE {} counter", name));
            output.push(format!("{} {}", name, counter.value));
            output.push(format!("{}_rate {}", name, counter.rate));
        }

        // Export gauges
        for (name, gauge) in &snapshot.gauges {
            output.push(format!("# TYPE {} gauge", name));
            output.push(format!("{} {}", name, gauge.value));
        }

        // Export timing metrics
        for (name, timing) in &snapshot.timings {
            output.push(format!("# TYPE {}_duration_seconds histogram", name));
            output.push(format!("{}_duration_seconds_count {}", name, timing.count));
            output.push(format!("{}_duration_seconds_sum {}", name, timing.total_duration.as_secs_f64()));
            output.push(format!("{}_duration_seconds_min {}", name, timing.min_duration.as_secs_f64()));
            output.push(format!("{}_duration_seconds_max {}", name, timing.max_duration.as_secs_f64()));
            output.push(format!("{}_duration_seconds_avg {}", name, timing.avg_duration.as_secs_f64()));
        }

        // Export communication metrics
        output.push("# Communication Metrics".to_string());
        output.push(format!("wip_requests_total {}", comm_metrics.requests_total));
        output.push(format!("wip_requests_successful {}", comm_metrics.requests_successful));
        output.push(format!("wip_requests_failed {}", comm_metrics.requests_failed));
        output.push(format!("wip_success_rate {}", comm_metrics.success_rate()));
        output.push(format!("wip_bytes_sent_total {}", comm_metrics.bytes_sent));
        output.push(format!("wip_bytes_received_total {}", comm_metrics.bytes_received));
        output.push(format!("wip_cache_hits_total {}", comm_metrics.cache_hits));
        output.push(format!("wip_cache_misses_total {}", comm_metrics.cache_misses));
        output.push(format!("wip_cache_hit_rate {}", comm_metrics.cache_hit_rate()));

        output.join("\n")
    }
}

// Timer utility for measuring durations
pub struct Timer {
    start: Instant,
    name: String,
    collector: Arc<MetricsCollector>,
}

impl Timer {
    pub fn new(name: String, collector: Arc<MetricsCollector>) -> Self {
        Self {
            start: Instant::now(),
            name,
            collector,
        }
    }

    pub fn stop(self) -> Duration {
        let duration = self.start.elapsed();
        self.collector.record_timing(&self.name, duration);
        duration
    }
}

impl Drop for Timer {
    fn drop(&mut self) {
        let duration = self.start.elapsed();
        self.collector.record_timing(&self.name, duration);
    }
}

// Convenience macros
#[macro_export]
macro_rules! time_operation {
    ($collector:expr, $name:expr, $block:block) => {
        {
            let _timer = Timer::new($name.to_string(), Arc::clone($collector));
            $block
        }
    };
}

#[macro_export]
macro_rules! increment_counter {
    ($collector:expr, $name:expr) => {
        $collector.increment_counter($name);
    };
    ($collector:expr, $name:expr, $amount:expr) => {
        $collector.increment_counter_by($name, $amount);
    };
}

// Global metrics instance
lazy_static::lazy_static! {
    pub static ref GLOBAL_METRICS: Arc<MetricsCollector> = 
        Arc::new(MetricsCollector::new(1000));
    
    pub static ref GLOBAL_COMM_METRICS: Arc<CommunicationMetricsCollector> = 
        Arc::new(CommunicationMetricsCollector::new(1000));
}

// Convenience functions
pub fn get_metrics_snapshot() -> MetricsSnapshot {
    GLOBAL_METRICS.get_snapshot()
}

pub fn get_communication_metrics() -> CommunicationMetrics {
    GLOBAL_COMM_METRICS.get_metrics()
}

pub fn export_prometheus_metrics() -> String {
    let exporter = PrometheusExporter::new(
        Arc::clone(&GLOBAL_METRICS),
        Arc::clone(&GLOBAL_COMM_METRICS),
    );
    exporter.export()
}