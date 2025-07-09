cmake_minimum_required(VERSION 3.10)
project(wipcommon)

# Create the static library target
add_library(wipcommon STATIC placeholder.cpp)

target_include_directories(wipcommon PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# Add subdirectories
add_subdirectory(packet)
add_subdirectory(clients)
add_subdirectory(utils)
