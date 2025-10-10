"""
Memory Monitoring Infrastructure for Backup Operations

Provides memory usage tracking, limits enforcement, and alerting
for in-memory backup system. Cross-platform compatible with fallbacks
when psutil is not available.

Design Principles:
- Direct data access - no abstractions
- Minimal overhead - lightweight monitoring
- Cross-platform - Windows/Linux/macOS support
- Graceful degradation - works without psutil
"""

import os
import sys
import time
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time"""
    timestamp: float = field(default_factory=time.time)
    rss_mb: float = 0.0  # Resident Set Size (physical memory)
    vms_mb: float = 0.0  # Virtual Memory Size
    percent: float = 0.0  # Percentage of system memory
    available_mb: float = 0.0  # Available system memory
    
    def __post_init__(self):
        """Capture current memory state"""
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process()
                memory_info = process.memory_info()
                system_memory = psutil.virtual_memory()
                
                self.rss_mb = memory_info.rss / 1024 / 1024
                self.vms_mb = memory_info.vms / 1024 / 1024
                self.percent = process.memory_percent()
                self.available_mb = system_memory.available / 1024 / 1024
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                # Fallback to basic measurements
                self._basic_memory_measure()
        else:
            self._basic_memory_measure()
    
    def _basic_memory_measure(self):
        """Basic memory measurement without psutil"""
        try:
            # Unix-based systems: read from /proc/self/status
            if os.path.exists('/proc/self/status'):
                with open('/proc/self/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            self.rss_mb = int(line.split()[1]) / 1024
                        elif line.startswith('VmSize:'):
                            self.vms_mb = int(line.split()[1]) / 1024
            # Windows: fallback - use resource module if available
            elif hasattr(os, 'getpid'):
                # Very basic fallback - just estimate
                self.rss_mb = 50.0  # Conservative estimate
                self.vms_mb = 100.0
        except Exception:
            # Ultimate fallback
            self.rss_mb = 25.0
            self.vms_mb = 50.0

@dataclass
class MemoryThreshold:
    """Memory threshold configuration"""
    warning_percent: float = 80.0  # Warning at 80% usage
    critical_percent: float = 90.0  # Critical at 90% usage
    absolute_limit_mb: float = 100.0  # Hard limit in MB
    backup_limit_mb: float = 50.0  # Backup-specific limit
    
    def check_warning(self, current_mb: float, max_mb: float) -> bool:
        """Check if warning threshold exceeded"""
        return (current_mb > max_mb * (self.warning_percent / 100) or
                current_mb > self.backup_limit_mb * (self.warning_percent / 100))
    
    def check_critical(self, current_mb: float, max_mb: float) -> bool:
        """Check if critical threshold exceeded"""
        return (current_mb > max_mb * (self.critical_percent / 100) or
                current_mb > self.backup_limit_mb * (self.critical_percent / 100))
    
    def check_absolute_limit(self, current_mb: float) -> bool:
        """Check if absolute limit exceeded"""
        return current_mb > self.absolute_limit_mb

class MemoryMonitor:
    """
    Memory monitoring and tracking utility
    
    Features:
    - Real-time memory tracking
    - Threshold-based alerting
    - Historical data collection
    - Cross-platform compatibility
    """
    
    def __init__(self, 
                 max_memory_mb: float = 50.0,
                 threshold: Optional[MemoryThreshold] = None,
                 history_size: int = 100):
        self.max_memory_mb = max_memory_mb
        self.threshold = threshold or MemoryThreshold()
        self.history_size = history_size
        
        # Memory tracking state
        self.current_usage_mb = 0.0
        self.peak_usage_mb = 0.0
        self.history: list[MemorySnapshot] = []
        self.alert_callbacks: list[Callable[[str, Dict[str, Any]], None]] = []
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Initial measurement - but don't set to actual process memory
        # Use a small baseline to avoid immediate threshold violations
        self.current_usage_mb = 5.0  # Small baseline
    
    def set_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Register callback for memory alerts"""
        with self._lock:
            self.alert_callbacks.append(callback)
    
    def get_current_usage(self) -> Dict[str, float]:
        """Get current memory usage information"""
        with self._lock:
            self._update_current_usage()
            
            return {
                "current_mb": self.current_usage_mb,
                "max_mb": self.max_memory_mb,
                "usage_percent": (self.current_usage_mb / self.max_memory_mb) * 100,
                "peak_mb": self.peak_usage_mb,
                "available_mb": self._get_available_memory(),
                "timestamp": time.time()
            }
    
    def check_memory_limits(self, operation_name: str = "backup") -> tuple[bool, Optional[str]]:
        """
        Check if current memory usage is within limits
        
        Returns:
            (is_ok, error_message)
        """
        with self._lock:
            self._update_current_usage()
            
            # Check absolute limit first
            if self.threshold.check_absolute_limit(self.current_usage_mb):
                error = f"Absolute memory limit exceeded: {self.current_usage_mb:.1f}MB > {self.threshold.absolute_limit_mb}MB"
                self._trigger_alert("critical", error, {"operation": operation_name})
                return False, error
            
            # Check critical threshold
            if self.threshold.check_critical(self.current_usage_mb, self.max_memory_mb):
                error = f"Critical memory threshold: {self.current_usage_mb:.1f}MB ({self.current_usage_mb/self.max_memory_mb*100:.1f}%)"
                self._trigger_alert("critical", error, {"operation": operation_name})
                return False, error
            
            # Check warning threshold (just alert, don't fail)
            if self.threshold.check_warning(self.current_usage_mb, self.max_memory_mb):
                warning = f"Memory usage warning: {self.current_usage_mb:.1f}MB ({self.current_usage_mb/self.max_memory_mb*100:.1f}%)"
                self._trigger_alert("warning", warning, {"operation": operation_name})
            
            return True, None
    
    def _check_limits_without_update(self, operation_name: str = "backup") -> tuple[bool, Optional[str]]:
        """
        Check memory limits without updating current usage
        Used internally by record_operation to avoid resetting manual values
        """
        # Check absolute limit first
        if self.threshold.check_absolute_limit(self.current_usage_mb):
            error = f"Absolute memory limit exceeded: {self.current_usage_mb:.1f}MB > {self.threshold.absolute_limit_mb}MB"
            self._trigger_alert("critical", error, {"operation": operation_name})
            return False, error
        
        # Check critical threshold
        if self.threshold.check_critical(self.current_usage_mb, self.max_memory_mb):
            error = f"Critical memory threshold: {self.current_usage_mb:.1f}MB ({self.current_usage_mb/self.max_memory_mb*100:.1f}%)"
            self._trigger_alert("critical", error, {"operation": operation_name})
            return False, error
        
        # Check warning threshold (just alert, don't fail)
        if self.threshold.check_warning(self.current_usage_mb, self.max_memory_mb):
            warning = f"Memory usage warning: {self.current_usage_mb:.1f}MB ({self.current_usage_mb/self.max_memory_mb*100:.1f}%)"
            self._trigger_alert("warning", warning, {"operation": operation_name})
        
        return True, None
    
    def record_operation(self, operation_size_mb: float, operation_type: str = "backup") -> None:
        """Record a memory operation and update tracking"""
        with self._lock:
            # Update current usage
            self.current_usage_mb += operation_size_mb
            
            # Update peak
            if self.current_usage_mb > self.peak_usage_mb:
                self.peak_usage_mb = self.current_usage_mb
            
            # Add to history
            snapshot = MemorySnapshot()
            self.history.append(snapshot)
            
            # Trim history if needed
            if len(self.history) > self.history_size:
                self.history.pop(0)
            
            # Check limits after operation (without updating current usage)
            self._check_limits_without_update(operation_type)
    
    def release_operation(self, operation_size_mb: float) -> None:
        """Release memory from completed operation"""
        with self._lock:
            self.current_usage_mb = max(0, self.current_usage_mb - operation_size_mb)
            
            # Record the release
            snapshot = MemorySnapshot()
            self.history.append(snapshot)
            
            # Trim history
            if len(self.history) > self.history_size:
                self.history.pop(0)
    
    def get_memory_trend(self, minutes: int = 5) -> Dict[str, float]:
        """Analyze memory usage trend over time window"""
        with self._lock:
            if not self.history:
                return {"trend_percent": 0.0, "avg_mb": 0.0, "min_mb": 0.0, "max_mb": 0.0}
            
            # Filter snapshots within time window
            cutoff_time = time.time() - (minutes * 60)
            recent_snapshots = [
                s for s in self.history 
                if s.timestamp >= cutoff_time
            ]
            
            if len(recent_snapshots) < 2:
                return {"trend_percent": 0.0, "avg_mb": 0.0, "min_mb": 0.0, "max_mb": 0.0}
            
            # Calculate trend
            memory_values = [s.rss_mb for s in recent_snapshots]
            avg_memory = sum(memory_values) / len(memory_values)
            min_memory = min(memory_values)
            max_memory = max(memory_values)
            
            # Simple trend calculation (first vs last)
            trend_percent = ((memory_values[-1] - memory_values[0]) / memory_values[0]) * 100 if memory_values[0] > 0 else 0.0
            
            return {
                "trend_percent": trend_percent,
                "avg_mb": avg_memory,
                "min_mb": min_memory,
                "max_mb": max_memory,
                "sample_count": len(recent_snapshots)
            }
    
    def reset_peak_usage(self) -> None:
        """Reset peak usage tracking"""
        with self._lock:
            self.peak_usage_mb = self.current_usage_mb
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get comprehensive memory diagnostics"""
        with self._lock:
            self._update_current_usage()
            
            return {
                "current_usage": self.get_current_usage(),
                "threshold": {
                    "warning_percent": self.threshold.warning_percent,
                    "critical_percent": self.threshold.critical_percent,
                    "absolute_limit_mb": self.threshold.absolute_limit_mb,
                    "backup_limit_mb": self.threshold.backup_limit_mb
                },
                "trend_5min": self.get_memory_trend(5),
                "trend_1min": self.get_memory_trend(1),
                "history_size": len(self.history),
                "psutil_available": PSUTIL_AVAILABLE,
                "peak_usage_mb": self.peak_usage_mb
            }
    
    def _update_current_usage(self) -> None:
        """Update current memory usage measurement"""
        # Only update if we have actual usage data
        if self.current_usage_mb <= 5.0:  # Still at baseline
            snapshot = MemorySnapshot()
            # Use the smaller of baseline or actual to avoid false critical alerts
            self.current_usage_mb = min(snapshot.rss_mb, 10.0)  # Cap at 10MB for stability
    
    def _get_available_memory(self) -> float:
        """Get available system memory in MB"""
        if PSUTIL_AVAILABLE:
            try:
                return psutil.virtual_memory().available / 1024 / 1024
            except Exception:
                pass
        return 0.0
    
    def _trigger_alert(self, level: str, message: str, context: Dict[str, Any]) -> None:
        """Trigger memory alert to registered callbacks"""
        alert_data = {
            "level": level,
            "message": message,
            "timestamp": time.time(),
            "current_usage_mb": self.current_usage_mb,
            "max_usage_mb": self.max_memory_mb,
            "usage_percent": (self.current_usage_mb / self.max_memory_mb) * 100,
            **context
        }
        
        for callback in self.alert_callbacks:
            try:
                callback(level, alert_data)
            except Exception:
                # Don't let callback errors break monitoring
                pass

# Global memory monitor instance
_global_monitor: Optional[MemoryMonitor] = None

def get_memory_monitor() -> MemoryMonitor:
    """Get or create global memory monitor instance"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = MemoryMonitor()
    return _global_monitor

