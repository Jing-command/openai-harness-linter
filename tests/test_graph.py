"""Tests for the graph building module."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harness_linter.cache import ImportGraphCache
from harness_linter.graph import (
    ImportGraphBuilder,
    IncrementalImportGraphBuilder,
    _sys_path_context,
)


class TestSysPathContext:
    """Tests for _sys_path_context context manager."""

    def test_adds_path_to_sys_path(self) -> None:
        """Test that path is added to sys.path."""
        test_path = "/test/path"
        original_len = len(sys.path)

        with _sys_path_context(test_path):
            assert test_path in sys.path
            assert len(sys.path) == original_len + 1

        # Path should be removed after context exits
        assert test_path not in sys.path
        assert len(sys.path) == original_len

    def test_does_not_duplicate_existing_path(self) -> None:
        """Test that existing path is not duplicated."""
        test_path = sys.path[0] if sys.path else "/existing/path"
        if test_path not in sys.path:
            sys.path.insert(0, test_path)

        original_len = len(sys.path)

        with _sys_path_context(test_path):
            # Should not add duplicate
            assert sys.path.count(test_path) == 1
            assert len(sys.path) == original_len

        # Path should still be there (wasn't removed because we didn't add it)
        assert test_path in sys.path

    def test_removes_path_on_exception(self) -> None:
        """Test that path is removed even if exception occurs."""
        test_path = "/test/path/exception"

        with pytest.raises(ValueError):
            with _sys_path_context(test_path):
                assert test_path in sys.path
                raise ValueError("Test exception")

        # Path should be removed after exception
        assert test_path not in sys.path


class TestImportGraphBuilder:
    """Tests for ImportGraphBuilder class."""

    def test_graph_builder_init(self) -> None:
        """Test ImportGraphBuilder initialization."""
        builder = ImportGraphBuilder("myproject")
        assert builder.root_package == "myproject"

    def test_build_graph(self, tmp_path: Path) -> None:
        """Test building import graph from source files."""
        # Create a mock package structure
        pkg_dir = tmp_path / "src" / "myproject"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("")

        module_a = pkg_dir / "module_a.py"
        module_a.write_text("import os\nimport sys\n")

        module_b = pkg_dir / "module_b.py"
        module_b.write_text("from . import module_a\n")

        builder = ImportGraphBuilder("myproject")

        # Mock grimp.build_graph to avoid actual import analysis
        mock_graph = MagicMock()
        with patch("harness_linter.graph.grimp.build_graph", return_value=mock_graph) as mock_build:
            graph = builder.build_from_path(pkg_dir)

            # Verify build_graph was called with correct arguments
            mock_build.assert_called_once_with(package_name="myproject")
            assert graph == mock_graph

    def test_find_source_files(self, tmp_path: Path) -> None:
        """Test finding all Python source files in a package."""
        # Create package structure
        pkg_dir = tmp_path / "src" / "myproject"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("")

        subpkg = pkg_dir / "subpackage"
        subpkg.mkdir()
        (subpkg / "__init__.py").write_text("")
        (subpkg / "module.py").write_text("pass")

        builder = ImportGraphBuilder("myproject")
        source_files = builder.find_source_files(pkg_dir)

        # Should find all modules
        assert "myproject" in source_files  # __init__.py
        assert "myproject.subpackage" in source_files  # subpackage/__init__.py
        assert "myproject.subpackage.module" in source_files  # subpackage/module.py

        # Verify paths are correct
        assert source_files["myproject"] == pkg_dir / "__init__.py"
        assert source_files["myproject.subpackage"] == subpkg / "__init__.py"
        assert source_files["myproject.subpackage.module"] == subpkg / "module.py"

    def test_get_imports_from_file(self, tmp_path: Path) -> None:
        """Test extracting imports from a Python file."""
        test_file = tmp_path / "test_module.py"
        test_file.write_text("""
import os
import sys
from pathlib import Path
from collections import OrderedDict

class MyClass:
    pass
