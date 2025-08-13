cmake_minimum_required(VERSION 3.20)

project(wiplib_cpp VERSION 0.1.0 LANGUAGES CXX)

option(WIPLIB_BUILD_TESTS "Build tests" ON)
option(WIPLIB_BUILD_SHARED "Build shared library" OFF)
option(WIPLIB_ENABLE_SANITIZERS "Enable address/ub sanitizers (non-MSVC)" OFF)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

set(WIPLIB_SRC
    src/packet/codec.cpp
    src/client/weather_client.cpp
    src/client/wip_client.cpp
    src/client/location_client.cpp
    src/client/query_client.cpp
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

target_compile_definitions(wiplib PRIVATE $<$<CONFIG:Debug>:WIPLIB_DEBUG=1>)

if(WIPLIB_ENABLE_SANITIZERS AND NOT MSVC)
  target_compile_options(wiplib PRIVATE -fsanitize=address,undefined -fno-omit-frame-pointer)
  target_link_libraries(wiplib PRIVATE -fsanitize=address,undefined)
endif()

if(WIPLIB_BUILD_TESTS)
  add_executable(wiplib_tests tests/test_codec.cpp)
  target_link_libraries(wiplib_tests PRIVATE wiplib)
  target_include_directories(wiplib_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
  add_executable(wiplib_golden tests/test_golden.cpp)
  target_link_libraries(wiplib_golden PRIVATE wiplib)
  target_include_directories(wiplib_golden PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
endif()

# CLI tool
add_executable(wip_client_cli tools/wip_client_cli.cpp)
target_link_libraries(wip_client_cli PRIVATE wiplib)
target_include_directories(wip_client_cli PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(wip_packet_gen tools/wip_packet_gen.cpp)
target_link_libraries(wip_packet_gen PRIVATE wiplib)
target_include_directories(wip_packet_gen PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(wip_packet_decode tools/wip_packet_decode.cpp)
target_link_libraries(wip_packet_decode PRIVATE wiplib)
target_include_directories(wip_packet_decode PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)

add_executable(wip_packet_roundtrip tools/wip_packet_roundtrip.cpp)
target_link_libraries(wip_packet_roundtrip PRIVATE wiplib)
target_include_directories(wip_packet_roundtrip PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
