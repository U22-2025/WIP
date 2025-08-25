use clap::{Parser, Subcommand};
use std::error::Error;
use wip_rust::wip_common_rs::clients::location_client::{LocationClient, LocationClientImpl};

#[derive(Parser)]
#[command(name = "wip-location")]
#[command(about = "WIP Location Client - 位置情報サービス")]
#[command(version = "0.1.0")]
struct Cli {
    /// サーバーホスト
    #[arg(short = 'H', long, default_value = "127.0.0.1")]
    host: String,

    /// サーバーポート
    #[arg(short, long, default_value = "4109")]
    port: u16,

    /// デバッグモード
    #[arg(short, long)]
    debug: bool,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// 座標からエリアコードを解決
    Resolve {
        /// 緯度
        latitude: f64,

        /// 経度
        longitude: f64,

        /// 詳細情報も表示
        #[arg(short, long)]
        verbose: bool,
    },
    /// 複数の座標を一括解決
    Batch {
        /// 座標ファイル（1行につき "lat,lng,name" 形式）
        #[arg(short, long)]
        file: String,
    },
    /// 主要都市の座標を解決
    Cities {
        /// 表示する都市数
        #[arg(short, long, default_value = "10")]
        count: usize,
    },
    /// 座標の検証
    Validate {
        /// 緯度
        latitude: f64,

        /// 経度
        longitude: f64,
    },
}

struct CityCoordinate {
    name: &'static str,
    latitude: f64,
    longitude: f64,
}

const MAJOR_CITIES: &[CityCoordinate] = &[
    CityCoordinate { name: "東京", latitude: 35.6812, longitude: 139.7671 },
    CityCoordinate { name: "大阪", latitude: 34.6937, longitude: 135.5023 },
    CityCoordinate { name: "札幌", latitude: 43.0642, longitude: 141.3469 },
    CityCoordinate { name: "福岡", latitude: 33.5904, longitude: 130.4017 },
    CityCoordinate { name: "名古屋", latitude: 35.1815, longitude: 136.9066 },
    CityCoordinate { name: "京都", latitude: 35.0116, longitude: 135.7681 },
    CityCoordinate { name: "神戸", latitude: 34.6901, longitude: 135.1956 },
    CityCoordinate { name: "仙台", latitude: 38.2682, longitude: 140.8694 },
    CityCoordinate { name: "広島", latitude: 34.3853, longitude: 132.4553 },
    CityCoordinate { name: "熊本", latitude: 32.7898, longitude: 130.7417 },
];

fn validate_coordinates(lat: f64, lng: f64) -> Result<(), String> {
    if lat < -90.0 || lat > 90.0 {
        return Err(format!("緯度が範囲外です: {} (有効範囲: -90.0 ～ 90.0)", lat));
    }
    if lng < -180.0 || lng > 180.0 {
        return Err(format!("経度が範囲外です: {} (有効範囲: -180.0 ～ 180.0)", lng));
    }
    Ok(())
}

fn is_in_japan(lat: f64, lng: f64) -> bool {
    lat >= 24.0 && lat <= 46.0 && lng >= 123.0 && lng <= 146.0
}

