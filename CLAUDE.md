# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Python Development
```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .                    # Development mode
pip install -e .[dev]              # With development tools
pip install -e .[servers]          # All server components

# Start all servers
python start_servers.bat           # Windows
./start_servers.sh                 # Linux/macOS
python python/launch_server.py --weather --location --query --report

# Start individual servers
python python/launch_server.py --weather
python python/launch_server.py --location  
python python/launch_server.py --query
python python/launch_server.py --report

# Run client tests
python -m WIPCommonPy.clients.weather_client
python -m WIPCommonPy.clients.location_client
python -m WIPCommonPy.clients.query_client

# Start web applications
python python/application/map/start_fastapi_server.py
python python/application/weather_api/start_fastapi_server.py
```

### Rust Development
```bash
# Build Rust implementation
cd Rust
cargo build --release

# Run tests
cargo test

# Run examples
cargo run --example client
cargo run --example structured_client
cargo run --example packet_showcase

# Run benchmarks
cargo bench
```

### Testing
```bash
# Python integration tests
python test/api_test.py

# Debug tools
python debug_tools/core/integrated_debug_suite.py --mode full
python debug_tools/performance/performance_debug_tool.py
```

## Architecture

### Overview
WIP (Weather Transfer Protocol) is an NTP-based UDP application protocol designed for lightweight weather data transfer. The system uses a distributed architecture with specialized servers and binary packet format for efficiency.

### Core Components

#### Server Architecture
- **Weather Server (Port 4110)**: Main proxy server that receives client requests and routes them to appropriate specialized servers
- **Location Server (Port 4109)**: Handles coordinate-to-area-code resolution using GPS coordinates and geographical boundaries
- **Query Server (Port 4111)**: Fetches and processes weather data from Japan Meteorological Agency (JMA), manages weather data cache
- **Report Server (Port 4112)**: Receives and validates sensor data reports from IoT devices

#### Packet Structure
- **Base packet size**: 16 bytes (128 bits)
- **Header fields**: Version (4bit), Packet ID (12bit), Type (3bit), Flags (8bit), Day (3bit), Reserved (2bit)
- **Core data**: Timestamp (64bit), Area Code (20bit), Checksum (12bit)
- **Extended fields**: Variable-length extensions for alerts, disaster info, coordinates

### Key Modules

#### Python Implementation (`src/WIPCommonPy/`)
- **packet/core/**: Bit manipulation, checksum calculation, packet format base classes
- **packet/types/**: Specific packet types (location, query, report, error responses)
- **clients/**: Network clients for each server type with connection pooling and caching
- **utils/**: Authentication, configuration loading, caching, logging utilities

#### Rust Implementation (`Rust/src/wip_common_rs/`)
- **packet/core/**: Rust equivalents of Python packet handling with zero-copy optimizations
- **clients/**: Async clients using tokio with connection pooling and retry mechanisms
- **utils/**: Configuration, authentication, caching, and logging utilities

### Data Sources
- **Japan Meteorological Agency (JMA)**: Primary source for weather data, alerts, and disaster information
- **Area codes**: 6-digit numerical codes following JMA regional classification system
- **Weather codes**: JMA weather code system (100-series for clear, 200-series for cloudy, etc.)

### Caching Strategy
- **Redis**: High-speed data caching with TTL management
- **File cache**: Persistent coordinate and area code caching
- **Memory cache**: In-process caching for frequently accessed data

### Security Features
- **Checksum validation**: 12-bit checksum for packet integrity
- **Timestamp validation**: Replay attack prevention
- **Packet ID tracking**: Duplicate packet detection
- **Authentication framework**: Extensible auth system with passphrase support

## Development Notes

### Packet Format Specifications
- Field definitions are stored in JSON files under `packet/format_spec/`
- Both Python and Rust implementations use the same field specifications
- Extended fields support variable-length data with 10-bit length + 6-bit type header

### Configuration
- Server configurations in `config.ini` files within each server directory
- Environment variables supported via `.env` files
- Redis configuration for caching and logging

### Performance Considerations
- Target response time: <100ms average
- Throughput: >100 requests/second
- Memory optimization through buffer pooling and zero-copy operations
- Parallel processing support for batch operations

### Testing Framework
- Integration tests verify end-to-end communication
- Performance benchmarks compare against external weather APIs
- Debug tools provide detailed packet analysis and communication flow tracking

### Multi-language Support
- Python implementation: Production-ready with full feature set
- Rust implementation: High-performance alternative with async support
- Both implementations maintain protocol compatibility

## Important Files
- `README.md`: Comprehensive project documentation with usage examples
- `Rust/TASKS.md`: Detailed implementation roadmap for Rust version
- `docs/WIP仕様表.md`: Technical specifications in Japanese
- `python/launch_server.py`: Multi-server launcher script
- `requirements.txt` / `pyproject.toml`: Python dependencies
- `Rust/Cargo.toml`: Rust dependencies and build configuration