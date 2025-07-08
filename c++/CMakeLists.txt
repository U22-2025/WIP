cmake_minimum_required(VERSION 3.10)
project(wip_cpp)
set(CMAKE_CXX_STANDARD 17)

find_package(OpenSSL REQUIRED)

add_library(wip_cpp
    common/utils/auth.cpp
    common/utils/file_cache.cpp
    common/packet/core/format_base.cpp
    common/packet/core/format.cpp
    common/packet/core/extended_field.cpp
    common/clients/query_client.cpp
    common/clients/location_client.cpp
    common/clients/report_client.cpp
    WIP_Client/client.cpp
)

target_include_directories(wip_cpp PUBLIC .)

target_link_libraries(wip_cpp OpenSSL::Crypto)

enable_testing()
add_executable(test_format_base tests/test_format_base.cpp)
target_link_libraries(test_format_base wip_cpp)
add_test(NAME format_base COMMAND test_format_base)
