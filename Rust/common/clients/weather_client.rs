use crate::common::clients::utils::packet_id_generator::PacketIDGenerator12Bit;
use crate::common::packet::types::query_packet::{QueryRequest, QueryResponse};
use std::net::UdpSocket;
use std::time::Duration;

pub struct WeatherClient {
    pub host: String,
    pub port: u16,
    socket: UdpSocket,
    pub debug: bool,
    pub pidg: PacketIDGenerator12Bit,
}

impl WeatherClient {
    pub fn new(host: &str, port: u16, debug: bool) -> std::io::Result<Self> {
        let socket = UdpSocket::bind("0.0.0.0:0")?;
        socket.set_read_timeout(Some(Duration::from_secs(10)))?;
        Ok(Self {
            host: host.to_string(),
            port,
            socket,
            debug,
            pidg: PacketIDGenerator12Bit::new(),
        })
    }

    pub fn send_raw(&self, data: &[u8]) -> std::io::Result<Vec<u8>> {
        self.socket.send_to(data, (self.host.as_str(), self.port))?;
        let mut buf = [0u8; 1024];
        let size = self.socket.recv(&mut buf)?;
        Ok(buf[..size].to_vec())
    }

    /// area_code を指定して QueryRequest を送信する簡易メソッド
    pub fn get_weather_simple(
        &self,
        area_code: u32,
        weather: bool,
        temperature: bool,
        precipitation_prob: bool,
        alert: bool,
        disaster: bool,
        day: u8,
    ) -> std::io::Result<Option<QueryResponse>> {
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
        let resp_bytes = self.send_raw(&bytes)?;
        Ok(QueryResponse::from_bytes(&resp_bytes))
    }
}
