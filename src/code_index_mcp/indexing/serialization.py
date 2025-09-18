"""
High-performance index serialization with backward compatibility.

This module provides a clean interface for saving/loading index data,
automatically choosing the best format while maintaining compatibility.
"""

import json
import os
from typing import Dict, Any, Optional

try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False


class IndexSerializer:
    """
    Unified serialization interface that eliminates format-specific branching.

    Design philosophy:
    - No special cases: same interface for all formats
    - Automatic format selection: prefers msgpack when available
    - Backward compatibility: always reads existing JSON files correctly
    """

    def __init__(self, prefer_binary: bool = True):
        self.prefer_binary = prefer_binary and HAS_MSGPACK

    def save(self, data: Dict[str, Any], file_path: str) -> bool:
        """Save index data using optimal format."""
        try:
            if self.prefer_binary:
                return self._save_msgpack(data, file_path + '.msgpack')
            else:
                return self._save_json(data, file_path)
        except Exception:
            # Fallback to JSON if binary fails
            return self._save_json(data, file_path)

    def load(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load index data, trying optimal format first."""
        # Try msgpack first if preferred
        if self.prefer_binary:
            msgpack_path = file_path + '.msgpack'
            if os.path.exists(msgpack_path):
                result = self._load_msgpack(msgpack_path)
                if result is not None:
                    return result

        # Fallback to JSON
        if os.path.exists(file_path):
            return self._load_json(file_path)

        return None

    def _save_msgpack(self, data: Dict[str, Any], file_path: str) -> bool:
        """Save using msgpack binary format."""
        try:
            with open(file_path, 'wb') as f:
                msgpack.pack(data, f, use_bin_type=True)
            return True
        except Exception:
            return False

    def _save_json(self, data: Dict[str, Any], file_path: str) -> bool:
        """Save using JSON text format."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False)
            return True
        except Exception:
            return False

    def _load_msgpack(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load from msgpack binary format."""
        try:
            with open(file_path, 'rb') as f:
                return msgpack.unpack(f, raw=False, strict_map_key=False)
        except Exception:
            return None

    def _load_json(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Load from JSON text format."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None