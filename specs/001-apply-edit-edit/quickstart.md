# Quick Start Guide: Apply Edit Backup Directory Fix

**Date**: 2025-10-09  
**Feature**: Apply Edit Backup Directory Fix

## Overview

This enhancement fixes backup directory write issues in the `apply_edit` function by implementing robust backup creation with automatic directory management, fallback mechanisms, and concurrent-safe operations.

## Key Features

- ✅ **Automatic Directory Creation**: `.edit_backup` directory created automatically
- ✅ **Fallback to System Temp**: Uses system temp directory when primary location unavailable
- ✅ **Concurrent-Safe Naming**: Microsecond timestamps prevent conflicts
- ✅ **Error Handling**: Clear error messages and graceful failure handling
- ✅ **Performance**: <50ms backup creation for files <1MB
- ✅ **Cleanup**: Automatic cleanup retaining only 100 most recent backups

## Usage Examples

### Basic File Edit with Backup

```python
from code_index_mcp import CodeIndex

# Initialize index
index = CodeIndex()

# Edit file with automatic backup
success, error = index.edit_file_atomic(
    file_path="src/example.py",
    old_content="old content",
    new_content="new content"
)

if success:
    print("Edit successful, backup created")
else:
    print(f"Edit failed: {error}")
```

### Batch File Operations

```python
from code_index_mcp import AtomicEdit

# Define multiple edits
edits = [
    AtomicEdit("file1.py", "old1", "new1"),
    AtomicEdit("file2.py", "old2", "new2"),
    AtomicEdit("file3.py", "old3", "new3")
]

# Execute atomic batch edit
success, error = index.edit_files_atomic(edits)
```

### MCP Tool Usage

```python
# Through MCP unified interface
result = unified_tool("apply_edit", {
    "file_path": "src/example.py",
    "old_content": "old content",
    "new_content": "new content"
})

if result["success"]:
    print("Backup created successfully")
```

## Backup File Management

### Backup Location Structure

```
project_root/
├── .edit_backup/              # Primary backup location
│   ├── src_example.py.1234567890123456.bak
│   ├── src_example.py.1234567890123457.bak
│   └── quarantine/            # Corrupted backups
│       └── corrupted_file.bak
└── src/
    └── example.py
```

### Backup Naming Convention

- **Format**: `{relative_path}.{microsecond_timestamp}.bak`
- **Example**: `src_example.py.1696845123456789.bak`
- **Uniqueness**: Microsecond precision + process ID ensures no conflicts

### Manual Backup Operations

```python
# Create backup manually
backup_path = index._create_backup(Path("important_file.py"))

# Clean up old backups
backup_dir = Path(".edit_backup")
# Keep only 100 most recent backups
backup_files = sorted(backup_dir.glob("*.bak"), key=os.path.getctime)
for old_backup in backup_files[100:]:
    old_backup.unlink()
```

## Error Handling

### Common Error Scenarios

1. **Permission Denied**
   ```python
   # System automatically falls back to temp directory
   # Error message: "Using system temp directory for backup"
   ```

2. **Disk Full**
   ```python
   # Operation aborts with clear error
   # Error message: "Disk full: Cannot create backup, edit aborted"
   ```

3. **Concurrent Access**
   ```python
   # Handled automatically with unique timestamps
   # No user intervention required
   ```

### Error Recovery

```python
success, error = index.edit_file_atomic(file_path, old, new)

if not success:
    if "permission" in error.lower():
        print("Check file permissions")
    elif "disk full" in error.lower():
        print("Free up disk space")
    elif "backup" in error.lower():
        print("Backup failed, but edit may have succeeded")
```

## Performance Considerations

### Optimization Tips

1. **Small Files**: Files <1MB use optimized fast copy
2. **Batch Operations**: Use `edit_files_atomic` for multiple files
3. **Cleanup**: Regular cleanup prevents directory bloat

### Performance Metrics

- **Backup Creation**: <20ms for files <1MB
- **Concurrent Operations**: 100+ simultaneous backups
- **Memory Overhead**: <10MB for backup operations
- **Disk Usage**: Automatically limited to 1GB

## Configuration

### Environment Variables

```bash
# Custom backup directory (optional)
export CODE_INDEX_BACKUP_DIR="/custom/backup/path"

# Maximum backup size (bytes)
export CODE_INDEX_MAX_BACKUP_SIZE=1073741824  # 1GB

# Backup retention count
export CODE_INDEX_BACKUP_RETENTION=100
```

### Programmatic Configuration

```python
# Custom backup manager
from core.backup_manager import BackupManager

backup_mgr = BackupManager(
    backup_dir=Path("/custom/backup"),
    max_size_mb=500,
    max_files=50
)

index.set_backup_manager(backup_mgr)
```

## Testing

### Unit Tests

```bash
# Run backup-specific tests
pytest tests/unit/test_backup_manager.py -v

# Run integration tests
pytest tests/integration/test_concurrent_backups.py -v
```

### Manual Testing

```python
# Test concurrent operations
import threading

def edit_file(thread_id):
    success, error = index.edit_file_atomic(
        f"test_file_{thread_id}.py",
        f"content_{thread_id}",
        f"new_content_{thread_id}"
    )

# Create 10 concurrent edits
threads = []
for i in range(10):
    t = threading.Thread(target=edit_file, args=(i,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()
```

## Troubleshooting

### Common Issues

1. **Backup Directory Not Created**
   - Check write permissions in project directory
   - Verify sufficient disk space
   - Check for antivirus interference

2. **Slow Backup Performance**
   - Ensure files are <1MB for fast path
   - Check disk I/O performance
   - Consider reducing backup retention count

3. **Concurrent Edit Failures**
   - Verify microsecond timestamp precision
   - Check for file system limitations
   - Ensure proper cleanup of old backups

### Debug Information

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check backup directory status
backup_dir = Path(".edit_backup")
print(f"Backup dir exists: {backup_dir.exists()}")
print(f"Backup dir writable: {os.access(backup_dir, os.W_OK)}")
print(f"Backup files: {len(list(backup_dir.glob('*.bak')))}")
```

## Migration from Previous Version

### Breaking Changes

- `edit.py` module is deprecated (backup logic moved to `index.py`)
- Backup naming format changed (now uses microsecond timestamps)
- Error messages improved for better debugging

### Migration Steps

1. **Update Code**: No changes required for existing `edit_file_atomic` calls
2. **Clean Old Backups**: Remove old `.edit_backup` directory if needed
3. **Update Tests**: Update test expectations for new error messages

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review test cases for usage patterns
3. Enable debug logging for detailed information