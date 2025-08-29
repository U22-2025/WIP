use log::{debug, warn};
use std::collections::HashMap;
use std::net::UdpSocket;
use std::time::{Duration, Instant};
use std::io::{self, ErrorKind};
use tokio::net::UdpSocket as AsyncUdpSocket;
use tokio::time::timeout;

#[derive(Debug, Clone)]
pub struct ReceiveConfig {
    pub timeout: Duration,
    pub max_retries: usize,
    pub buffer_size: usize,
    pub packet_id_offset: usize,
    pub packet_id_length: usize,
}

impl Default for ReceiveConfig {
    fn default() -> Self {
        Self {
            timeout: Duration::from_secs(10),
            max_retries: 3,
            buffer_size: 2048,
            packet_id_offset: 0,
            packet_id_length: 2,
        }
    }
}

#[derive(Debug, Clone)]
pub struct ReceivedPacket {
    pub data: Vec<u8>,
    pub packet_id: u16,
    pub received_at: Instant,
    pub source_addr: std::net::SocketAddr,
}

impl ReceivedPacket {
    pub fn new(data: Vec<u8>, packet_id: u16, source_addr: std::net::SocketAddr) -> Self {
        Self {
            data,
            packet_id,
            received_at: Instant::now(),
            source_addr,
        }
    }
}

pub struct PacketBuffer {
    packets: HashMap<u16, ReceivedPacket>,
    max_size: usize,
    cleanup_threshold: Duration,
}

impl PacketBuffer {
    pub fn new(max_size: usize, cleanup_threshold: Duration) -> Self {
        Self {
            packets: HashMap::new(),
            max_size,
            cleanup_threshold,
        }
    }
    
    pub fn insert(&mut self, packet: ReceivedPacket) {
        let packet_id = packet.packet_id;
        self.packets.insert(packet_id, packet);
        
        if self.packets.len() > self.max_size {
            self.cleanup_old_packets();
        }
    }
    
    pub fn remove(&mut self, packet_id: u16) -> Option<ReceivedPacket> {
        self.packets.remove(&packet_id)
    }
    
    pub fn contains(&self, packet_id: u16) -> bool {
        self.packets.contains_key(&packet_id)
    }
    
    fn cleanup_old_packets(&mut self) {
        let now = Instant::now();
        let threshold = self.cleanup_threshold;
        
        self.packets.retain(|_, packet| {
            now.duration_since(packet.received_at) < threshold
        });
        
        if self.packets.len() > self.max_size {
            let mut packets_vec: Vec<_> = self.packets.iter().map(|(id, packet)| (*id, packet.received_at)).collect();
            packets_vec.sort_by_key(|(_, received_at)| *received_at);
            
            let remove_count = self.packets.len() - self.max_size / 2;
            for (packet_id, _) in packets_vec.into_iter().take(remove_count) {
                self.packets.remove(&packet_id);
            }
        }
    }
    
    pub fn len(&self) -> usize {
        self.packets.len()
    }
}

pub fn extract_packet_id(data: &[u8], config: &ReceiveConfig) -> Result<u16, io::Error> {
    if data.len() < config.packet_id_offset + config.packet_id_length {
        return Err(io::Error::new(
            ErrorKind::InvalidData,
            "Data too short to contain packet ID"
        ));
    }
    
    match config.packet_id_length {
        1 => Ok((data[config.packet_id_offset] as u16) & 0x0F),
        2 => {
            // Protocol: first 4 bits = version, next 12 bits = packet_id (LSB0, LE)
            let bytes = [
                data[config.packet_id_offset],
                data[config.packet_id_offset + 1],
            ];
            let value = u16::from_le_bytes(bytes);
            Ok((value >> 4) & 0x0FFF)
        }
        4 => {
            let bytes = [
                data[config.packet_id_offset],
                data[config.packet_id_offset + 1],
                data[config.packet_id_offset + 2],
                data[config.packet_id_offset + 3],
            ];
            // Use lower 16 bits after shifting out version nibble (compat fallback)
            let value32 = u32::from_le_bytes(bytes);
            Ok(((value32 >> 4) & 0x0FFF) as u16)
        }
        _ => Err(io::Error::new(
            ErrorKind::InvalidInput,
            "Unsupported packet ID length"
        )),
    }
}

