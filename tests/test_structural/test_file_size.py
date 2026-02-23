"""Tests for file size structural checks."""

from __future__ import annotations

import pytest
from pathlib import Path

from harness_linter.structural.file_size import FileSizeCheck, FileSizeConfig
from harness_linter.structural.base import StructuralViolation


class TestFileSizeConfig:
    """Tests for FileSizeConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = FileSizeConfig()
        assert config.max_lines == 500
        assert config.max_blank_lines_ratio == 0.3

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = FileSizeConfig(max_lines=300, max_blank_lines_ratio=0.2)
        assert config.max_lines == 300
        assert config.max_blank_lines_ratio == 0.2


class TestFileSizeViolation:
    """Tests for file size violation detection."""

    def test_file_within_limits(self, tmp_path: Path) -> None:
        """Test file within size limits passes."""
        check = FileSizeCheck(FileSizeConfig(max_lines=10))
        file_path = tmp_path / "small_file.py"
        file_path.write_text("line1\nline2\nline3\n")

        violations = check.check_file(file_path)
        assert len(violations) == 0

    def test_file_exceeds_max_lines(self, tmp_path: Path) -> None:
        """Test file exceeding max lines is detected."""
        check = FileSizeCheck(FileSizeConfig(max_lines=5))
        file_path = tmp_path / "large_file.py"
        file_path.write_text("line\n" * 10)  # 10 lines

        violations = check.check_file(file_path)
        assert len(violations) == 1
        assert violations[0].check_name == "file-size"
        assert "exceeds" in violations[0].message.lower()
        assert "10" in violations[0].message
        assert "5" in violations[0].message

    def test_file_size_violation_structure(self, tmp_path: Path) -> None:
        """Test violation has correct structure."""
        check = FileSizeCheck(FileSizeConfig(max_lines=3))
        file_path = tmp_path / "test_file.py"
        file_path.write_text("line1\nline2\nline3\nline4\n")

        violations = check.check_file(file_path)
        assert len(violations) == 1
        violation = violations[0]
        assert isinstance(violation, StructuralViolation)
        assert violation.file_path == file_path
        assert violation.suggestion != ""


class TestBlankLinesRatio:
    """Tests for blank lines ratio detection."""

    def test_normal_blank_lines_ratio(self, tmp_path: Path) -> None:
        """Test file with normal blank lines ratio passes."""
        check = FileSizeCheck(FileSizeConfig(max_lines=100, max_blank_lines_ratio=0.3))
        file_path = tmp_path / "normal_file.py"
        # 10 lines, 2 blank (20%)
        content = "def foo():\n    pass\n\ndef bar():\n    pass\n"
        file_path.write_text(content)

        violations = check.check_file(file_path)
        # Should not have blank lines ratio violation
        blank_violations = [v for v in violations if "blank" in v.message.lower()]
        assert len(blank_violations) == 0

    def test_excessive_blank_lines(self, tmp_path: Path) -> None:
        """Test file with excessive blank lines is detected."""
        check = FileSizeCheck(FileSizeConfig(max_lines=100, max_blank_lines_ratio=0.3))
        file_path = tmp_path / "sparse_file.py"
        # 10 lines, 5 blank (50%)
        content = "def foo():\n\n\n    pass\n\n\ndef bar():\n\n\n    pass\n"
        file_path.write_text(content)

        violations = check.check_file(file_path)
        blank_violations = [v for v in violations if "blank" in v.message.lower()]
        assert len(blank_violations) == 1
        assert "blank" in blank_violations[0].message.lower()
        assert blank_violations[0].check_name == "file-size"

    def test_blank_lines_ratio_calculation(self, tmp_path: Path) -> None:
        """Test blank lines ratio is calculated correctly."""
        check = FileSizeCheck(FileSizeConfig(max_lines=20, max_blank_lines_ratio=0.25))
        file_path = tmp_path / "ratio_test.py"
        # 12 lines total, 4 blank (33.3% > 25%)
        content = "line1\n\nline2\n\nline3\n\nline4\n\n"
        file_path.write_text(content)

        violations = check.check_file(file_path)
        blank_violations = [v for v in violations if "blank" in v.message.lower()]
        assert len(blank_violations) == 1
        # Check that ratio is mentioned in message
        assert "%" in blank_violations[0].message or "percent" in blank_violations[0].message.lower()


class TestFileSizeCheckInit:
    """Tests for FileSizeCheck initialization."""

    def test_default_initialization(self) -> None:
        """Test check initializes with default config."""
        check = FileSizeCheck()
        assert check.name == "file-size"
        assert check.config.max_lines == 500

    def test_custom_config_initialization(self) -> None:
        """Test check initializes with custom config."""
        config = FileSizeConfig(max_lines=200)
        check = FileSizeCheck(config)
        assert check.config.max_lines == 200
