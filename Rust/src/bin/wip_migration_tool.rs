/*!
 * WIP Python → Rust 移行支援ツール
 * 
 * Python版のWIPクライアントコードをRust版に変換する支援を行う
 * また、Python版とRust版の互換性をチェックする機能も提供
 */

use std::fs;
use std::path::Path;
use std::process::{Command, exit};
use regex::Regex;
use clap::{Command as ClapCommand, Arg};

fn main() {
    let matches = ClapCommand::new("WIP Migration Tool")
        .version("1.0")
        .author("WIP Development Team")
        .about("Python → Rust migration and compatibility tool for WIP")
        .subcommand(
            ClapCommand::new("analyze")
                .about("Analyze Python WIP code for migration readiness")
                .arg(
                    Arg::new("python_file")
                        .help("Python file to analyze")
                        .required(true)
                        .index(1),
                ),
        )
        .subcommand(
            ClapCommand::new("convert")
                .about("Convert Python WIP code to Rust equivalent")
                .arg(
                    Arg::new("python_file")
                        .help("Python file to convert")
                        .required(true)
                        .index(1),
                )
                .arg(
                    Arg::new("output")
                        .short('o')
                        .long("output")
                        .value_name("FILE")
                        .help("Output Rust file")
                        .action(clap::ArgAction::Set),
                ),
        )
        .subcommand(
            ClapCommand::new("test")
                .about("Test compatibility between Python and Rust implementations")
                .arg(
                    Arg::new("python_script")
                        .help("Python script to test")
                        .required(false)
                        .index(1),
                ),
        )
        .subcommand(
            ClapCommand::new("benchmark")
                .about("Benchmark Python vs Rust performance")
                .arg(
                    Arg::new("iterations")
                        .short('n')
                        .long("iterations")
                        .value_name("NUMBER")
                        .help("Number of iterations for benchmark")
                        .action(clap::ArgAction::Set)
                        .default_value("1000"),
                ),
        )
        .get_matches();

    match matches.subcommand() {
        Some(("analyze", sub_matches)) => {
            let python_file = sub_matches.get_one::<String>("python_file").unwrap();
            analyze_python_code(python_file);
        }
        Some(("convert", sub_matches)) => {
            let python_file = sub_matches.get_one::<String>("python_file").unwrap();
            let output_file = sub_matches.get_one::<String>("output");
            convert_python_to_rust(python_file, output_file);
        }
        Some(("test", sub_matches)) => {
            let python_script = sub_matches.get_one::<String>("python_script");
            test_compatibility(python_script);
        }
        Some(("benchmark", sub_matches)) => {
            let iterations: usize = sub_matches
                .get_one::<String>("iterations")
                .unwrap()
                .parse()
                .expect("Invalid number of iterations");
            benchmark_performance(iterations);
        }
        _ => {
            println!("No subcommand provided. Use --help for usage information.");
            exit(1);
        }
    }
}

/// Python WIPコードを分析して移行の準備状況を評価
fn analyze_python_code(python_file: &str) {
    println!("🔍 Analyzing Python WIP code: {}", python_file);
    
    if !Path::new(python_file).exists() {
        eprintln!("❌ Error: File {} does not exist", python_file);
        exit(1);
    }

    let content = match fs::read_to_string(python_file) {
        Ok(content) => content,
        Err(e) => {
            eprintln!("❌ Error reading file: {}", e);
            exit(1);
        }
    };

    let mut compatibility_score = 100;
    let mut issues = Vec::new();
    let mut suggestions = Vec::new();

    // WIPクライアントの使用パターンを分析
    analyze_wip_imports(&content, &mut compatibility_score, &mut issues, &mut suggestions);
    analyze_client_usage(&content, &mut compatibility_score, &mut issues, &mut suggestions);
    analyze_api_calls(&content, &mut compatibility_score, &mut issues, &mut suggestions);
    analyze_error_handling(&content, &mut compatibility_score, &mut issues, &mut suggestions);

    // レポート出力
    println!("\n📊 Migration Analysis Report");
    println!("{}", "=".repeat(50));
    println!("Compatibility Score: {}/100", compatibility_score);
    
    if compatibility_score >= 90 {
        println!("✅ Excellent! This code is highly compatible with Rust migration.");
    } else if compatibility_score >= 70 {
        println!("⚠️  Good. Some minor adjustments needed for Rust migration.");
    } else if compatibility_score >= 50 {
        println!("🔄 Moderate compatibility. Several changes required.");
    } else {
        println!("❌ Low compatibility. Significant refactoring needed.");
    }

    if !issues.is_empty() {
        println!("\n⚠️  Issues Found:");
        for (i, issue) in issues.iter().enumerate() {
            println!("  {}. {}", i + 1, issue);
        }
    }

    if !suggestions.is_empty() {
        println!("\n💡 Suggestions:");
        for (i, suggestion) in suggestions.iter().enumerate() {
            println!("  {}. {}", i + 1, suggestion);
        }
    }

    println!("\n📋 Migration Checklist:");
    println!("  [ ] Update imports to use wip_rust crate");
    println!("  [ ] Replace Python client with PythonCompatibleClient");
    println!("  [ ] Update error handling to use Result<T, E>");
    println!("  [ ] Convert dictionary returns to structured types");
    println!("  [ ] Test packet format compatibility");
}

