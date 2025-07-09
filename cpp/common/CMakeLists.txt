cmake_minimum_required(VERSION 3.10)
project(wipcommon)

cmake_policy(SET CMP0076 NEW)

find_package(OpenSSL REQUIRED)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 静的ライブラリを作成
add_library(wipcommon STATIC placeholder.cpp)

target_include_directories(wipcommon PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(wipcommon PUBLIC OpenSSL::Crypto)

# サブディレクトリの登録
add_subdirectory(packet)
add_subdirectory(clients)
add_subdirectory(utils)
