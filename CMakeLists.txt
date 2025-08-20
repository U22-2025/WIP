cmake_minimum_required(VERSION 3.15)
project(WIP LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(wip_app src/main.cpp)

find_package(Threads REQUIRED)
target_link_libraries(wip_app PRIVATE Threads::Threads)

set_target_properties(wip_app PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)
