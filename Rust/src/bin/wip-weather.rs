use clap::{Parser, Subcommand};
use std::{env, error::Error};
use wip_rust::wip_common_rs::clients::weather_client::WeatherClient;

#[derive(Parser)]
#[command(name = "wip-weather")]
#[command(about = "WIP Weather Client - 気象データ取得ツール")]
#[command(version = "0.1.0")]
struct Cli {
    /// サーバーホスト
    #[arg(short = 'H', long)]
    host: Option<String>,

    /// サーバーポート
    #[arg(short, long)]
    port: Option<u16>,

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

fn print_weather_response(
    response: &wip_rust::wip_common_rs::packet::types::query_packet::QueryResponse,
) {
    println!("=== 気象データ ===");
    println!("エリアコード: {}", response.area_code);
    println!("パケットID: {}", response.packet_id);
    println!("バージョン: {}", response.version);

    if let Some(weather_code) = response.weather_code {
        println!(
            "天気: {} (コード: {})",
            weather_code_to_string(weather_code),
            weather_code
        );
    }

    if let Some(temperature) = response.temperature {
        println!("気温: {}°C", temperature);
    }

    if let Some(precipitation) = response.precipitation {
        println!("降水確率: {}%", precipitation);
    }

    // Note: alert_flag and disaster_flag are not available in current QueryResponse struct
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let cli = Cli::parse();

    if cli.debug {
        env_logger::init();
    }

    let env_host = env::var("WEATHER_SERVER_HOST").unwrap_or_else(|_| "127.0.0.1".to_string());
    let env_port = env::var("WEATHER_SERVER_PORT")
        .ok()
        .and_then(|p| p.parse().ok())
        .unwrap_or(4111);

    let host = cli.host.unwrap_or(env_host);
    let port = cli.port.unwrap_or(env_port);

    let mut client = WeatherClient::new(&host, port, cli.debug)?;

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

            match client.get_weather_simple(
                area_code,
                weather,
                temperature,
                precipitation,
                alerts,
                disaster,
                day,
            )? {
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
            // 座標から気象データを取得する場合は、まず座標をLocationRequestで送信する必要がある
            println!(
                "座標 ({:.4}, {:.4}) から気象データを取得中...",
                latitude, longitude
            );
            println!("注意: この機能には位置解決サービスとの連携が必要です");

            // 今のところ、座標から直接エリアコードを推定（簡易実装）
            let estimated_area_code = estimate_area_code_from_coords(latitude, longitude);
            println!("推定エリアコード: {}", estimated_area_code);

            match client.get_weather_simple(
                estimated_area_code,
                weather,
                temperature,
                precipitation,
                alerts,
                disaster,
                day,
            )? {
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

                match client.get_weather_simple(area_code, true, true, true, false, false, day)? {
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

// 簡易的な座標からエリアコード推定（実際には位置解決サービスを使用）
fn estimate_area_code_from_coords(lat: f64, lng: f64) -> u32 {
    // 日本の主要都市の座標範囲からエリアコードを推定
    if lat >= 35.6 && lat <= 35.8 && lng >= 139.6 && lng <= 139.8 {
        11000 // 東京
    } else if lat >= 34.6 && lat <= 34.8 && lng >= 135.4 && lng <= 135.6 {
        12000 // 大阪（仮想エリアコード）
    } else if lat >= 43.0 && lat <= 43.1 && lng >= 141.3 && lng <= 141.4 {
        13000 // 札幌（仮想エリアコード）
    } else if lat >= 33.5 && lat <= 33.7 && lng >= 130.3 && lng <= 130.5 {
        14000 // 福岡（仮想エリアコード）
    } else {
        11000 // デフォルトは東京
    }
}