pub fn receive_with_id(
    socket: &UdpSocket,
    expected_id: u16,
    config: Option<ReceiveConfig>,
) -> io::Result<Vec<u8>> {
    let config = config.unwrap_or_default();
    let start_time = Instant::now();
    let mut buffer = vec![0u8; config.buffer_size];
    let mut packet_buffer = PacketBuffer::new(100, Duration::from_secs(30));
    let mut retries = 0;
    
    debug!("Waiting for packet with ID: {}", expected_id);
    
    loop {
        let elapsed = start_time.elapsed();
        if elapsed >= config.timeout {
            return Err(io::Error::new(
                ErrorKind::TimedOut,
                format!("Timeout waiting for packet ID {}", expected_id)
            ));
        }
        
        if let Some(packet) = packet_buffer.remove(expected_id) {
            debug!("Found buffered packet with ID: {}", expected_id);
            return Ok(packet.data);
        }
        
        socket.set_read_timeout(Some(Duration::from_millis(100)))?;
        
        match socket.recv_from(&mut buffer) {
            Ok((len, src_addr)) => {
                let data = &buffer[..len];
                
                match extract_packet_id(data, &config) {
                    Ok(packet_id) => {
                        debug!("Received packet with ID: {} from {}", packet_id, src_addr);
                        
                        if packet_id == expected_id {
                            return Ok(data.to_vec());
                        } else {
                            let packet = ReceivedPacket::new(data.to_vec(), packet_id, src_addr);
                            packet_buffer.insert(packet);
                            debug!("Buffered packet with ID: {} (expected: {})", packet_id, expected_id);
                        }
                    }
                    Err(e) => {
                        warn!("Failed to extract packet ID: {}", e);
                        continue;
                    }
                }
            }
            Err(ref e) if e.kind() == ErrorKind::WouldBlock || e.kind() == ErrorKind::TimedOut => {
                continue;
            }
            Err(e) => {
                retries += 1;
                if retries >= config.max_retries {
                    return Err(e);
                }
                warn!("Receive error (retry {}/{}): {}", retries, config.max_retries, e);
                std::thread::sleep(Duration::from_millis(100));
            }
        }
    }
}

pub fn receive_multiple_with_ids(
    socket: &UdpSocket,
    expected_ids: &[u16],
    config: Option<ReceiveConfig>,
) -> io::Result<HashMap<u16, Vec<u8>>> {
    let config = config.unwrap_or_default();
    let start_time = Instant::now();
    let mut buffer = vec![0u8; config.buffer_size];
    let mut packet_buffer = PacketBuffer::new(100, Duration::from_secs(30));
    let mut results = HashMap::new();
    let mut remaining_ids: std::collections::HashSet<u16> = expected_ids.iter().copied().collect();
    
    debug!("Waiting for packets with IDs: {:?}", expected_ids);
    
    while !remaining_ids.is_empty() {
        let elapsed = start_time.elapsed();
        if elapsed >= config.timeout {
            return Err(io::Error::new(
                ErrorKind::TimedOut,
                format!("Timeout waiting for packets: {:?}", remaining_ids)
            ));
        }
        
        for &id in &remaining_ids.clone() {
            if let Some(packet) = packet_buffer.remove(id) {
                debug!("Found buffered packet with ID: {}", id);
                results.insert(id, packet.data);
                remaining_ids.remove(&id);
            }
        }
        
        if remaining_ids.is_empty() {
            break;
        }
        
        socket.set_read_timeout(Some(Duration::from_millis(100)))?;
        
        match socket.recv_from(&mut buffer) {
            Ok((len, src_addr)) => {
                let data = &buffer[..len];
                
                match extract_packet_id(data, &config) {
                    Ok(packet_id) => {
                        debug!("Received packet with ID: {} from {}", packet_id, src_addr);
                        
                        if remaining_ids.contains(&packet_id) {
                            results.insert(packet_id, data.to_vec());
                            remaining_ids.remove(&packet_id);
                        } else {
                            let packet = ReceivedPacket::new(data.to_vec(), packet_id, src_addr);
                            packet_buffer.insert(packet);
                            debug!("Buffered unexpected packet with ID: {}", packet_id);
                        }
                    }
                    Err(e) => {
                        warn!("Failed to extract packet ID: {}", e);
                        continue;
                    }
                }
            }
            Err(ref e) if e.kind() == ErrorKind::WouldBlock || e.kind() == ErrorKind::TimedOut => {
                continue;
            }
            Err(e) => {
                return Err(e);
            }
        }
    }
    
    Ok(results)
}