/// Python WIPコードをRust等価コードに変換
fn convert_python_to_rust(python_file: &str, output_file: Option<&String>) {
    println!("🔄 Converting Python WIP code to Rust: {}", python_file);
    
    let content = match fs::read_to_string(python_file) {
        Ok(content) => content,
        Err(e) => {
            eprintln!("❌ Error reading file: {}", e);
            exit(1);
        }
    };

    let mut rust_code = String::new();
    rust_code.push_str("// Auto-generated Rust code from Python WIP client\n");
    rust_code.push_str("// Generated by wip_migration_tool\n\n");
    rust_code.push_str("use wip_rust::wip_common_rs::clients::python_compatible_client::*;\n");
    rust_code.push_str("use std::collections::HashMap;\n\n");

    // Python imports を Rust の use に変換
    convert_imports(&content, &mut rust_code);
    
    // クライアント初期化を変換
    convert_client_initialization(&content, &mut rust_code);
    
    // API呼び出しを変換
    convert_api_calls(&content, &mut rust_code);
    
    // エラーハンドリングを変換
    convert_error_handling(&content, &mut rust_code);

    // 出力ファイルを決定
    let output_path = match output_file {
        Some(path) => path.clone(),
        None => {
            let base_name = Path::new(python_file)
                .file_stem()
                .unwrap()
                .to_str()
                .unwrap();
            format!("{}_converted.rs", base_name)
        }
    };

    // Rustコードを書き込み
    match fs::write(&output_path, rust_code) {
        Ok(_) => {
            println!("✅ Converted code written to: {}", output_path);
            println!("\n📝 Next steps:");
            println!("  1. Review the generated Rust code");
            println!("  2. Add it to your Cargo.toml dependencies");
            println!("  3. Test the converted functionality");
            println!("  4. Run the compatibility tests");
        }
        Err(e) => {
            eprintln!("❌ Error writing output file: {}", e);
            exit(1);
        }
    }
}

/// Python版とRust版の互換性をテスト
fn test_compatibility(python_script: Option<&String>) {
    println!("🧪 Testing Python-Rust compatibility");
    
    // デフォルトの互換性テストを実行
    run_default_compatibility_tests();
    
    // 指定されたPythonスクリプトがあれば実行
    if let Some(script) = python_script {
        run_custom_python_test(script.as_str());
    }
}

