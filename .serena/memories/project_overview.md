# Project Overview

## Purpose
WIP (Weather Transfer Protocol) is an NTP-based UDP application protocol for lightweight weather data transfer. It's designed for IoT devices with efficient binary packet format (16 bytes base size) to distribute weather data from Japan Meteorological Agency (JMA).

## Architecture
- **Weather Server (Port 4110)**: Main proxy server that routes requests to specialized servers
- **Location Server (Port 4109)**: Converts GPS coordinates to area codes
- **Query Server (Port 4111)**: Fetches weather data from JMA and manages cache
- **Report Server (Port 4112)**: Receives sensor data reports from IoT devices

## Tech Stack
- **Python**: Production implementation with full feature set
- **Rust**: High-performance alternative with async support (current focus)
- **Redis/KeyDB**: Caching and logging
- **PostgreSQL + PostGIS**: Geographic data for location resolution
- **Binary protocol**: Custom 16-byte UDP packets with extensions

## Project Structure
- `/python/`: Python implementation (WIPCommonPy)
- `/Rust/`: Rust implementation (current work)
- `/src/`: Legacy Python sources
- `/docs/`: Technical specifications
- `/debug_tools/`: Comprehensive debugging suite
- `/test/`: Integration tests and performance benchmarks