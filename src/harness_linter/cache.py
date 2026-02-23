"""Incremental analysis cache system for harness_linter.

This module provides a file fingerprint-based cache system similar to mypy --incremental,
which allows for faster repeated checks on large projects by only re-analyzing changed files.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FileFingerprint:
    """File fingerprint for cache invalidation detection.

    Uses mtime, size, and content hash to detect file changes.
    """

    path: Path
    mtime: float
    size: int
    hash: str  # First 16 characters of SHA256 content hash

    @classmethod
    def from_path(cls, path: Path) -> "FileFingerprint":
        """Create a fingerprint from a file path.

        Args:
            path: Path to the file

        Returns:
            FileFingerprint: The fingerprint of the file
        """
        stat = path.stat()
        content = path.read_bytes()
        # Use first 16 chars of SHA256 hash for efficiency
        content_hash = hashlib.sha256(content).hexdigest()[:16]

        return cls(
            path=path,
            mtime=stat.st_mtime,
            size=stat.st_size,
            hash=content_hash,
        )

    def is_stale(self, current: "FileFingerprint") -> bool:
        """Check if this fingerprint is stale compared to current.

        Args:
            current: The current fingerprint to compare against

        Returns:
            bool: True if stale (different), False if fresh (same)
        """
        if self.size != current.size:
            return True
        if self.mtime != current.mtime:
            return True
        if self.hash != current.hash:
            return True
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "path": str(self.path),
            "mtime": self.mtime,
            "size": self.size,
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileFingerprint":
        """Create from dictionary."""
        return cls(
            path=Path(data["path"]),
            mtime=data["mtime"],
            size=data["size"],
            hash=data["hash"],
        )


class ImportGraphCache:
    """Import graph analysis result cache.

    Stores file fingerprints and import relationships to enable
    incremental analysis of Python projects.

    Cache format (JSON):
    {
        "version": "1",
        "fingerprints": {
            "module.name": {
                "path": "...",
                "mtime": 1234567890.0,
                "size": 100,
                "hash": "abc123..."
            }
        },
        "imports": {
            "module.name": ["imported.module1", "imported.module2"]
        },
        "imported_by": {
            "module.name": ["module.that.imports.this"]
        }
    }
    """

    CACHE_VERSION = "1"

    def __init__(self, cache_path: Path = Path(".harness_cache")):
        """Initialize the cache.

        Args:
            cache_path: Path to the cache file
        """
        self.cache_path = cache_path
        self._fingerprints: dict[str, FileFingerprint] = {}
        self._imports: dict[str, list[str]] = {}
        self._imported_by: dict[str, list[str]] = {}

    def load(self) -> bool:
        """Load cache from disk.

        Returns:
            bool: True if cache was loaded successfully, False otherwise
        """
        if not self.cache_path.exists():
            return False

        try:
            data = json.loads(self.cache_path.read_text(encoding="utf-8"))

            # Check version
            if data.get("version") != self.CACHE_VERSION:
                return False

            # Load fingerprints
            self._fingerprints = {
                module: FileFingerprint.from_dict(fp_data)
                for module, fp_data in data.get("fingerprints", {}).items()
            }

            # Load imports
            self._imports = data.get("imports", {})

            # Load imported_by
            self._imported_by = data.get("imported_by", {})

            return True
        except json.JSONDecodeError as e:
            logger.warning(f"Cache file is not valid JSON: {e}")
            self.clear()
            return False
        except KeyError as e:
            logger.warning(f"Cache file is missing required key: {e}")
            self.clear()
            return False
        except TypeError as e:
            logger.warning(f"Cache file has invalid type: {e}")
            self.clear()
            return False

    def save(self) -> None:
        """Save cache to disk."""
        data = {
            "version": self.CACHE_VERSION,
            "fingerprints": {
                module: fp.to_dict() for module, fp in self._fingerprints.items()
            },
            "imports": self._imports,
            "imported_by": self._imported_by,
        }

        # Ensure parent directory exists
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def is_fresh(self, module: str, source_path: Path) -> bool:
        """Check if module cache is fresh.

        Args:
            module: Module name
            source_path: Path to the source file

        Returns:
            bool: True if cache is fresh, False if stale or not cached
        """
        if module not in self._fingerprints:
            return False

        cached_fp = self._fingerprints[module]
        current_fp = FileFingerprint.from_path(source_path)

        return not cached_fp.is_stale(current_fp)

    def get_changed_modules(
        self, source_files: dict[str, Path]
    ) -> tuple[set[str], set[str]]:
        """Get changed modules and modules affected by changes.

        Args:
            source_files: Dictionary mapping module names to file paths

        Returns:
            Tuple of (directly_changed_modules, affected_modules)
            directly_changed_modules: Modules whose source files changed
            affected_modules: Modules that import changed modules (and need re-analysis)
        """
        changed: set[str] = set()

        # Find directly changed modules
        for module, path in source_files.items():
            if not self.is_fresh(module, path):
                changed.add(module)

        # Find new modules (in source_files but not in cache)
        cached_modules = set(self._fingerprints.keys())
        current_modules = set(source_files.keys())
        new_modules = current_modules - cached_modules
        changed.update(new_modules)

        # Find modules affected by changes (modules that import changed modules)
        affected: set[str] = set()
        for changed_module in changed:
            # Find all modules that import the changed module
            for importer in self._imported_by.get(changed_module, []):
                if importer not in changed:  # Don't include already changed modules
                    affected.add(importer)

        return changed, affected

    def update(self, module: str, source_path: Path, imports: list[str]) -> None:
        """Update cache for a module.

        Args:
            module: Module name
            source_path: Path to the source file
            imports: List of modules imported by this module
        """
        # Update fingerprint
        self._fingerprints[module] = FileFingerprint.from_path(source_path)

        # Remove old import relationships
        old_imports = self._imports.get(module, [])
        for imported in old_imports:
            if imported in self._imported_by:
                self._imported_by[imported] = [
                    m for m in self._imported_by[imported] if m != module
                ]

        # Update imports
        self._imports[module] = imports

        # Update imported_by relationships
        for imported in imports:
            if imported not in self._imported_by:
                self._imported_by[imported] = []
            if module not in self._imported_by[imported]:
                self._imported_by[imported].append(module)

    def clear(self) -> None:
        """Clear all cached data and remove cache file."""
        self._fingerprints.clear()
        self._imports.clear()
        self._imported_by.clear()

        if self.cache_path.exists():
            self.cache_path.unlink()
