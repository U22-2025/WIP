use crate::wip_common_rs::clients::utils::packet_id_generator::PacketIDGenerator12Bit;
use crate::wip_common_rs::packet::types::error_response::ErrorResponse;
use crate::wip_common_rs::packet::types::report_packet::{ReportRequest, ReportResponse};
use async_trait::async_trait;
use log::{debug, error, info, warn};
use std::collections::VecDeque;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::net::UdpSocket;
use tokio::sync::{Mutex, RwLock, Semaphore};
use tokio::time::{interval, sleep, timeout, Interval};

#[derive(Debug, Clone)]
pub struct CompressionConfig {
    pub enable_compression: bool,
    pub compression_level: u32,
    pub min_size_for_compression: usize,
}

impl Default for CompressionConfig {
    fn default() -> Self {
        Self {
            enable_compression: false,
            compression_level: 6,
            min_size_for_compression: 1024,
        }
    }
}

#[derive(Debug, Clone)]
pub struct EncryptionConfig {
    pub enable_encryption: bool,
    pub encryption_key: Option<Vec<u8>>,
    pub encryption_algorithm: String,
}

impl Default for EncryptionConfig {
    fn default() -> Self {
        Self {
            enable_encryption: false,
            encryption_key: None,
            encryption_algorithm: "AES-256-GCM".to_string(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct BatchConfig {
    pub enable_batching: bool,
    pub max_batch_size: usize,
    pub max_batch_wait_time: Duration,
    pub max_batch_memory_size: usize,
}

impl Default for BatchConfig {
    fn default() -> Self {
        Self {
            enable_batching: true,
            max_batch_size: 50,
            max_batch_wait_time: Duration::from_millis(500),
            max_batch_memory_size: 1024 * 1024, // 1MB
        }
    }
}

#[derive(Debug, Clone)]
pub struct ReportClientConfig {
    pub timeout: Duration,
    pub max_concurrent_reports: usize,
    pub retry_attempts: usize,
    pub retry_delay: Duration,
    pub compression: CompressionConfig,
    pub encryption: EncryptionConfig,
    pub batching: BatchConfig,
    pub enable_debug: bool,
    pub auth_enabled: bool,
    pub auth_passphrase: Option<String>,
}

impl Default for ReportClientConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(10),
            max_concurrent_reports: 100,
            retry_attempts: 3,
            retry_delay: Duration::from_millis(500),
            compression: CompressionConfig::default(),
            encryption: EncryptionConfig::default(),
            batching: BatchConfig::default(),
            enable_debug: false,
            auth_enabled: false,
            auth_passphrase: None,
        }
    }
}

#[derive(Debug, Clone)]
pub struct PendingReport {
    pub request: ReportRequest,
    pub added_at: Instant,
    pub estimated_size: usize,
}

impl PendingReport {
    pub fn new(request: ReportRequest) -> Self {
        let estimated_size = std::mem::size_of_val(&request) + request.get_data().len();
        Self {
            request,
            added_at: Instant::now(),
            estimated_size,
        }
    }
}

#[derive(Debug, Default, Clone)]
pub struct ReportStats {
    pub total_reports: usize,
    pub successful_reports: usize,
    pub failed_reports: usize,
    pub batched_reports: usize,
    pub compressed_reports: usize,
    pub encrypted_reports: usize,
    pub retry_attempts: usize,
    pub timeouts: usize,
    pub bytes_sent: usize,
    pub bytes_compressed: usize,
}

#[async_trait]
pub trait ReportClient {
    async fn send_report(
        &self,
        report: ReportRequest,
    ) -> Result<ReportResponse, Box<dyn std::error::Error + Send + Sync>>;
    async fn send_reports_batch(
        &self,
        reports: Vec<ReportRequest>,
    ) -> Vec<Result<ReportResponse, Box<dyn std::error::Error + Send + Sync>>>;
    async fn queue_report(
        &self,
        report: ReportRequest,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>>;
    async fn flush_queued_reports(
        &self,
    ) -> Result<Vec<ReportResponse>, Box<dyn std::error::Error + Send + Sync>>;
    fn get_stats(&self) -> ReportStats;
    async fn get_queue_size(&self) -> usize;
}

#[derive(Debug)]
pub struct ReportClientImpl {
    host: String,
    port: u16,
    addr: SocketAddr,
    config: ReportClientConfig,
    socket: Arc<UdpSocket>,
    pidg: Arc<Mutex<PacketIDGenerator12Bit>>,
    semaphore: Arc<Semaphore>,
    stats: Arc<RwLock<ReportStats>>,
    pending_reports: Arc<Mutex<VecDeque<PendingReport>>>,
    batch_timer: Arc<Mutex<Option<Interval>>>,
}

impl ReportClientImpl {
    pub async fn new(host: &str, port: u16) -> tokio::io::Result<Self> {
        Self::with_config(host, port, ReportClientConfig::default()).await
    }

