cmake_minimum_required(VERSION 3.20)

project(wiplib_cpp VERSION 0.1.0 LANGUAGES CXX)

option(WIPLIB_BUILD_TESTS "Build tests" OFF)
option(WIPLIB_BUILD_SHARED "Build shared library" OFF)
option(WIPLIB_ENABLE_SANITIZERS "Enable address/ub sanitizers (non-MSVC)" OFF)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(WIPLIB_SRC
    src/packet/codec.cpp
    src/packet/checksum.cpp
    src/packet/bit_utils.cpp
    src/packet/format_base.cpp
    src/packet/extended_field.cpp
    src/packet/request.cpp
    src/packet/response.cpp
    src/packet/report_packet_compat.cpp
    src/packet/report_packet.cpp
    src/packet/location_packet.cpp
    src/packet/error_response.cpp
    src/packet/format_parser.cpp
    src/packet/dynamic_packet_parser.cpp
    src/client/weather_client.cpp
    src/client/wip_client.cpp
    src/client/location_client.cpp
    src/client/query_client.cpp
    src/client/async_weather_client.cpp
    src/client/client.cpp
    src/client/client_async.cpp
    src/client/report_client.cpp
    src/client/utils/safe_sock_sendto.cpp
    src/client/utils/receive_with_id.cpp
    src/client/utils/connection_pool.cpp
    src/utils/log_config.cpp
    src/utils/auth.cpp
    src/utils/auth_config.cpp
    src/utils/dotenv.cpp
    src/utils/config_loader.cpp
    src/utils/file_cache.cpp
    src/utils/encoding.cpp
    src/utils/env.cpp
    src/utils/network.cpp
    src/utils/platform_compat.cpp
    src/utils/redis_log_handler.cpp
    src/packet/debug/debug_logger.cpp
    src/compatibility/python_errors.cpp
    src/compatibility/python_config.cpp
    src/compatibility/python_protocol.cpp
)

if(WIPLIB_BUILD_SHARED)
  add_library(wiplib SHARED ${WIPLIB_SRC})
else()
  add_library(wiplib STATIC ${WIPLIB_SRC})
endif()

target_include_directories(wiplib
  PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Link required libraries
find_package(Threads REQUIRED)
target_link_libraries(wiplib PRIVATE Threads::Threads)

# Optional external libraries
if(WIN32)
  # Typical installation paths for prebuilt Windows binaries
  set(OPENSSL_ROOT_DIR
      "C:/OpenSSL-Win64"
      "C:/Program Files/OpenSSL-Win64"
      CACHE PATH "OpenSSL installation root")
  set(BOOST_ROOT
      "C:/local/boost_1_84_0"
      CACHE PATH "Boost installation root")
endif()

find_package(OpenSSL QUIET)
if(OpenSSL_FOUND)
  target_link_libraries(wiplib PRIVATE OpenSSL::SSL OpenSSL::Crypto)
else()
  message(STATUS "OpenSSL not found; continuing without SSL support")
endif()

find_package(Boost QUIET)
if(Boost_FOUND)
  target_link_libraries(wiplib PRIVATE Boost::boost)
else()
  message(STATUS "Boost not found; continuing without Boost")
endif()

# Platform-specific socket libraries
if(WIN32)
    target_link_libraries(wiplib PRIVATE ws2_32 wsock32)
endif()

target_compile_definitions(wiplib PRIVATE $<$<CONFIG:Debug>:WIPLIB_DEBUG=1>)

# Windows specific compiler options
if(MSVC)
  # Apply UTF-8 to all targets
  add_compile_options(/utf-8)
  target_compile_options(wiplib PRIVATE /utf-8)
endif()

if(WIPLIB_ENABLE_SANITIZERS AND NOT MSVC)
  target_compile_options(wiplib PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
  target_link_libraries(wiplib PRIVATE -fsanitize=address,undefined)
endif()

if(WIPLIB_BUILD_TESTS)
  # Enable testing
  enable_testing()

  # Try to find Google Test first
  find_package(GTest QUIET)
  
  if(NOT GTest_FOUND)
    # Google Test via FetchContent
    include(FetchContent)
    FetchContent_Declare(
      googletest
      GIT_REPOSITORY https://github.com/google/googletest.git
      GIT_TAG release-1.12.1
      GIT_SHALLOW TRUE
    )
    # For Windows: Prevent overriding the parent project's compiler/linker settings
    set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googletest)
    
    # Create aliases for compatibility (only if they don't exist)
    if(NOT TARGET GTest::gtest)
      add_library(GTest::gtest ALIAS gtest)
    endif()
    if(NOT TARGET GTest::gtest_main)
      add_library(GTest::gtest_main ALIAS gtest_main)
    endif()
  endif()

  message(STATUS "No test directory found, skipping test build")
endif()

# CLI tools
add_executable(wip_client_cli tools/wip_client_cli.cpp)
target_link_libraries(wip_client_cli PRIVATE wiplib)
target_include_directories(wip_client_cli PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(unified_client_cli tools/unified_client_cli.cpp)
target_link_libraries(unified_client_cli PRIVATE wiplib)
target_include_directories(unified_client_cli PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(report_debug_tool tools/report_debug_tool.cpp)
target_link_libraries(report_debug_tool PRIVATE wiplib)
target_include_directories(report_debug_tool PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(wip_packet_gen tools/wip_packet_gen.cpp)
target_link_libraries(wip_packet_gen PRIVATE wiplib)
target_include_directories(wip_packet_gen PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(wip_packet_decode tools/wip_packet_decode.cpp)
target_link_libraries(wip_packet_decode PRIVATE wiplib)
target_include_directories(wip_packet_decode PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(wip_packet_roundtrip tools/wip_packet_roundtrip.cpp)
target_link_libraries(wip_packet_roundtrip PRIVATE wiplib)
target_include_directories(wip_packet_roundtrip PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(async_weather_cli tools/async_weather_cli.cpp)
target_link_libraries(async_weather_cli PRIVATE wiplib)
target_include_directories(async_weather_cli PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Additional tools
add_executable(wip_packet_analyzer tools/wip_packet_analyzer.cpp)
target_link_libraries(wip_packet_analyzer PRIVATE wiplib)
target_include_directories(wip_packet_analyzer PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(wip_config_validator tools/wip_config_validator.cpp)
target_link_libraries(wip_config_validator PRIVATE wiplib)
target_include_directories(wip_config_validator PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(wip_performance_test tools/wip_performance_test.cpp)
target_link_libraries(wip_performance_test PRIVATE wiplib)
target_include_directories(wip_performance_test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(packet_encoding_debug tools/packet_encoding_debug.cpp)
target_link_libraries(packet_encoding_debug PRIVATE wiplib)
target_include_directories(packet_encoding_debug PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(mock_report_server tools/mock_report_server.cpp)
target_link_libraries(mock_report_server PRIVATE wiplib)
target_include_directories(mock_report_server PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(test_auth_vars tools/test_auth_vars.cpp)
target_link_libraries(test_auth_vars PRIVATE wiplib)
target_include_directories(test_auth_vars PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
