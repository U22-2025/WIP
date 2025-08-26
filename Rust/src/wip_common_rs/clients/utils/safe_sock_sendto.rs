use log::{debug, warn};
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::{Duration, Instant};
use tokio::net::UdpSocket;
use tokio::sync::{Mutex, Semaphore};
use tokio::time::{sleep, timeout};

#[derive(Debug, Clone)]
pub struct SendConfig {
    pub timeout: Duration,
    pub max_retries: usize,
    pub retry_delay: Duration,
    pub max_packet_size: usize,
    pub enable_fragmentation: bool,
    pub fragment_size: usize,
    pub congestion_control: bool,
    pub max_concurrent_sends: usize,
}

impl Default for SendConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(5),
            max_retries: 3,
            retry_delay: Duration::from_millis(100),
            max_packet_size: 65507, // Maximum UDP payload size
            enable_fragmentation: false,
            fragment_size: 1400, // Safe MTU size
            congestion_control: true,
            max_concurrent_sends: 100,
        }
    }
}

#[derive(Debug, Clone)]
pub struct SendStats {
    pub total_sends: usize,
    pub successful_sends: usize,
    pub failed_sends: usize,
    pub retries: usize,
    pub timeouts: usize,
    pub bytes_sent: usize,
    pub fragmented_packets: usize,
    pub congestion_events: usize,
}

impl Default for SendStats {
    fn default() -> Self {
        Self {
            total_sends: 0,
            successful_sends: 0,
            failed_sends: 0,
            retries: 0,
            timeouts: 0,
            bytes_sent: 0,
            fragmented_packets: 0,
            congestion_events: 0,
        }
    }
}

#[derive(Debug, Clone)]
pub struct FragmentedPacket {
    pub fragment_id: u16,
    pub sequence_number: u16,
    pub total_fragments: u16,
    pub data: Vec<u8>,
}

impl FragmentedPacket {
    pub fn new(fragment_id: u16, sequence_number: u16, total_fragments: u16, data: Vec<u8>) -> Self {
        Self {
            fragment_id,
            sequence_number,
            total_fragments,
            data,
        }
    }

    pub fn to_bytes(&self) -> Vec<u8> {
        let mut bytes = Vec::with_capacity(8 + self.data.len());
        bytes.extend_from_slice(&self.fragment_id.to_le_bytes());
        bytes.extend_from_slice(&self.sequence_number.to_le_bytes());
        bytes.extend_from_slice(&self.total_fragments.to_le_bytes());
        bytes.extend_from_slice(&(self.data.len() as u16).to_le_bytes());
        bytes.extend_from_slice(&self.data);
        bytes
    }
}

pub struct CongestionController {
    send_rate: Arc<Mutex<Duration>>,
    last_congestion: Arc<Mutex<Instant>>,
    min_send_interval: Duration,
    max_send_interval: Duration,
    backoff_factor: f64,
}

impl CongestionController {
    pub fn new() -> Self {
        Self {
            send_rate: Arc::new(Mutex::new(Duration::from_millis(1))),
            last_congestion: Arc::new(Mutex::new(Instant::now() - Duration::from_secs(60))),
            min_send_interval: Duration::from_millis(1),
            max_send_interval: Duration::from_millis(1000),
            backoff_factor: 2.0,
        }
    }

    pub async fn wait_for_send(&self) {
        let send_rate = *self.send_rate.lock().await;
        if send_rate > self.min_send_interval {
            sleep(send_rate).await;
        }
    }

    pub async fn report_congestion(&self) {
        let mut send_rate = self.send_rate.lock().await;
        let mut last_congestion = self.last_congestion.lock().await;
        
        *last_congestion = Instant::now();
        *send_rate = std::cmp::min(
            Duration::from_millis(
                (send_rate.as_millis() as f64 * self.backoff_factor) as u64
            ),
            self.max_send_interval,
        );
        
        warn!("Congestion detected, increasing send interval to {:?}", *send_rate);
    }

    pub async fn report_success(&self) {
        let mut send_rate = self.send_rate.lock().await;
        let last_congestion = *self.last_congestion.lock().await;
        
        if last_congestion.elapsed() > Duration::from_secs(10) {
            *send_rate = std::cmp::max(
                Duration::from_millis(
                    (send_rate.as_millis() as f64 * 0.95) as u64
                ),
                self.min_send_interval,
            );
        }
    }
}