    pub async fn with_config(
        host: &str,
        port: u16,
        config: ReportClientConfig,
    ) -> tokio::io::Result<Self> {
        // localhostをwip.ncc.onlに解決
        let resolved_host = if host == "localhost" {
            "wip.ncc.onl"
        } else {
            host
        };

        let addr_str = format!("{}:{}", resolved_host, port);
        let addr: SocketAddr = addr_str.parse().map_err(|e| {
            tokio::io::Error::new(
                tokio::io::ErrorKind::InvalidInput,
                format!("Invalid socket address '{}': {}", addr_str, e),
            )
        })?;

        let socket = Arc::new(UdpSocket::bind("0.0.0.0:0").await?);
        let semaphore = Arc::new(Semaphore::new(config.max_concurrent_reports));

        if config.enable_debug {
            env_logger::init();
        }

        let client = Self {
            host: host.to_string(),
            port,
            addr,
            config: config.clone(),
            socket,
            pidg: Arc::new(Mutex::new(PacketIDGenerator12Bit::new())),
            semaphore,
            stats: Arc::new(RwLock::new(ReportStats::default())),
            pending_reports: Arc::new(Mutex::new(VecDeque::new())),
            batch_timer: Arc::new(Mutex::new(None)),
        };

        if config.batching.enable_batching {
            client.start_batch_processor().await;
        }

        Ok(client)
    }

    async fn start_batch_processor(&self) {
        let pending_reports = self.pending_reports.clone();
        let batch_config = self.config.batching.clone();
        let client = self.clone();

        tokio::spawn(async move {
            let mut interval = interval(batch_config.max_batch_wait_time);

            loop {
                interval.tick().await;

                let reports_to_process = {
                    let mut queue = pending_reports.lock().await;
                    let mut batch = Vec::new();
                    let mut total_size = 0;

                    while let Some(pending) = queue.pop_front() {
                        if batch.len() >= batch_config.max_batch_size
                            || total_size + pending.estimated_size
                                > batch_config.max_batch_memory_size
                        {
                            queue.push_front(pending);
                            break;
                        }

                        total_size += pending.estimated_size;
                        batch.push(pending.request);
                    }

                    batch
                };

                if !reports_to_process.is_empty() {
                    debug!("Processing batch of {} reports", reports_to_process.len());
                    let _ = client.send_reports_batch(reports_to_process).await;
                }
            }
        });
    }

    async fn generate_packet_id(&self) -> u16 {
        let mut pidg = self.pidg.lock().await;
        pidg.next_id()
    }

    async fn compress_data(
        &self,
        data: &[u8],
    ) -> Result<Vec<u8>, Box<dyn std::error::Error + Send + Sync>> {
        if !self.config.compression.enable_compression
            || data.len() < self.config.compression.min_size_for_compression
        {
            return Ok(data.to_vec());
        }

        // Placeholder for actual compression implementation
        // In a real implementation, you would use a compression library like flate2
        debug!("Compressing {} bytes of data", data.len());
        let compressed = data.to_vec(); // Placeholder - no actual compression

        let mut stats = self.stats.write().await;
        stats.compressed_reports += 1;
        stats.bytes_compressed += data.len() - compressed.len();

        Ok(compressed)
    }

