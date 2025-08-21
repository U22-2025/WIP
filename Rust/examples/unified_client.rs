/// Pythonクライアント同様にオプションで異なるリクエストタイプを切り替えられる統合クライアント
use std::env;
use std::process;
use wip_rust::prelude::*;
use wip_rust::wip_common_rs::clients::{
    location_client::{LocationClient, LocationClientImpl},
    report_client::{ReportClient, ReportClientImpl, ReportClientConfig},
    utils::packet_id_generator::PacketIDGenerator12Bit,
};

use wip_rust::wip_common_rs::packet::types::report_packet::ReportRequest;

use tokio::runtime::Runtime;

#[derive(Debug)]
struct ClientArgs {
    // Mode flags
    use_coordinates: bool,
    use_proxy: bool,
    debug_enabled: bool,
    use_report: bool,
    
    // Data values
    area_code: u32,
    weather_code: u16,
    pops: u8,
    temperature: f64,
    alerts: Vec<String>,
    disasters: Vec<String>,
    latitude: f64,
    longitude: f64,
}

impl Default for ClientArgs {
    fn default() -> Self {
        Self {
            use_coordinates: false,
            use_proxy: false,
            debug_enabled: false,
            use_report: false,
            area_code: 460010, // 名古屋
            weather_code: 100, // 晴れ
            pops: 30,
            temperature: 25.0,
            alerts: Vec::new(),
            disasters: Vec::new(),
            latitude: 35.6895, // 東京
            longitude: 139.6917, // 東京
        }
    }
}

fn parse_args() -> ClientArgs {
    let args: Vec<String> = env::args().collect();
    let mut client_args = ClientArgs::default();
    
    // Parse flags
    client_args.use_coordinates = args.contains(&"--coord".to_string());
    client_args.use_proxy = args.contains(&"--proxy".to_string());
    client_args.debug_enabled = args.contains(&"--debug".to_string());
    client_args.use_report = args.contains(&"--report".to_string());
    
    // Parse values
    if let Some(pos) = args.iter().position(|x| x == "--area") {
        if let Some(val) = args.get(pos + 1) {
            if let Ok(area) = val.parse::<u32>() {
                client_args.area_code = area;
            } else {
                eprintln!("無効なエリアコード: {}, デフォルト値を使用します", val);
            }
        }
    }
    
    if let Some(pos) = args.iter().position(|x| x == "--weather") {
        if let Some(val) = args.get(pos + 1) {
            if let Ok(weather) = val.parse::<u16>() {
                client_args.weather_code = weather;
            } else {
                eprintln!("無効な天気コード: {}, デフォルト値を使用します", val);
            }
        }
    }
    
    if let Some(pos) = args.iter().position(|x| x == "--pops") {
        if let Some(val) = args.get(pos + 1) {
            if let Ok(pops) = val.parse::<u8>() {
                client_args.pops = pops;
            } else {
                eprintln!("無効な降水確率: {}, デフォルト値を使用します", val);
            }
        }
    }
    
    if let Some(pos) = args.iter().position(|x| x == "--temp") {
        if let Some(val) = args.get(pos + 1) {
            if let Ok(temp) = val.parse::<f64>() {
                client_args.temperature = temp;
            } else {
                eprintln!("無効な温度値: {}, デフォルト値を使用します", val);
            }
        }
    }
    
    if let Some(pos) = args.iter().position(|x| x == "--lat") {
        if let Some(val) = args.get(pos + 1) {
            if let Ok(lat) = val.parse::<f64>() {
                client_args.latitude = lat;
            } else {
                eprintln!("無効な緯度: {}, デフォルト値を使用します", val);
            }
        }
    }
    
    if let Some(pos) = args.iter().position(|x| x == "--lon") {
        if let Some(val) = args.get(pos + 1) {
            if let Ok(lon) = val.parse::<f64>() {
                client_args.longitude = lon;
            } else {
                eprintln!("無効な経度: {}, デフォルト値を使用します", val);
            }
        }
    }
    
    if let Some(pos) = args.iter().position(|x| x == "--alert") {
        if let Some(val) = args.get(pos + 1) {
            client_args.alerts = val.split(',').map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect();
        }
    }
    
    if let Some(pos) = args.iter().position(|x| x == "--disaster") {
        if let Some(val) = args.get(pos + 1) {
            client_args.disasters = val.split(',').map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect();
        }
    }
    
    client_args
}

