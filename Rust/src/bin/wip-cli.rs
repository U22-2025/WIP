use clap::{Parser, Subcommand};
use std::error::Error;

#[derive(Parser)]
#[command(name = "wip")]
#[command(about = "WIP (Weather Transfer Protocol) - 統合CLIツール")]
#[command(version = "0.1.0")]
#[command(long_about = "
WIP (Weather Transfer Protocol) 統合CLIツール

このツールは以下の機能を提供します：
- weather:   気象データの取得
- location:  座標とエリアコードの解決
- query:     情報クエリサービス
- report:    災害・センサーレポート
- auth:      認証管理

各サービスは個別のバイナリとしても利用できます：
- wip-weather, wip-location, wip-query, wip-report, wip-auth

詳細は各サブコマンドの --help を参照してください。
")]
struct Cli {
    /// グローバルサーバーホスト
    #[arg(short = 'H', long, global = true)]
    host: Option<String>,

    /// デバッグモード
    #[arg(short, long, global = true)]
    debug: bool,

    /// 認証トークン
    #[arg(short, long, global = true)]
    auth_token: Option<String>,

    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// 気象データサービス (ポート 4110)
    #[command(alias = "w")]
    Weather {
        /// サーバーポート
        #[arg(short, long, default_value = "4111")]
        port: u16,

        #[command(subcommand)]
        command: WeatherCommands,
    },
    /// 位置情報サービス (ポート 4109)
    #[command(alias = "l")]
    Location {
        /// サーバーポート
        #[arg(short, long, default_value = "4109")]
        port: u16,

        #[command(subcommand)]
        command: LocationCommands,
    },
    /// クエリサービス (ポート 4111)
    #[command(alias = "q")]
    Query {
        /// サーバーポート
        #[arg(short, long, default_value = "4111")]
        port: u16,

        #[command(subcommand)]
        command: QueryCommands,
    },
    /// レポートサービス (ポート 4112)
    #[command(alias = "r")]
    Report {
        /// サーバーポート
        #[arg(short, long, default_value = "4112")]
        port: u16,

        #[command(subcommand)]
        command: ReportCommands,
    },
    /// 認証管理
    #[command(alias = "a")]
    Auth {
        #[command(subcommand)]
        command: AuthCommands,
    },
    /// サーバー状態確認
    Status {
        /// 確認するサービス (all, weather, location, query, report)
        #[arg(short, long, default_value = "all")]
        service: String,

        /// サーバーホスト
        #[arg(long, default_value = "127.0.0.1")]
        server_host: String,
    },
    /// 設定情報表示
    Config {
        /// 設定を表形式で表示
        #[arg(short, long)]
        table: bool,
    },
}

#[derive(Subcommand)]
enum WeatherCommands {
    /// エリアコードから気象データを取得
    Get {
        /// エリアコード
        area_code: u32,
        #[arg(short, long)] weather: bool,
        #[arg(short, long)] temperature: bool,
        #[arg(short = 'p', long)] precipitation: bool,
        #[arg(short = 'A', long)] alerts: bool,
        #[arg(short = 'D', long)] disaster: bool,
        #[arg(short = 'T', long, default_value = "0")] day: u8,
    },
    /// 座標から気象データを取得
    Coords {
        latitude: f64,
        longitude: f64,
        #[arg(short, long)] weather: bool,
        #[arg(short, long)] temperature: bool,
        #[arg(short = 'p', long)] precipitation: bool,
        #[arg(short = 'A', long)] alerts: bool,
        #[arg(short = 'D', long)] disaster: bool,
        #[arg(short = 'T', long, default_value = "0")] day: u8,
    },
    /// 複数日の予報を取得
    Forecast {
        area_code: u32,
        #[arg(short = 'T', long, default_value = "3")] days: u8,
    },
}

#[derive(Subcommand)]
enum LocationCommands {
    /// 座標からエリアコードを解決
    Resolve {
        latitude: f64,
        longitude: f64,
        #[arg(short, long)] verbose: bool,
    },
    /// バッチ処理
    Batch {
        #[arg(short, long)] file: String,
    },
    /// 主要都市の解決
    Cities {
        #[arg(short, long, default_value = "10")] count: usize,
    },
    /// 座標検証
    Validate {
        latitude: f64,
        longitude: f64,
    },
}

