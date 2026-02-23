"""Tests for formatters module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from harness_linter.contracts.base import Violation
from harness_linter.formatters.rust_style import RustStyleFormatter


class TestRustStyleFormatter:
    """Tests for RustStyleFormatter."""

    def test_rust_style_formatter_initialization(self):
        """Test formatter initialization with default and custom values."""
        formatter = RustStyleFormatter()
        assert formatter.max_context_lines == 2

        formatter = RustStyleFormatter(max_context_lines=5)
        assert formatter.max_context_lines == 5

    def test_format_violation_basic(self):
        """Test basic violation formatting without source."""
        formatter = RustStyleFormatter()
        violation = Violation(
            importer="myproject.types",
            imported="myproject.service",
            message="Layer violation detected",
            line_number=5,
        )

        result = formatter.format_violation(violation)

        assert "error: Layer violation detected" in result
        assert "-->" in result
        assert "myproject/types.py:5:1" in result or "myproject.types" in result

    def test_format_violation_with_source(self, tmp_path: Path):
        """Test violation formatting with source code."""
        formatter = RustStyleFormatter()

        # Create a temporary source file
        source_file = tmp_path / "test_module.py"
        source_file.write_text("from myproject.service import UserService\n")

        violation = Violation(
            importer="test_module",
            imported="myproject.service",
            message="Layer violation detected",
            line_number=1,
        )

        result = formatter.format_violation(
            violation,
            source_file=source_file,
            source_line="from myproject.service import UserService",
        )

        assert "error: Layer violation detected" in result
        assert "from myproject.service import UserService" in result
        assert "^" in result  # Underline indicator

    def test_format_violation_without_line_number(self):
        """Test formatting violation without line number."""
        formatter = RustStyleFormatter()
        violation = Violation(
            importer="myproject.types",
            imported="myproject.service",
            message="Layer violation detected",
            line_number=None,
        )

        result = formatter.format_violation(violation)

        assert "error: Layer violation detected" in result
        # Should still show the module info
        assert "myproject.types" in result or "myproject/types" in result

    def test_format_source_snippet(self):
        """Test source snippet formatting with highlighting."""
        formatter = RustStyleFormatter()

        result = formatter._format_source_snippet(
            source_line="from myproject.service import UserService",
            line_number=5,
            column=0,
            length=39,
        )

        assert "5" in result
        assert "from myproject.service import UserService" in result
        assert "^" in result
        # Check for the pipe character used in Rust-style formatting
        assert "|" in result

    def test_format_source_snippet_with_column_offset(self):
        """Test source snippet with column offset."""
        formatter = RustStyleFormatter()

        result = formatter._format_source_snippet(
            source_line="    from myproject.service import UserService",
            line_number=10,
            column=4,
            length=39,
        )

        assert "10" in result
        assert "from myproject.service import UserService" in result
        assert "^" in result

    def test_format_import_chain(self):
        """Test import chain formatting."""
        formatter = RustStyleFormatter()

        chain = ["myproject.ui", "myproject.service", "myproject.repo"]
        result = formatter.format_import_chain(chain, highlight_idx=2)

        assert "myproject.ui" in result
        assert "myproject.service" in result
        assert "myproject.repo" in result
        assert "imports" in result.lower() or "->" in result

    def test_format_import_chain_empty(self):
        """Test formatting empty import chain."""
        formatter = RustStyleFormatter()

        result = formatter.format_import_chain([])
        assert result == ""

    def test_format_import_chain_single_item(self):
        """Test formatting single item import chain."""
        formatter = RustStyleFormatter()

        chain = ["myproject.ui"]
        result = formatter.format_import_chain(chain)

        assert "myproject.ui" in result

    def test_format_summary(self):
        """Test summary formatting."""
        formatter = RustStyleFormatter()

        result = formatter.format_summary(
            total_violations=5,
            analyzed_modules=10,
            duration_ms=123.45,
        )

        assert "5" in result
        assert "10" in result
        assert "123.45" in result or "123" in result
        assert "error" in result.lower() or "violation" in result.lower() or "[ERROR]" in result

    def test_format_summary_no_violations(self):
        """Test summary formatting with no violations."""
        formatter = RustStyleFormatter()

        result = formatter.format_summary(
            total_violations=0,
            analyzed_modules=10,
            duration_ms=50.0,
        )

        assert "0" in result
        assert "10" in result

    def test_get_source_line_success(self, tmp_path: Path):
        """Test successfully reading source line from file."""
        formatter = RustStyleFormatter()

        source_file = tmp_path / "test.py"
        source_file.write_text("line1\nline2\nline3\n")

        result = formatter._get_source_line(source_file, 2)
        assert result == "line2"

    def test_get_source_line_out_of_range(self, tmp_path: Path):
        """Test reading source line with out of range line number."""
        formatter = RustStyleFormatter()

        source_file = tmp_path / "test.py"
        source_file.write_text("line1\n")

        result = formatter._get_source_line(source_file, 10)
        assert result is None

    def test_get_source_line_file_not_found(self):
        """Test reading source line from non-existent file."""
        formatter = RustStyleFormatter()

        result = formatter._get_source_line(Path("/nonexistent/file.py"), 1)
        assert result is None

    def test_format_violation_with_help_notes(self):
        """Test that violation formatting includes help notes."""
        formatter = RustStyleFormatter()
        violation = Violation(
            importer="myproject.types",
            imported="myproject.service",
            message="Layer violation detected",
            line_number=5,
        )

        result = formatter.format_violation(violation)

        # Should contain help or note information
        assert "help:" in result or "note:" in result or "=" in result

    def test_format_violation_with_import_chain(self):
        """Test violation formatting with import chain visualization."""
        formatter = RustStyleFormatter()
        violation = Violation(
            importer="myproject.ui",
            imported="myproject.repo",
            message="Layer violation detected",
            line_number=10,
        )

        # Mock the import chain detection
        with patch.object(
            formatter,
            '_get_import_chain',
            return_value=["myproject.ui", "myproject.service", "myproject.repo"],
        ):
            result = formatter.format_violation(violation)

            # Should show the chain
            assert "myproject.ui" in result
            assert "myproject.service" in result
            assert "myproject.repo" in result


class TestRustStyleFormatterIntegration:
    """Integration tests for RustStyleFormatter."""

    def test_full_output_format(self, tmp_path: Path):
        """Test the complete output format matches Rust style."""
        formatter = RustStyleFormatter()

        source_file = tmp_path / "types.py"
        source_file.write_text("""# Line 1
