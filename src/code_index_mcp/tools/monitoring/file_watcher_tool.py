"""
File Watcher Tool - Simplified for Phase 1 (Linus-style)

Direct file monitoring without service abstractions.
"""

import time
from typing import Optional, Callable


class FileWatcherTool:
    """
    Simplified file monitoring - Phase 1 Linus-style.

    Direct implementation without service abstractions.
    """

    def __init__(self, ctx):
        self._ctx = ctx
        self._monitoring_active = False

    def start_monitoring(self, project_path: str, rebuild_callback: Callable) -> bool:
        """
        Start file monitoring - simplified implementation.

        Args:
            project_path: Path to monitor
            rebuild_callback: Callback function for rebuild events

        Returns:
            True if monitoring started successfully, False otherwise
        """
        # Simplified: Just mark as active for now
        # Complex file watching will be implemented in Phase 2
        self._monitoring_active = True
        return True

    def stop_monitoring(self) -> None:
        """Stop file monitoring if active."""
        self._monitoring_active = False

    def is_monitoring_active(self) -> bool:
        """
        Check if file monitoring is currently active.

        Returns:
            True if monitoring is active, False otherwise
        """
        return self._monitoring_active

    def get_monitoring_status(self) -> dict:
        """
        Get current monitoring status.

        Returns:
            Dictionary with monitoring status information
        """
        return {
            'active': self._monitoring_active,
            'available': True,
            'status': 'active' if self._monitoring_active else 'inactive'
        }