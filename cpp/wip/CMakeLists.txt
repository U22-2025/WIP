cmake_minimum_required(VERSION 3.10)
project(wip)

file(GLOB_RECURSE COMMON_SOURCES CONFIGURE_DEPENDS
    "common/*.cpp"
)

# テスト用やサンプル用のソースはビルド対象から除外する
list(FILTER COMMON_SOURCES EXCLUDE REGEX "/tests/")
list(FILTER COMMON_SOURCES EXCLUDE REGEX "/examples/")

# Boost と OpenSSL を取得（CONFIG モード）
find_package(boost CONFIG REQUIRED COMPONENTS asio filesystem system multiprecision)
find_package(OpenSSL REQUIRED)
find_package(Catch2 CONFIG REQUIRED)

# メインバイナリ
add_executable(wip wip.cpp ${COMMON_SOURCES})

target_link_libraries(wip PRIVATE
    boost::asio
    boost::filesystem
    boost::system
    boost::multiprecision
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

# テストバイナリ
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
    boost::asio
    boost::filesystem
    boost::system
    boost::multiprecision
    OpenSSL::SSL
    OpenSSL::Crypto
)

enable_testing()
add_test(NAME all_tests COMMAND wip_tests)
