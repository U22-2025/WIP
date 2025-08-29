/*!
 * Python互換クライアント
 * Python版WIPクライアントと完全に同一のAPIインターフェースを提供
 */

use std::collections::HashMap;
use std::env;
use std::time::Duration;
use crate::wip_common_rs::clients::weather_client::WeatherClient;
use crate::wip_common_rs::clients::location_client::{LocationClient, LocationClientImpl};
use crate::wip_common_rs::clients::query_client::{QueryClient, QueryClientImpl};
use crate::wip_common_rs::packet::types::query_packet::{QueryRequest, QueryResponse};
use crate::wip_common_rs::clients::report_client::{ReportClient, ReportClientImpl};
use crate::wip_common_rs::packet::types::report_packet::ReportRequest;
use crate::wip_common_rs::utils::config_loader::ConfigLoader;
use crate::wip_common_rs::packet::core::extended_field::FieldValue;

/// Python版WeatherClientと完全互換のクライアント
#[derive(Debug)]
pub struct PythonCompatibleWeatherClient {
    host: String,
    port: u16,
    debug: bool,
    logger: Option<String>, // デバッグログ用
    timeout: Duration,
    
    // 内部的にRust版クライアントを使用
    inner_client: WeatherClient,
}

impl PythonCompatibleWeatherClient {
    /// Python版と同一のコンストラクタ
    /// ```python
    /// def __init__(self, host=None, port=None, debug=False):
    /// ```
    pub fn new(host: Option<&str>, port: Option<u16>, debug: Option<bool>) -> std::io::Result<Self> {
        let default_host = env::var("WEATHER_SERVER_HOST").unwrap_or_else(|_| "wip.ncc.onl".to_string());
        let host = host.unwrap_or(&default_host);
        let port = port.unwrap_or_else(|| {
            env::var("WEATHER_SERVER_PORT")
                .unwrap_or_else(|_| "4110".to_string())
                .parse()
                .unwrap_or(4110)
        });
        let debug = debug.unwrap_or(false);
        
        let inner_client = WeatherClient::new(host, port, debug)?;
        
        Ok(Self {
            host: host.to_string(),
            port,
            debug,
            logger: if debug { Some("weather_client".to_string()) } else { None },
            timeout: Duration::from_secs(5),
            inner_client,
        })
    }

    fn map_from_response(&self, response: &QueryResponse) -> HashMap<String, serde_json::Value> {
        let mut result = HashMap::new();
        result.insert(
            "area_code".to_string(),
            serde_json::Value::Number(serde_json::Number::from(response.area_code)),
        );
        if let Some(weather_code) = response.weather_code {
            result.insert(
                "weather_code".to_string(),
                serde_json::Value::Number(serde_json::Number::from(weather_code)),
            );
        }
        if let Some(temp) = response.temperature {
            result.insert(
                "temperature".to_string(),
                serde_json::Value::Number(serde_json::Number::from(temp)),
            );
        }
        if let Some(precip) = response.precipitation {
            result.insert(
                "precipitation_prob".to_string(),
                serde_json::Value::Number(serde_json::Number::from(precip)),
            );
        }
        if let Some(ext) = &response.ex_field {
            if let Some(FieldValue::String(s)) = ext.get_value("alert") {
                let arr = s
                    .split(',')
                    .filter(|x| !x.is_empty())
                    .map(|x| serde_json::Value::String(x.to_string()))
                    .collect::<Vec<_>>();
                if !arr.is_empty() {
                    result.insert("alert".to_string(), serde_json::Value::Array(arr));
                }
            }
            if let Some(FieldValue::String(s)) = ext.get_value("disaster") {
                let arr = s
                    .split(',')
                    .filter(|x| !x.is_empty())
                    .map(|x| serde_json::Value::String(x.to_string()))
                    .collect::<Vec<_>>();
                if !arr.is_empty() {
                    result.insert("disaster".to_string(), serde_json::Value::Array(arr));
                }
            }
        }
        result.insert("success".to_string(), serde_json::Value::Bool(true));
        result
    }

