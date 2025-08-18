use crate::wip_common_rs::clients::utils::packet_id_generator::PacketIDGenerator12Bit;
use crate::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};
use std::io;
use std::net::{SocketAddr, ToSocketAddrs, UdpSocket};
use std::time::Duration;

pub struct WeatherClient {
    pub host: String,
    pub port: u16,
    addr: SocketAddr,
    socket: UdpSocket,
    pub debug: bool,
    pub pidg: PacketIDGenerator12Bit,
}

impl WeatherClient {
    pub fn new(host: &str, port: u16, debug: bool) -> io::Result<Self> {
        let addr = (host, port)
            .to_socket_addrs()?
            .next()
            .ok_or_else(|| io::Error::new(io::ErrorKind::Other, "invalid address"))?;

        let bind_addr = if addr.is_ipv4() {
            "0.0.0.0:0"
        } else {
            "[::]:0"
        };
        let socket = UdpSocket::bind(bind_addr)?;
        socket.set_read_timeout(Some(Duration::from_secs(10)))?;

        Ok(Self {
            host: host.to_string(),
            port,
            addr,
            socket,
            debug,
            pidg: PacketIDGenerator12Bit::new(),
        })
    }

    fn receive_with_id(&self, expected_id: u16) -> io::Result<Vec<u8>> {
        let start_time = std::time::Instant::now();
        let timeout = Duration::from_secs(10);
        
        loop {
            let elapsed = start_time.elapsed();
            if elapsed >= timeout {
                return Err(io::Error::new(io::ErrorKind::TimedOut, "receive timeout"));
            }
            
            let remaining = timeout - elapsed;
            self.socket.set_read_timeout(Some(remaining))?;
            
            let mut buf = [0u8; 1024];
            match self.socket.recv_from(&mut buf) {
                Ok((size, addr)) => {
                    if self.debug {
                        println!("Received {} bytes from {}", size, addr);
                        println!("Response packet: {:02X?}", &buf[..size]);
                    }
                    
                    if size >= 2 {
                        let value = u16::from_le_bytes([buf[0], buf[1]]);
                        let packet_id = (value >> 4) & 0x0FFF;
                        
                        if self.debug {
                            println!("Expected ID: {}, Received ID: {}", expected_id, packet_id);
                        }
                        
                        if packet_id == expected_id {
                            return Ok(buf[..size].to_vec());
                        }
                    }
                }
                Err(e) => {
                    if e.kind() == io::ErrorKind::TimedOut || e.kind() == io::ErrorKind::WouldBlock {
                        continue;
                    }
                    if self.debug {
                        println!("Receive error: {}", e);
                    }
                    return Err(e);
                }
            }
        }
    }

    pub fn send_raw(&self, data: &[u8]) -> io::Result<Vec<u8>> {
        if self.debug {
            println!("Sending {} bytes to {}", data.len(), self.addr);
        }
        
        match self.socket.send_to(data, self.addr) {
            Ok(sent) => {
                if self.debug {
                    println!("Successfully sent {} bytes", sent);
                }
            }
            Err(e) => {
                if self.debug {
                    println!("Send error: {}", e);
                }
                return Err(e);
            }
        }
        
        // Extract packet ID from sent data for matching response
        if data.len() >= 2 {
            let value = u16::from_le_bytes([data[0], data[1]]);
            let packet_id = (value >> 4) & 0x0FFF;
            
            if self.debug {
                println!("Raw bytes: {:02X} {:02X}", data[0], data[1]);
                println!("Combined value: 0x{:04X}", value);
                println!("Extracted packet ID: {} (0x{:03X})", packet_id, packet_id);
                println!("Full packet: {:02X?}", data);
            }
            
            return self.receive_with_id(packet_id);
        }
        
        Err(io::Error::new(io::ErrorKind::InvalidInput, "Invalid packet data"))
    }

    /// area_code を指定して QueryRequest を送信する簡易メソッド
    pub fn get_weather_simple(
        &mut self,
        area_code: u32,
        weather: bool,
        temperature: bool,
        precipitation_prob: bool,
        alert: bool,
        disaster: bool,
        day: u8,
    ) -> io::Result<Option<QueryResponse>> {
        let req = QueryRequest::new(
            area_code,
            self.pidg.next_id(),
            weather,
            temperature,
            precipitation_prob,
            alert,
            disaster,
            day,
        );
        let bytes = req.to_bytes();
        
        if self.debug {
            // チェックサム検証
            use crate::wip_common_rs::packet::core::checksum::verify_checksum12;
            let is_checksum_valid = verify_checksum12(&bytes, 116, 12);
            println!("Checksum validation: {}", if is_checksum_valid { "✅ Valid" } else { "❌ Invalid" });
            
            // パケット詳細
            println!("Request packet details:");
            println!("  Length: {} bytes", bytes.len());
            println!("  Area code in packet: {}", req.area_code);
            println!("  Flags: weather={} temp={} pop={} alert={} disaster={}", 
                    req.weather_flag, req.temperature_flag, req.pop_flag, req.alert_flag, req.disaster_flag);
        }
        
        let resp_bytes = self.send_raw(&bytes)?;
        
        if self.debug {
            println!("Response analysis:");
            if resp_bytes.len() >= 3 {
                let packet_type = resp_bytes[2] & 0x07;
                println!("  Response type: {} (3=QueryResponse, 7=Error)", packet_type);
                
                if packet_type == 7 && resp_bytes.len() >= 4 {
                    let error_code = resp_bytes[3];
                    println!("  Error code: {} (1=Invalid packet format, 2=Checksum error, etc.)", error_code);
                }
            }
        }
        
        Ok(QueryResponse::from_bytes(&resp_bytes))
    }
}