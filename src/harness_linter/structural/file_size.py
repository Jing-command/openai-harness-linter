"""File size structural checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness_linter.structural.base import StructuralCheck, StructuralViolation


@dataclass
class FileSizeConfig:
    """Configuration for file size checks."""
    max_lines: int = 500
    max_blank_lines_ratio: float = 0.3


class FileSizeCheck(StructuralCheck):
    """Check file size limits."""

    def __init__(self, config: FileSizeConfig | None = None):
        super().__init__("file-size")
        self.config = config or FileSizeConfig()

    def check_file(self, file_path: Path, **context) -> list[StructuralViolation]:
        """Check file for size violations.

        Args:
            file_path: Path to the file to check
            **context: Additional context (unused)

        Returns:
            List of structural violations found
        """
        violations: list[StructuralViolation] = []

        try:
            content = file_path.read_text(encoding="utf-8")
        except (IOError, UnicodeDecodeError) as e:
            violations.append(
                StructuralViolation(
                    check_name=self.name,
                    message=f"Could not read file: {e}",
                    file_path=file_path,
                    suggestion="Check file permissions and encoding",
                )
            )
            return violations

        lines = content.splitlines()
        total_lines = len(lines)

        # Check line count limit
        if total_lines > self.config.max_lines:
            violations.append(
                StructuralViolation(
                    check_name=self.name,
                    message=f"File has {total_lines} lines, exceeds limit of {self.config.max_lines}",
                    file_path=file_path,
                    suggestion=f"Consider splitting this file into smaller modules (max {self.config.max_lines} lines)",
                )
            )

        # Check blank lines ratio
        blank_lines = sum(1 for line in lines if line.strip() == "")
        if total_lines > 0:
            blank_ratio = blank_lines / total_lines
            if blank_ratio > self.config.max_blank_lines_ratio:
                percentage = blank_ratio * 100
                violations.append(
                    StructuralViolation(
                        check_name=self.name,
                        message=f"File has {percentage:.1f}% blank lines, exceeds limit of {self.config.max_blank_lines_ratio * 100:.1f}%",
                        file_path=file_path,
                        suggestion="Consider removing excessive blank lines to improve code density",
                    )
                )

        return violations