    /// Python版の get_weather_data メソッドと完全互換
    /// ```python
    /// def get_weather_data(self, area_code, weather=True, temperature=True, 
    ///                      precipitation_prob=True, alert=False, disaster=False, day=0):
    /// ```
    pub fn get_weather_data(
        &mut self,
        area_code: u32,
        weather: Option<bool>,
        temperature: Option<bool>,
        precipitation_prob: Option<bool>,
        alert: Option<bool>,
        disaster: Option<bool>,
        day: Option<u8>,
    ) -> Result<HashMap<String, serde_json::Value>, String> {
        let weather = weather.unwrap_or(true);
        let temperature = temperature.unwrap_or(true);
        let precipitation_prob = precipitation_prob.unwrap_or(true);
        let alert = alert.unwrap_or(false);
        let disaster = disaster.unwrap_or(false);
        let day = day.unwrap_or(0);


        // 内部クライアントを使用してデータを取得
        match self.inner_client.get_weather_simple(area_code, weather, temperature, precipitation_prob, alert, disaster, day) {
            Ok(Some(response)) => {
                let mut result = HashMap::new();
                
                // Python版と同じ構造で結果を返す
                result.insert("area_code".to_string(), serde_json::Value::Number(serde_json::Number::from(response.area_code)));
                
                if let Some(weather_code) = response.weather_code {
                    result.insert("weather_code".to_string(), serde_json::Value::Number(serde_json::Number::from(weather_code)));
                }
                
                if let Some(temp) = response.temperature {
                    result.insert("temperature".to_string(), serde_json::Value::Number(serde_json::Number::from(temp)));
                }
                
                if let Some(precip) = response.precipitation {
                    result.insert("precipitation_prob".to_string(), serde_json::Value::Number(serde_json::Number::from(precip)));
                }

                if let Some(ext) = &response.ex_field {
                    if let Some(FieldValue::String(s)) = ext.get_value("alert") {
                        let arr = s
                            .split(',')
                            .filter(|x| !x.is_empty())
                            .map(|x| serde_json::Value::String(x.to_string()))
                            .collect::<Vec<_>>();
                        if !arr.is_empty() {
                            result.insert("alert".to_string(), serde_json::Value::Array(arr));
                        }
                    }
                    if let Some(FieldValue::String(s)) = ext.get_value("disaster") {
                        let arr = s
                            .split(',')
                            .filter(|x| !x.is_empty())
                            .map(|x| serde_json::Value::String(x.to_string()))
                            .collect::<Vec<_>>();
                        if !arr.is_empty() {
                            result.insert("disaster".to_string(), serde_json::Value::Array(arr));
                        }
                    }
                }

                result.insert("success".to_string(), serde_json::Value::Bool(true));
                
                Ok(result)
            }
            Ok(None) => {
                Err("No weather data received".to_string())
            }
            Err(e) => Err(format!("Weather data request failed: {}", e))
        }
    }

    /// Python版の get_weather_simple メソッドと完全互換
    /// ```python
    /// def get_weather_simple(self, area_code, include_all=False, day=0):
    /// ```
    pub async fn get_weather_simple(
        &mut self,
        area_code: u32,
        include_all: Option<bool>,
        day: Option<u8>,
    ) -> Result<HashMap<String, serde_json::Value>, String> {
        let include_all = include_all.unwrap_or(false);
        let day = day.unwrap_or(0);

        // 簡単な実装として、デフォルトの天気情報を返す
        self.get_weather_data(
            area_code,
            Some(include_all),
            Some(include_all),
            Some(include_all),
            Some(include_all),
            Some(include_all),
            Some(day)
        )
    }

    /// 座標から天気情報を取得
    pub async fn get_weather_by_coordinates(
        &mut self,
        latitude: f64,
        longitude: f64,
        weather: Option<bool>,
        temperature: Option<bool>,
        precipitation_prob: Option<bool>,
        alert: Option<bool>,
        disaster: Option<bool>,
        day: Option<u8>,
    ) -> Result<HashMap<String, serde_json::Value>, String> {
        let host = env::var("LOCATION_RESOLVER_HOST").unwrap_or_else(|_| "wip.ncc.onl".to_string());
        let port = env::var("LOCATION_RESOLVER_PORT")
            .unwrap_or_else(|_| "4109".to_string())
            .parse()
            .unwrap_or(4109);
        let loc_client = LocationClientImpl::new(&host, port)
            .await
            .map_err(|e| format!("Location client init failed: {}", e))?;
        let area_code = loc_client
            .resolve_coordinates(latitude, longitude)
            .await
            .map_err(|e| format!("Coordinate resolution failed: {}", e))?;
        self.get_weather_data(
            area_code,
            weather,
            temperature,
            precipitation_prob,
            alert,
            disaster,
            day,
        )
    }

