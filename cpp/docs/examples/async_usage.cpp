/**
 * @file async_usage.cpp
 * @brief WIPLib C++ 非同期処理使用例
 * 
 * このファイルは、WIPLib C++の非同期処理機能の使用方法を示すサンプルコードです。
 * Python版のasyncio相当の処理をstd::futureで実現する方法を学べます。
 */

#include <iostream>
#include <vector>
#include <future>
#include <chrono>
#include <thread>
#include <iomanip>
#include "wiplib/client/client_async.hpp"

// 複数の非同期タスクを並行実行する例
void example_concurrent_requests() {
    std::cout << "\n=== 複数の非同期リクエスト例 ===" << std::endl;
    
    wiplib::client::ClientAsync client(
        35.6762, 139.6503, 130010,
        "localhost", 8080,
        "localhost", 8081, 
        "localhost", 8082
    );
    
    // 複数の都市のエリアコード
    std::vector<std::pair<uint32_t, std::string>> cities = {
        {130010, "東京"},
        {140010, "横浜"},
        {270000, "大阪"},
        {230010, "名古屋"},
        {160010, "富山"}
    };
    
    std::cout << "複数都市の天気データを並行取得中..." << std::endl;
    
    // 非同期リクエストを同時に開始
    std::vector<std::future<std::optional<WeatherData>>> futures;
    auto start_time = std::chrono::high_resolution_clock::now();
    
    for (const auto& city : cities) {
        futures.push_back(client.get_weather_by_area_code_async(city.first));
    }
    
    // 結果を順次取得
    for (size_t i = 0; i < futures.size(); ++i) {
        auto weather = futures[i].get();
        if (weather.has_value()) {
            std::cout << std::fixed << std::setprecision(1);
            std::cout << "✓ " << cities[i].second 
                      << ": " << weather->temperature << "°C, "
                      << weather->humidity << "%" << std::endl;
        } else {
            std::cout << "✗ " << cities[i].second << ": データ取得失敗" << std::endl;
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    std::cout << "並行処理完了時間: " << duration.count() << "ms" << std::endl;
}

// タイムアウト付き非同期処理の例
void example_timeout_handling() {
    std::cout << "\n=== タイムアウト処理例 ===" << std::endl;
    
    wiplib::client::ClientAsync client(
        35.6762, 139.6503, 130010,
        "localhost", 8080,
        "localhost", 8081,
        "localhost", 8082
    );
    
    // 短いタイムアウトを設定
    client.set_timeout(std::chrono::milliseconds(2000));
    
    std::cout << "タイムアウト2秒で天気データを取得中..." << std::endl;
    
    auto future = client.get_weather_async();
    
    // タイムアウト付きで結果を待機
    auto status = future.wait_for(std::chrono::seconds(5));
    
    if (status == std::future_status::ready) {
        auto weather = future.get();
        if (weather.has_value()) {
            std::cout << "✓ 天気データ取得成功: " << weather->temperature << "°C" << std::endl;
        } else {
            std::cout << "✗ 天気データ取得失敗（サーバーエラー）" << std::endl;
        }
    } else if (status == std::future_status::timeout) {
        std::cout << "✗ タイムアウトが発生しました" << std::endl;
    } else {
        std::cout << "✗ 予期しない状態です" << std::endl;
    }
}

// 非同期設定変更の例
void example_async_configuration() {
    std::cout << "\n=== 非同期設定変更例 ===" << std::endl;
    
    wiplib::client::ClientAsync client(
        35.6762, 139.6503, 130010,
        "localhost", 8080,
        "localhost", 8081,
        "localhost", 8082
    );
    
    std::cout << "設定を非同期で変更中..." << std::endl;
    
    // 座標を非同期で変更
    auto coord_future = client.set_coordinates_async(34.6937, 135.5023); // 大阪
    
    // サーバー設定を非同期で変更
    auto server_future = client.set_server_async(
        "new-weather.example.com", 8080,
        "new-location.example.com", 8081,
        "new-query.example.com", 8082
    );
    
    std::cout << "設定変更の完了を待機中..." << std::endl;
    
    // 設定変更の完了を待機
    coord_future.get();
    server_future.get();
    
    std::cout << "✓ 座標とサーバー設定の変更完了" << std::endl;
    
    // 新しい設定で天気データを取得
    auto weather_future = client.get_weather_async();
    auto weather = weather_future.get();
    
    if (weather.has_value()) {
        std::cout << "✓ 新しい設定での天気データ取得成功: " 
                  << weather->temperature << "°C" << std::endl;
    }
    
    // 現在の状態を確認
    auto state = client.get_state();
    std::cout << "現在の座標: (" << state.latitude << ", " << state.longitude << ")" << std::endl;
}

// Python asyncio.gather() 相当の実装例
template<typename... Futures>
auto gather_futures(Futures&&... futures) {
    return std::make_tuple(futures.get()...);
}

void example_gather_pattern() {
    std::cout << "\n=== Gather パターン例 ===" << std::endl;
    
    wiplib::client::ClientAsync client(
        35.6762, 139.6503, 130010,
        "localhost", 8080,
        "localhost", 8081,
        "localhost", 8082
    );
    
    std::cout << "複数タスクを同時実行し、すべての完了を待機..." << std::endl;
    
    // 複数のタスクを作成
    auto task1 = client.get_weather_by_area_code_async(130010); // 東京
    auto task2 = client.get_weather_by_area_code_async(140010); // 横浜
    auto task3 = client.get_weather_by_area_code_async(270000); // 大阪
    
    // すべてのタスクの完了を待機（Python の asyncio.gather 相当）
    auto results = gather_futures(std::move(task1), std::move(task2), std::move(task3));
    
    // 結果を展開
    auto& [tokyo_weather, yokohama_weather, osaka_weather] = results;
    
    // 結果を表示
    std::vector<std::pair<std::string, std::optional<WeatherData>&>> cities = {
        {"東京", tokyo_weather},
        {"横浜", yokohama_weather}, 
        {"大阪", osaka_weather}
    };
    
    for (const auto& [city_name, weather] : cities) {
        if (weather.has_value()) {
            std::cout << "✓ " << city_name << ": " << weather->temperature << "°C" << std::endl;
        } else {
            std::cout << "✗ " << city_name << ": データ取得失敗" << std::endl;
        }
    }
}

// エラーハンドリングの例
void example_error_handling() {
    std::cout << "\n=== 非同期エラーハンドリング例 ===" << std::endl;
    
    wiplib::client::ClientAsync client(
        35.6762, 139.6503, 130010,
        "localhost", 8080,
        "localhost", 8081,
        "localhost", 8082
    );
    
    std::cout << "無効なリクエストでエラーハンドリングをテスト..." << std::endl;
    
    try {
        // 無効なエリアコードで非同期リクエスト
        auto future = client.get_weather_by_area_code_async(999999);
        auto weather = future.get();
        
        if (!weather.has_value()) {
            std::cout << "✓ 想定通りエラーが発生しました" << std::endl;
            
            auto error = client.get_last_error();
            if (error.has_value()) {
                std::cout << "  エラーコード: " << error->code << std::endl;
                std::cout << "  エラーメッセージ: " << error->message << std::endl;
            }
        } else {
            std::cout << "✗ 予期しない成功" << std::endl;
        }
        
    } catch (const std::exception& e) {
        std::cout << "✓ 例外をキャッチしました: " << e.what() << std::endl;
    }
}

// 高負荷処理の例
void example_high_load_processing() {
    std::cout << "\n=== 高負荷処理例 ===" << std::endl;
    
    wiplib::client::ClientAsync client(
        35.6762, 139.6503, 130010,
        "localhost", 8080,
        "localhost", 8081,
        "localhost", 8082
    );
    
    const int request_count = 20;
    std::cout << request_count << "個のリクエストを並行処理中..." << std::endl;
    
    std::vector<std::future<std::optional<WeatherData>>> futures;
    auto start_time = std::chrono::high_resolution_clock::now();
    
    // 大量の非同期リクエストを開始
    for (int i = 0; i < request_count; ++i) {
        uint32_t area_code = 130010 + (i % 10); // 10種類のエリアコードを循環
        futures.push_back(client.get_weather_by_area_code_async(area_code));
    }
    
    // 結果を取得
    int success_count = 0;
    for (auto& future : futures) {
        auto weather = future.get();
        if (weather.has_value()) {
            success_count++;
        }
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end_time - start_time);
    
    std::cout << "✓ " << success_count << "/" << request_count 
              << " リクエスト成功 (" << duration.count() << "ms)" << std::endl;
    
    double success_rate = (double)success_count / request_count * 100;
    std::cout << "成功率: " << std::fixed << std::setprecision(1) << success_rate << "%" << std::endl;
}

int main() {
    std::cout << "=== WIPLib C++ 非同期処理使用例 ===" << std::endl;
    
    try {
        // 各種非同期処理の例を実行
        example_concurrent_requests();
        
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        example_timeout_handling();
        
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        example_async_configuration();
        
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        example_gather_pattern();
        
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        example_error_handling();
        
        std::this_thread::sleep_for(std::chrono::milliseconds(500));
        example_high_load_processing();
        
    } catch (const std::exception& e) {
        std::cerr << "例外が発生しました: " << e.what() << std::endl;
        return 1;
    }
    
    std::cout << "\n=== 非同期処理使用例完了 ===" << std::endl;
    return 0;
}

/*
コンパイル方法:
g++ -std=c++20 -I../include async_usage.cpp -lwiplib -pthread -o async_usage

実行方法:
./async_usage

重要なポイント:
1. std::future を使用してPython asyncio 相当の機能を実現
2. 複数の非同期リクエストを同時実行してパフォーマンス向上
3. タイムアウトやエラーハンドリングを適切に処理
4. gather パターンで複数タスクの完了を待機
5. 高負荷処理でのスループット確認

Python版との対応:
- asyncio.create_task() → std::async() または future作成
- await → future.get()
- asyncio.gather() → カスタムgather_futures()実装
- asyncio.wait_for() → future.wait_for()
*/