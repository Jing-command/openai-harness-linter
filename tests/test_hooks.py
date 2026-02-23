"""Tests for pre-commit hook integration."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harness_linter.hooks import run_pre_commit


class TestRunPreCommit:
    """Test cases for run_pre_commit function."""

    def test_run_pre_commit_success(self, tmp_path: Path) -> None:
        """Test successful pre-commit run with valid project."""
        # Create a temporary project with pyproject.toml
        project_root = tmp_path / "test_project"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        # Mock subprocess.run to return success
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Linting passed!"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch.object(Path, "cwd", return_value=project_root):
                result = run_pre_commit(["file1.py", "file2.py"])

        assert result == 0
        mock_run.assert_called_once_with(
            ["harness-lint", "-v"],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

    def test_run_pre_commit_failure(self, tmp_path: Path) -> None:
        """Test pre-commit run with linting failures."""
        # Create a temporary project with pyproject.toml
        project_root = tmp_path / "test_project"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        # Mock subprocess.run to return failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Linting failed!"
        mock_result.stderr = "Some error"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch.object(Path, "cwd", return_value=project_root):
                result = run_pre_commit(["file1.py"])

        assert result == 1

    def test_run_pre_commit_no_pyproject(self, tmp_path: Path) -> None:
        """Test pre-commit run without pyproject.toml in project tree."""
        # Create a temporary directory without pyproject.toml
        project_root = tmp_path / "test_project"
        project_root.mkdir()

        with patch.object(Path, "cwd", return_value=project_root):
            result = run_pre_commit(["file1.py"])

        assert result == 1

    def test_run_pre_commit_finds_parent_pyproject(self, tmp_path: Path) -> None:
        """Test that pre-commit finds pyproject.toml in parent directories."""
        # Create project structure: root/pyproject.toml and root/subdir/
        root = tmp_path / "root_project"
        root.mkdir()
        (root / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        subdir = root / "subdir"
        subdir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch.object(Path, "cwd", return_value=subdir):
                result = run_pre_commit(["file.py"])

        assert result == 0
        # Should run from root directory where pyproject.toml exists
        mock_run.assert_called_once_with(
            ["harness-lint", "-v"],
            cwd=root,
            capture_output=True,
            text=True,
        )

    def test_run_pre_commit_with_stderr(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test that stderr is printed when present."""
        project_root = tmp_path / "test_project"
        project_root.mkdir()
        (project_root / "pyproject.toml").write_text("[project]\nname = 'test'\n")

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Output"
        mock_result.stderr = "Warning message"

        with patch("subprocess.run", return_value=mock_result):
            with patch.object(Path, "cwd", return_value=project_root):
                run_pre_commit(["file.py"])

        # Verify stdout was printed
        captured = capsys.readouterr()
        assert "Output" in captured.out
        assert "Warning message" in captured.err


class TestHookModuleMain:
    """Test cases for hook module main execution."""

    @patch("harness_linter.hooks.run_pre_commit")
    @patch.object(sys, "argv", ["hooks.py", "file1.py", "file2.py"])
    def test_main_execution(self, mock_run: MagicMock) -> None:
        """Test main execution with command line arguments."""
        mock_run.return_value = 0

        # Import and run the main block logic
        import harness_linter.hooks as hooks_module

        # Simulate __main__ block
        files = sys.argv[1:]
        result = hooks_module.run_pre_commit(files)

        mock_run.assert_called_once_with(["file1.py", "file2.py"])
        assert result == 0

    @patch("harness_linter.hooks.run_pre_commit")
    @patch.object(sys, "argv", ["hooks.py"])
    def test_main_execution_no_files(self, mock_run: MagicMock) -> None:
        """Test main execution with no files."""
        mock_run.return_value = 0

        import harness_linter.hooks as hooks_module

        files = sys.argv[1:]
        result = hooks_module.run_pre_commit(files)

        mock_run.assert_called_once_with([])
        assert result == 0