    async fn encrypt_data(
        &self,
        data: &[u8],
    ) -> Result<Vec<u8>, Box<dyn std::error::Error + Send + Sync>> {
        if !self.config.encryption.enable_encryption {
            return Ok(data.to_vec());
        }

        // Placeholder for actual encryption implementation
        // In a real implementation, you would use a crypto library like ring or openssl
        debug!("Encrypting {} bytes of data", data.len());
        let encrypted = data.to_vec(); // Placeholder - no actual encryption

        let mut stats = self.stats.write().await;
        stats.encrypted_reports += 1;

        Ok(encrypted)
    }

    async fn process_report_data(
        &self,
        data: &[u8],
    ) -> Result<Vec<u8>, Box<dyn std::error::Error + Send + Sync>> {
        let compressed = self.compress_data(data).await?;
        let encrypted = self.encrypt_data(&compressed).await?;
        Ok(encrypted)
    }

    async fn send_report_with_retry(
        &self,
        mut report: ReportRequest,
    ) -> Result<ReportResponse, Box<dyn std::error::Error + Send + Sync>> {
        let mut attempts = 0;
        let packet_id = self.generate_packet_id().await;
        report.set_packet_id(packet_id);

        // 認証が有効な場合はパスフレーズを設定し、認証フラグを追加
        if self.config.auth_enabled {
            if let Some(passphrase) = &self.config.auth_passphrase {
                report.enable_auth(passphrase);
            }
        }
        // enable_auth()が呼ばれていればauth_hashが拡張フィールドに追加される
        report.set_auth_flags();

        loop {
            attempts += 1;

            match self.send_single_report(&report).await {
                Ok(response) => {
                    if attempts > 1 {
                        let mut stats = self.stats.write().await;
                        stats.retry_attempts += attempts - 1;
                    }
                    return Ok(response);
                }
                Err(e) => {
                    if attempts >= self.config.retry_attempts {
                        let mut stats = self.stats.write().await;
                        stats.failed_reports += 1;
                        return Err(e);
                    }

                    warn!("Report attempt {} failed, retrying: {}", attempts, e);
                    sleep(self.config.retry_delay).await;
                }
            }
        }
    }

    async fn send_single_report(
        &self,
        report: &ReportRequest,
    ) -> Result<ReportResponse, Box<dyn std::error::Error + Send + Sync>> {
        let raw_data = report.to_bytes();
        let processed_data = self.process_report_data(&raw_data).await?;
        let packet_id = report.get_packet_id();

        debug!(
            "Sending report with packet ID {} to {} ({} bytes)",
            packet_id,
            self.addr,
            processed_data.len()
        );
        self.socket.send_to(&processed_data, &self.addr).await?;

        let mut stats = self.stats.write().await;
        stats.bytes_sent += processed_data.len();
        drop(stats);

        let result = timeout(self.config.timeout, async {
            let mut buf = [0u8; 2048];
            loop {
                let (len, _) = self.socket.recv_from(&mut buf).await?;
                let response_data = &buf[..len];

                if response_data.len() >= 2 {
                    let raw = u16::from_le_bytes([response_data[0], response_data[1]]);
                    let response_packet_id = (raw >> 4) & 0x0FFF; // version(4bit) + packet_id(12bit)
                    if response_packet_id == packet_id {
                        // まずReportResponseとしてパース試行
                        if let Some(response) = ReportResponse::from_bytes(response_data) {
                            return Ok(response);
                        }

                        // ReportResponseパースが失敗した場合、ErrorResponseとして試行
                        if let Some(error_response) = ErrorResponse::parse_bytes(response_data) {
                            let error_msg = format!(
                                "Server returned error: {} (code: {})",
                                error_response.get_error_type(),
                                error_response.get_error_code()
                            );
                            return Err(error_msg.into());
                        }

                        // 両方とも失敗した場合
                        return Err(
                            "Failed to parse server response as ReportResponse or ErrorResponse"
                                .into(),
                        );
                    }
                }
            }
        })
        .await;

        match result {
            Ok(response) => {
                info!("Received report response for packet ID {}", packet_id);
                response
            }
            Err(_) => {
                let mut stats = self.stats.write().await;
                stats.timeouts += 1;
                Err("Report timeout".into())
            }
        }
    }
}

#[async_trait]
impl ReportClient for ReportClientImpl {
    async fn send_report(
        &self,
        report: ReportRequest,
    ) -> Result<ReportResponse, Box<dyn std::error::Error + Send + Sync>> {
        let _permit = self.semaphore.acquire().await?;

        let mut stats = self.stats.write().await;
        stats.total_reports += 1;
        drop(stats);

        let response = self.send_report_with_retry(report).await?;

        let mut stats = self.stats.write().await;
        stats.successful_reports += 1;

        Ok(response)
    }

