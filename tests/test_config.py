"""Tests for the config module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from harness_linter.config import Config, find_project_root, load_config


class TestConfig:
    """Tests for the Config class."""

    def test_config_creation(self) -> None:
        """Test basic config creation."""
        config = Config(
            root_package="myproject",
            layers=[{"name": "types", "index": 0}],
            providers=[{"name": "logging"}],
            contracts=["layer"],
            cache_path=".cache",
        )
        assert config.root_package == "myproject"
        assert len(config.layers) == 1
        assert len(config.providers) == 1
        assert config.contracts == ["layer"]
        assert config.cache_path == ".cache"

    def test_config_defaults(self) -> None:
        """Test config default values."""
        config = Config(root_package="myproject")
        assert config.layers == []
        assert config.providers == []
        assert config.contracts == []
        assert config.cache_path == ".harness_cache"

    def test_default_config(self) -> None:
        """Test creating default configuration."""
        config = Config.default("myproject")

        assert config.root_package == "myproject"
        assert len(config.layers) == 6
        assert len(config.providers) == 2
        assert config.contracts == ["layer", "provider"]

        # Check layer names and indices
        layer_names = [layer["name"] for layer in config.layers]
        assert layer_names == ["types", "config", "repo", "service", "runtime", "ui"]

        for i, layer in enumerate(config.layers):
            assert layer["index"] == i
            assert f"myproject.{layer['name']}" in layer["modules"]


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_load_config_not_found(self) -> None:
        """Test loading config when file doesn't exist."""
        with patch.object(Path, "exists", return_value=False):
            result = load_config(Path("/nonexistent/pyproject.toml"))
        assert result is None

    def test_load_config_no_harness_section(self) -> None:
        """Test loading config without harness-linter section."""
        toml_content = b"""
[project]
name = "myproject"
"""
        with patch("builtins.open", mock_open(read_data=toml_content)):
            with patch.object(Path, "exists", return_value=True):
                result = load_config(Path("pyproject.toml"))
        assert result is None

    def test_load_config_no_root_package(self) -> None:
        """Test loading config without root-package."""
        toml_content = b"""
[tool.harness-linter]
layers = []
"""
        with patch("builtins.open", mock_open(read_data=toml_content)):
            with patch.object(Path, "exists", return_value=True):
                result = load_config(Path("pyproject.toml"))
        assert result is None

    def test_load_config_success(self) -> None:
        """Test loading valid configuration."""
        toml_content = b"""
[tool.harness-linter]
root-package = "myproject"
contracts = ["layer", "provider"]
cache-path = ".my_cache"

[[tool.harness-linter.layers]]
name = "types"
index = 0
modules = ["myproject.types"]

[[tool.harness-linter.layers]]
name = "service"
index = 3
modules = ["myproject.service"]

[[tool.harness-linter.providers]]
name = "logging"
modules = ["myproject.providers.logging"]
allowed_layers = ["service", "runtime"]
"""
        with patch("builtins.open", mock_open(read_data=toml_content)):
            with patch.object(Path, "exists", return_value=True):
                result = load_config(Path("pyproject.toml"))

        assert result is not None
        assert result.root_package == "myproject"
        assert result.contracts == ["layer", "provider"]
        assert result.cache_path == ".my_cache"
        assert len(result.layers) == 2
        assert len(result.providers) == 1

    def test_load_config_default_contracts(self) -> None:
        """Test that default contracts are used if not specified."""
        toml_content = b"""
[tool.harness-linter]
root-package = "myproject"
"""
        with patch("builtins.open", mock_open(read_data=toml_content)):
            with patch.object(Path, "exists", return_value=True):
                result = load_config(Path("pyproject.toml"))

        assert result is not None
        assert result.contracts == ["layer", "provider"]

    def test_load_config_default_cache_path(self) -> None:
        """Test that default cache path is used if not specified."""
        toml_content = b"""
[tool.harness-linter]
root-package = "myproject"
"""
        with patch("builtins.open", mock_open(read_data=toml_content)):
            with patch.object(Path, "exists", return_value=True):
                result = load_config(Path("pyproject.toml"))

        assert result is not None
        assert result.cache_path == ".harness_cache"


class TestFindProjectRoot:
    """Tests for the find_project_root function."""

    def test_find_project_root_current_dir(self, tmp_path: Path) -> None:
        """Test finding project root in current directory."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = \"test\"\n")

        result = find_project_root(tmp_path)
        assert result == tmp_path

    def test_find_project_root_parent_dir(self, tmp_path: Path) -> None:
        """Test finding project root in parent directory."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = \"test\"\n")

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        result = find_project_root(subdir)
        assert result == tmp_path

    def test_find_project_root_not_found(self, tmp_path: Path) -> None:
        """Test when project root is not found."""
        result = find_project_root(tmp_path)
        assert result is None

    def test_find_project_root_none_uses_cwd(self) -> None:
        """Test that None uses current working directory."""
        with patch("pathlib.Path.cwd", return_value=Path("/mock/cwd")):
            with patch.object(Path, "exists", return_value=True):
                result = find_project_root(None)
        # Should find the mock cwd
        assert result is not None
