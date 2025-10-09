# Data Model: Apply Edit Backup Directory Fix

**Date**: 2025-10-09  
**Feature**: Apply Edit Backup Directory Fix

## Core Entities

### BackupFile
```python
@dataclass
class BackupFile:
    """Represents a backup file with metadata"""
    path: Path                    # Full path to backup file
    original_path: Path          # Original file path
    timestamp: int               # Microsecond timestamp
    size: int                    # File size in bytes
    checksum: str                # MD5 hash for integrity
    operation_id: Optional[str]  # Associated edit operation ID
    is_corrupted: bool = False   # Corruption flag
```

### BackupDirectory
```python
@dataclass
class BackupDirectory:
    """Represents a backup directory with management capabilities"""
    path: Path                    # Directory path
    max_size_bytes: int = 1024*1024*1024  # 1GB limit
    max_file_count: int = 100     # Maximum backup files
    created_at: datetime = field(default_factory=datetime.now)
    
    def cleanup_old_backups(self) -> int:
        """Remove old backups, return count removed"""
        
    def get_total_size(self) -> int:
        """Calculate total size of all backups"""
        
    def validate_integrity(self) -> List[BackupFile]:
        """Check backup file integrity"""
```

### EditOperation
```python
@dataclass
class EditOperation:
    """Represents a file edit operation with backup context"""
    file_path: Path              # Target file path
    old_content: str             # Original content
    new_content: str             # New content
    backup_path: Optional[Path]  # Backup file path
    operation_id: str            # Unique operation identifier
    timestamp: int               # Operation timestamp
    status: EditStatus           # Operation status
    
    def create_backup(self) -> bool:
        """Create backup before edit"""
        
    def rollback(self) -> bool:
        """Rollback using backup"""
```

## Enums

### EditStatus
```python
class EditStatus(Enum):
    PENDING = "pending"
    BACKUP_CREATED = "backup_created"
    EDIT_APPLIED = "edit_applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
```

### BackupLocation
```python
class BackupLocation(Enum):
    PROJECT_DIR = "project_dir"      # .edit_backup in project
    SYSTEM_TEMP = "system_temp"      # System temp directory
    CUSTOM = "custom"                # User-specified location
```

## Relationships

```
EditOperation (1) -> (1) BackupFile
BackupDirectory (1) -> (*) BackupFile
BackupFile (*) -> (1) BackupDirectory
```

## Validation Rules

### BackupFile Validation
- Path must exist and be readable
- Size must match original file
- Checksum must validate content integrity
- Timestamp must be unique within directory

### BackupDirectory Validation
- Path must be writable
- Must not exceed max_size_bytes
- Must not exceed max_file_count
- Must have proper permissions

### EditOperation Validation
- File path must exist
- Old content must match current file content
- New content must be valid UTF-8
- Operation ID must be unique

## State Transitions

### EditOperation Lifecycle
```
PENDING -> BACKUP_CREATED -> EDIT_APPLIED
    |            |               |
    v            v               v
FAILED <------ FAILED <------ FAILED
    |
    v
ROLLED_BACK
```

### BackupFile Lifecycle
```
CREATED -> VALID -> CORRUPTED -> QUARANTINED
    |          |          |
    v          v          v
CLEANED   ARCHIVED   DELETED
```

## Data Access Patterns

### Direct File Operations (Constitution Compliant)
```python
# Direct dictionary access for performance
backup_registry: Dict[str, BackupFile] = {}
directory_cache: Dict[Path, BackupDirectory] = {}

# Zero-copy operations
def create_backup_atomic(source: Path, backup_dir: Path) -> BackupFile:
    """Atomic backup creation with direct file operations"""
```

### Cache Management
```python
class BackupCache:
    """LRU cache for backup metadata"""
    def __init__(self, max_size: int = 1000):
        self.cache: OrderedDict[str, BackupFile] = OrderedDict()
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[BackupFile]:
        """Get backup file with LRU update"""
        
    def put(self, key: str, backup: BackupFile):
        """Store backup with size management"""
```

## Performance Considerations

### Memory Usage
- BackupFile objects: ~200 bytes each
- Directory metadata: ~1KB per directory
- Cache overhead: <10MB for 10,000 backups

### Disk I/O Patterns
- Sequential writes for backup creation
- Random reads for integrity checks
- Batch operations for cleanup

### Concurrency Support
- Thread-safe cache operations
- Atomic file operations
- Lock-free naming strategy