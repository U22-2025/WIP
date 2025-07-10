cmake_minimum_required(VERSION 3.8)
project(wip LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

file(GLOB_RECURSE WIP_SOURCES
    "common/*.cpp"
    "client.cpp"
    "wip.cpp"
)
list(FILTER WIP_SOURCES EXCLUDE REGEX ".*/packet/examples/.*")

add_executable(wip ${WIP_SOURCES})

target_include_directories(wip PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/common
)

# Optionally build tests if Catch2 is available
file(GLOB_RECURSE TEST_SOURCES "tests/*.cpp")
if(TEST_SOURCES)
    find_package(Catch2 QUIET)
    if(Catch2_FOUND)
        enable_testing()
        add_executable(wip_tests ${TEST_SOURCES})
        target_link_libraries(wip_tests PRIVATE Catch2::Catch2WithMain)
        target_include_directories(wip_tests PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/common)
        add_test(NAME wip_tests COMMAND wip_tests)
    endif()
endif()
