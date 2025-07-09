cmake_minimum_required(VERSION 3.10)
project(wipcommon)

# 必要に応じて CMake policy を設定
cmake_policy(SET CMP0076 NEW)  # target_sources用
cmake_policy(SET CMP0079 NEW)  # 親ターゲットにリンクさせる場合に備えて

# C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# OpenSSL
find_package(OpenSSL REQUIRED)

# ライブラリを作成
add_library(wipcommon STATIC common/placeholder.cpp)

# インクルードパス
target_include_directories(wipcommon PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/common)

# 必要ライブラリをリンク
target_link_libraries(wipcommon PUBLIC OpenSSL::Crypto)

# サブディレクトリ登録（ここでソースを足す）
add_subdirectory(common)
