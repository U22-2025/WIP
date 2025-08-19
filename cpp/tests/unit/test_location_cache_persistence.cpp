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
    auto path = fs::temp_directory_path() / "wip_location_cache.json";
    if (fs::exists(path)) fs::remove(path);

    LocationClientCacheTestHelper c1;
    c1.set_cache_enabled(true, std::chrono::seconds{60});
    packet::Coordinate coord{35.0, 139.0};
    CoordinateResult res{};
    res.area_code = "654321";
    res.original_coordinate = coord;
    res.normalized_coordinate = coord;
    res.precision_level = PrecisionLevel::Medium;
    c1.cache_public(c1.key_public(coord, PrecisionLevel::Medium), res);

    LocationClient c2;
    c2.set_cache_enabled(true, std::chrono::seconds{60});
    auto fut = c2.get_area_code_detailed_async(coord, PrecisionLevel::Medium);
    auto result = fut.get();
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->area_code, "654321");

    if (fs::exists(path)) fs::remove(path);
}
