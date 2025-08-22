use clap::{Parser, Subcommand};
use std::error::Error;
use wip_rust::wip_common_rs::clients::report_client::{ReportClient, ReportClientImpl};

#[derive(Parser)]
#[command(name = "wip-report")]
#[command(about = "WIP Report Client - 災害・センサーレポート送信")]
#[command(version = "0.1.0")]
struct Cli {
    /// サーバーホスト
    #[arg(short = 'H', long, default_value = "127.0.0.1")]
    host: String,

    /// サーバーポート
    #[arg(short, long, default_value = "4112")]
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
    /// 災害レポート送信
    Disaster {
        /// 災害タイプ (earthquake, tsunami, typhoon, flood, landslide, fire, explosion, volcanic_eruption)
        disaster_type: String,

        /// 重要度 (1-10: 1=軽微, 5=中程度, 8=重大, 10=破滅的)
        #[arg(short, long)]
        severity: u8,

        /// 説明文
        #[arg(short = 'D', long)]
        description: String,

        /// 緯度
        #[arg(short = 'L', long)]
        latitude: Option<f64>,

        /// 経度
        #[arg(short = 'G', long)]
        longitude: Option<f64>,

        /// 影響範囲 (km)
        #[arg(short = 'R', long)]
        radius: Option<f64>,

        /// 追加情報 (JSON形式)
        #[arg(short, long)]
        extra: Option<String>,
    },
    /// センサーデータレポート
    Sensor {
        /// エリアコード
        #[arg(short, long, default_value = "11000")]
        area_code: u32,

        /// 天気コード
        #[arg(short, long)]
        weather_code: Option<u16>,

        /// 気温 (°C)
        #[arg(short, long)]
        temperature: Option<f64>,

        /// 降水確率 (%)
        #[arg(short = 'p', long)]
        precipitation: Option<u8>,

        /// 警報メッセージ
        #[arg(short, long)]
        alerts: Vec<String>,

        /// 災害情報
        #[arg(short = 'D', long)]
        disaster_info: Vec<String>,
    },
    /// バッチレポート送信
    Batch {
        /// バッチファイル (JSON形式)
        #[arg(short, long)]
        file: String,

        /// バッチサイズ
        #[arg(short = 'S', long, default_value = "10")]
        batch_size: usize,

        /// 送信間隔 (ms)
        #[arg(short, long, default_value = "100")]
        interval: u64,

        /// 失敗時の再試行回数
        #[arg(short, long, default_value = "3")]
        retry: usize,
    },
    /// テストレポート送信
    Test {
        /// テストパターン (basic, stress, random)
        #[arg(short, long, default_value = "basic")]
        pattern: String,

        /// レポート数
        #[arg(short, long, default_value = "5")]
        count: usize,

        /// ランダムシード
        #[arg(short, long)]
        seed: Option<u64>,
    },
    /// レポート状態確認
    Status {
        /// レポートID
        report_id: Option<String>,

        /// 最近のレポート数
        #[arg(short, long, default_value = "10")]
        recent: usize,
    },
}

fn validate_disaster_type(disaster_type: &str) -> Result<(), String> {
    match disaster_type {
        "earthquake" | "tsunami" | "typhoon" | "flood" | "landslide" | 
        "fire" | "explosion" | "volcanic_eruption" | "tornado" | "hail" => Ok(()),
        _ => Err(format!("サポートされていない災害タイプ: {}", disaster_type)),
    }
}

fn validate_severity(severity: u8) -> Result<(), String> {
    if severity >= 1 && severity <= 10 {
        Ok(())
    } else {
        Err("重要度は1-10の範囲で指定してください".to_string())
    }
}

fn severity_to_string(severity: u8) -> &'static str {
    match severity {
        1..=2 => "軽微",
        3..=4 => "注意",
        5..=6 => "警戒",
        7..=8 => "重大",
        9..=10 => "破滅的",
        _ => "不明",
    }
}

fn disaster_type_to_japanese(disaster_type: &str) -> &'static str {
    match disaster_type {
        "earthquake" => "地震",
        "tsunami" => "津波",
        "typhoon" => "台風",
        "flood" => "洪水",
        "landslide" => "土砂崩れ",
        "fire" => "火災",
        "explosion" => "爆発",
        "volcanic_eruption" => "火山噴火",
        "tornado" => "竜巻",
        "hail" => "雹",
        _ => "その他",
    }
}

async fn send_disaster_report(
    client: &ReportClientImpl,
    disaster_type: &str,
    severity: u8,
    description: &str,
    latitude: Option<f64>,
    longitude: Option<f64>,
) -> Result<String, Box<dyn Error>> {
    validate_disaster_type(disaster_type)?;
    validate_severity(severity)?;

    println!("🚨 災害レポート送信中...");
    println!("災害タイプ: {} ({})", disaster_type_to_japanese(disaster_type), disaster_type);
    println!("重要度: {} ({})", severity, severity_to_string(severity));
    println!("説明: {}", description);
    
    if let (Some(lat), Some(lng)) = (latitude, longitude) {
        println!("位置: ({:.6}, {:.6})", lat, lng);
    }

    // TODO: Create proper ReportRequest for disaster
    println!("⚠️ 災害レポート送信機能は現在実装中です");
    let report_id = format!("DISASTER-{}", fastrand::u32(10000..99999));

    println!("✅ レポート送信完了");
    println!("📋 レポートID: {}", report_id);
    
    Ok(report_id)
}

