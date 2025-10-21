# Design Decisions

## Architecture Approach
Linus-style: direct data manipulation, no abstractions, solve real problems.

## Core Fixes

### Edit Operations
**Problem**: 100% baseline test failures
**Solution**: Direct file operations, fix root cause, no wrapper layers

### Backup API  
**Problem**: Interface inconsistencies
**Solution**: Single consistent interface, direct file system operations

### Code Complexity
**Problem**: Functions >30 lines
**Solution**: Extract helpers, single responsibility, direct data access

## What We're NOT Doing
- ❌ Streaming architecture (over-engineering for 1MB files)
- ❌ Memory monitoring systems (unnecessary complexity)
- ❌ Performance optimizations (focus on functionality first)
- ❌ Enhanced test coverage (fix core issues first)

## Constraints
- Functions <30 lines
- Direct error raising
- No service abstractions
- Minimal changes