/// パフォーマンスベンチマークを実行
fn benchmark_performance(iterations: usize) {
    println!("📈 Benchmarking Python vs Rust performance");
    println!("Iterations: {}", iterations);
    
    // Pythonベンチマークスクリプトを生成
    let python_benchmark = format!(r#"
import sys
import os
import time
sys.path.insert(0, '/mnt/c/Users/pijon/Desktop/wip/src')

from WIPCommonPy.clients.weather_client import WeatherClient
from WIPCommonPy.packet.types.query_packet import QueryRequest

def benchmark_python():
    iterations = {iterations}
    
    # クライアント作成ベンチマーク
    start = time.time()
    for i in range(iterations):
        client = WeatherClient("localhost", 4110, False)
    client_creation_time = time.time() - start
    
    # パケット生成ベンチマーク
    start = time.time()
    for i in range(iterations):
        request = QueryRequest.create_query_request(
            area_code=130010,
            packet_id=i % 4096,
            weather=True,
            temperature=False,
            precipitation_prob=False,
            alert=False,
            disaster=False,
            day=0,
            version=1
        )
        packet_bytes = request.to_bytes()
    packet_generation_time = time.time() - start
    
    print(f"Python Results ({iterations} iterations):")
    print(f"  Client creation: {{:.4f}}s ({{:.2f}} μs/op)".format(client_creation_time, client_creation_time * 1000000 / iterations))
    print(f"  Packet generation: {{:.4f}}s ({{:.2f}} μs/op)".format(packet_generation_time, packet_generation_time * 1000000 / iterations))

if __name__ == "__main__":
    benchmark_python()
"#);

    // Pythonベンチマークを実行
    fs::write("temp_python_benchmark.py", python_benchmark).expect("Failed to write Python benchmark");
    
    println!("\n🐍 Running Python benchmark...");
    let python_output = Command::new("python3")
        .arg("temp_python_benchmark.py")
        .output()
        .expect("Failed to execute Python benchmark");
    
    println!("{}", String::from_utf8_lossy(&python_output.stdout));
    
    // Rustベンチマークを実行
    println!("🦀 Running Rust benchmark...");
    benchmark_rust_performance(iterations);
    
    // クリーンアップ
    let _ = fs::remove_file("temp_python_benchmark.py");
}

// === ヘルパー関数 ===

fn analyze_wip_imports(content: &str, score: &mut i32, issues: &mut Vec<String>, _suggestions: &mut Vec<String>) {
    let import_patterns = vec![
        r"from WIPCommonPy\.clients",
        r"from WIPCommonPy\.packet",
        r"import WeatherClient",
        r"import LocationClient",
    ];

    let mut found_wip_imports = false;
    for pattern in import_patterns {
        let regex = Regex::new(pattern).unwrap();
        if regex.is_match(content) {
            found_wip_imports = true;
            break;
        }
    }

    if !found_wip_imports {
        *score -= 20;
        issues.push("No WIP client imports found".to_string());
    }
}

fn analyze_client_usage(content: &str, score: &mut i32, issues: &mut Vec<String>, suggestions: &mut Vec<String>) {
    let client_patterns = vec![
        (r"WeatherClient\(", "WeatherClient instantiation found"),
        (r"LocationClient\(", "LocationClient instantiation found"),
        (r"\.get_weather_", "Weather API usage found"),
        (r"\.get_area_code", "Location API usage found"),
    ];

    let mut found_usage = false;
    for (pattern, _description) in client_patterns {
        let regex = Regex::new(pattern).unwrap();
        if regex.is_match(content) {
            found_usage = true;
            break;
        }
    }

    if found_usage {
        suggestions.push("Consider using PythonCompatibleWeatherClient for easier migration".to_string());
    } else {
        *score -= 10;
        issues.push("No WIP client usage patterns found".to_string());
    }
}

fn analyze_api_calls(content: &str, _score: &mut i32, _issues: &mut Vec<String>, suggestions: &mut Vec<String>) {
    let deprecated_patterns = vec![
        (r"get_weather_by_area_code", "Consider using get_weather_data() instead"),
        (r"get_area_code_from_coordinates", "Consider using get_area_code_simple() instead"),
    ];

    for (pattern, suggestion) in deprecated_patterns {
        let regex = Regex::new(pattern).unwrap();
        if regex.is_match(content) {
            suggestions.push(suggestion.to_string());
        }
    }
}

fn analyze_error_handling(content: &str, score: &mut i32, issues: &mut Vec<String>, suggestions: &mut Vec<String>) {
    if !content.contains("try:") && !content.contains("except") {
        *score -= 5;
        issues.push("No error handling found".to_string());
        suggestions.push("Add proper error handling for network operations".to_string());
    }
}

fn convert_imports(_content: &str, rust_code: &mut String) {
    // Python imports を Rust use statements に変換
    rust_code.push_str("// Python imports converted to Rust use statements\n");
    rust_code.push_str("use wip_rust::wip_common_rs::clients::python_compatible_client::{\n");
    rust_code.push_str("    PythonCompatibleWeatherClient,\n");
    rust_code.push_str("    PythonCompatibleLocationClient,\n");
    rust_code.push_str("};\n\n");
}

fn convert_client_initialization(content: &str, rust_code: &mut String) {
    // WeatherClient の初期化を変換
    let weather_client_regex = Regex::new(r"WeatherClient\(([^)]*)\)").unwrap();
    if weather_client_regex.is_match(content) {
        rust_code.push_str("fn create_weather_client() -> PythonCompatibleWeatherClient {\n");
        rust_code.push_str("    // Converted from Python WeatherClient initialization\n");
        rust_code.push_str("    PythonCompatibleWeatherClient::new(Some(\"localhost\"), Some(4110), Some(false))\n");
        rust_code.push_str("}\n\n");
    }

    // LocationClient の初期化を変換
    let location_client_regex = Regex::new(r"LocationClient\(([^)]*)\)").unwrap();
    if location_client_regex.is_match(content) {
        rust_code.push_str("fn create_location_client() -> PythonCompatibleLocationClient {\n");
        rust_code.push_str("    // Converted from Python LocationClient initialization\n");
        rust_code.push_str("    PythonCompatibleLocationClient::new(Some(\"localhost\"), Some(4109), Some(false), None, None, None)\n");
        rust_code.push_str("}\n\n");
    }
}

fn convert_api_calls(content: &str, rust_code: &mut String) {
    rust_code.push_str("// Example API call conversion\n");
    rust_code.push_str("fn example_weather_request() -> Result<HashMap<String, serde_json::Value>, String> {\n");
    rust_code.push_str("    let client = create_weather_client();\n");
    
    if content.contains("get_weather_data") {
        rust_code.push_str("    // Converted from Python get_weather_data call\n");
        rust_code.push_str("    client.get_weather_data(130010, Some(true), Some(true), Some(true), Some(false), Some(false), Some(0))\n");
    } else if content.contains("get_weather_simple") {
        rust_code.push_str("    // Converted from Python get_weather_simple call\n");
        rust_code.push_str("    client.get_weather_simple(130010, Some(false), Some(0))\n");
    } else {
        rust_code.push_str("    // Add your API calls here\n");
        rust_code.push_str("    client.get_weather_simple(130010, Some(false), Some(0))\n");
    }
    
    rust_code.push_str("}\n\n");
}

fn convert_error_handling(_content: &str, rust_code: &mut String) {
    rust_code.push_str("// Error handling example\n");
    rust_code.push_str("fn handle_weather_request() {\n");
    rust_code.push_str("    match example_weather_request() {\n");
    rust_code.push_str("        Ok(result) => {\n");
    rust_code.push_str("            println!(\"Weather data received: {:?}\", result);\n");
    rust_code.push_str("        }\n");
    rust_code.push_str("        Err(e) => {\n");
    rust_code.push_str("            eprintln!(\"Error getting weather data: {}\", e);\n");
    rust_code.push_str("        }\n");
    rust_code.push_str("    }\n");
    rust_code.push_str("}\n\n");
}

fn run_default_compatibility_tests() {
    println!("Running default compatibility tests...");
    
    // Cargo test を実行して互換性テストを実行
    let output = Command::new("cargo")
        .args(&["test", "python_rust_interoperability", "--", "--nocapture"])
        .output()
        .expect("Failed to execute compatibility tests");
    
    if output.status.success() {
        println!("✅ Default compatibility tests passed");
    } else {
        println!("❌ Some compatibility tests failed");
        println!("stderr: {}", String::from_utf8_lossy(&output.stderr));
    }
}

fn run_custom_python_test(script: &str) {
    println!("Running custom Python test: {}", script);
    
    let output = Command::new("python3")
        .arg(script)
        .output()
        .expect("Failed to execute Python script");
    
    println!("Python test output:");
    println!("{}", String::from_utf8_lossy(&output.stdout));
    
    if !output.status.success() {
        println!("Python test stderr:");
        println!("{}", String::from_utf8_lossy(&output.stderr));
    }
}

fn benchmark_rust_performance(iterations: usize) {
    use std::time::Instant;
    use wip_rust::wip_common_rs::clients::python_compatible_client::PythonCompatibleWeatherClient;
    use wip_rust::wip_common_rs::packet::types::query_packet::QueryRequest;

    // クライアント作成ベンチマーク
    let start = Instant::now();
    for _i in 0..iterations {
        let _client = PythonCompatibleWeatherClient::new(Some("localhost"), Some(4110), Some(false));
    }
    let client_creation_time = start.elapsed();

    // パケット生成ベンチマーク
    let start = Instant::now();
    for i in 0..iterations {
        let request = QueryRequest::new(
            130010,
            (i % 4096) as u16,
            true,
            false,
            false,
            false,
            false,
            0,
        );
        let _packet_bytes = request.to_bytes();
    }
    let packet_generation_time = start.elapsed();

    println!("Rust Results ({} iterations):", iterations);
    println!("  Client creation: {:.4}s ({:.2} μs/op)", 
             client_creation_time.as_secs_f64(), 
             client_creation_time.as_micros() as f64 / iterations as f64);
    println!("  Packet generation: {:.4}s ({:.2} μs/op)", 
             packet_generation_time.as_secs_f64(), 
             packet_generation_time.as_micros() as f64 / iterations as f64);
}