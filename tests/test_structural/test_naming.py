"""Tests for naming convention structural checks."""

from __future__ import annotations

import pytest
from pathlib import Path

from harness_linter.structural.naming import NamingCheck, NamingConfig, LayerNamingRules
from harness_linter.structural.base import StructuralViolation


class TestNamingConfig:
    """Tests for NamingConfig."""

    def test_default_config(self) -> None:
        """Test default configuration has expected layer patterns."""
        check = NamingCheck()
        config = check.config

        assert "service" in config.layer_patterns
        assert "repo" in config.layer_patterns

        service_rules = config.layer_patterns["service"]
        assert "Service" in service_rules.class_suffixes

        repo_rules = config.layer_patterns["repo"]
        assert "Repository" in repo_rules.class_suffixes or "Repo" in repo_rules.class_suffixes


class TestServiceNamingConvention:
    """Tests for service layer naming conventions."""

    def test_service_class_with_correct_suffix(self, tmp_path: Path) -> None:
        """Test service class with Service suffix passes."""
        check = NamingCheck()
        file_path = tmp_path / "user_service.py"
        file_path.write_text("""
class UserService:
    pass
""")

        violations = check.check_file(file_path, layer="service")
        assert len(violations) == 0

    def test_service_class_with_wrong_suffix(self, tmp_path: Path) -> None:
        """Test service class without Service suffix is flagged."""
        check = NamingCheck()
        file_path = tmp_path / "user_manager.py"
        file_path.write_text("""
class UserManager:
    pass
""")

        violations = check.check_file(file_path, layer="service")
        assert len(violations) == 1
        assert violations[0].check_name == "naming"
        assert "UserManager" in violations[0].message
        assert "Service" in violations[0].suggestion

    def test_multiple_service_classes(self, tmp_path: Path) -> None:
        """Test multiple classes in service file."""
        check = NamingCheck()
        file_path = tmp_path / "services.py"
        file_path.write_text("""
class UserService:
    pass

class OrderService:
    pass

class Helper:  # Wrong naming
    pass
""")

        violations = check.check_file(file_path, layer="service")
        assert len(violations) == 1
        assert "Helper" in violations[0].message


class TestRepoNamingConvention:
    """Tests for repository layer naming conventions."""

    def test_repo_class_with_repository_suffix(self, tmp_path: Path) -> None:
        """Test repo class with Repository suffix passes."""
        check = NamingCheck()
        file_path = tmp_path / "user_repository.py"
        file_path.write_text("""
class UserRepository:
    pass
""")

        violations = check.check_file(file_path, layer="repo")
        assert len(violations) == 0

    def test_repo_class_with_repo_suffix(self, tmp_path: Path) -> None:
        """Test repo class with Repo suffix passes."""
        check = NamingCheck()
        file_path = tmp_path / "user_repo.py"
        file_path.write_text("""
class UserRepo:
    pass
""")

        violations = check.check_file(file_path, layer="repo")
        assert len(violations) == 0

    def test_repo_class_with_wrong_suffix(self, tmp_path: Path) -> None:
        """Test repo class without Repository/Repo suffix is flagged."""
        check = NamingCheck()
        file_path = tmp_path / "user_accessor.py"
        file_path.write_text("""
class UserAccessor:
    pass
""")

        violations = check.check_file(file_path, layer="repo")
        assert len(violations) == 1
        assert violations[0].check_name == "naming"
        assert "UserAccessor" in violations[0].message
        assert "Repository" in violations[0].suggestion or "Repo" in violations[0].suggestion


class TestNamingCheckEdgeCases:
    """Tests for edge cases in naming check."""

    def test_no_layer_context(self, tmp_path: Path) -> None:
        """Test check with no layer context skips naming validation."""
        check = NamingCheck()
        file_path = tmp_path / "some_file.py"
        file_path.write_text("""
class SomeClass:
    pass
""")

        violations = check.check_file(file_path)
        # Without layer context, should not check naming
        assert len(violations) == 0

    def test_unknown_layer(self, tmp_path: Path) -> None:
        """Test check with unknown layer skips validation."""
        check = NamingCheck()
        file_path = tmp_path / "some_file.py"
        file_path.write_text("""
class SomeClass:
    pass
""")

        violations = check.check_file(file_path, layer="unknown_layer")
        # Unknown layer should not produce violations
        assert len(violations) == 0

    def test_non_class_definitions_ignored(self, tmp_path: Path) -> None:
        """Test that functions and variables are ignored."""
        check = NamingCheck()
        file_path = tmp_path / "service.py"
        file_path.write_text("""
def helper_function():
    pass

CONSTANT = 42

class ValidService:
    pass
""")

        violations = check.check_file(file_path, layer="service")
        # Function and constant should not trigger violations
        assert len(violations) == 0

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test empty file produces no violations."""
        check = NamingCheck()
        file_path = tmp_path / "empty.py"
        file_path.write_text("")

        violations = check.check_file(file_path, layer="service")
        assert len(violations) == 0

    def test_syntax_error_handling(self, tmp_path: Path) -> None:
        """Test handling of files with syntax errors."""
        check = NamingCheck()
        file_path = tmp_path / "broken.py"
        file_path.write_text("class Broken Class:")  # Invalid syntax

        # Should handle syntax error gracefully
        violations = check.check_file(file_path, layer="service")
        # May produce a violation about syntax error or return empty
        assert isinstance(violations, list)


class TestCustomNamingConfig:
    """Tests for custom naming configurations."""

    def test_custom_layer_rules(self, tmp_path: Path) -> None:
        """Test custom layer naming rules."""
        rules = LayerNamingRules(class_suffixes=["Controller"])
        config = NamingConfig(layer_patterns={"controller": rules})
        check = NamingCheck(config)

        file_path = tmp_path / "controller.py"
        file_path.write_text("""
class UserController:
    pass

class BadName:
    pass
""")

        violations = check.check_file(file_path, layer="controller")
        assert len(violations) == 1
        assert "BadName" in violations[0].message
