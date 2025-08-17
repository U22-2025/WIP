/**
 * @file basic_usage.cpp
 * @brief WIPLib C++ 基本的な使用例
 * 
 * このファイルは、WIPLib C++の基本的な使用方法を示すサンプルコードです。
 * Python版WIPClientPyと同じAPIを使用して天気データを取得する方法を学べます。
 */

#include <iostream>
#include <iomanip>
#include "wiplib/client/client.hpp"

int main() {
    std::cout << "=== WIPLib C++ 基本使用例 ===" << std::endl;
    
    try {
        // 1. クライアントの作成
        // Python版と同じ引数順序：緯度, 経度, エリアコード, サーバー情報
        std::cout << "\n1. クライアントを作成中..." << std::endl;
        
        wiplib::client::Client client(
            35.6762,      // latitude (東京駅)
            139.6503,     // longitude
            130010,       // area_code (東京都千代田区)
            "localhost",  // weather_host
            8080,         // weather_port
            "localhost",  // location_host
            8081,         // location_port
            "localhost",  // query_host
            8082          // query_port
        );
        
        std::cout << "✓ クライアントの作成完了" << std::endl;
        
        // 2. 基本的な天気データ取得
        std::cout << "\n2. 天気データを取得中..." << std::endl;
        
        auto weather = client.get_weather();
        if (weather.has_value()) {
            std::cout << "✓ 天気データの取得成功" << std::endl;
            
            // 天気データの表示
            std::cout << std::fixed << std::setprecision(1);
            std::cout << "  気温: " << weather->temperature << "°C" << std::endl;
            std::cout << "  湿度: " << weather->humidity << "%" << std::endl;
            std::cout << "  気圧: " << weather->pressure << " hPa" << std::endl;
            std::cout << "  風速: " << weather->wind_speed << " m/s" << std::endl;
            std::cout << "  風向: " << weather->wind_direction << "°" << std::endl;
            std::cout << "  降水量: " << weather->precipitation << " mm" << std::endl;
            
            // オプショナルフィールドの表示
            if (weather->visibility.has_value()) {
                std::cout << "  視程: " << weather->visibility.value() << " km" << std::endl;
            }
            if (weather->uv_index.has_value()) {
                std::cout << "  UV指数: " << weather->uv_index.value() << std::endl;
            }
            if (weather->cloud_coverage.has_value()) {
                std::cout << "  雲量: " << weather->cloud_coverage.value() << "%" << std::endl;
            }
        } else {
            std::cout << "✗ 天気データの取得失敗" << std::endl;
            
            // エラー情報の表示
            auto error = client.get_last_error();
            if (error.has_value()) {
                std::cout << "  エラーコード: " << error->code << std::endl;
                std::cout << "  エラーメッセージ: " << error->message << std::endl;
            }
        }
        
        // 3. 座標による天気データ取得
        std::cout << "\n3. 座標による天気データ取得..." << std::endl;
        
        // 大阪の座標で天気を取得
        double osaka_lat = 34.6937;
        double osaka_lon = 135.5023;
        
        auto osaka_weather = client.get_weather_by_coordinates(osaka_lat, osaka_lon);
        if (osaka_weather.has_value()) {
            std::cout << "✓ 大阪の天気データ取得成功" << std::endl;
            std::cout << "  大阪の気温: " << osaka_weather->temperature << "°C" << std::endl;
            std::cout << "  大阪の湿度: " << osaka_weather->humidity << "%" << std::endl;
        } else {
            std::cout << "✗ 大阪の天気データ取得失敗" << std::endl;
        }
        
        // 4. エリアコードによる天気データ取得
        std::cout << "\n4. エリアコードによる天気データ取得..." << std::endl;
        
        uint32_t yokohama_area_code = 140010; // 横浜
        auto yokohama_weather = client.get_weather_by_area_code(yokohama_area_code);
        if (yokohama_weather.has_value()) {
            std::cout << "✓ 横浜の天気データ取得成功" << std::endl;
            std::cout << "  横浜の気温: " << yokohama_weather->temperature << "°C" << std::endl;
            std::cout << "  横浜の湿度: " << yokohama_weather->humidity << "%" << std::endl;
        } else {
            std::cout << "✗ 横浜の天気データ取得失敗" << std::endl;
        }
        
        // 5. 座標の変更
        std::cout << "\n5. 座標の変更..." << std::endl;
        
        double new_lat = 43.0642;  // 札幌
        double new_lon = 141.3469;
        
        client.set_coordinates(new_lat, new_lon);
        std::cout << "✓ 座標を札幌に変更しました" << std::endl;
        
        // 新しい座標で天気を取得
        auto sapporo_weather = client.get_weather();
        if (sapporo_weather.has_value()) {
            std::cout << "✓ 札幌の天気データ取得成功" << std::endl;
            std::cout << "  札幌の気温: " << sapporo_weather->temperature << "°C" << std::endl;
            std::cout << "  札幌の湿度: " << sapporo_weather->humidity << "%" << std::endl;
        }
        
        // 6. クライアント状態の確認
        std::cout << "\n6. クライアント状態の確認..." << std::endl;
        
        auto state = client.get_state();
        std::cout << "  現在の緯度: " << state.latitude << std::endl;
        std::cout << "  現在の経度: " << state.longitude << std::endl;
        std::cout << "  現在のエリアコード: " << state.area_code << std::endl;
        std::cout << "  天気サーバー: " << state.weather_host << ":" << state.weather_port << std::endl;
        
        // 7. プロパティアクセス
        std::cout << "\n7. プロパティアクセス..." << std::endl;
        
        std::cout << "  latitude(): " << client.latitude() << std::endl;
        std::cout << "  longitude(): " << client.longitude() << std::endl;
        std::cout << "  area_code(): " << client.area_code() << std::endl;
        
        // 8. クライアントのクローズ
        std::cout << "\n8. クライアントをクローズ..." << std::endl;
        client.close();
        std::cout << "✓ クライアントのクローズ完了" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "例外が発生しました: " << e.what() << std::endl;
        return 1;
    }
    
    std::cout << "\n=== 基本使用例完了 ===" << std::endl;
    return 0;
}

/*
コンパイル方法:
g++ -std=c++20 -I../include basic_usage.cpp -lwiplib -o basic_usage

実行方法:
./basic_usage

期待される出力:
=== WIPLib C++ 基本使用例 ===

1. クライアントを作成中...
✓ クライアントの作成完了

2. 天気データを取得中...
✓ 天気データの取得成功
  気温: 25.5°C
  湿度: 60%
  気圧: 1013.2 hPa
  風速: 3.2 m/s
  風向: 180°
  降水量: 0.0 mm

3. 座標による天気データ取得...
✓ 大阪の天気データ取得成功
  大阪の気温: 24.1°C
  大阪の湿度: 65%

4. エリアコードによる天気データ取得...
✓ 横浜の天気データ取得成功
  横浜の気温: 26.0°C
  横浜の湿度: 58%

5. 座標の変更...
✓ 座標を札幌に変更しました
✓ 札幌の天気データ取得成功
  札幌の気温: 18.5°C
  札幌の湿度: 70%

6. クライアント状態の確認...
  現在の緯度: 43.0642
  現在の経度: 141.3469
  現在のエリアコード: 16010
  天気サーバー: localhost:8080

7. プロパティアクセス...
  latitude(): 43.0642
  longitude(): 141.3469
  area_code(): 16010

8. クライアントをクローズ...
✓ クライアントのクローズ完了

=== 基本使用例完了 ===
*/