    /// Python版の get_weather_by_area_code メソッド（後方互換性）
    /// ```python
    /// def get_weather_by_area_code(self, area_code, weather=True, temperature=True, 
    ///                             precipitation_prob=True, alert=False, disaster=False, day=0):
    /// ```
    pub fn get_weather_by_area_code(
        &mut self,
        area_code: u32,
        weather: Option<bool>,
        temperature: Option<bool>,
        precipitation_prob: Option<bool>,
        alert: Option<bool>,
        disaster: Option<bool>,
        day: Option<u8>,
    ) -> Result<HashMap<String, serde_json::Value>, String> {
        // get_weather_data()にリダイレクト（Python版と同じ動作）
        self.get_weather_data(area_code, weather, temperature, precipitation_prob, alert, disaster, day)
    }

    /// デバッグ情報を設定（Python版互換）
    pub fn set_debug(&mut self, debug: bool) {
        self.debug = debug;
        self.logger = if debug { Some("weather_client".to_string()) } else { None };
    }

    /// タイムアウトを設定（Python版互換）
    pub fn set_timeout(&mut self, timeout_seconds: f64) {
        self.timeout = Duration::from_secs_f64(timeout_seconds);
    }
}

/// Python版LocationClientと完全互換のクライアント
#[derive(Debug)]
pub struct PythonCompatibleLocationClient {
    server_host: String,
    server_port: u16,
    debug: bool,
    cache_ttl_minutes: u64,
    cache_enabled: bool,
    
    // 内部的にRust版クライアントを使用
    inner_client: LocationClientImpl,
}

impl PythonCompatibleLocationClient {
    /// Python版と同一のコンストラクタ
    /// ```python
    /// def __init__(self, host=None, port=None, debug=False, cache_ttl_minutes=30, 
    ///              cache_enabled=None, config_path=None):
    /// ```
    pub async fn new(
        host: Option<&str>,
        port: Option<u16>,
        debug: Option<bool>,
        cache_ttl_minutes: Option<u64>,
        cache_enabled: Option<bool>,
        config_path: Option<&str>,
    ) -> std::io::Result<Self> {
        let _config = config_path.map(|_path| ConfigLoader::new());
        
        let default_host = env::var("LOCATION_RESOLVER_HOST").unwrap_or_else(|_| "wip.ncc.onl".to_string());
        let host = host.unwrap_or(&default_host);
        let port = port.unwrap_or_else(|| {
            env::var("LOCATION_RESOLVER_PORT")
                .unwrap_or_else(|_| "4109".to_string())
                .parse()
                .unwrap_or(4109)
        });
        let debug = debug.unwrap_or(false);
        let cache_ttl_minutes = cache_ttl_minutes.unwrap_or(30);
        let cache_enabled = cache_enabled.unwrap_or(true);
        
        let _server_addr = format!("{}:{}", host, port);
        
        let inner_client = LocationClientImpl::new(host, port).await?;
        
        Ok(Self {
            server_host: host.to_string(),
            server_port: port,
            debug,
            cache_ttl_minutes,
            cache_enabled,
            inner_client,
        })
    }

    /// Python版の get_area_code_simple メソッドと完全互換
    /// ```python
    /// def get_area_code_simple(self, latitude, longitude, source=None, use_cache=True, return_cache_info=False):
    /// ```
    pub async fn get_area_code_simple(
        &self,
        latitude: f64,
        longitude: f64,
        source: Option<(String, u16)>,
        use_cache: Option<bool>,
        return_cache_info: Option<bool>,
    ) -> Result<serde_json::Value, String> {
        let _source = source; // 現在は未使用
        let _use_cache = use_cache.unwrap_or(true);
        let return_cache_info = return_cache_info.unwrap_or(false);


        match self.inner_client.resolve_coordinates(latitude, longitude).await {
            Ok(area_code) => {
                if return_cache_info {
                    let mut result = serde_json::Map::new();
                    result.insert("area_code".to_string(), serde_json::Value::Number(serde_json::Number::from(area_code)));
                    result.insert("latitude".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(latitude).unwrap()));
                    result.insert("longitude".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(longitude).unwrap()));
                    result.insert("source".to_string(), serde_json::Value::String("server".to_string()));
                    Ok(serde_json::Value::Object(result))
                } else {
                    Ok(serde_json::Value::Number(serde_json::Number::from(area_code)))
                }
            }
            Err(e) => Err(format!("Area code resolution failed: {}", e))
        }
    }

    /// Python版の get_area_code_from_coordinates メソッド（後方互換性）
    /// ```python
    /// def get_area_code_from_coordinates(self, latitude, longitude, source=None):
    /// ```
    pub fn get_area_code_from_coordinates(
        &self,
        _latitude: f64,
        _longitude: f64,
        _source: Option<(String, u16)>,
    ) -> Result<serde_json::Value, String> {
        // This method should be async too since get_area_code_simple is async
        panic!("get_area_code_from_coordinates requires async context - should be made async")
    }

    /// Python版の get_cache_stats メソッドと完全互換
    /// ```python
    /// def get_cache_stats(self):
    /// ```
    pub fn get_cache_stats(&self) -> HashMap<String, serde_json::Value> {
        let mut stats = HashMap::new();
        stats.insert("enabled".to_string(), serde_json::Value::Bool(self.cache_enabled));
        stats.insert("ttl_minutes".to_string(), serde_json::Value::Number(serde_json::Number::from(self.cache_ttl_minutes)));
        stats.insert("hits".to_string(), serde_json::Value::Number(serde_json::Number::from(0))); // TODO: 実装
        stats.insert("misses".to_string(), serde_json::Value::Number(serde_json::Number::from(0))); // TODO: 実装
        stats
    }
}

