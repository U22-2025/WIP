cmake_minimum_required(VERSION 3.10)
project(wip)

file(GLOB_RECURSE COMMON_SOURCES CONFIGURE_DEPENDS
    "common/*.cpp"
)

# テスト用やサンプル用のソースはビルド対象から除外する
list(FILTER COMMON_SOURCES EXCLUDE REGEX "/tests/")
list(FILTER COMMON_SOURCES EXCLUDE REGEX "/examples/")

add_executable(wip wip.cpp ${COMMON_SOURCES})

find_package(OpenSSL REQUIRED)
find_package(Boost REQUIRED)
target_link_libraries(wip PRIVATE OpenSSL::Crypto Boost::headers)

target_include_directories(wip PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/common
)

if (CMAKE_VERSION VERSION_GREATER 3.12)
  set_property(TARGET wip PROPERTY CXX_STANDARD 20)
endif()

# TODO: テストを追加し、必要な場合は、ターゲットをインストールします。
