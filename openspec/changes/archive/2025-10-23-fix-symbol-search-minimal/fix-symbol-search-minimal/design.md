# Symbol Search Fix Design - Minimal Approach

## Current Implementation Analysis

### Symbol Search Flow
1. `search_code()` with `search_type="symbol"` calls `SearchEngine._search_symbol()`
2. Method attempts ripgrep search first (`_search_symbol_with_ripgrep`)
3. Falls back to index search (`_search_symbol_fallback`)
4. Both paths currently return empty results

### Identified Issues

#### 1. Ripgrep Symbol Search Issues
- Uses only `-w` flag for word boundaries, insufficient for symbol definitions
- Symbol type detection in `_detect_symbol_type` is too simplistic
- No language-specific patterns for different symbol types

#### 2. Index-Based Search Issues
- May have case sensitivity or pattern matching problems
- Symbol database population needs verification

## Minimal Fix Strategy

### Phase 1: Improve Ripgrep Patterns
- Add better ripgrep patterns for function/class/variable detection
- Enhance `_detect_symbol_type` with more comprehensive patterns
- Test with sample code files

### Phase 2: Verify Index Fallback
- Check if `self.index.symbols` contains expected data
- Fix any pattern matching issues in the fallback logic
- Ensure case sensitivity handling is correct

### Phase 3: Basic Testing
- Create simple test cases for symbol search
- Verify fixes work across different languages
- Ensure no regression in other search types

## Implementation Notes

### Linus-Style Principles
- Direct data manipulation, no abstractions
- Keep changes minimal and focused
- Functions under 30 lines, files under 200 lines
- No service layers or complex patterns

### Performance Considerations
- Maintain sub-second search times
- Use existing ripgrep and index infrastructure
- No additional caching or complexity needed

### Testing Strategy
- Simple unit tests for each fix
- Integration tests with sample projects
- No complex performance benchmarks needed