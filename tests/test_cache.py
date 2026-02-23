"""Tests for the incremental analysis cache system."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from harness_linter.cache import FileFingerprint, ImportGraphCache


class TestFileFingerprint:
    """Tests for FileFingerprint class."""

    def test_file_fingerprint(self, tmp_path: Path) -> None:
        """Test file fingerprint creation."""
        # Create a test file
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        # Create fingerprint
        fingerprint = FileFingerprint.from_path(test_file)

        # Verify attributes
        assert fingerprint.path == test_file
        assert fingerprint.mtime == test_file.stat().st_mtime
        assert fingerprint.size == test_file.stat().st_size
        assert len(fingerprint.hash) == 16  # SHA256 first 16 chars
        assert all(c in "0123456789abcdef" for c in fingerprint.hash)

    def test_is_stale_same_file(self, tmp_path: Path) -> None:
        """Test that identical file is not stale."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        fp1 = FileFingerprint.from_path(test_file)
        fp2 = FileFingerprint.from_path(test_file)

        assert not fp1.is_stale(fp2)

    def test_is_stale_different_mtime(self, tmp_path: Path) -> None:
        """Test that file with different mtime is stale."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        fp1 = FileFingerprint.from_path(test_file)

        # Modify file
        import time

        time.sleep(0.01)
        test_file.write_text("print('world')")

        fp2 = FileFingerprint.from_path(test_file)

        assert fp1.is_stale(fp2)

    def test_is_stale_different_size(self, tmp_path: Path) -> None:
        """Test that file with different size is stale."""
        test_file = tmp_path / "test.py"
        test_file.write_text("print('hello')")

        fp1 = FileFingerprint.from_path(test_file)

        # Modify file with different content length
        test_file.write_text("print('hello world')")

        fp2 = FileFingerprint.from_path(test_file)

        assert fp1.is_stale(fp2)

    def test_is_stale_different_hash(self, tmp_path: Path) -> None:
        """Test that file with different hash is stale."""
        test_file = tmp_path / "test.py"
        test_file.write_text("x = 1")

        fp1 = FileFingerprint.from_path(test_file)

        # Modify file but keep same size
        test_file.write_text("x = 2")

        fp2 = FileFingerprint.from_path(test_file)

        # Size is same, but hash should be different
        assert fp1.size == fp2.size
        assert fp1.is_stale(fp2)


class TestImportGraphCache:
    """Tests for ImportGraphCache class."""

    def test_cache_save_and_load(self, tmp_path: Path) -> None:
        """Test cache save and load functionality."""
        cache_path = tmp_path / ".harness_cache"

        # Create and populate cache
        cache1 = ImportGraphCache(cache_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("import os")

        fingerprint = FileFingerprint.from_path(test_file)
        cache1._fingerprints["test.module"] = fingerprint
        cache1._imports["test.module"] = ["os"]
        cache1._imported_by["os"] = ["test.module"]

        cache1.save()

        # Verify file exists
        assert cache_path.exists()

        # Load cache
        cache2 = ImportGraphCache(cache_path)
        assert cache2.load()

        # Verify loaded data
        assert "test.module" in cache2._fingerprints
        loaded_fp = cache2._fingerprints["test.module"]
        assert loaded_fp.path == test_file
        assert loaded_fp.hash == fingerprint.hash

    def test_cache_load_missing_file(self, tmp_path: Path) -> None:
        """Test loading non-existent cache returns False."""
        cache_path = tmp_path / ".nonexistent_cache"
        cache = ImportGraphCache(cache_path)

        assert not cache.load()

    def test_is_fresh(self, tmp_path: Path) -> None:
        """Test cache freshness check."""
        cache_path = tmp_path / ".harness_cache"
        cache = ImportGraphCache(cache_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("import os")

        # Initially not fresh (not in cache)
        assert not cache.is_fresh("test.module", test_file)

        # Update cache
        cache.update("test.module", test_file, ["os"])

        # Now should be fresh
        assert cache.is_fresh("test.module", test_file)

        # Modify file
        import time

        time.sleep(0.01)
        test_file.write_text("import sys")

        # Should no longer be fresh
        assert not cache.is_fresh("test.module", test_file)

    def test_get_changed_modules(self, tmp_path: Path) -> None:
        """Test detecting changed modules."""
        cache_path = tmp_path / ".harness_cache"
        cache = ImportGraphCache(cache_path)

        # Create test files
        module_a = tmp_path / "a.py"
        module_b = tmp_path / "b.py"
        module_c = tmp_path / "c.py"

        module_a.write_text("import b")
        module_b.write_text("import c")
        module_c.write_text("pass")

        # Populate cache
        cache.update("a", module_a, ["b"])
        cache.update("b", module_b, ["c"])
        cache.update("c", module_c, [])

        # All fresh - no changes
        source_files = {"a": module_a, "b": module_b, "c": module_c}
        changed, affected = cache.get_changed_modules(source_files)
        assert len(changed) == 0
        assert len(affected) == 0

        # Modify module b
        import time

        time.sleep(0.01)
        module_b.write_text("import c\nimport os")

        # Now b is changed, a is affected (imports b)
        changed, affected = cache.get_changed_modules(source_files)
        assert "b" in changed
        assert "a" in affected
        assert "b" not in affected  # Changed modules are not in affected

    def test_get_changed_modules_new_file(self, tmp_path: Path) -> None:
        """Test detecting new files as changed."""
        cache_path = tmp_path / ".harness_cache"
        cache = ImportGraphCache(cache_path)

        # Create one file
        module_a = tmp_path / "a.py"
        module_a.write_text("pass")
        cache.update("a", module_a, [])

        # Add new file
        module_b = tmp_path / "b.py"
        module_b.write_text("pass")

        source_files = {"a": module_a, "b": module_b}
        changed, affected = cache.get_changed_modules(source_files)

        assert "b" in changed
        assert len(affected) == 0

    def test_clear(self, tmp_path: Path) -> None:
        """Test clearing cache."""
        cache_path = tmp_path / ".harness_cache"
        cache = ImportGraphCache(cache_path)

        test_file = tmp_path / "test.py"
        test_file.write_text("import os")

        cache.update("test.module", test_file, ["os"])
        cache.save()

        assert cache_path.exists()

        cache.clear()

        assert not cache_path.exists()
        assert len(cache._fingerprints) == 0
        assert len(cache._imports) == 0
        assert len(cache._imported_by) == 0

    def test_cache_version_mismatch(self, tmp_path: Path) -> None:
        """Test that cache with different version is rejected."""
        cache_path = tmp_path / ".harness_cache"

        # Create cache with wrong version
        data = {
            "version": "999",
            "fingerprints": {},
            "imports": {},
        }
        cache_path.write_text(json.dumps(data))

        cache = ImportGraphCache(cache_path)
        assert not cache.load()
