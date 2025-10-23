# Symbol Search Fix Specification

## ADDED Requirements

### Requirement: Improved Ripgrep Symbol Detection
#### Description:
Enhance the ripgrep-based symbol search to properly detect function, class, and variable definitions across multiple programming languages.

#### Scenario:
When a user searches for a symbol name like "myFunction", the system should return all occurrences where "myFunction" is defined as a function, not just where it appears as a word.

#### Acceptance Criteria:
- Ripgrep patterns correctly identify function definitions in Python (`def myFunction`)
- Ripgrep patterns correctly identify class definitions in JavaScript (`class MyClass`)
- Ripgrep patterns correctly identify variable declarations in Java (`int myVar`)

### Requirement: Enhanced Symbol Type Classification
#### Description:
Improve the `_detect_symbol_type` method to accurately classify symbols by type across different programming languages.

#### Scenario:
When symbol search finds a match, it should correctly identify whether the symbol is a function, class, method, variable, or other type.

#### Acceptance Criteria:
- Python functions are classified as "function"
- JavaScript classes are classified as "class"
- Java variables are classified as "variable"
- Method definitions are classified as "method"

### Requirement: Reliable Index-Based Fallback
#### Description:
Ensure the index-based symbol search fallback works correctly when ripgrep search fails or is unavailable.

#### Scenario:
When ripgrep is not available or fails to find symbols, the system should fall back to searching the symbol database directly.

#### Acceptance Criteria:
- Index search returns results when ripgrep is unavailable
- Symbol name matching works correctly with case sensitivity options
- Fallback search maintains the same result format as ripgrep search

## MODIFIED Requirements

### Requirement: Symbol Search Result Format
#### Description:
Maintain consistent result format across both ripgrep and index-based symbol search methods.

#### Scenario:
Whether using ripgrep or index search, the results should have the same structure to ensure MCP tool compatibility.

#### Acceptance Criteria:
- Both search methods return results with `symbol`, `type`, `file`, `line` fields
- Result format is consistent with existing MCP tool interface
- No breaking changes to existing API