fn print_args(args: &ClientArgs) {
    println!("\nコマンドライン引数解析結果:");
    println!("use_coordinates: {}", args.use_coordinates);
    println!("use_proxy: {}", args.use_proxy);
    println!("debug_enabled: {}", args.debug_enabled);
    println!("use_report: {}", args.use_report);
    println!("area_code: {} (型: {})", args.area_code, std::any::type_name::<u32>());
    println!("weather_code: {}", args.weather_code);
    println!("pops: {}", args.pops);
    println!("temperature: {}", args.temperature);
    println!("alerts: {:?}", args.alerts);
    println!("disasters: {:?}", args.disasters);
    println!("latitude: {}", args.latitude);
    println!("longitude: {}", args.longitude);
    println!("{}", "=".repeat(60));
}

async fn handle_report_mode(args: &ClientArgs) -> Result<(), Box<dyn std::error::Error>> {
    println!("Weather Client Example - Report Mode");
    println!("Report mode enabled - Data will be sent to Report Server");
    println!("{}", "=".repeat(60));
    
    println!("\n=== Report Mode: Sending dummy data to Report Server ===");
    println!("{}", "-".repeat(55));
    
    println!("\nレポートデータ作成前の変数値:");
    println!("area_code: {} (型: {})", args.area_code, std::any::type_name::<u32>());
    println!("weather_code: {}", args.weather_code);
    println!("temperature: {}", args.temperature);
    println!("pops: {}", args.pops);
    println!("alerts: {:?}", args.alerts);
    println!("disasters: {:?}", args.disasters);
    
    println!("Using sensor data from command line:");
    println!("  area_code: {}", args.area_code);
    println!("  weather_code: {}", args.weather_code);
    println!("  temperature: {}", args.temperature);
    println!("  pops: {}", args.pops);
    println!("  alert: {:?}", args.alerts);
    println!("  disaster: {:?}", args.disasters);
    
    println!("\nSending report to Report Server...");
    
    let (report_host, report_port) = if args.use_proxy {
        let host = env::var("WEATHER_SERVER_HOST").unwrap_or_else(|_| "localhost".to_string());
        let port = env::var("WEATHER_SERVER_PORT")
            .unwrap_or_else(|_| "4110".to_string())
            .parse::<u16>()
            .unwrap_or(4110);
        println!("Using proxy mode - sending via Weather Server ({}:{})", host, port);
        (host, port)
    } else {
        let host = env::var("REPORT_SERVER_HOST").unwrap_or_else(|_| "localhost".to_string());
        let port = env::var("REPORT_SERVER_PORT")
            .unwrap_or_else(|_| "4112".to_string())
            .parse::<u16>()
            .unwrap_or(4112);
        println!("Using direct mode - sending directly to Report Server ({}:{})", host, port);
        (host, port)
    };
    
    let mut config = ReportClientConfig::default();
    config.enable_debug = args.debug_enabled;
    let report_client = ReportClientImpl::with_config(&report_host, report_port, config).await?;
    
    let start_time = std::time::Instant::now();
    
    // ReportRequestを作成
    let mut pidg = PacketIDGenerator12Bit::new();
    let packet_id = pidg.next_id();
    
    let mut report_request = ReportRequest::create_sensor_data_report(
        &args.area_code.to_string(),
        Some(args.weather_code),
        Some(args.temperature),
        Some(args.pops),
        if args.alerts.is_empty() { None } else { Some(args.alerts.clone()) },
        if args.disasters.is_empty() { None } else { Some(args.disasters.clone()) },
        1, // version
        packet_id,
    );
    
    // 認証が有効な場合（環境変数またはデフォルトのパスフレーズを使用）
    if let Ok(passphrase) = std::env::var("WIP_AUTH_PASSPHRASE") {
        report_request.enable_auth(&passphrase);
        report_request.set_auth_flags();
        
        if args.debug_enabled {
            println!("Debug: Authentication enabled with passphrase");
        }
    } else {
        // デフォルトのパスフレーズを使用（テスト用）
        let default_passphrase = "test_passphrase";
        report_request.enable_auth(default_passphrase);
        report_request.set_auth_flags();
        
        if args.debug_enabled {
            println!("Debug: Authentication enabled with default passphrase: {}", default_passphrase);
        }
    }
    
    match report_client.send_report(report_request).await {
        Ok(result) => {
            let elapsed_time = start_time.elapsed();
            println!("\nOK Report sent successfully! (Execution time: {:.3}s)", elapsed_time.as_secs_f64());
            println!("=== Report Response ===");
            println!("Response: {:?}", result);
            println!("=======================");
        }
        Err(e) => {
            println!("\n✗ Failed to send report to Report Server: {}", e);
            if args.debug_enabled {
                eprintln!("Debug: {:?}", e);
            }
        }
    }
    
    println!("\n{}", "=".repeat(60));
    println!("Report mode completed");
    Ok(())
}

