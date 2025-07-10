cmake_minimum_required(VERSION 3.8)
project(wip LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenSSL REQUIRED)

file(GLOB_RECURSE COMMON_SOURCES
    "wip/common/*.cpp"
)
list(FILTER COMMON_SOURCES EXCLUDE REGEX ".*/packet/examples/.*")

add_library(wipcommon STATIC ${COMMON_SOURCES})
target_include_directories(wipcommon PUBLIC wip/common)
target_link_libraries(wipcommon PUBLIC OpenSSL::Crypto)

add_executable(wip_client wip/client.cpp)
target_link_libraries(wip_client PRIVATE wipcommon)

add_executable(wip_sample wip/wip.cpp)
target_link_libraries(wip_sample PRIVATE wipcommon)

file(GLOB_RECURSE TEST_SOURCES "wip/tests/*.cpp")
if(TEST_SOURCES)
    find_package(Catch2 QUIET)
    if(Catch2_FOUND)
        enable_testing()
        add_executable(wip_tests ${TEST_SOURCES})
        target_link_libraries(wip_tests PRIVATE wipcommon Catch2::Catch2WithMain)
        target_include_directories(wip_tests PRIVATE wip/common)
        add_test(NAME wip_tests COMMAND wip_tests)
    endif()
endif()
