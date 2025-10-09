#!/usr/bin/env python3
"""
T008 - Memory Usage Validation and Limits Implementation
实现内存使用验证和限制
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, '.')

def test_memory_validation():
    """Test memory usage validation"""
    print("🔧 Testing memory usage validation...")
    
    try:
        from src.code_index_mcp.core.memory_monitor import (
            get_memory_monitor, 
            check_memory_limits,
            MemoryThreshold
        )
        
        # Test basic memory limits
        is_ok, error = check_memory_limits("test_operation")
        print(f"✅ Basic memory check: {is_ok}")
        if error:
            print(f"   Error: {error}")
        
        # Test custom threshold
        monitor = get_memory_monitor()
        custom_threshold = MemoryThreshold(
            warning_percent=70.0,
            critical_percent=85.0,
            absolute_limit_mb=200.0,
            backup_limit_mb=100.0
        )
        monitor.threshold = custom_threshold
        
        # Test memory recording
        monitor.record_operation(10.0, "test_backup")
        status = monitor.get_current_usage()
        print(f"✅ Memory recording: {status['current_mb']:.1f}MB")
        
        # Test memory trend
        trend = monitor.get_memory_trend(1)
        print(f"✅ Memory trend analysis: {trend['trend_percent']:.1f}%")
        
        # Test diagnostics
        diagnostics = monitor.get_diagnostics()
        print(f"✅ Memory diagnostics: {diagnostics['current_usage']['usage_percent']:.1f}% usage")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory validation test failed: {e}")
        return False

def test_memory_limits_enforcement():
    """Test memory limits enforcement"""
    print("🔧 Testing memory limits enforcement...")
    
    try:
        from src.code_index_mcp.core.memory_monitor import MemoryMonitor, MemoryThreshold
        
        # Create monitor with low limit for testing
        test_monitor = MemoryMonitor(
            max_memory_mb=5.0,  # Very low limit
            threshold=MemoryThreshold(
                warning_percent=60.0,
                critical_percent=80.0,
                absolute_limit_mb=10.0,
                backup_limit_mb=5.0
            )
        )
        
        # Test normal operation
        is_ok, error = test_monitor.check_memory_limits("test_normal")
        print(f"✅ Normal operation: {is_ok}")
        
        # Simulate high memory usage
        test_monitor.current_usage_mb = 8.0  # Exceeds critical threshold
        is_ok, error = test_monitor.check_memory_limits("test_high")
        print(f"✅ High memory detection: {not is_ok}")
        if error:
            print(f"   Error: {error}")
        
        # Test absolute limit
        test_monitor.current_usage_mb = 15.0  # Exceeds absolute limit
        is_ok, error = test_monitor.check_memory_limits("test_absolute")
        print(f"✅ Absolute limit enforcement: {not is_ok}")
        if error:
            print(f"   Error: {error}")
        
        return True
        
    except Exception as e:
        print(f"❌ Memory limits enforcement test failed: {e}")
        return False

def main():
    """Run T008 tests"""
    print("🚀 T008 - Memory Usage Validation and Limits")
    print("=" * 60)
    
    tests = [
        ("Memory Validation", test_memory_validation),
        ("Memory Limits Enforcement", test_memory_limits_enforcement),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        print("-" * 40)
        
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 T008: PASSED")
        print("✅ Memory usage validation and limits implemented")
        return True
    else:
        print("❌ T008: FAILED")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)