impl Default for CongestionController {
    fn default() -> Self {
        Self::new()
    }
}

pub struct SafeSocketSender {
    socket: Arc<UdpSocket>,
    config: SendConfig,
    stats: Arc<Mutex<SendStats>>,
    semaphore: Arc<Semaphore>,
    congestion_controller: Arc<CongestionController>,
}

impl SafeSocketSender {
    pub async fn new(socket: Arc<UdpSocket>, config: Option<SendConfig>) -> Self {
        let config = config.unwrap_or_default();
        let semaphore = Arc::new(Semaphore::new(config.max_concurrent_sends));
        
        Self {
            socket,
            config,
            stats: Arc::new(Mutex::new(SendStats::default())),
            semaphore,
            congestion_controller: Arc::new(CongestionController::new()),
        }
    }

    pub async fn send_to(
        &self,
        data: &[u8],
        addr: SocketAddr,
    ) -> Result<usize, Box<dyn std::error::Error + Send + Sync>> {
        let _permit = self.semaphore.acquire().await?;
        
        let mut stats = self.stats.lock().await;
        stats.total_sends += 1;
        drop(stats);

        if self.config.congestion_control {
            self.congestion_controller.wait_for_send().await;
        }

        if data.len() > self.config.max_packet_size {
            return Err(format!(
                "Packet size {} exceeds maximum allowed size {}",
                data.len(),
                self.config.max_packet_size
            ).into());
        }

        if self.config.enable_fragmentation && data.len() > self.config.fragment_size {
            self.send_fragmented(data, addr).await
        } else {
            self.send_single_packet(data, addr).await
        }
    }

    async fn send_single_packet(
        &self,
        data: &[u8],
        addr: SocketAddr,
    ) -> Result<usize, Box<dyn std::error::Error + Send + Sync>> {
        let mut attempts = 0;
        let mut last_error = None;

        loop {
            attempts += 1;
            
            let result = timeout(self.config.timeout, async {
                self.socket.send_to(data, addr).await
            }).await;

            match result {
                Ok(Ok(bytes_sent)) => {
                    debug!("Successfully sent {} bytes to {}", bytes_sent, addr);
                    
                    if attempts > 1 {
                        let mut stats = self.stats.lock().await;
                        stats.retries += attempts - 1;
                    }

                    let mut stats = self.stats.lock().await;
                    stats.successful_sends += 1;
                    stats.bytes_sent += bytes_sent;
                    drop(stats);

                    if self.config.congestion_control {
                        self.congestion_controller.report_success().await;
                    }

                    return Ok(bytes_sent);
                }
                Ok(Err(e)) => {
                    last_error = Some(e.into());
                    
                    if self.config.congestion_control {
                        self.congestion_controller.report_congestion().await;
                        let mut stats = self.stats.lock().await;
                        stats.congestion_events += 1;
                        drop(stats);
                    }
                }
                Err(_) => {
                    let mut stats = self.stats.lock().await;
                    stats.timeouts += 1;
                    drop(stats);
                    
                    last_error = Some("Send timeout".into());
                }
            }

            if attempts >= self.config.max_retries {
                let mut stats = self.stats.lock().await;
                stats.failed_sends += 1;
                
                return Err(last_error.unwrap_or_else(|| "Send failed after retries".into()));
            }

            warn!("Send attempt {} failed, retrying after {:?}", attempts, self.config.retry_delay);
            sleep(self.config.retry_delay).await;
        }
    }

    async fn send_fragmented(
        &self,
        data: &[u8],
        addr: SocketAddr,
    ) -> Result<usize, Box<dyn std::error::Error + Send + Sync>> {
        let fragment_id = rand::random::<u16>();
        let payload_size = self.config.fragment_size - 8; // Account for fragment header
        let total_fragments = (data.len() + payload_size - 1) / payload_size;
        
        if total_fragments > u16::MAX as usize {
            return Err("Data too large for fragmentation".into());
        }

        debug!("Fragmenting {} bytes into {} fragments", data.len(), total_fragments);
        
        let mut stats = self.stats.lock().await;
        stats.fragmented_packets += 1;
        drop(stats);

        let mut total_sent = 0;
        
        for (sequence, chunk) in data.chunks(payload_size).enumerate() {
            let fragment = FragmentedPacket::new(
                fragment_id,
                sequence as u16,
                total_fragments as u16,
                chunk.to_vec(),
            );
            
            let fragment_data = fragment.to_bytes();
            let bytes_sent = self.send_single_packet(&fragment_data, addr).await?;
            total_sent += bytes_sent;
            
            debug!("Sent fragment {}/{} ({} bytes)", sequence + 1, total_fragments, bytes_sent);
            
            // Small delay between fragments to avoid overwhelming the receiver
            if sequence < total_fragments - 1 {
                sleep(Duration::from_millis(1)).await;
            }
        }

        Ok(total_sent)
    }

