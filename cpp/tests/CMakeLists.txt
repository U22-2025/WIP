cmake_minimum_required(VERSION 3.10)
project(wip_tests)

find_package(Catch2 3 REQUIRED)
find_package(OpenSSL REQUIRED)

include(CTest)
enable_testing()

add_executable(test_auth test_auth.cpp)
add_executable(test_packet test_packet.cpp)

# Link wipcommon library from parent directory build
target_link_libraries(test_auth PRIVATE wipcommon Catch2::Catch2WithMain OpenSSL::Crypto)
target_link_libraries(test_packet PRIVATE wipcommon Catch2::Catch2WithMain)

include(Catch)
catch_discover_tests(test_auth)
catch_discover_tests(test_packet)
