"""
Test Memory Backup Configuration System

Tests that configuration loading from environment variables works correctly
and that the memory backup system respects these configurations.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from code_index_mcp.config import get_memory_backup_config, reset_config
from code_index_mcp.core.edit_models import MemoryBackupManager


class TestMemoryBackupConfig:
    """Test memory backup configuration system"""
    
    def test_default_configuration(self):
        """Test that default configuration values are loaded correctly"""
        # Reset any existing config
        reset_config()
        
        # Clear environment variables
        env_vars_to_clear = [
            "CODE_INDEX_MAX_MEMORY_MB",
            "CODE_INDEX_MAX_FILE_SIZE_MB", 
            "CODE_INDEX_MAX_BACKUPS",
            "CODE_INDEX_BACKUP_TIMEOUT_SECONDS",
            "CODE_INDEX_MEMORY_WARNING_THRESHOLD"
        ]
        
        original_values = {}
        for var in env_vars_to_clear:
            original_values[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
        
        try:
            config = get_memory_backup_config()
            
            # Check default values
            assert config.max_memory_mb == 50, f"Expected 50, got {config.max_memory_mb}"
            assert config.max_file_size_mb == 10, f"Expected 10, got {config.max_file_size_mb}"
            assert config.max_backups == 1000, f"Expected 1000, got {config.max_backups}"
            assert config.backup_timeout_seconds == 300, f"Expected 300, got {config.backup_timeout_seconds}"
            assert config.memory_warning_threshold == 0.8, f"Expected 0.8, got {config.memory_warning_threshold}"
            
            print(f"✅ Default configuration loaded correctly")
            print(f"   {config}")
            
        finally:
            # Restore environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
            reset_config()
    
    def test_environment_variable_override(self):
        """Test that environment variables override defaults"""
        # Reset any existing config
        reset_config()
        
        # Set environment variables
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "100",
            "CODE_INDEX_MAX_FILE_SIZE_MB": "20",
            "CODE_INDEX_MAX_BACKUPS": "2000",
            "CODE_INDEX_BACKUP_TIMEOUT_SECONDS": "600",
            "CODE_INDEX_MEMORY_WARNING_THRESHOLD": "0.9"
        }
        
        original_values = {}
        for var, value in env_vars.items():
            original_values[var] = os.environ.get(var)
            os.environ[var] = value
        
        try:
            config = get_memory_backup_config()
            
            # Check that environment variables are used
            assert config.max_memory_mb == 100, f"Expected 100, got {config.max_memory_mb}"
            assert config.max_file_size_mb == 20, f"Expected 20, got {config.max_file_size_mb}"
            assert config.max_backups == 2000, f"Expected 2000, got {config.max_backups}"
            assert config.backup_timeout_seconds == 600, f"Expected 600, got {config.backup_timeout_seconds}"
            assert config.memory_warning_threshold == 0.9, f"Expected 0.9, got {config.memory_warning_threshold}"
            
            print(f"✅ Environment variable overrides work correctly")
            print(f"   {config}")
            
        finally:
            # Restore environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
            reset_config()
    
    def test_configuration_validation(self):
        """Test that invalid configuration values are rejected"""
        # Reset any existing config
        reset_config()
        
        test_cases = [
            ("CODE_INDEX_MAX_MEMORY_MB", "0", "max_memory_mb must be positive"),
            ("CODE_INDEX_MAX_FILE_SIZE_MB", "-5", "max_file_size_mb must be positive"),
            ("CODE_INDEX_MAX_BACKUPS", "0", "max_backups must be positive"),
            ("CODE_INDEX_BACKUP_TIMEOUT_SECONDS", "-1", "backup_timeout_seconds must be positive"),
            ("CODE_INDEX_MEMORY_WARNING_THRESHOLD", "1.5", "memory_warning_threshold must be between 0.0 and 1.0"),
            ("CODE_INDEX_MEMORY_WARNING_THRESHOLD", "0.0", "memory_warning_threshold must be between 0.0 and 1.0"),
        ]
        
        for env_var, value, expected_error in test_cases:
            # Set invalid environment variable
            original_value = os.environ.get(env_var)
            os.environ[env_var] = value
            
            try:
                reset_config()
                
                # This should raise ValueError
                with pytest.raises(ValueError, match=expected_error):
                    get_memory_backup_config()
                
                print(f"✅ Configuration validation works for {env_var}={value}")
                
            finally:
                # Restore environment variable
                if original_value is not None:
                    os.environ[env_var] = original_value
                elif env_var in os.environ:
                    del os.environ[env_var]
                reset_config()
    
    def test_file_size_vs_memory_limit_validation(self):
        """Test that file size limit cannot exceed memory limit"""
        # Reset any existing config
        reset_config()
        
        # Set invalid configuration (file size > memory limit)
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "50",
            "CODE_INDEX_MAX_FILE_SIZE_MB": "100"  # Invalid: larger than memory limit
        }
        
        original_values = {}
        for var, value in env_vars.items():
            original_values[var] = os.environ.get(var)
            os.environ[var] = value
        
        try:
            reset_config()
            
            # This should raise ValueError
            with pytest.raises(ValueError, match="max_file_size_mb.*cannot exceed.*max_memory_mb"):
                get_memory_backup_config()
            
            print(f"✅ File size vs memory limit validation works")
            
        finally:
            # Restore environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
            reset_config()
    
    def test_memory_backup_manager_uses_config(self):
        """Test that MemoryBackupManager uses configuration system"""
        # Reset any existing config
        reset_config()
        
        # Set custom environment variables
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "75",
            "CODE_INDEX_MAX_FILE_SIZE_MB": "15",
            "CODE_INDEX_MAX_BACKUPS": "1500",
            "CODE_INDEX_BACKUP_TIMEOUT_SECONDS": "450",
            "CODE_INDEX_MEMORY_WARNING_THRESHOLD": "0.85"
        }
        
        original_values = {}
        for var, value in env_vars.items():
            original_values[var] = os.environ.get(var)
            os.environ[var] = value
        
        try:
            reset_config()
            
            # Create MemoryBackupManager
            manager = MemoryBackupManager()
            
            # Check that manager uses configuration
            assert manager.max_memory_mb == 75, f"Expected 75, got {manager.max_memory_mb}"
            assert manager.max_file_size_mb == 15, f"Expected 15, got {manager.max_file_size_mb}"
            assert manager.max_backups == 1500, f"Expected 1500, got {manager.max_backups}"
            assert manager.backup_timeout_seconds == 450, f"Expected 450, got {manager.backup_timeout_seconds}"
            assert manager.memory_warning_threshold == 0.85, f"Expected 0.85, got {manager.memory_warning_threshold}"
            
            print(f"✅ MemoryBackupManager uses configuration correctly")
            print(f"   Manager config: max_memory={manager.max_memory_mb}MB, max_file={manager.max_file_size_mb}MB")
            
        finally:
            # Restore environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
            reset_config()
    
    def test_helper_methods(self):
        """Test configuration helper methods"""
        reset_config()
        
        # Set custom values
        env_vars = {
            "CODE_INDEX_MAX_MEMORY_MB": "100",
            "CODE_INDEX_MAX_FILE_SIZE_MB": "20",
            "CODE_INDEX_MEMORY_WARNING_THRESHOLD": "0.8"
        }
        
        original_values = {}
        for var, value in env_vars.items():
            original_values[var] = os.environ.get(var)
            os.environ[var] = value
        
        try:
            reset_config()
            config = get_memory_backup_config()
            
            # Test helper methods
            assert config.get_memory_bytes() == 100 * 1024 * 1024
            assert config.get_max_file_size_bytes() == 20 * 1024 * 1024
            assert config.get_warning_threshold_bytes() == int(100 * 1024 * 1024 * 0.8)
            
            print(f"✅ Configuration helper methods work correctly")
            print(f"   Memory bytes: {config.get_memory_bytes():,}")
            print(f"   File size bytes: {config.get_max_file_size_bytes():,}")
            print(f"   Warning threshold bytes: {config.get_warning_threshold_bytes():,}")
            
        finally:
            # Restore environment variables
            for var, value in original_values.items():
                if value is not None:
                    os.environ[var] = value
                elif var in os.environ:
                    del os.environ[var]
            reset_config()


def run_config_tests():
    """Run all configuration tests manually"""
    print("=== Memory Backup Configuration Tests ===")
    
    test_instance = TestMemoryBackupConfig()
    
    try:
        test_instance.test_default_configuration()
        test_instance.test_environment_variable_override()
        test_instance.test_configuration_validation()
        test_instance.test_file_size_vs_memory_limit_validation()
        test_instance.test_memory_backup_manager_uses_config()
        test_instance.test_helper_methods()
        
        print("\n=== All Configuration Tests Passed ===")
        print("✅ Memory backup configuration system works correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_config_tests()
    if not success:
        sys.exit(1)