    async fn send_reports_batch(
        &self,
        reports: Vec<ReportRequest>,
    ) -> Vec<Result<ReportResponse, Box<dyn std::error::Error + Send + Sync>>> {
        if self.config.batching.enable_batching {
            let mut stats = self.stats.write().await;
            stats.batched_reports += reports.len();
            drop(stats);
        }

        let mut handles = Vec::new();

        for report in reports {
            let client = self.clone();
            let handle = tokio::spawn(async move { client.send_report(report).await });
            handles.push(handle);
        }

        let mut results = Vec::new();
        for handle in handles {
            match handle.await {
                Ok(result) => results.push(result),
                Err(e) => results.push(Err(e.into())),
            }
        }

        results
    }

    async fn queue_report(
        &self,
        report: ReportRequest,
    ) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
        if !self.config.batching.enable_batching {
            return Err("Batching is not enabled".into());
        }

        let pending_report = PendingReport::new(report);
        let mut queue = self.pending_reports.lock().await;
        queue.push_back(pending_report);

        debug!("Queued report, queue size: {}", queue.len());
        Ok(())
    }

    async fn flush_queued_reports(
        &self,
    ) -> Result<Vec<ReportResponse>, Box<dyn std::error::Error + Send + Sync>> {
        let reports_to_flush = {
            let mut queue = self.pending_reports.lock().await;
            let reports: Vec<ReportRequest> = queue.drain(..).map(|p| p.request).collect();
            reports
        };

        if reports_to_flush.is_empty() {
            return Ok(Vec::new());
        }

        info!("Flushing {} queued reports", reports_to_flush.len());
        let results = self.send_reports_batch(reports_to_flush).await;

        let mut responses = Vec::new();
        for result in results {
            match result {
                Ok(response) => responses.push(response),
                Err(e) => {
                    error!("Failed to flush report: {}", e);
                    return Err(e);
                }
            }
        }

        Ok(responses)
    }

    fn get_stats(&self) -> ReportStats {
        // Simplified synchronous version - return default for now
        ReportStats::default()
    }

    async fn get_queue_size(&self) -> usize {
        self.pending_reports.lock().await.len()
    }
}

impl Clone for ReportClientImpl {
    fn clone(&self) -> Self {
        Self {
            host: self.host.clone(),
            port: self.port,
            addr: self.addr,
            config: self.config.clone(),
            socket: self.socket.clone(),
            pidg: self.pidg.clone(),
            semaphore: self.semaphore.clone(),
            stats: self.stats.clone(),
            pending_reports: self.pending_reports.clone(),
            batch_timer: self.batch_timer.clone(),
        }
    }
}

impl ReportClientImpl {
    pub async fn get_detailed_stats(&self) -> ReportStats {
        self.stats.read().await.clone()
    }

    pub async fn reset_stats(&self) {
        let mut stats = self.stats.write().await;
        *stats = ReportStats::default();
    }

    pub async fn set_timeout(&mut self, timeout: Duration) {
        self.config.timeout = timeout;
    }

    pub async fn enable_compression(&mut self, enable: bool) {
        self.config.compression.enable_compression = enable;
    }

    pub async fn enable_encryption(&mut self, enable: bool) {
        self.config.encryption.enable_encryption = enable;
    }

    pub async fn set_encryption_key(&mut self, key: Vec<u8>) {
        self.config.encryption.encryption_key = Some(key);
    }

    pub async fn get_pending_reports_size(&self) -> (usize, usize) {
        let queue = self.pending_reports.lock().await;
        let count = queue.len();
        let total_size = queue.iter().map(|p| p.estimated_size).sum();
        (count, total_size)
    }
}