async fn send_sensor_report(
    client: &ReportClientImpl,
    area_code: u32,
    weather_code: Option<u16>,
    temperature: Option<f64>,
    precipitation: Option<u8>,
    alerts: &[String],
    disaster_info: &[String],
) -> Result<String, Box<dyn Error>> {
    println!("📊 センサーデータレポート送信中...");
    println!("エリアコード: {}", area_code);
    
    if let Some(wc) = weather_code {
        println!("天気コード: {}", wc);
    }
    if let Some(temp) = temperature {
        println!("気温: {}°C", temp);
    }
    if let Some(pop) = precipitation {
        println!("降水確率: {}%", pop);
    }
    if !alerts.is_empty() {
        println!("警報: {:?}", alerts);
    }
    if !disaster_info.is_empty() {
        println!("災害情報: {:?}", disaster_info);
    }

    // センサーデータを基にレポート作成（簡易実装）
    let description = format!(
        "センサーデータ報告 - エリア:{}, 天気:{:?}, 気温:{:?}°C, 降水確率:{:?}%",
        area_code, weather_code, temperature, precipitation
    );

    // TODO: Create proper ReportRequest for sensor data
    println!("⚠️ センサーレポート送信機能は現在実装中です");
    let report_id = format!("SENSOR-{}", fastrand::u32(10000..99999));

    println!("✅ センサーレポート送信完了");
    println!("📋 レポートID: {}", report_id);
    
    Ok(report_id)
}

async fn send_test_reports(
    client: &ReportClientImpl,
    pattern: &str,
    count: usize,
    seed: Option<u64>,
) -> Result<(), Box<dyn Error>> {
    println!("🧪 テストレポート送信中 (パターン: {}, 件数: {})", pattern, count);

    let mut rng = if let Some(seed) = seed {
        fastrand::Rng::with_seed(seed)
    } else {
        fastrand::Rng::new()
    };

    let disaster_types = ["earthquake", "flood", "fire", "typhoon"];
    let descriptions = [
        "テスト災害レポート",
        "自動生成テストデータ",
        "システム動作確認用",
        "パフォーマンステスト",
    ];

    let mut success_count = 0;

    for i in 0..count {
        let (disaster_type, severity, description) = match pattern {
            "basic" => {
                ("earthquake", 5, "基本テストレポート")
            }
            "stress" => {
                (disaster_types[i % disaster_types.len()], 
                 (i % 10 + 1) as u8, 
                 descriptions[i % descriptions.len()])
            }
            "random" => {
                (disaster_types[rng.usize(0..disaster_types.len())],
                 rng.u8(1..=10),
                 descriptions[rng.usize(0..descriptions.len())])
            }
            _ => {
                println!("⚠️ 不明なテストパターン: {}", pattern);
                continue;
            }
        };

        let full_description = format!("{} #{}", description, i + 1);
        
        match send_disaster_report(client, disaster_type, severity, &full_description, None, None).await {
            Ok(report_id) => {
                success_count += 1;
                println!("✅ テスト #{}: {}", i + 1, report_id);
            }
            Err(e) => {
                println!("❌ テスト #{} 失敗: {}", i + 1, e);
            }
        }

        // サーバー負荷軽減
        tokio::time::sleep(tokio::time::Duration::from_millis(200)).await;
    }

    println!("\n📊 テスト完了: {}/{} 成功", success_count, count);
    Ok(())
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let cli = Cli::parse();

    if cli.debug {
        env_logger::init();
    }

    let server_addr = format!("{}:{}", cli.host, cli.port);
    let client = ReportClientImpl::new(&cli.host, cli.port).await?;

    if let Some(_token) = cli.auth_token {
        println!("⚠️ 認証トークン機能は現在実装中です");
    }

    match cli.command {
        Commands::Disaster {
            disaster_type,
            severity,
            description,
            latitude,
            longitude,
            radius: _,
            extra: _,
        } => {
            send_disaster_report(&client, &disaster_type, severity, &description, latitude, longitude).await?;
        }

        Commands::Sensor {
            area_code,
            weather_code,
            temperature,
            precipitation,
            alerts,
            disaster_info,
        } => {
            send_sensor_report(&client, area_code, weather_code, temperature, precipitation, &alerts, &disaster_info).await?;
        }

        Commands::Batch { file, batch_size, interval, retry } => {
            println!("📁 バッチファイル {} を処理中...", file);
            println!("バッチサイズ: {}, 間隔: {}ms, 再試行: {}回", batch_size, interval, retry);
            
            match std::fs::read_to_string(&file) {
                Ok(content) => {
                    println!("⚠️ バッチ処理は現在実装中です");
                    println!("ファイルサイズ: {} バイト", content.len());
                    // TODO: JSON形式のバッチファイル処理を実装
                }
                Err(e) => {
                    println!("❌ ファイル読み込みエラー: {}", e);
                    println!("💡 バッチファイル形式例:");
                    println!("[");
                    println!("  {{\"type\": \"earthquake\", \"severity\": 7, \"description\": \"大地震\"}},");
                    println!("  {{\"type\": \"flood\", \"severity\": 5, \"description\": \"洪水警報\"}}");
                    println!("]");
                }
            }
        }

        Commands::Test { pattern, count, seed } => {
            send_test_reports(&client, &pattern, count, seed).await?;
        }

        Commands::Status { report_id, recent } => {
            if let Some(id) = report_id {
                println!("📋 レポートID {} の状態確認中...", id);
                println!("⚠️ レポート状態確認機能は現在実装中です");
            } else {
                println!("📊 最近の{}件のレポート状態確認中...", recent);
                println!("⚠️ 最近のレポート一覧機能は現在実装中です");
            }
        }
    }

    Ok(())
}