#[derive(Subcommand)]
enum QueryCommands {
    /// システム状態クエリ
    Status {
        #[arg(short, long)] region: Option<String>,
        #[arg(short, long)] verbose: bool,
    },
    /// 気象警報クエリ
    Alerts {
        #[arg(short, long)] region: Option<String>,
        #[arg(short, long, default_value = "medium")] severity: String,
        #[arg(short = 'v', long)] active_only: bool,
    },
    /// 履歴データクエリ
    History {
        #[arg(short, long, default_value = "all")] data_type: String,
        #[arg(short, long)] from: Option<String>,
        #[arg(short, long)] to: Option<String>,
        #[arg(short, long, default_value = "10")] limit: u32,
    },
    /// 予報データクエリ
    Forecast {
        #[arg(short, long, default_value = "tokyo")] location: String,
        #[arg(short, long, default_value = "24h")] period: String,
        #[arg(short = 'D', long, default_value = "basic")] detail: String,
    },
    /// カスタムクエリ
    Custom {
        query_type: String,
        parameters: String,
        #[arg(short, long, default_value = "table")] format: String,
    },
}

#[derive(Subcommand)]
enum ReportCommands {
    /// 災害レポート送信
    Disaster {
        disaster_type: String,
        #[arg(short, long)] severity: u8,
        #[arg(short = 'D', long)] description: String,
        #[arg(short = 'L', long)] latitude: Option<f64>,
        #[arg(short = 'G', long)] longitude: Option<f64>,
    },
    /// センサーデータレポート
    Sensor {
        #[arg(short, long, default_value = "11000")] area_code: u32,
        #[arg(short, long)] weather_code: Option<u16>,
        #[arg(short, long)] temperature: Option<f64>,
        #[arg(short = 'p', long)] precipitation: Option<u8>,
    },
    /// テストレポート送信
    Test {
        #[arg(short, long, default_value = "basic")] pattern: String,
        #[arg(short, long, default_value = "5")] count: usize,
    },
}

#[derive(Subcommand)]
enum AuthCommands {
    /// ユーザー作成
    CreateUser {
        username: String,
        #[arg(short, long)] password: Option<String>,
        #[arg(short, long)] admin: bool,
    },
    /// トークン生成
    Token {
        username: String,
        #[arg(short, long)] password: Option<String>,
    },
    /// ユーザー一覧
    List {
        #[arg(short, long)] verbose: bool,
    },
    /// ポリシー表示
    Policy,
}

async fn run_weather_command(host: &str, port: u16, auth_token: Option<String>, debug: bool, command: WeatherCommands) -> Result<(), Box<dyn Error>> {
    use std::process::Command;
    
    let mut cmd = Command::new("cargo");
    cmd.args(&["run", "--bin", "wip-weather", "--"]);
    cmd.args(&["-H", host, "-p", &port.to_string()]);
    
    if debug {
        cmd.arg("-d");
    }
    
    if let Some(token) = auth_token {
        cmd.args(&["-a", &token]);
    }
    
    match command {
        WeatherCommands::Get { area_code, weather, temperature, precipitation, alerts, disaster, day } => {
            cmd.args(&["get", &area_code.to_string()]);
            if weather { cmd.arg("-w"); }
            if temperature { cmd.arg("-t"); }
            if precipitation { cmd.arg("-p"); }
            if alerts { cmd.arg("-A"); }
            if disaster { cmd.arg("-D"); }
            cmd.args(&["-T", &day.to_string()]);
        }
        WeatherCommands::Coords { latitude, longitude, weather, temperature, precipitation, alerts, disaster, day } => {
            cmd.args(&["coords", &latitude.to_string(), &longitude.to_string()]);
            if weather { cmd.arg("-w"); }
            if temperature { cmd.arg("-t"); }
            if precipitation { cmd.arg("-p"); }
            if alerts { cmd.arg("-A"); }
            if disaster { cmd.arg("-D"); }
            cmd.args(&["-T", &day.to_string()]);
        }
        WeatherCommands::Forecast { area_code, days } => {
            cmd.args(&["forecast", &area_code.to_string(), "-T", &days.to_string()]);
        }
    }
    
    let output = cmd.output()?;
    print!("{}", String::from_utf8_lossy(&output.stdout));
    eprint!("{}", String::from_utf8_lossy(&output.stderr));
    
    Ok(())
}

