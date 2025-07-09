target_sources(wipcommon
    PRIVATE
        LocationClient.cpp
        QueryClient.cpp
        ReportClient.cpp
        WeatherClient.cpp
    PUBLIC
        LocationClient.hpp
        QueryClient.hpp
        ReportClient.hpp
        WeatherClient.hpp
        clients.hpp
)

add_subdirectory(utils)
