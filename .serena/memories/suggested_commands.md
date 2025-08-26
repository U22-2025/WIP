# Suggested Commands for WIP Development

## Rust Development Commands

### Build and Test
```bash
# Build the Rust implementation
cd Rust
cargo build --release

# Run all tests
cargo test

# Run specific test categories
cargo test unit
cargo test integration
cargo test --test test_packets

# Run tests with output
cargo test -- --nocapture

# Run benchmarks
cargo bench
```

### Examples and Usage
```bash
# Run client examples
cargo run --example client
cargo run --example structured_client
cargo run --example packet_showcase
```

### Documentation
```bash
# Generate API documentation
cargo doc --open

# Check documentation
cargo doc --no-deps
```

### Code Quality
```bash
# Format code
cargo fmt

# Lint code
cargo clippy

# Check without building
cargo check
```

## Python Development Commands

### Server Management
```bash
# Start all servers
python start_servers.bat           # Windows
./start_servers.sh                 # Linux/macOS
python python/launch_server.py --weather --location --query --report

# Start individual servers
python python/launch_server.py --weather
python python/launch_server.py --location  
python python/launch_server.py --query
python python/launch_server.py --report
```

### Client Testing
```bash
# Run client tests
python -m WIPCommonPy.clients.weather_client
python -m WIPCommonPy.clients.location_client
python -m WIPCommonPy.clients.query_client
```

### Web Applications
```bash
# Start FastAPI servers
python python/application/map/start_fastapi_server.py
python python/application/weather_api/start_fastapi_server.py
```

### Testing and Debugging
```bash
# Python integration tests
python test/api_test.py

# Comprehensive debug suite
python debug_tools/core/integrated_debug_suite.py --mode full
python debug_tools/performance/performance_debug_tool.py
```

## Environment Setup

### Dependencies
```bash
# Python dependencies
pip install -r requirements.txt
pip install -e .                    # Development mode
pip install -e .[dev]              # With development tools
pip install -e .[servers]          # All server components

# Rust dependencies (handled by Cargo)
# No manual installation needed
```

### Database Setup
```bash
# PostgreSQL + PostGIS for geographic data
# Redis for caching
# Configure via .env file or config.ini
```

## When Task is Complete
1. Run `cargo test` to ensure all tests pass
2. Run `cargo clippy` for linting
3. Run `cargo fmt` for formatting
4. Run `cargo doc` to verify documentation
5. For integration: run Python servers and test communication