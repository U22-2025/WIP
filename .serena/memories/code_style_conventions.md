# Code Style and Conventions

## Rust Conventions

### General Style
- Follow standard Rust conventions (use `cargo fmt`)
- Use `cargo clippy` for linting
- Document public APIs with `///` comments
- Use meaningful variable and function names
- Prefer `snake_case` for functions and variables
- Use `PascalCase` for types and traits

### Error Handling
- Use custom error types derived from `thiserror` or similar
- Chain errors appropriately for debugging
- Prefer `Result<T, E>` over panicking
- Use `?` operator for error propagation

### Async Programming
- Use `tokio` for async runtime
- Implement `async` traits where appropriate
- Use connection pooling for network operations
- Handle timeouts and retries gracefully

### Testing
- Unit tests in same file with `#[cfg(test)]`
- Integration tests in `tests/` directory  
- Use descriptive test names
- Include both positive and negative test cases
- Mock external dependencies

### Memory Management
- Prefer zero-copy operations where possible
- Use `Arc` and `Mutex` for shared state
- Implement buffer pooling for frequent allocations
- Profile memory usage for optimization

## Python Conventions (Reference)

### Style Guidelines
- Follow PEP 8 standards
- Use type hints for function signatures
- Document functions with docstrings
- Use `snake_case` for functions and variables
- Use `PascalCase` for classes

### Project-Specific
- Binary protocol must be byte-compatible between Python and Rust
- Packet format follows JSON specifications in `format_spec/`
- Extended fields use 10-bit length + 6-bit type header
- Checksum calculation must be identical (12-bit carry fold)

## Architecture Patterns

### Packet Design
- Implement `PacketFormat` trait for all packet types
- Support both request and response packets
- Include automatic checksum calculation
- Handle extended fields dynamically

### Client Design
- Async-first with sync compatibility
- Connection pooling and retry logic
- Comprehensive error handling
- Debug logging integration

### Network Protocol
- UDP-based communication
- 16-byte base packet size
- NTP-style timestamp format
- Binary encoding for efficiency