"""Configuration system for harness_linter.

This module provides configuration loading and management for the linter.
Configuration can be loaded from pyproject.toml files.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["Config", "load_config", "find_project_root"]


@dataclass
class Config:
    """Configuration for the harness linter.

    Attributes:
        root_package: The root package name to analyze
        layers: List of layer configurations (name, index, modules)
        providers: List of provider configurations (name, modules, allowed_layers)
        contracts: List of contract names to check
        cache_path: Path to the cache file
    """

    root_package: str
    layers: list[dict[str, Any]] = field(default_factory=list)
    providers: list[dict[str, Any]] = field(default_factory=list)
    contracts: list[str] = field(default_factory=list)
    cache_path: str = ".harness_cache"

    @classmethod
    def default(cls, root_package: str) -> "Config":
        """Create a default configuration with standard layers.

        Args:
            root_package: The root package name

        Returns:
            Config with standard 6-layer Harness architecture
        """
        return cls(
            root_package=root_package,
            layers=[
                {"name": "types", "index": 0, "modules": [f"{root_package}.types"]},
                {"name": "config", "index": 1, "modules": [f"{root_package}.config"]},
                {"name": "repo", "index": 2, "modules": [f"{root_package}.repo"]},
                {"name": "service", "index": 3, "modules": [f"{root_package}.service"]},
                {"name": "runtime", "index": 4, "modules": [f"{root_package}.runtime"]},
                {"name": "ui", "index": 5, "modules": [f"{root_package}.ui"]},
            ],
            providers=[
                {"name": "logging", "modules": [f"{root_package}.providers.logging"]},
                {"name": "metrics", "modules": [f"{root_package}.providers.metrics"]},
            ],
            contracts=["layer", "provider"],
        )


def load_config(path: Path | None = None) -> Config | None:
    """Load configuration from a pyproject.toml file.

    Args:
        path: Path to the pyproject.toml file, or None to search in current directory

    Returns:
        Config if found and valid, None otherwise
    """
    if path is None:
        path = Path("pyproject.toml")

    if not path.exists():
        logger.debug(f"Config file not found: {path}")
        return None

    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore[no-redef]

    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)

        tool_config = data.get("tool", {}).get("harness-linter")
        if tool_config is None:
            logger.debug("No [tool.harness-linter] section found in pyproject.toml")
            return None

        root_package = tool_config.get("root-package")
        if not root_package:
            logger.warning("No root-package specified in config")
            return None

        return Config(
            root_package=root_package,
            layers=tool_config.get("layers", []),
            providers=tool_config.get("providers", []),
            contracts=tool_config.get("contracts", ["layer", "provider"]),
            cache_path=tool_config.get("cache-path", ".harness_cache"),
        )
    except (tomllib.TOMLDecodeError, IOError, OSError) as e:
        logger.warning(f"Failed to load config from {path}: {e}")
        return None


def find_project_root(start_path: Path | None = None) -> Path | None:
    """Find the project root by looking for pyproject.toml.

    Args:
        start_path: Path to start searching from, or None for current directory

    Returns:
        Path to project root if found, None otherwise
    """
    if start_path is None:
        start_path = Path.cwd()

    current = start_path.resolve()

    while True:
        pyproject = current / "pyproject.toml"
        if pyproject.exists():
            return current

        parent = current.parent
        if parent == current:  # Reached root
            return None
        current = parent
