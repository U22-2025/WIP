#!/bin/bash

# Simple build script for testing auth functionality
echo "Building minimal test..."

# Compile auth config test
g++ -std=c++17 -I include -O2 \
    test_auth_config.cpp \
    src/utils/auth_config.cpp \
    -o test_auth_config_new

# Try to compile the main client (might have dependency issues but worth trying)
echo "Attempting to build wip_client_cli..."
g++ -std=c++17 -I include -O2 \
    tools/wip_client_cli.cpp \
    src/utils/auth_config.cpp \
    src/utils/auth.cpp \
    src/packet/codec.cpp \
    src/packet/checksum.cpp \
    src/packet/bit_utils.cpp \
    src/client/query_client.cpp \
    src/client/weather_client.cpp \
    src/client/wip_client.cpp \
    src/client/location_client.cpp \
    -o wip_client_cli_debug 2>&1 | head -20

echo "Build complete (check for errors above)"