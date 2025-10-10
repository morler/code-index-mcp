"""
Configuration Management for Code Index MCP

Following Linus's principle: "Good configuration is no configuration."
Provides sensible defaults with optional environment variable overrides.
"""

import os
from typing import Optional


class MemoryBackupConfig:
    """Memory backup system configuration"""

    # Default values - chosen based on testing and performance analysis
    DEFAULT_MAX_MEMORY_MB = 50  # Total memory limit for backups
    DEFAULT_MAX_FILE_SIZE_MB = 10  # Maximum single file size
    DEFAULT_MAX_BACKUPS = 1000  # Maximum number of backup entries
    DEFAULT_BACKUP_TIMEOUT_SECONDS = 300  # 5 minutes
    DEFAULT_MEMORY_WARNING_THRESHOLD = 0.8  # 80% of limit

    def __init__(self):
        # Load from environment variables with fallback to defaults
        self.max_memory_mb = self._get_int_env(
            "CODE_INDEX_MAX_MEMORY_MB", self.DEFAULT_MAX_MEMORY_MB
        )
        self.max_file_size_mb = self._get_int_env(
            "CODE_INDEX_MAX_FILE_SIZE_MB", self.DEFAULT_MAX_FILE_SIZE_MB
        )
        self.max_backups = self._get_int_env("CODE_INDEX_MAX_BACKUPS", self.DEFAULT_MAX_BACKUPS)
        self.backup_timeout_seconds = self._get_int_env(
            "CODE_INDEX_BACKUP_TIMEOUT_SECONDS", self.DEFAULT_BACKUP_TIMEOUT_SECONDS
        )
        self.memory_warning_threshold = self._get_float_env(
            "CODE_INDEX_MEMORY_WARNING_THRESHOLD", self.DEFAULT_MEMORY_WARNING_THRESHOLD
        )

        # Validate configuration
        self._validate_config()

    def _get_int_env(self, key: str, default: int) -> int:
        """Get integer from environment variable with fallback"""
        try:
            value = os.environ.get(key)
            if value is not None:
                return int(value)
        except (ValueError, TypeError):
            pass
        return default

    def _get_float_env(self, key: str, default: float) -> float:
        """Get float from environment variable with fallback"""
        try:
            value = os.environ.get(key)
            if value is not None:
                return float(value)
        except (ValueError, TypeError):
            pass
        return default

    def _validate_config(self):
        """Validate configuration values"""
        if self.max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        if self.max_file_size_mb <= 0:
            raise ValueError("max_file_size_mb must be positive")
        if self.max_backups <= 0:
            raise ValueError("max_backups must be positive")
        if self.backup_timeout_seconds <= 0:
            raise ValueError("backup_timeout_seconds must be positive")
        if not 0.0 < self.memory_warning_threshold <= 1.0:
            raise ValueError("memory_warning_threshold must be between 0.0 and 1.0")

        # Ensure file size limit is reasonable relative to total memory
        if self.max_file_size_mb > self.max_memory_mb:
            raise ValueError(
                f"max_file_size_mb ({self.max_file_size_mb}) cannot exceed "
                f"max_memory_mb ({self.max_memory_mb})"
            )

    def get_memory_bytes(self) -> int:
        """Get max memory in bytes"""
        return self.max_memory_mb * 1024 * 1024

    def get_max_file_size_bytes(self) -> int:
        """Get max file size in bytes"""
        return self.max_file_size_mb * 1024 * 1024

    def get_warning_threshold_bytes(self) -> int:
        """Get memory warning threshold in bytes"""
        return int(self.get_memory_bytes() * self.memory_warning_threshold)

    def __repr__(self) -> str:
        return (
            f"MemoryBackupConfig("
            f"max_memory_mb={self.max_memory_mb}, "
            f"max_file_size_mb={self.max_file_size_mb}, "
            f"max_backups={self.max_backups}, "
            f"backup_timeout_seconds={self.backup_timeout_seconds}, "
            f"memory_warning_threshold={self.memory_warning_threshold})"
        )


# Global configuration instance
_config: Optional[MemoryBackupConfig] = None


def get_memory_backup_config() -> MemoryBackupConfig:
    """Get global memory backup configuration instance"""
    global _config
    if _config is None:
        _config = MemoryBackupConfig()
    return _config


def reset_config():
    """Reset configuration (mainly for testing)"""
    global _config
    _config = None


# Environment documentation
CONFIG_DOCS = """
Memory Backup Configuration Environment Variables:

- CODE_INDEX_MAX_MEMORY_MB: Maximum memory for backups (default: 50)
- CODE_INDEX_MAX_FILE_SIZE_MB: Maximum single file size (default: 10)  
- CODE_INDEX_MAX_BACKUPS: Maximum number of backup entries (default: 1000)
- CODE_INDEX_BACKUP_TIMEOUT_SECONDS: Backup timeout in seconds (default: 300)
- CODE_INDEX_MEMORY_WARNING_THRESHOLD: Memory warning threshold 0.0-1.0 (default: 0.8)

Example usage:
    export CODE_INDEX_MAX_MEMORY_MB=100
    export CODE_INDEX_MAX_FILE_SIZE_MB=20
    export CODE_INDEX_MEMORY_WARNING_THRESHOLD=0.9
"""