""")

        builder = ImportGraphBuilder("myproject")
        imports = builder.get_imports_from_file(test_file)

        # Should extract all import statements
        assert "os" in imports
        assert "sys" in imports
        assert "pathlib" in imports
        assert "collections" in imports

    def test_get_imports_from_file_with_syntax_error(self, tmp_path: Path) -> None:
        """Test handling of file with syntax error."""
        test_file = tmp_path / "bad_syntax.py"
        test_file.write_text("def broken(:")

        builder = ImportGraphBuilder("myproject")

        with patch("harness_linter.graph.logger") as mock_logger:
            imports = builder.get_imports_from_file(test_file)
            assert imports == []
            mock_logger.warning.assert_called_once()
            assert "Failed to parse" in mock_logger.warning.call_args[0][0]

    def test_get_imports_from_file_with_encoding_error(self, tmp_path: Path) -> None:
        """Test handling of file with encoding error."""
        test_file = tmp_path / "bad_encoding.py"
        # Write invalid UTF-8 bytes
        test_file.write_bytes(b"\xff\xfe\x00\x00invalid utf-8")

        builder = ImportGraphBuilder("myproject")

        with patch("harness_linter.graph.logger") as mock_logger:
            imports = builder.get_imports_from_file(test_file)
            assert imports == []
            mock_logger.warning.assert_called_once()


class TestIncrementalImportGraphBuilder:
    """Tests for IncrementalImportGraphBuilder class."""

    def test_incremental_builder_init(self, tmp_path: Path) -> None:
        """Test IncrementalImportGraphBuilder initialization."""
        cache = ImportGraphCache(tmp_path / ".cache")
        builder = IncrementalImportGraphBuilder("myproject", cache)

        assert builder.root_package == "myproject"
        assert builder.cache == cache

    def test_build_from_path_incremental(self, tmp_path: Path) -> None:
        """Test incremental graph building."""
        # Create package structure
        pkg_dir = tmp_path / "src" / "myproject"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "__init__.py").write_text("")

        module_a = pkg_dir / "module_a.py"
        module_a.write_text("pass")

        cache = ImportGraphCache(tmp_path / ".cache")
        builder = IncrementalImportGraphBuilder("myproject", cache)

        source_files = {"myproject": pkg_dir / "__init__.py"}

        mock_graph = MagicMock()
        with patch("harness_linter.graph.grimp.build_graph", return_value=mock_graph):
            graph, reanalyzed = builder.build_from_path_incremental(pkg_dir, source_files)

            assert graph == mock_graph
            # New file should be in reanalyzed set
            assert "myproject" in reanalyzed

    def test_build_from_path_incremental_with_changed_modules(self, tmp_path: Path) -> None:
        """Test incremental build detects changed modules."""
        pkg_dir = tmp_path / "src" / "myproject"
        pkg_dir.mkdir(parents=True)

        module_a = pkg_dir / "module_a.py"
        module_a.write_text("pass")

        cache = ImportGraphCache(tmp_path / ".cache")
        builder = IncrementalImportGraphBuilder("myproject", cache)

        # First build - module is new
        source_files = {"myproject.module_a": module_a}

        mock_graph = MagicMock()
        with patch("harness_linter.graph.grimp.build_graph", return_value=mock_graph):
            graph, reanalyzed = builder.build_from_path_incremental(pkg_dir, source_files)
            assert "myproject.module_a" in reanalyzed

        # Update cache to mark as fresh
        cache.update("myproject.module_a", module_a, [])

        # Second build - no changes
        with patch("harness_linter.graph.grimp.build_graph", return_value=mock_graph):
            graph, reanalyzed = builder.build_from_path_incremental(pkg_dir, source_files)
            # No modules should need reanalysis
            assert len(reanalyzed) == 0

    def test_update_cache_for_modules(self, tmp_path: Path) -> None:
        """Test cache update for modules."""
        pkg_dir = tmp_path / "src" / "myproject"
        pkg_dir.mkdir(parents=True)

        module_a = pkg_dir / "module_a.py"
        module_a.write_text("import os\n")

        cache = ImportGraphCache(tmp_path / ".cache")
        builder = IncrementalImportGraphBuilder("myproject", cache)

        source_files = {"myproject.module_a": module_a}

        builder._update_cache_for_modules({"myproject.module_a"}, source_files)

        # Cache should be updated
        assert "myproject.module_a" in cache._fingerprints
        assert cache._imports.get("myproject.module_a") == ["os"]
