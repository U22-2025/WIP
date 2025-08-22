use crate::wip_common_rs::clients::utils::packet_id_generator::PacketIDGenerator12Bit;
use crate::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};
use crate::wip_common_rs::packet::core::extended_field::{FieldValue, ExtendedFieldManager, FieldDefinition};
use crate::wip_common_rs::utils::auth::WIPAuth;
use std::env;
use std::io;
use std::net::{SocketAddr, ToSocketAddrs, UdpSocket};
use std::time::Duration;

#[derive(Debug)]
pub struct WeatherClient {
    pub host: String,
    pub port: u16,
    addr: SocketAddr,
    socket: UdpSocket,
    pub debug: bool,
    pub pidg: PacketIDGenerator12Bit,
    // 認証設定
    auth_enabled: bool,
    auth_passphrase: String,
    response_auth_enabled: bool,
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

        // 認証設定を環境変数から読み込み
        let auth_enabled = env::var("WEATHER_SERVER_REQUEST_AUTH_ENABLED")
            .unwrap_or_else(|_| "false".to_string())
            .to_lowercase() == "true";
        let auth_passphrase = env::var("WEATHER_SERVER_PASSPHRASE")
            .unwrap_or_default();
        let response_auth_enabled = env::var("WEATHER_SERVER_RESPONSE_AUTH_ENABLED")
            .unwrap_or_else(|_| "false".to_string())
            .to_lowercase() == "true";

        Ok(Self {
            host: host.to_string(),
            port,
            addr,
            socket,
            debug,
            pidg: PacketIDGenerator12Bit::new(),
            auth_enabled,
            auth_passphrase,
            response_auth_enabled,
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
                    
                    if size >= 2 {
                        let value = u16::from_le_bytes([buf[0], buf[1]]);
                        let packet_id = (value >> 4) & 0x0FFF;
                        
                        
                        if packet_id == expected_id {
                            return Ok(buf[..size].to_vec());
                        }
                    }
                }
                Err(e) => {
                    if e.kind() == io::ErrorKind::TimedOut || e.kind() == io::ErrorKind::WouldBlock {
                        continue;
                    }
                    return Err(e);
                }
            }
        }
    }

    pub fn send_raw(&self, data: &[u8]) -> io::Result<Vec<u8>> {
        match self.socket.send_to(data, self.addr) {
            Ok(_sent) => {}
            Err(e) => {
                return Err(e);
            }
        }
        
        // Extract packet ID from sent data for matching response
        if data.len() >= 2 {
            let value = u16::from_le_bytes([data[0], data[1]]);
            let packet_id = (value >> 4) & 0x0FFF;
            
            
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
        let mut req = QueryRequest::new(
            area_code,
            self.pidg.next_id(),
            weather,
            temperature,
            precipitation_prob,
            alert,
            disaster,
            day,
        );
        
        // 認証設定を適用
        self.apply_auth_to_request(&mut req);
        
        let bytes = req.to_bytes();
        let resp_bytes = self.send_raw(&bytes)?;
        
        if let Some(response) = QueryResponse::from_bytes(&resp_bytes) {
            // レスポンス認証検証
            if self.verify_response_auth(&response) {
                Ok(Some(response))
            } else {
                if self.debug {
                    eprintln!("Response authentication verification failed");
                }
                Ok(None)
            }
        } else {
            Ok(None)
        }
    }
    
    /// Python版と同一のAPIを提供するメイン関数
    pub fn get_weather_data(
        &mut self,
        area_code: u32,
        weather: Option<bool>,
        temperature: Option<bool>,
        precipitation_prob: Option<bool>,
        alert: Option<bool>,
        disaster: Option<bool>,
        day: Option<u8>,
    ) -> io::Result<Option<QueryResponse>> {
        self.get_weather_simple(
            area_code,
            weather.unwrap_or(true),
            temperature.unwrap_or(true),
            precipitation_prob.unwrap_or(true),
            alert.unwrap_or(false),
            disaster.unwrap_or(false),
            day.unwrap_or(0),
        )
    }
    
    /// リクエストに認証設定を適用
    fn apply_auth_to_request(&self, request: &mut QueryRequest) {
        if self.auth_enabled && !self.auth_passphrase.is_empty() {
            let hash = WIPAuth::calculate_auth_hash(
                request.packet_id,
                request.timestamp,
                &self.auth_passphrase,
            );
            let mut ext = ExtendedFieldManager::new();
            let def = FieldDefinition::new("auth_hash".to_string(), FieldValue::String("".to_string()).get_type());
            ext.add_definition(def);
            let _ = ext.set_value("auth_hash".to_string(), FieldValue::String(hex::encode(hash)));
            request.ex_field = Some(ext);
            request.request_auth = true;
            request.ex_flag = true;
        }

        if self.response_auth_enabled {
            request.response_auth = true;
        }
    }

    /// レスポンス認証を検証
    fn verify_response_auth(&self, response: &QueryResponse) -> bool {
        if !self.response_auth_enabled {
            return true;
        }

        if self.auth_passphrase.is_empty() {
            if self.debug {
                eprintln!("Response authentication enabled but passphrase not set");
            }
            return false;
        }

        if !response.response_auth {
            if self.debug {
                eprintln!("Response auth flag not set");
            }
            return false;
        }

        // 拡張フィールドからauth_hashを取得して検証
        if let Some(ref ext) = response.ex_field {
            if let Some(FieldValue::String(hex_hash)) = ext.get_value("auth_hash") {
                if let Ok(hash) = hex::decode(hex_hash) {
                    if WIPAuth::verify_auth_hash(
                        response.packet_id,
                        response.timestamp,
                        &self.auth_passphrase,
                        &hash,
                    ) {
                        return true;
                    } else {
                        if self.debug {
                            eprintln!("Response auth hash verification failed");
                        }
                        return false;
                    }
                }
            }
        }

        if self.debug {
            eprintln!("Response auth hash missing");
        }
        false
    }
}