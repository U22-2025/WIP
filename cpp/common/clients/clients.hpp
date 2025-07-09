#ifndef WIP_CLIENTS_ALL_HPP
#define WIP_CLIENTS_ALL_HPP

namespace wip {
namespace clients {

class QueryClient;
class WeatherClient;
class LocationClient;
class ReportClient;

} // namespace clients
} // namespace wip

#ifdef WIP_CLIENTS_INCLUDE_ALL
#include "QueryClient.hpp"
#include "WeatherClient.hpp"
#include "LocationClient.hpp"
#include "ReportClient.hpp"
#endif

#endif // WIP_CLIENTS_ALL_HPP