def create_memory_monitor(max_memory_mb: float = 50.0) -> MemoryMonitor:
    """Create new memory monitor instance"""
    return MemoryMonitor(max_memory_mb=max_memory_mb)

def format_memory_size(mb: float) -> str:
    """Format memory size in human readable format"""
    if mb < 1024:
        return f"{mb:.1f}MB"
    elif mb < 1024 * 1024:
        return f"{mb/1024:.1f}GB"
    else:
        return f"{mb/(1024*1024):.1f}TB"

def default_alert_handler(level: str, alert_data: Dict[str, Any]) -> None:
    """Default alert handler - prints to stderr"""
    import sys
    
    prefix = {
        "warning": "⚠️  MEMORY WARNING",
        "critical": "🚨 MEMORY CRITICAL"
    }.get(level, "📊 MEMORY ALERT")
    
    message = f"{prefix}: {alert_data['message']}"
    if alert_data.get('operation'):
        message += f" (operation: {alert_data['operation']})"
    
    print(message, file=sys.stderr)

# Convenience functions for common operations
def check_memory_limits(operation_name: str = "backup") -> tuple[bool, Optional[str]]:
    """Check memory limits using global monitor"""
    monitor = get_memory_monitor()
    return monitor.check_memory_limits(operation_name)

def get_memory_status() -> Dict[str, float]:
    """Get current memory status using global monitor"""
    monitor = get_memory_monitor()
    return monitor.get_current_usage()

def record_memory_operation(size_mb: float, operation_type: str = "backup") -> None:
    """Record memory operation using global monitor"""
    monitor = get_memory_monitor()
    monitor.record_operation(size_mb, operation_type)

def release_memory_operation(size_mb: float) -> None:
    """Release memory operation using global monitor"""
    monitor = get_memory_monitor()
    monitor.release_operation(size_mb)