## MODIFIED Requirements
### Requirement: Unified Core Data Structures
The system SHALL provide a single, unified core module for all indexing operations.

#### Scenario: Single source of truth
- **WHEN** accessing core functionality
- **THEN** all imports resolve to `src/core/` only
- **AND** no duplicate modules exist

#### Scenario: File size limits
- **WHEN** implementing core modules
- **THEN** each file contains <200 lines of code
- **AND** maximum 3 levels of indentation

#### Scenario: Data structure consistency
- **WHEN** storing file and symbol information
- **THEN** use unified FileInfo and SymbolInfo dataclasses
- **AND** eliminate duplicate definitions

## REMOVED Requirements
### Requirement: Dual Core Architecture
**Reason**: Eliminates code duplication and maintenance overhead
**Migration**: All code should import from `src/core/` only

### Requirement: Large File Processing
**Reason**: Violates maintainability principles
**Migration**: Split files into focused, single-responsibility modules

## ADDED Requirements
### Requirement: Linus-style Architecture
The system SHALL follow Linus Torvalds' design principles.

#### Scenario: Good taste implementation
- **WHEN** designing data structures
- **THEN** eliminate special cases and if/else chains
- **AND** use direct data manipulation

#### Scenario: Zero abstraction principle
- **WHEN** implementing functionality
- **THEN** avoid unnecessary service wrappers
- **AND** prefer direct data access patterns

#### Scenario: Unified tool interface
- **WHEN** exposing MCP tools
- **THEN** use single `execute_tool()` function
- **AND** eliminate 30+ specialized tool functions