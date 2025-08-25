use crate::wip_common_rs::clients::{
    location_client::{LocationClient, LocationClientImpl},
    query_client::{QueryClient, QueryClientImpl},
    report_client::{ReportClient, ReportClientImpl},
    weather_client::WeatherClient,
};
use crate::wip_common_rs::packet::types::{
    query_packet::{QueryRequest, QueryResponse},
    report_packet::{ReportRequest, ReportResponse},
};
use std::error::Error;

/// Python版と同等の統合クライアント
///
/// Weather/Location/Query/Report の各クライアントを内部で保持し、
/// 高レベルAPIを提供する。
#[derive(Debug)]
pub struct WipClient {
    pub weather_client: WeatherClient,
    pub location_client: LocationClientImpl,
    pub query_client: QueryClientImpl,
    pub report_client: ReportClientImpl,
    area_code: Option<u32>,
    coordinates: Option<(f64, f64)>,
}

impl WipClient {
    /// すべてのサーバーに接続する新しいクライアントを生成する。
    pub async fn new(
        host: &str,
        weather_port: u16,
        location_port: u16,
        query_port: u16,
        report_port: u16,
        debug: bool,
    ) -> Result<Self, Box<dyn Error + Send + Sync>> {
        let weather_client = WeatherClient::new(host, weather_port, debug)?;
        let location_client = LocationClientImpl::new(host, location_port).await?;
        let query_client = QueryClientImpl::new(host, query_port).await?;
        let report_client = ReportClientImpl::new(host, report_port).await?;
        Ok(Self {
            weather_client,
            location_client,
            query_client,
            report_client,
            area_code: None,
            coordinates: None,
        })
    }

    /// エリアコードを直接設定する。
    pub fn set_area_code(&mut self, area_code: u32) {
        self.area_code = Some(area_code);
    }

    /// 座標を設定し、LocationClientでエリアコードを解決する。
    pub async fn set_coordinates(
        &mut self,
        latitude: f64,
        longitude: f64,
    ) -> Result<u32, Box<dyn Error + Send + Sync>> {
        let area_code = self
            .location_client
            .resolve_coordinates(latitude, longitude)
            .await?;
        self.coordinates = Some((latitude, longitude));
        self.area_code = Some(area_code);
        Ok(area_code)
    }

    /// 現在設定されているエリアコードで気象データを取得する。
    pub async fn get_weather(
        &mut self,
        weather: bool,
        temperature: bool,
        precipitation: bool,
        alert: bool,
        disaster: bool,
        day: u8,
        proxy: bool,
    ) -> Result<Option<QueryResponse>, Box<dyn Error + Send + Sync>> {
        let area_code = match self.area_code {
            Some(code) => code,
            None => {
                if let Some((lat, lng)) = self.coordinates {
                    let code = self
                        .location_client
                        .resolve_coordinates(lat, lng)
                        .await?;
                    self.area_code = Some(code);
                    code
                } else {
                    return Err("area code or coordinates not set".into());
                }
            }
        };

        if proxy {
            let resp = self.weather_client.get_weather_simple(
                area_code,
                weather,
                temperature,
                precipitation,
                alert,
                disaster,
                day,
            )?;
            Ok(resp)
        } else {
            let query = QueryRequest::new(
                area_code,
                0,
                weather,
                temperature,
                precipitation,
                alert,
                disaster,
                day,
            );
            let resp = self.query_client.execute_query(query).await?;
            Ok(Some(resp))
        }
    }

    /// ReportServerにレポートを送信する。
    pub async fn send_report(
        &self,
        report: ReportRequest,
    ) -> Result<ReportResponse, Box<dyn Error + Send + Sync>> {
        self.report_client.send_report(report).await
    }

    /// 低レベルのReportClient実装へのアクセスを提供する。
    pub fn report_client(&self) -> &ReportClientImpl {
        &self.report_client
    }
}