# Line 2
from myproject.service import UserService
# Line 4
""")

        violation = Violation(
            importer="myproject.types",
            imported="myproject.service",
            message="Layer violation: types cannot import from service",
            line_number=3,
        )

        result = formatter.format_violation(
            violation,
            source_file=source_file,
        )

        # Check Rust-style format elements
        lines = result.split("\n")

        # First line should have "error:"
        assert any("error:" in line for line in lines)

        # Should have location indicator with "-->"
        assert any("-->" in line for line in lines)

        # Should have source code with line number
        assert any("3" in line and "from myproject.service" in line for line in lines)

        # Should have underline with ^ characters
        assert any("^" in line for line in lines)

        # Should have help/note with "=" prefix
        assert any("=" in line for line in lines)

    def test_multiple_violations_formatting(self):
        """Test formatting multiple violations."""
        formatter = RustStyleFormatter()

        violations = [
            Violation(
                importer="myproject.types",
                imported="myproject.service",
                message="First violation",
                line_number=1,
            ),
            Violation(
                importer="myproject.config",
                imported="myproject.ui",
                message="Second violation",
                line_number=2,
            ),
        ]

        results = [formatter.format_violation(v) for v in violations]

        assert all("error:" in r for r in results)
        assert "First violation" in results[0]
        assert "Second violation" in results[1]
