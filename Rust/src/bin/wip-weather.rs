use clap::{Parser, Subcommand};
use log::debug;
use std::{env, error::Error};
use wip_rust::wip_common_rs::client::WipClient;
use wip_rust::wip_common_rs::clients::location_client::{LocationClient, LocationClientImpl};

#[derive(Parser)]
#[command(name = "wip-weather")]
#[command(about = "WIP Weather Client - 気象データ取得ツール")]
#[command(version = "0.1.0")]
struct Cli {
    /// サーバーホスト
    #[arg(short = 'H', long, default_value = "127.0.0.1")]
    host: String,

    /// サーバーポート (デフォルト: 4110)
    #[arg(short, long, default_value = "4110")]
    port: u16,

    /// デバッグモード
    #[arg(short, long)]
    debug: bool,

    /// 認証トークン
    #[arg(short, long)]
    auth_token: Option<String>,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// エリアコードから気象データを取得
    Get {
        /// エリアコード (例: 11000)
        area_code: u32,

        /// 天気コードを取得
        #[arg(short, long)]
        weather: bool,

        /// 気温を取得
        #[arg(short, long)]
        temperature: bool,

        /// 降水確率を取得
        #[arg(short = 'p', long)]
        precipitation: bool,

        /// 警報情報を取得
        #[arg(short = 'A', long)]
        alerts: bool,

        /// 災害情報を取得
        #[arg(short = 'D', long)]
        disaster: bool,

        /// 対象日 (0=今日, 1=明日, 2=明後日)
        #[arg(short = 'T', long, default_value = "0")]
        day: u8,
    },
    /// 座標から気象データを取得
    Coords {
        /// 緯度
        latitude: f64,

        /// 経度
        longitude: f64,

        /// 天気コードを取得
        #[arg(short, long)]
        weather: bool,

        /// 気温を取得
        #[arg(short, long)]
        temperature: bool,

        /// 降水確率を取得
        #[arg(short = 'p', long)]
        precipitation: bool,

        /// 警報情報を取得
        #[arg(short = 'A', long)]
        alerts: bool,

        /// 災害情報を取得
        #[arg(short = 'D', long)]
        disaster: bool,

        /// 対象日 (0=今日, 1=明日, 2=明後日)
        #[arg(short = 'T', long, default_value = "0")]
        day: u8,
    },
    /// 複数日の予報を取得
    Forecast {
        /// エリアコード
        area_code: u32,

        /// 予報日数 (1-7)
        #[arg(short = 'T', long, default_value = "3")]
        days: u8,
    },
}

fn weather_code_to_string(code: u16) -> &'static str {
    match code {
        100..=199 => "晴れ",
        200..=299 => "曇り",
        300..=399 => "雨",
        400..=499 => "雪",
        500..=599 => "霧",
        600..=699 => "雷",
        700..=799 => "強風",
        800..=899 => "台風",
        _ => "不明",
    }
}

fn print_weather_response(response: &wip_rust::wip_common_rs::packet::types::query_packet::QueryResponse) {
    println!("=== 気象データ ===");
    println!("エリアコード: {}", response.area_code);
    println!("パケットID: {}", response.packet_id);
    println!("バージョン: {}", response.version);

    if let Some(weather_code) = response.weather_code {
        println!("天気: {} (コード: {})", weather_code_to_string(weather_code), weather_code);
    }

    if let Some(temperature) = response.temperature {
        println!("気温: {}°C", temperature);
    }

    if let Some(precipitation) = response.precipitation {
        println!("降水確率: {}%", precipitation);
    }

    if let Some(alerts) = response.get_alert() {
        if !alerts.is_empty() {
            println!("警報: {}", alerts.join(", "));
        }
    }

    if let Some(disaster) = response.get_disaster() {
        if !disaster.is_empty() {
            println!("災害情報: {}", disaster.join(", "));
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let cli = Cli::parse();

    if cli.debug {
        env_logger::init();
    }

    let mut client = WipClient::new(&cli.host, cli.port, 4109, cli.port, 4112, cli.debug).await?;

    if let Some(_token) = cli.auth_token {
        println!("⚠️ 認証トークン機能は現在実装中です");
    }

    match cli.command {
        Commands::Get {
            area_code,
            weather,
            temperature,
            precipitation,
            alerts,
            disaster,
            day,
        } => {
            println!("エリアコード {} の気象データを取得中...", area_code);
            client.set_area_code(area_code);
            match client.get_weather(weather, temperature, precipitation, alerts, disaster, day).await? {
                Some(response) => {
                    print_weather_response(&response);
                }
                None => {
                    println!("❌ レスポンスを取得できませんでした");
                }
            }
        }

        Commands::Coords {
            latitude,
            longitude,
            weather,
            temperature,
            precipitation,
            alerts,
            disaster,
            day,
        } => {
            // 座標から気象データを取得する場合は、位置解決サービスを使用する
            println!("座標 ({:.4}, {:.4}) から気象データを取得中...", latitude, longitude);
            println!("注意: この機能には位置解決サービスとの連携が必要です");

            let loc_host = env::var("LOCATION_SERVER_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
            let loc_port = env::var("LOCATION_SERVER_PORT")
                .ok()
                .and_then(|v| v.parse::<u16>().ok())
                .unwrap_or(4109);
            debug!("Location server: {}:{}", loc_host, loc_port);

            let loc_client = match LocationClientImpl::new(&loc_host, loc_port).await {
                Ok(c) => c,
                Err(e) => {
                    println!("❌ Locationクライアントの初期化に失敗しました: {}", e);
                    return Ok(());
                }
            };

            let area_code = match loc_client.resolve_coordinates(latitude, longitude).await {
                Ok(code) => {
                    debug!("Resolved area code: {}", code);
                    code
                }
                Err(e) => {
                    println!("❌ 座標の解決に失敗しました: {}", e);
                    return Ok(());
                }
            };

            println!("取得エリアコード: {}", area_code);
            client.set_area_code(area_code);
            match client.get_weather(weather, temperature, precipitation, alerts, disaster, day).await? {
                Some(response) => {
                    print_weather_response(&response);
                }
                None => {
                    println!("❌ レスポンスを取得できませんでした");
                }
            }
        }

        Commands::Forecast { area_code, days } => {
            println!("エリアコード {} の{}日間予報を取得中...", area_code, days);

            for day in 0..days.min(7) {
                let day_name = match day {
                    0 => "今日",
                    1 => "明日", 
                    2 => "明後日",
                    _ => &format!("{}日後", day),
                };

                println!("\n--- {} ---", day_name);

                client.set_area_code(area_code);
                match client.get_weather(true, true, true, false, false, day).await? {
                    Some(response) => {
                        if let Some(weather_code) = response.weather_code {
                            println!("天気: {}", weather_code_to_string(weather_code));
                        }
                        if let Some(temperature) = response.temperature {
                            println!("気温: {}°C", temperature);
                        }
                        if let Some(precipitation) = response.precipitation {
                            println!("降水確率: {}%", precipitation);
                        }
                    }
                    None => {
                        println!("データなし");
                    }
                }

                // サーバー負荷軽減のため少し待機
                tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
            }
        }
    }

    Ok(())
}
