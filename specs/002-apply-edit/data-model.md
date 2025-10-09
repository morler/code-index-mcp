# Data Model: Apply Edit Backup Removal

## Core Entities

### EditOperation

Represents a file editing operation with in-memory backup capability.

```python
@dataclass
class EditOperation:
    file_path: str
    original_content: Optional[str] = None
    new_content: Optional[str] = None
    status: EditStatus = EditStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    memory_size: int = 0
    
    def __post_init__(self):
        if self.original_content:
            self.memory_size = len(self.original_content.encode('utf-8'))
```

### FileState

Tracks file state during editing operations for rollback capability.

```python
@dataclass
class FileState:
    path: str
    checksum: str
    size: int
    modified_time: datetime
    is_locked: bool = False
    lock_owner: Optional[str] = None
```

### MemoryBackupManager

Manages in-memory backups with LRU eviction policy.

```python
@dataclass
class MemoryBackupManager:
    max_memory_mb: int = 50
    current_memory_mb: float = 0.0
    backup_cache: Dict[str, EditOperation] = field(default_factory=dict)
    access_order: List[str] = field(default_factory=list)
    
    def add_backup(self, operation: EditOperation) -> bool:
        """Add backup to memory cache with LRU eviction"""
        
    def get_backup(self, file_path: str) -> Optional[EditOperation]:
        """Retrieve backup from cache"""
        
    def remove_backup(self, file_path: str) -> None:
        """Remove backup from cache"""
        
    def evict_if_needed(self, required_memory: int) -> None:
        """Evict old backups to make room"""
```

## Enums

### EditStatus

```python
class EditStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
```

## Validation Rules

### File Size Validation

- Files larger than 10MB cannot be edited (memory protection)
- Total backup cache cannot exceed configured memory limit
- Individual file content must be valid UTF-8

### Lock Validation

- Only one edit operation per file at a time
- Lock timeout after 30 seconds (prevents deadlocks)
- Automatic lock cleanup on process termination

### Content Validation

- New content must be string type
- File path must be absolute and exist
- Original content checksum must match current file state

## State Transitions

```
PENDING → IN_PROGRESS → COMPLETED
    ↓         ↓           ↓
  FAILED   FAILED    (cleanup)
    ↓         ↓
ROLLED_BACK ROLLED_BACK
```

## Memory Management

### LRU Eviction Policy

1. When memory limit exceeded, evict least recently used backups
2. Completed operations are evicted before failed ones
3. Operations older than 1 hour are automatically evicted
4. Emergency eviction when memory critically low (>90% usage)

### Memory Monitoring

```python
def get_memory_usage() -> Dict[str, float]:
    return {
        "current_mb": current_memory_mb,
        "max_mb": max_memory_mb,
        "usage_percent": (current_memory_mb / max_memory_mb) * 100,
        "backup_count": len(backup_cache)
    }
```

## Error Handling

### Exception Types

```python
class EditOperationError(Exception):
    """Base class for edit operation errors"""

class MemoryLimitExceededError(EditOperationError):
    """Raised when file too large for memory backup"""

class FileLockError(EditOperationError):
    """Raised when file cannot be locked"""

class FileCorruptionError(EditOperationError):
    """Raised when file checksum mismatch detected"""
```

### Recovery Strategies

- **Memory Limit**: Reject operation with clear error message
- **Lock Timeout**: Force unlock and retry operation
- **Checksum Mismatch**: Abort operation and alert user
- **Process Crash**: Automatic cleanup on restart