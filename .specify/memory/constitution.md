<!--
Sync Impact Report:
Version change: 1.0.0 → 1.0.0 (initial constitution)
Modified principles: None (initial creation)
Added sections: Core Principles (5), Architecture Standards, Development Workflow, Governance
Removed sections: None
Templates requiring updates: ✅ plan-template.md, ✅ spec-template.md, ✅ tasks-template.md
Follow-up TODOs: None
-->

# Code Index MCP Constitution

## Core Principles

### I. Linus-Style Direct Data Manipulation
Every operation MUST manipulate data structures directly - no service abstractions, no wrapper classes, no delegation patterns. The CodeIndex class is the single source of truth for ALL indexing operations. Function dispatch through operation registry eliminates if/else chains. Atomic operations with automatic rollback ensure data integrity.

### II. Unified Interface Elimination
All MCP tools MUST route through `unified_tool()` - no specialized tool functions. Single entry point eliminates branching complexity and ensures consistent behavior. Text-based protocols (stdin/stdout/stderr) for all operations ensuring debuggability without special logging infrastructure.

### III. SCIP Protocol First (NON-NEGOTIABLE)
All symbol operations MUST use SCIP protocol for semantic analysis. Tree-sitter parsing for 7 core languages (Python, JavaScript, TypeScript, Java, Go, Zig, Objective-C) with fallback strategy for others. No regex-based symbol extraction - fail fast with clear errors when parsers unavailable.

### IV. Incremental Performance
Only changed files MAY be processed - full rebuilds only for structural changes. LRU caching with 80% memory threshold cleanup. Hash-based change detection using xxhash for rapid file comparison. Direct dictionary access with zero copying - no data transformation layers.

### V. Simplicity Obsession
Files MUST stay under 200 lines with maximum 3 indentation levels. Functions under 30 lines doing one thing well. No more than 3 levels of directory nesting. Dataclasses for data structures only - no inheritance hierarchies beyond essential SCIP protocol requirements.

## Architecture Standards

### Data Structure Rules
- Single CodeIndex class handles ALL operations
- Direct dictionary access for symbol storage
- No ORM or database abstraction layers
- Atomic edit operations with automatic backup/rollback
- SCIP symbol IDs as primary keys for cross-file references

### Performance Requirements
- Sub-100ms response for file operations
- Memory usage under 100MB for typical projects
- Incremental updates under 1 second for <100 changed files
- Zero-copy data access patterns throughout

### Language Support Strategy
- Tree-sitter parsers for core languages (Python, JS, TS, Java, Go, Zig, Objective-C)
- FallbackParsingStrategy for all other languages
- Fail fast with clear error messages when parsing unavailable
- No language-specific special cases in core logic

## Development Workflow

### Code Review Requirements
- All PRs MUST verify compliance with simplicity constraints
- Complexity beyond 3 indentation levels requires explicit justification
- Any new abstraction MUST be approved with concrete performance benefit
- Backward compatibility is mandatory - never break existing MCP tool contracts

### Testing Discipline
- Unit tests for core data structure operations
- Integration tests for SCIP protocol compliance
- Performance tests for incremental updates
- Cross-language symbol resolution tests

### Quality Gates
- MyPy type checking with strict mode
- Maximum 100 character line length
- Functions under 30 lines without justification
- No circular imports between core modules

## Governance

This constitution supersedes all other development practices. Amendments require:
1. Documentation of specific problem being solved
2. Performance impact analysis with benchmarks
3. Migration plan ensuring backward compatibility
4. Approval through PR process with constitution compliance check

All code reviews MUST verify constitutional compliance. Complexity violations require explicit justification in PR description with performance benchmarks proving necessity. Use AGENTS.md for runtime development guidance updates.

**Version**: 1.0.0 | **Ratified**: 2025-01-09 | **Last Amended**: 2025-01-09