async fn handle_normal_mode(args: &ClientArgs) -> Result<(), Box<dyn std::error::Error>> {
    if args.use_proxy {
        println!("Weather Client Example - Via Weather Server (Proxy Mode)");
    } else {
        println!("Weather Client Example - Direct Communication");
    }
    println!("{}", "=".repeat(60));
    
    let start_time = std::time::Instant::now();
    
    let result = if args.use_coordinates {
        println!("\n1. Coordinate-based request using Rust WeatherClient");
        println!("{}", "-".repeat(50));
        
        // 座標からエリアコードを取得
        let (location_host, location_port) = if args.use_proxy {
            ("127.0.0.1", 4110) // プロキシモード: WeatherServer経由
        } else {
            ("127.0.0.1", 4109) // ダイレクトモード: LocationServer直接
        };
        
        let location_client = LocationClientImpl::new(location_host, location_port).await?;
        
        match location_client.resolve_coordinates(args.latitude, args.longitude).await {
            Ok(area_code) => {
                println!("座標 ({}, {}) がエリアコード {} に解決されました", args.latitude, args.longitude, area_code);
                
                // 天気データを取得
                let (weather_host, weather_port) = if args.use_proxy {
                    ("127.0.0.1", 4110) // プロキシモード: WeatherServer経由
                } else {
                    ("127.0.0.1", 4111) // ダイレクトモード: QueryServer直接
                };
                
                let mut client = WeatherClient::new(weather_host, weather_port, args.debug_enabled)
                    .map_err(|e| format!("Failed to create weather client: {}", e))?;
                
                client.get_weather_simple(area_code, true, true, true, false, false, 0)
            }
            Err(e) => {
                eprintln!("座標解決エラー: {}. デフォルトエリアコードを使用します", e);
                
                // デフォルトエリアコードで天気データを取得
                let (weather_host, weather_port) = if args.use_proxy {
                    ("127.0.0.1", 4110) // プロキシモード: WeatherServer経由
                } else {
                    ("127.0.0.1", 4111) // ダイレクトモード: QueryServer直接
                };
                
                let mut client = WeatherClient::new(weather_host, weather_port, args.debug_enabled)
                    .map_err(|e| format!("Failed to create weather client: {}", e))?;
                
                client.get_weather_simple(args.area_code, true, true, true, false, false, 0)
            }
        }
    } else {
        println!("\n1. Area code request using Rust WeatherClient");
        println!("{}", "-".repeat(40));
        
        // 天気データを取得
        let (weather_host, weather_port) = if args.use_proxy {
            ("127.0.0.1", 4110) // プロキシモード: WeatherServer経由
        } else {
            ("127.0.0.1", 4111) // ダイレクトモード: QueryServer直接
        };
        
        let mut client = WeatherClient::new(weather_host, weather_port, args.debug_enabled)
            .map_err(|e| format!("Failed to create weather client: {}", e))?;
        
        client.get_weather_simple(args.area_code, true, true, true, false, false, 0)
    };
    
    match result {
        Ok(Some(weather_resp)) => {
            let elapsed_time = start_time.elapsed();
            println!("\nOK Request successful! (Execution time: {:.3}s)", elapsed_time.as_secs_f64());
            println!("  area_code: {}", weather_resp.area_code);
            if let Some(weather_code) = weather_resp.weather_code {
                println!("  weather_code: {}", weather_code);
            }
            if let Some(temperature) = weather_resp.temperature {
                println!("  temperature: {}°C", temperature);
            }
            if let Some(precipitation) = weather_resp.precipitation {
                println!("  precipitation_prob: {}%", precipitation);
            }
            println!("  version: {}", weather_resp.version);
            println!("  packet_id: {}", weather_resp.packet_id);
        }
        Ok(None) => {
            println!("\n✗ No response received from server");
        }
        Err(e) => {
            println!("\n✗ Failed to get weather data: {}", e);
            if args.debug_enabled {
                eprintln!("Debug: {:?}", e);
            }
        }
    }
    
    Ok(())
}

fn main() {
    let args = parse_args();
    print_args(&args);
    
    let rt = Runtime::new().unwrap();
    let result = rt.block_on(async {
        if args.use_report {
            handle_report_mode(&args).await
        } else {
            handle_normal_mode(&args).await
        }
    });
    
    if let Err(e) = result {
        eprintln!("Error: {}", e);
        process::exit(1);
    }
}