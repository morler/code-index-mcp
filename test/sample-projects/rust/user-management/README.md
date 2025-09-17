# Rust User Management Sample Project

This is a sample Rust project demonstrating user management functionality, similar to the other language examples in the test suite.

## Project Structure

```
src/
├── main.rs          # Main application entry point with TCP server
├── lib.rs           # Library entry point
├── models/          # Data models
│   ├── mod.rs       # Module declarations
│   └── user.rs      # User, Person, and related enums
├── services/        # Business logic
│   ├── mod.rs       # Module declarations
│   └── user_manager.rs  # Core user management service
└── utils/           # Utility functions
    ├── mod.rs       # Module declarations
    ├── errors.rs     # Custom error types
    └── validators.rs # Input validation functions
```

## Features

- **User Model**: Complete user structure with UUID, timestamps, and enums for roles/status
- **Validation**: Email and username validation with regex patterns
- **Error Handling**: Custom error types using thiserror crate
- **User Management**: CRUD operations with indexing by username and email
- **TCP Server**: Simple async TCP server for testing the user management API
- **Enums**: UserRole and UserStatus for type-safe state management

## Key Rust Concepts Demonstrated

- **Structs and Enums**: Type-safe data modeling
- **Traits**: Error handling with thiserror
- **Ownership**: Proper memory management with references and cloning
- **Pattern Matching**: Comprehensive error handling and data processing
- **Modules**: Clean code organization with pub mod and use statements
- **Async Programming**: Tokio-based TCP server
- **Collections**: HashMap for efficient user lookup and indexing
- **Macros**: println!, format! for string formatting

## Usage

```bash
# Build the project
cargo build

# Run the server
cargo run

# Test the server (in another terminal)
# The server listens on 127.0.0.1:8080
```

## Server Commands

The TCP server accepts simple text commands:

- `CREATE username email first_name last_name` - Create a new user
- `GET <username|email|id>` - Get user information
- `LIST` - List all users
- `DELETE <username|email|id>` - Delete a user
- `HELP` - Show available commands

## Dependencies

- `serde` - Serialization framework
- `serde_json` - JSON serialization
- `uuid` - UUID generation and parsing
- `chrono` - Date and time handling
- `tokio` - Async runtime
- `thiserror` - Error handling derive macro
- `regex` - Regular expressions for validation

This project serves as a comprehensive example of idiomatic Rust code structure and patterns for testing the code indexing functionality.