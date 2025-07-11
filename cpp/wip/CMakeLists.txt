cmake_minimum_required(VERSION 3.31)
cmake_policy(SET CMP0167 OLD)  # FindBoost.cmake を許可

project(wip)

file(GLOB_RECURSE COMMON_SOURCES CONFIGURE_DEPENDS
    "common/*.cpp"
)
list(FILTER COMMON_SOURCES EXCLUDE REGEX "/tests/")
list(FILTER COMMON_SOURCES EXCLUDE REGEX "/examples/")

# FindBoost を使う（CMP0167 を OLD にしたので有効）
find_package(Boost REQUIRED COMPONENTS asio filesystem system multiprecision)
find_package(OpenSSL REQUIRED)
find_package(Catch2 CONFIG REQUIRED)

add_executable(wip wip.cpp ${COMMON_SOURCES})

target_link_libraries(wip PRIVATE
    Boost::asio
    Boost::filesystem
    Boost::system
    Boost::multiprecision
    OpenSSL::SSL
    OpenSSL::Crypto
)

target_include_directories(wip PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/common
)

target_compile_definitions(wip PRIVATE
    FORMAT_SPEC_DIR="${CMAKE_CURRENT_SOURCE_DIR}/common/packet/format_spec"
)

if (CMAKE_VERSION VERSION_GREATER 3.12)
  set_property(TARGET wip PROPERTY CXX_STANDARD 20)
endif()

add_executable(wip_tests
    tests/test_main.cpp
    tests/test_packet.cpp
    tests/test_auth.cpp
    tests/test_dynamic.cpp
    ${COMMON_SOURCES}
)

set_property(TARGET wip_tests PROPERTY CXX_STANDARD 20)

target_include_directories(wip_tests PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/common
)

target_compile_definitions(wip_tests PRIVATE
    FORMAT_SPEC_DIR="${CMAKE_CURRENT_SOURCE_DIR}/common/packet/format_spec"
)

target_link_libraries(wip_tests PRIVATE
    Catch2::Catch2WithMain
    Boost::asio
    Boost::filesystem
    Boost::system
    Boost::multiprecision
    OpenSSL::SSL
    OpenSSL::Crypto
)

enable_testing()
add_test(NAME all_tests COMMAND wip_tests)
