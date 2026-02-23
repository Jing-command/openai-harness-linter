"""Import graph building functionality using grimp."""

from __future__ import annotations

import ast
import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import grimp

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Generator

    from grimp import ImportGraph

    from harness_linter.cache import ImportGraphCache


@contextmanager
def _sys_path_context(path: str) -> Generator[None, None, None]:
    """Context manager to temporarily add a path to sys.path.

    Args:
        path: Path to add to sys.path

    Yields:
        None
    """
    inserted = False
    if path not in sys.path:
        sys.path.insert(0, path)
        inserted = True
    try:
        yield
    finally:
        if inserted:
            sys.path.remove(path)


class ImportGraphBuilder:
    """Builds import graphs for Python packages."""

    def __init__(self, root_package: str):
        self.root_package = root_package

    def build_from_path(self, path: Path) -> ImportGraph:
        """Build import graph from a package path.

        Args:
            path: Path to the package directory

        Returns:
            ImportGraph: The built import graph
        """
        # Add parent directory to path for grimp to find the package
        parent_path = str(path.parent)

        with _sys_path_context(parent_path):
            graph = grimp.build_graph(
                package_name=self.root_package,
            )
        return graph

    def find_source_files(self, path: Path) -> dict[str, Path]:
        """Find all Python source files in a package.

        Args:
            path: Path to the package directory

        Returns:
            dict mapping module names to file paths
        """
        source_files = {}

        for py_file in path.rglob("*.py"):
            if py_file.name == "__init__.py":
                # Calculate module name from relative path
                relative = py_file.parent.relative_to(path.parent)
                module_name = str(relative).replace("\\", ".").replace("/", ".")
            else:
                relative = py_file.relative_to(path.parent)
                module_name = str(relative.with_suffix("")).replace("\\", ".").replace("/", ".")

            source_files[module_name] = py_file

        return source_files

    def get_imports_from_file(self, path: Path) -> list[str]:
        """Parse a Python file and extract its imports.

        Args:
            path: Path to the Python file

        Returns:
            list of imported module names
        """
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to parse {path}: {e}")
            return []

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)

        return imports


class IncrementalImportGraphBuilder(ImportGraphBuilder):
    """Builds import graphs incrementally using a cache.

    Only re-analyzes files that have changed or depend on changed files.
    """

    def __init__(self, root_package: str, cache: ImportGraphCache):
        """Initialize the incremental builder.

        Args:
            root_package: Name of the root package
            cache: Cache instance for storing/retrieving analysis results
        """
        super().__init__(root_package)
        self.cache = cache

    def build_from_path_incremental(
        self,
        path: Path,
        source_files: dict[str, Path]
    ) -> tuple[ImportGraph, set[str]]:
        """Build import graph incrementally.

        Uses the cache to determine which files need re-analysis.

        Args:
            path: Path to the package directory
            source_files: Dictionary mapping module names to file paths

        Returns:
            Tuple of (import_graph, reanalyzed_modules)
            import_graph: The built import graph
            reanalyzed_modules: Set of modules that were re-analyzed
        """
        # Find changed modules and affected modules
        changed, affected = self.cache.get_changed_modules(source_files)

        # Modules that need re-analysis
        to_reanalyze = changed | affected

        # Add parent directory to path for grimp to find the package
        parent_path = str(path.parent)

        with _sys_path_context(parent_path):
            # Build graph using grimp (always builds full graph)
            graph = grimp.build_graph(
                package_name=self.root_package,
            )

        # Update cache for changed and affected modules
        self._update_cache_for_modules(changed, source_files)
        self._update_cache_for_modules(affected, source_files)

        return graph, to_reanalyze

    def _update_cache_for_modules(
        self, modules: set[str], source_files: dict[str, Path]
    ) -> None:
        """Update cache for a set of modules.

        Args:
            modules: Set of module names to update
            source_files: Dictionary mapping module names to file paths
        """
        for module in modules:
            if module in source_files:
                source_path = source_files[module]
                imports = self.get_imports_from_file(source_path)
                self.cache.update(module, source_path, imports)