async fn check_server_status(service: &str, host: &str) -> bool {
    use std::net::{TcpStream, SocketAddr};
    use std::time::Duration;
    
    let port = match service {
        "weather" => 4110,
        "location" => 4109,
        "query" => 4111,
        "report" => 4112,
        _ => return false,
    };
    
    if let Ok(addr) = format!("{}:{}", host, port).parse::<SocketAddr>() {
        TcpStream::connect_timeout(&addr, Duration::from_secs(3)).is_ok()
    } else {
        false
    }
}

fn print_config(table: bool) {
    if table {
        println!("┌─────────────────┬─────────────────┬─────────────────┐");
        println!("│ サービス        │ デフォルトポート │ 説明            │");
        println!("├─────────────────┼─────────────────┼─────────────────┤");
        println!("│ Weather         │ 4110            │ 気象データ      │");
        println!("│ Location        │ 4109            │ 位置情報        │");
        println!("│ Query           │ 4111            │ 情報クエリ      │");
        println!("│ Report          │ 4112            │ レポート        │");
        println!("└─────────────────┴─────────────────┴─────────────────┘");
    } else {
        println!("WIP設定情報:");
        println!("  🌤️ Weather Service:  ポート 4110 - 気象データの取得");
        println!("  🌍 Location Service: ポート 4109 - 座標とエリアコードの解決");
        println!("  🔍 Query Service:    ポート 4111 - 情報クエリと検索");
        println!("  📋 Report Service:   ポート 4112 - 災害・センサーレポート");
        println!();
        println!("利用可能なコマンド:");
        println!("  wip weather get 11000 --weather --temperature");
        println!("  wip location resolve 35.6812 139.7671");
        println!("  wip query alerts --region tokyo");
        println!("  wip report disaster earthquake --severity 7 --description '大地震'");
        println!("  wip auth token myuser");
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let cli = Cli::parse();

    if cli.debug {
        env_logger::init();
    }

    let default_host = cli.host.as_deref().unwrap_or("127.0.0.1");

    match cli.command {
        Commands::Weather { port, command } => {
            run_weather_command(default_host, port, cli.auth_token, cli.debug, command).await?;
        }

        Commands::Location { port, command } => {
            println!("🌍 Location サービスを呼び出し中... ({}:{})", default_host, port);
            println!("⚠️ 詳細実装は wip-location バイナリを直接使用してください");
        }

        Commands::Query { port, command } => {
            println!("🔍 Query サービスを呼び出し中... ({}:{})", default_host, port);
            println!("⚠️ 詳細実装は wip-query バイナリを直接使用してください");
        }

        Commands::Report { port, command } => {
            println!("📋 Report サービスを呼び出し中... ({}:{})", default_host, port);
            println!("⚠️ 詳細実装は wip-report バイナリを直接使用してください");
        }

        Commands::Auth { command } => {
            println!("🔐 認証管理を呼び出し中...");
            println!("⚠️ 詳細実装は wip-auth バイナリを直接使用してください");
        }

        Commands::Status { service, server_host } => {
            println!("📊 WIPサーバー状態確認:");
            println!("ホスト: {}", server_host);
            println!();

            let services = if service == "all" {
                vec!["weather", "location", "query", "report"]
            } else {
                vec![service.as_str()]
            };

            for svc in services {
                let port = match svc {
                    "weather" => 4110,
                    "location" => 4109,
                    "query" => 4111,
                    "report" => 4112,
                    _ => continue,
                };

                let status = if check_server_status(svc, &server_host).await {
                    "🟢 オンライン"
                } else {
                    "🔴 オフライン"
                };

                let service_name = match svc {
                    "weather" => "気象サービス",
                    "location" => "位置サービス",
                    "query" => "クエリサービス",
                    "report" => "レポートサービス",
                    _ => svc,
                };

                println!("  {}: {} (ポート {})", service_name, status, port);
            }
        }

        Commands::Config { table } => {
            print_config(table);
        }
    }

    Ok(())
}