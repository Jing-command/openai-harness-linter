"""Base classes for structural checks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class StructuralViolation:
    """Violation of a structural rule."""
    check_name: str
    message: str
    file_path: Path
    line_number: Optional[int] = None
    suggestion: str = ""


class StructuralCheck(ABC):
    """Abstract base class for structural checks."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def check_file(self, file_path: Path, **context) -> list[StructuralViolation]:
        """Check a single file."""
        pass

    def check_project(
        self,
        source_files: list[Path],
        layer_resolver: Optional[callable] = None
    ) -> list[StructuralViolation]:
        """Check the entire project."""
        all_violations: list[StructuralViolation] = []

        for file_path in source_files:
            # Determine layer context if resolver is provided
            context = {}
            if layer_resolver:
                layer = layer_resolver(file_path)
                if layer:
                    context["layer"] = layer

            violations = self.check_file(file_path, **context)
            all_violations.extend(violations)

        return all_violations
