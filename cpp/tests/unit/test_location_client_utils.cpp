#include <gtest/gtest.h>
#include "wiplib/client/location_client.hpp"

using namespace wiplib::client;
using wiplib::packet::Coordinate;

TEST(LocationClientUtils, ManageGpsPrecision) {
    LocationClient cli;
    Coordinate coord{35.123456, 139.987654};
    auto r = cli.manage_gps_precision(coord, PrecisionLevel::High);
    EXPECT_NEAR(r.latitude, 35.1235, 1e-4);
    EXPECT_NEAR(r.longitude, 139.9877, 1e-4);
}

TEST(LocationClientUtils, CheckGeographicBounds) {
    LocationClient cli;
    GeographicBounds bounds{10.0, 20.0, 30.0, 40.0, "test"};
    EXPECT_TRUE(cli.check_geographic_bounds(Coordinate{15.0, 35.0}, bounds));
    EXPECT_FALSE(cli.check_geographic_bounds(Coordinate{25.0, 35.0}, bounds));
}

TEST(LocationClientUtils, NormalizeCoordinate) {
    LocationClient cli;
    Coordinate coord{35.1234567, 139.9876543};
    auto n = cli.normalize_coordinate(coord, 3);
    EXPECT_DOUBLE_EQ(n.latitude, 35.123);
    EXPECT_DOUBLE_EQ(n.longitude, 139.988);
}

TEST(LocationClientUtils, EstimatePrecisionLevel) {
    LocationClient cli;
    EXPECT_EQ(cli.estimate_precision_level(Coordinate{35.1, 139.1}), PrecisionLevel::Low);
    EXPECT_EQ(cli.estimate_precision_level(Coordinate{35.123, 139.123}), PrecisionLevel::Medium);
    EXPECT_EQ(cli.estimate_precision_level(Coordinate{35.1234, 139.1234}), PrecisionLevel::High);
}

TEST(LocationClientUtils, ValidateCoordinate) {
    LocationClient cli;
    auto [ok, msg] = cli.validate_coordinate(Coordinate{0.0, 0.0});
    EXPECT_TRUE(ok);
    auto [ok2, msg2] = cli.validate_coordinate(Coordinate{-100.0, 0.0});
    EXPECT_FALSE(ok2);
    EXPECT_FALSE(msg2.empty());
}
