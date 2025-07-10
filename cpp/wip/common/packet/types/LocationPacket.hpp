#pragma once
#include "../models/Request.hpp"
#include "../models/Response.hpp"
#include <optional>

namespace wip {
namespace packet {

class LocationRequest : public Request {
public:
    static LocationRequest create_coordinate_lookup(double latitude,
                                                    double longitude,
                                                    uint16_t packet_id,
                                                    bool weather = true,
                                                    bool temperature = true,
                                                    bool precipitation_prob = true,
                                                    bool alert = false,
                                                    bool disaster = false,
                                                    std::optional<std::pair<std::string,int>> source = std::nullopt,
                                                    uint8_t day = 0,
                                                    uint8_t version = 1);
};

class LocationResponse : public Response {
public:
    static LocationResponse create_area_code_response(const LocationRequest& req,
                                                      const std::string& area_code,
                                                      uint8_t version = 1);
};

} // namespace packet
} // namespace wip
