#include <gtest/gtest.h>
#include "wiplib/client/location_client.hpp"
#include <filesystem>

using namespace wiplib::client;

class LocationClientCacheTestHelper : public LocationClient {
public:
    using LocationClient::LocationClient;
    void cache_public(const std::string& key, const CoordinateResult& res) {
        cache_result(key, res);
    }
    std::string key_public(const packet::Coordinate& c, PrecisionLevel p) const {
        return generate_cache_key(c, p);
    }
};

TEST(LocationClientCachePersistence, ReloadsFromDisk) {
    namespace fs = std::filesystem;
    auto path = fs::temp_directory_path() / "test_location_cache.json";
    if (fs::exists(path)) fs::remove(path);

    LocationClientCacheTestHelper c1;
    c1.set_cache_file_path(path);
    c1.set_cache_enabled(true, std::chrono::seconds{60});
    packet::Coordinate coord{35.0, 139.0};
    CoordinateResult res{};
    res.area_code = "654321";
    res.original_coordinate = coord;
    res.normalized_coordinate = coord;
    res.precision_level = PrecisionLevel::Medium;
    c1.cache_public(c1.key_public(coord, PrecisionLevel::Medium), res);

    LocationClient c2;
    c2.set_cache_file_path(path);
    c2.set_cache_enabled(true, std::chrono::seconds{60});
    auto fut = c2.get_area_code_detailed_async(coord, PrecisionLevel::Medium);
    auto result = fut.get();
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->area_code, "654321");

    if (fs::exists(path)) fs::remove(path);
}

TEST(LocationClientCachePersistence, PythonCompatibleFormat) {
    namespace fs = std::filesystem;
    auto path = fs::temp_directory_path() / "test_python_cache.json";
    if (fs::exists(path)) fs::remove(path);

    // Python形式のキャッシュファイルを作成
    std::ofstream ofs(path);
    ofs << R"({
  "coord:35.6895,139.6917": {
    "area_code": "130001",
    "timestamp": 1692345678.123456
  },
  "coord:34.0522,-118.2437": {
    "area_code": "060001", 
    "timestamp": 1692345679.987654
  }
})";
    ofs.close();

    // C++クライアントでPython形式を読み込み
    LocationClient client;
    client.set_cache_file_path(path);
    client.set_cache_enabled(true, std::chrono::seconds{3600});

    packet::Coordinate coord1{35.6895, 139.6917};
    auto fut1 = client.get_area_code_detailed_async(coord1, PrecisionLevel::Medium);
    auto result1 = fut1.get();
    ASSERT_TRUE(result1.has_value());
    EXPECT_EQ(result1->area_code, "130001");

    packet::Coordinate coord2{34.0522, -118.2437};
    auto fut2 = client.get_area_code_detailed_async(coord2, PrecisionLevel::Medium);
    auto result2 = fut2.get();
    ASSERT_TRUE(result2.has_value());
    EXPECT_EQ(result2->area_code, "060001");

    if (fs::exists(path)) fs::remove(path);
}

TEST(LocationClientCachePersistence, CacheKeyCompatibility) {
    LocationClientCacheTestHelper helper;
    
    // Pythonと同じキー形式を確認
    packet::Coordinate coord{35.6895, 139.6917};
    std::string key = helper.key_public(coord, PrecisionLevel::Medium);
    EXPECT_EQ(key, "coord:35.6895,139.6917");
    
    // 精度4桁の丸めを確認
    packet::Coordinate coord_precise{35.68954321, 139.69176789};
    std::string key_precise = helper.key_public(coord_precise, PrecisionLevel::Medium);
    EXPECT_EQ(key_precise, "coord:35.6895,139.6918");
}