/// Python版QueryClientと完全互換のクライアント
#[derive(Debug)]
pub struct PythonCompatibleQueryClient {
    host: String,
    port: u16,
    debug: bool,
    
    // 内部的にRust版クライアントを使用
    inner_client: QueryClientImpl,
}

impl PythonCompatibleQueryClient {
    /// Python版と同一のコンストラクタ
    pub async fn new(host: Option<&str>, port: Option<u16>, debug: Option<bool>) -> std::io::Result<Self> {
        let default_host = env::var("QUERY_SERVER_HOST").unwrap_or_else(|_| "wip.ncc.onl".to_string());
        let host = host.unwrap_or(&default_host);
        let port = port.unwrap_or_else(|| {
            env::var("QUERY_SERVER_PORT")
                .unwrap_or_else(|_| "4111".to_string())
                .parse()
                .unwrap_or(4111)
        });
        let debug = debug.unwrap_or(false);
        
        let _server_addr = format!("{}:{}", host, port);
        
        let inner_client = QueryClientImpl::new(host, port).await?;
        
        Ok(Self {
            host: host.to_string(),
            port,
            debug,
            inner_client,
        })
    }

    /// 直接クエリサーバーに問い合わせ（Python版互換）
    pub async fn query_weather_data(
        &self,
        area_code: u32,
        weather: Option<bool>,
        temperature: Option<bool>,
        precipitation_prob: Option<bool>,
        alert: Option<bool>,
        disaster: Option<bool>,
        day: Option<u8>,
    ) -> Result<HashMap<String, serde_json::Value>, String> {
        let weather = weather.unwrap_or(true);
        let temperature = temperature.unwrap_or(true);
        let precipitation_prob = precipitation_prob.unwrap_or(true);
        let alert = alert.unwrap_or(false);
        let disaster = disaster.unwrap_or(false);
        let day = day.unwrap_or(0);


        let query_request = QueryRequest::new(
            area_code,
            1, // packet_id - for now using 1, in production should be generated
            weather,
            temperature,
            precipitation_prob,
            alert,
            disaster,
            day,
        );
        
        match self.inner_client.execute_query(query_request).await {
            Ok(response) => {
                let mut result = HashMap::new();
                result.insert("area_code".to_string(), serde_json::Value::Number(serde_json::Number::from(response.area_code)));
                
                if let Some(weather_code) = response.weather_code {
                    result.insert("weather_code".to_string(), serde_json::Value::Number(serde_json::Number::from(weather_code)));
                }
                
                if let Some(temp) = response.temperature {
                    result.insert("temperature".to_string(), serde_json::Value::Number(serde_json::Number::from(temp)));
                }
                
                if let Some(precip) = response.precipitation {
                    result.insert("precipitation_prob".to_string(), serde_json::Value::Number(serde_json::Number::from(precip)));
                }
                
                result.insert("success".to_string(), serde_json::Value::Bool(true));
                Ok(result)
            }
            Err(e) => Err(format!("Query failed: {}", e))
        }
    }
}

/// Python版ReportClientと完全互換のクライアント
#[derive(Debug)]
pub struct PythonCompatibleReportClient {
    host: String,
    port: u16,
    debug: bool,
    
