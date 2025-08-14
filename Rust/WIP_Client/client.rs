use std::collections::HashMap;
use crate::common::clients::weather_client::WeatherClient;

pub struct ServerConfig {
    pub host: String,
    pub port: u16,
}

impl ServerConfig {
    pub fn new(host: String, port: u16) -> Self {
        Self { host, port }
    }
}

pub struct ClientState {
    pub latitude: Option<f64>,
    pub longitude: Option<f64>,
    pub area_code: Option<String>,
}

pub struct Client {
    pub config: ServerConfig,
    pub state: ClientState,
    weather_client: WeatherClient,
}

impl Client {
    pub fn new(host: Option<String>, port: Option<u16>) -> std::io::Result<Self> {
        let host = host.unwrap_or_else(|| "localhost".to_string());
        let port = port.unwrap_or(4110);
        let weather_client = WeatherClient::new(&host, port, false)?;
        Ok(Self {
            config: ServerConfig::new(host, port),
            state: ClientState { latitude: None, longitude: None, area_code: None },
            weather_client,
        })
    }

    pub fn set_coordinates(&mut self, lat: f64, lon: f64) {
        self.state.latitude = Some(lat);
        self.state.longitude = Some(lon);
        self.state.area_code = None;
    }

    pub fn set_area_code(&mut self, code: String) {
        self.state.area_code = Some(code);
        self.state.latitude = None;
        self.state.longitude = None;
    }

    pub fn get_weather(&self) -> std::io::Result<Vec<u8>> {
        let mut data = Vec::new();
        if let Some(code) = &self.state.area_code {
            data.extend_from_slice(code.as_bytes());
        }
        self.weather_client.send_raw(&data)
    }

    pub fn get_state(&self) -> HashMap<String, String> {
        let mut map = HashMap::new();
        if let Some(lat) = self.state.latitude {
            map.insert("latitude".to_string(), lat.to_string());
        }
        if let Some(lon) = self.state.longitude {
            map.insert("longitude".to_string(), lon.to_string());
        }
        if let Some(code) = &self.state.area_code {
            map.insert("area_code".to_string(), code.clone());
        }
        map.insert("host".to_string(), self.config.host.clone());
        map.insert("port".to_string(), self.config.port.to_string());
        map
    }
}