async fn resolve_single_coordinate(
    client: &LocationClientImpl,
    lat: f64,
    lng: f64,
    name: Option<&str>,
    verbose: bool,
) -> Result<(), Box<dyn Error>> {
    let display_name = name.unwrap_or("座標");
    
    println!("🌍 {} ({:.4}, {:.4}) を解決中...", display_name, lat, lng);
    
    if verbose {
        validate_coordinates(lat, lng)?;
        
        if is_in_japan(lat, lng) {
            println!("✅ 日本国内の座標です");
        } else {
            println!("⚠️ 日本国外の座標です");
        }
    }
    
    match client.resolve_coordinates(lat, lng).await {
        Ok(area_code) => {
            println!("✅ エリアコード: {}", area_code);
            
            if verbose {
                // エリアコードから地域名を推定
                let region_name = match area_code {
                    11000..=11999 => "東京都市圏",
                    12000..=12999 => "関西圏",
                    13000..=13999 => "北海道",
                    14000..=14999 => "九州",
                    15000..=15999 => "東北",
                    16000..=16999 => "中部",
                    17000..=17999 => "中国",
                    18000..=18999 => "四国",
                    _ => "その他の地域",
                };
                println!("📍 推定地域: {}", region_name);
            }
        }
        Err(e) => {
            println!("❌ 解決失敗: {}", e);
        }
    }
    
    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let cli = Cli::parse();

    if cli.debug {
        env_logger::init();
    }

    let server_addr = format!("{}:{}", cli.host, cli.port);
    let client = LocationClientImpl::new(&cli.host, cli.port).await?;

    match cli.command {
        Commands::Resolve { latitude, longitude, verbose } => {
            resolve_single_coordinate(&client, latitude, longitude, None, verbose).await?;
        }

        Commands::Batch { file } => {
            println!("📁 バッチファイル {} を処理中...", file);
            
            match std::fs::read_to_string(&file) {
                Ok(content) => {
                    let mut success_count = 0;
                    let mut total_count = 0;
                    
                    for (line_no, line) in content.lines().enumerate() {
                        if line.trim().is_empty() || line.starts_with('#') {
                            continue;
                        }
                        
                        let parts: Vec<&str> = line.split(',').collect();
                        if parts.len() < 2 {
                            println!("⚠️ 行 {}: 形式が正しくありません: {}", line_no + 1, line);
                            continue;
                        }
                        
                        let lat = match parts[0].trim().parse::<f64>() {
                            Ok(v) => v,
                            Err(_) => {
                                println!("⚠️ 行 {}: 緯度が正しくありません: {}", line_no + 1, parts[0]);
                                continue;
                            }
                        };
                        
                        let lng = match parts[1].trim().parse::<f64>() {
                            Ok(v) => v,
                            Err(_) => {
                                println!("⚠️ 行 {}: 経度が正しくありません: {}", line_no + 1, parts[1]);
                                continue;
                            }
                        };
                        
                        let name = if parts.len() >= 3 {
                            Some(parts[2].trim())
                        } else {
                            None
                        };
                        
                        total_count += 1;
                        
                        if resolve_single_coordinate(&client, lat, lng, name, false).await.is_ok() {
                            success_count += 1;
                        }
                        
                        // サーバー負荷軽減
                        tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
                    }
                    
                    println!("\n📊 バッチ処理完了: {}/{} 成功", success_count, total_count);
                }
                Err(e) => {
                    println!("❌ ファイル読み込みエラー: {}", e);
                    println!("💡 ファイル形式例:");
                    println!("35.6812,139.7671,東京");
                    println!("34.6937,135.5023,大阪");
                    println!("43.0642,141.3469,札幌");
                }
            }
        }

        Commands::Cities { count } => {
            println!("🏙️ 主要都市のエリアコード解決:");
            
            let cities_to_process = MAJOR_CITIES.iter().take(count);
            let mut success_count = 0;
            
            for city in cities_to_process {
                if resolve_single_coordinate(&client, city.latitude, city.longitude, Some(city.name), false).await.is_ok() {
                    success_count += 1;
                }
                
                // サーバー負荷軽減
                tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
            }
            
            println!("\n📊 {}/{} 都市の解決に成功", success_count, count.min(MAJOR_CITIES.len()));
        }

        Commands::Validate { latitude, longitude } => {
            println!("🔍 座標検証: ({:.6}, {:.6})", latitude, longitude);
            
            match validate_coordinates(latitude, longitude) {
                Ok(()) => {
                    println!("✅ 座標形式は正しいです");
                    
                    if is_in_japan(latitude, longitude) {
                        println!("✅ 日本国内の座標です");
                        
                        // 実際の解決を試行
                        match client.resolve_coordinates(latitude, longitude).await {
                            Ok(area_code) => {
                                println!("✅ エリアコード解決成功: {}", area_code);
                            }
                            Err(e) => {
                                println!("⚠️ エリアコード解決失敗: {}", e);
                            }
                        }
                    } else {
                        println!("⚠️ 日本国外の座標です");
                        println!("💡 WIPサービスは主に日本国内をサポートしています");
                    }
                    
                    // 最寄りの主要都市を表示
                    let mut min_distance = f64::MAX;
                    let mut nearest_city = None;
                    
                    for city in MAJOR_CITIES {
                        let distance = ((latitude - city.latitude).powi(2) + (longitude - city.longitude).powi(2)).sqrt();
                        if distance < min_distance {
                            min_distance = distance;
                            nearest_city = Some(city);
                        }
                    }
                    
                    if let Some(city) = nearest_city {
                        println!("📍 最寄りの主要都市: {} (距離: {:.2}度)", city.name, min_distance);
                    }
                }
                Err(e) => {
                    println!("❌ 座標検証エラー: {}", e);
                }
            }
        }
    }

    Ok(())
}