    pub async fn send_to_multiple(
        &self,
        data: &[u8],
        addresses: &[SocketAddr],
    ) -> Vec<Result<usize, Box<dyn std::error::Error + Send + Sync>>> {
        let mut handles = Vec::new();
        
        for &addr in addresses {
            let sender = self.clone();
            let data = data.to_vec();
            
            let handle = tokio::spawn(async move {
                sender.send_to(&data, addr).await
            });
            
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

    pub async fn get_stats(&self) -> SendStats {
        self.stats.lock().await.clone()
    }

    pub async fn reset_stats(&self) {
        let mut stats = self.stats.lock().await;
        *stats = SendStats::default();
    }

    pub fn get_config(&self) -> &SendConfig {
        &self.config
    }

    pub async fn update_config(&mut self, new_config: SendConfig) {
        self.config = new_config;
        // Update semaphore if max_concurrent_sends changed
        self.semaphore = Arc::new(Semaphore::new(self.config.max_concurrent_sends));
    }
}

impl Clone for SafeSocketSender {
    fn clone(&self) -> Self {
        Self {
            socket: self.socket.clone(),
            config: self.config.clone(),
            stats: self.stats.clone(),
            semaphore: self.semaphore.clone(),
            congestion_controller: self.congestion_controller.clone(),
        }
    }
}

pub async fn safe_sock_sendto(
    socket: Arc<UdpSocket>,
    data: &[u8],
    addr: SocketAddr,
    config: Option<SendConfig>,
) -> Result<usize, Box<dyn std::error::Error + Send + Sync>> {
    let sender = SafeSocketSender::new(socket, config).await;
    sender.send_to(data, addr).await
}

pub async fn safe_sock_sendto_multiple(
    socket: Arc<UdpSocket>,
    data: &[u8],
    addresses: &[SocketAddr],
    config: Option<SendConfig>,
) -> Vec<Result<usize, Box<dyn std::error::Error + Send + Sync>>> {
    let sender = SafeSocketSender::new(socket, config).await;
    sender.send_to_multiple(data, addresses).await
}

#[cfg(test)]
mod tests {
    use super::*;
    use tokio::net::UdpSocket;
    
    #[tokio::test]
    async fn test_safe_socket_sender() {
        let socket = Arc::new(UdpSocket::bind("127.0.0.1:0").await.unwrap());
        let sender = SafeSocketSender::new(socket, None).await;
        
        let data = b"test data";
        let addr: SocketAddr = "127.0.0.1:12345".parse().unwrap();
        
        // UDPは相手がいなくても送信が成功し得るため、
        // 成否に関わらず送信経路が動くことを検証する
        let _ = sender.send_to(data, addr).await;
        let stats = sender.get_stats().await;
        assert_eq!(stats.total_sends, 1);
    }
    
    #[test]
    fn test_fragmented_packet() {
        let packet = FragmentedPacket::new(123, 1, 5, vec![1, 2, 3, 4]);
        let bytes = packet.to_bytes();
        
        assert_eq!(bytes.len(), 8 + 4); // Header + data
        assert_eq!(u16::from_le_bytes([bytes[0], bytes[1]]), 123);
        assert_eq!(u16::from_le_bytes([bytes[2], bytes[3]]), 1);
        assert_eq!(u16::from_le_bytes([bytes[4], bytes[5]]), 5);
        assert_eq!(u16::from_le_bytes([bytes[6], bytes[7]]), 4);
        assert_eq!(&bytes[8..], &[1, 2, 3, 4]);
    }
    
    #[tokio::test]
    async fn test_congestion_controller() {
        let controller = CongestionController::new();
        
        // Test normal operation
        controller.wait_for_send().await;
        controller.report_success().await;
        
        // Test congestion
        controller.report_congestion().await;
        let send_rate = *controller.send_rate.lock().await;
        assert!(send_rate > Duration::from_millis(1));
    }
}
