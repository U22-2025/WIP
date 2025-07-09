#include "../c++common/packet/types/QueryPacket.hpp"
#include "../c++common/packet/models/Request.hpp"
#include <catch2/catch_test_macros.hpp>

using namespace wip::packet;

TEST_CASE("QueryRequest round trip", "[packet]") {
    auto req = QueryRequest::create_query_request("123456", 42, true, true, false, false, false, 1);
    auto bytes = req.to_bytes();
    auto base = Request::from_bytes(bytes);
    REQUIRE(base.packet_id == req.packet_id);
    REQUIRE(base.area_code == req.area_code);
    REQUIRE(base.type == req.type);
    REQUIRE(base.day == req.day);
    REQUIRE(base.weather_flag == req.weather_flag);
    REQUIRE(base.temperature_flag == req.temperature_flag);
    REQUIRE(base.pop_flag == req.pop_flag);
    REQUIRE(base.alert_flag == req.alert_flag);
    REQUIRE(base.disaster_flag == req.disaster_flag);
}