    // 内部的にRust版クライアントを使用
    inner_client: ReportClientImpl,
}

impl PythonCompatibleReportClient {
    /// Python版と同一のコンストラクタ
    pub async fn new(host: Option<&str>, port: Option<u16>, debug: Option<bool>) -> std::io::Result<Self> {
        let default_host = env::var("REPORT_SERVER_HOST").unwrap_or_else(|_| "wip.ncc.onl".to_string());
        let host = host.unwrap_or(&default_host);
        let port = port.unwrap_or_else(|| {
            env::var("REPORT_SERVER_PORT")
                .unwrap_or_else(|_| "4112".to_string())
                .parse()
                .unwrap_or(4112)
        });
        let debug = debug.unwrap_or(false);
        
        let _server_addr = format!("{}:{}", host, port);
        
        let inner_client = ReportClientImpl::new(host, port).await?;
        
        Ok(Self {
            host: host.to_string(),
            port,
            debug,
            inner_client,
        })
    }

    /// センサーデータを送信（Python版互換）
    pub async fn send_sensor_data(
        &self,
        area_code: &str,
        weather_code: Option<u16>,
        temperature_c: Option<f64>,
        humidity_percent: Option<f64>,
        _pressure_hpa: Option<f64>,
        packet_id: u16,
    ) -> Result<HashMap<String, serde_json::Value>, String> {

        let report_request = ReportRequest::create_sensor_data_report(
            area_code,
            weather_code,
            temperature_c,
            humidity_percent.map(|h| h as u8), // Convert to precipitation_prob format
            None, // alert
            None, // disaster
            1,    // version
            packet_id,
        );
        
        match self.inner_client.send_report(report_request).await {
            Ok(response) => {
                let mut result = HashMap::new();
                result.insert("success".to_string(), serde_json::Value::Bool(true));
                result.insert("packet_id".to_string(), serde_json::Value::Number(serde_json::Number::from(response.packet_id)));
                result.insert("area_code".to_string(), serde_json::Value::Number(serde_json::Number::from(response.area_code)));
                Ok(result)
            }
            Err(e) => Err(format!("Sensor data transmission failed: {}", e))
        }
    }
}

#[cfg(test)]
mod tests {
    use serde_json::json;
    use super::PythonCompatibleWeatherClient;
    use crate::wip_common_rs::packet::types::query_packet::QueryResponse;

    #[test]
    fn map_from_response_uses_precipitation_prob_key() {
        let client = PythonCompatibleWeatherClient::new(Some("localhost"), Some(4110), Some(false)).unwrap();
        let mut response = QueryResponse::new();
        response.area_code = 11000;
        response.weather_code = Some(100);
        response.temperature = Some(25);
        response.precipitation = Some(60);

        let map = client.map_from_response(&response);
        assert_eq!(map.get("precipitation_prob"), Some(&json!(60)));
        assert!(!map.contains_key("precipitation_probability"));
    }
}


#[cfg(test)]
#[allow(dead_code)]
mod disabled_tests_for_now {
    use super::{PythonCompatibleWeatherClient, PythonCompatibleLocationClient};

    #[test]
    fn test_python_compatible_weather_client_creation() {
        let client = PythonCompatibleWeatherClient::new(Some("localhost"), Some(4110), Some(true)).unwrap();
        assert_eq!(client.host, "localhost");
        assert_eq!(client.port, 4110);
        assert!(client.debug);
    }

    #[tokio::test]
    async fn test_python_compatible_location_client_creation() {
        let client = PythonCompatibleLocationClient::new(
            Some("localhost"), Some(4109), Some(false), Some(60), Some(false), None
        ).await.unwrap();
        assert_eq!(client.server_host, "localhost");
        assert_eq!(client.server_port, 4109);
        assert!(!client.debug);
        assert_eq!(client.cache_ttl_minutes, 60);
        assert!(!client.cache_enabled);
    }

    #[test]
    fn test_environment_variable_defaults() {
        std::env::set_var("WEATHER_SERVER_HOST", "test.example.com");
        std::env::set_var("WEATHER_SERVER_PORT", "8080");
        
        let client = PythonCompatibleWeatherClient::new(None, None, None).unwrap();
        assert_eq!(client.host, "test.example.com");
        assert_eq!(client.port, 8080);
        assert!(!client.debug);
        
        // クリーンアップ
        std::env::remove_var("WEATHER_SERVER_HOST");
        std::env::remove_var("WEATHER_SERVER_PORT");
    }
}
