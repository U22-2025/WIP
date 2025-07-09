#pragma once
#include "../models/Request.hpp"
#include "../models/Response.hpp"
#include <optional>
#include <vector>

namespace wip {
namespace packet {

class QueryRequest : public Request {
public:
    static QueryRequest create_query_request(const std::string& area_code,
                                             uint16_t packet_id,
                                             bool weather = true,
                                             bool temperature = true,
                                             bool precipitation_prob = true,
                                             bool alert = false,
                                             bool disaster = false,
                                             uint8_t day = 0,
                                             std::optional<std::pair<std::string,int>> source = std::nullopt,
                                             uint8_t version = 1);
    static QueryRequest from_location_response(const Response& res,
                                              std::optional<std::pair<std::string,int>> source = std::nullopt);
};

class QueryResponse : public Response {
public:
    static QueryResponse create_query_response(const QueryRequest& req,
                                               uint8_t version = 1);
};

} // namespace packet
} // namespace wip
