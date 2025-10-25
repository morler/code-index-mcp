# Fix Symbol Search Functionality - Minimal Approach

## Problem Statement
The symbol search functionality in the code-index-mcp project is returning empty results, preventing users from effectively searching for symbols across the codebase. This impacts the core functionality of the MCP server.

## Current Behavior
- Symbol search queries return `{"success": true, "matches": [], "total_count": 0, "search_time": 0.001...}`
- Text and regex searches work correctly
- Symbol indexing appears to complete successfully (1323 symbols indexed)
- The issue is in the symbol search retrieval mechanism

## Root Cause Analysis
Based on code inspection in `src/core/search.py`, the issue appears to be:
1. Ripgrep symbol search uses overly simplistic patterns (`-w` flag only)
2. Symbol type detection is too basic and misses many patterns
3. Index-based fallback may have symbol name matching issues

## Proposed Solution - Minimal Fix
Implement targeted fixes to the existing symbol search implementation:
1. Improve ripgrep symbol patterns for better detection
2. Enhance symbol type detection logic
3. Verify and fix index-based search fallback
4. Add basic tests to verify the fixes work

## Success Criteria
- Symbol search returns accurate results for functions, classes, and variables
- Search performance remains under 1 second for typical queries
- All existing tests continue to pass
- New tests verify symbol search works

## Scope
This change focuses specifically on fixing the symbol search bug without modifying architecture or other search functionality. Follows Linus-style principles with direct data manipulation.