pub async fn receive_with_id_async(
    socket: &AsyncUdpSocket,
    expected_id: u16,
    config: Option<ReceiveConfig>,
) -> Result<Vec<u8>, Box<dyn std::error::Error + Send + Sync>> {
    let config = config.unwrap_or_default();
    let mut buffer = vec![0u8; config.buffer_size];
    let mut packet_buffer = PacketBuffer::new(100, Duration::from_secs(30));
    
    debug!("Waiting for packet with ID: {} (async)", expected_id);
    
    let result = timeout(config.timeout, async {
        loop {
            if let Some(packet) = packet_buffer.remove(expected_id) {
                debug!("Found buffered packet with ID: {}", expected_id);
                return Ok(packet.data);
            }
            
            match socket.recv_from(&mut buffer).await {
                Ok((len, src_addr)) => {
                    let data = &buffer[..len];
                    
                    match extract_packet_id(data, &config) {
                        Ok(packet_id) => {
                            debug!("Received packet with ID: {} from {}", packet_id, src_addr);
                            
                            if packet_id == expected_id {
                                return Ok(data.to_vec());
                            } else {
                                let packet = ReceivedPacket::new(data.to_vec(), packet_id, src_addr);
                                packet_buffer.insert(packet);
                                debug!("Buffered packet with ID: {} (expected: {})", packet_id, expected_id);
                            }
                        }
                        Err(e) => {
                            warn!("Failed to extract packet ID: {}", e);
                            continue;
                        }
                    }
                }
                Err(e) => {
                    return Err(e.into());
                }
            }
        }
    }).await;

    match result {
        Ok(data) => data,
        Err(_) => Err(format!("Timeout waiting for packet ID {}", expected_id).into()),
    }
}

pub async fn receive_multiple_with_ids_async(
    socket: &AsyncUdpSocket,
    expected_ids: &[u16],
    config: Option<ReceiveConfig>,
) -> Result<HashMap<u16, Vec<u8>>, Box<dyn std::error::Error + Send + Sync>> {
    let config = config.unwrap_or_default();
    let mut buffer = vec![0u8; config.buffer_size];
    let mut packet_buffer = PacketBuffer::new(100, Duration::from_secs(30));
    let mut results = HashMap::new();
    let mut remaining_ids: std::collections::HashSet<u16> = expected_ids.iter().copied().collect();
    
    debug!("Waiting for packets with IDs: {:?} (async)", expected_ids);
    
    let result = timeout(config.timeout, async {
        while !remaining_ids.is_empty() {
            for &id in &remaining_ids.clone() {
                if let Some(packet) = packet_buffer.remove(id) {
                    debug!("Found buffered packet with ID: {}", id);
                    results.insert(id, packet.data);
                    remaining_ids.remove(&id);
                }
            }
            
            if remaining_ids.is_empty() {
                break;
            }
            
            match socket.recv_from(&mut buffer).await {
                Ok((len, src_addr)) => {
                    let data = &buffer[..len];
                    
                    match extract_packet_id(data, &config) {
                        Ok(packet_id) => {
                            debug!("Received packet with ID: {} from {}", packet_id, src_addr);
                            
                            if remaining_ids.contains(&packet_id) {
                                results.insert(packet_id, data.to_vec());
                                remaining_ids.remove(&packet_id);
                            } else {
                                let packet = ReceivedPacket::new(data.to_vec(), packet_id, src_addr);
                                packet_buffer.insert(packet);
                                debug!("Buffered unexpected packet with ID: {}", packet_id);
                            }
                        }
                        Err(e) => {
                            warn!("Failed to extract packet ID: {}", e);
                            continue;
                        }
                    }
                }
                Err(e) => {
                    return Err(e.into());
                }
            }
        }
        
        Ok(results)
    }).await;

    match result {
        Ok(data) => data,
        Err(_) => Err(format!("Timeout waiting for packets: {:?}", remaining_ids).into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::SocketAddr;
    
    #[test]
    fn test_extract_packet_id() {
        let config = ReceiveConfig::default();
        let data = vec![0x34, 0x12, 0xFF, 0xAA];
        
        let packet_id = extract_packet_id(&data, &config).unwrap();
        assert_eq!(packet_id, 0x0123); // (0x1234 >> 4) & 0x0FFF
    }
    
    #[test]
    fn test_packet_buffer() {
        let mut buffer = PacketBuffer::new(2, Duration::from_secs(1));
        let addr: SocketAddr = "127.0.0.1:0".parse().unwrap();
        
        let packet1 = ReceivedPacket::new(vec![1, 2, 3], 100, addr);
        let packet2 = ReceivedPacket::new(vec![4, 5, 6], 200, addr);
        let packet3 = ReceivedPacket::new(vec![7, 8, 9], 300, addr);
        
        buffer.insert(packet1);
        buffer.insert(packet2);
        assert_eq!(buffer.len(), 2);
        
        buffer.insert(packet3);
        assert!(buffer.len() <= 2);
        
        assert!(buffer.contains(200) || buffer.contains(300));
    }
}
