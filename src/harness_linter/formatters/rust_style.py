"""Rust compiler-style error formatter for harness_linter.

This module provides the RustStyleFormatter which formats violations
in a style similar to the Rust compiler's error messages.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from harness_linter.contracts.base import Violation


class RustStyleFormatter:
    """Rust compiler-style error formatter

    Provides detailed error information, including:
    - File position and line numbers
    - Source code snippet highlighting
    - Multi-level help/note information
    - Import chain visualization

    Example output:
    ```
    error: Layer violation detected
      --> myproject/types.py:5:1
       |
     5 | from myproject.service import UserService
       | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
       |
       = note: types (level 0) cannot import from service (level 3)
       = help: Consider moving shared code to 'types' or 'config' layer
    ```
    """

    def __init__(self, max_context_lines: int = 2):
        self.max_context_lines = max_context_lines

    def format_violation(
        self,
        violation: "Violation",
        source_file: Optional[Path] = None,
        source_line: Optional[str] = None,
    ) -> str:
        """Format a single violation in Rust-style format.

        Args:
            violation: The violation to format
            source_file: Optional path to the source file
            source_line: Optional source line content

        Returns:
            Formatted error message string
        """
        lines = []

        # Error header
        lines.append(f"error: {violation.message}")

        # Location line
        location = self._format_location(violation, source_file)
        lines.append(location)

        # Source snippet
        if source_line is None and source_file and violation.line_number:
            source_line = self._get_source_line(source_file, violation.line_number)

        if source_line and violation.line_number:
            snippet = self._format_source_snippet(
                source_line,
                violation.line_number,
                column=0,
                length=len(source_line),
            )
            lines.append(snippet)
        else:
            # Add empty separator if no source
            lines.append("   |")

        # Help and note messages
        help_notes = self._generate_help_notes(violation)
        for note in help_notes:
            lines.append(f"   = {note}")

        # Import chain if applicable
        import_chain = self._get_import_chain(violation)
        if import_chain and len(import_chain) > 1:
            chain_str = self.format_import_chain(import_chain)
            if chain_str:
                lines.append("   |")
                lines.append("   = note: Import chain:")
                for chain_line in chain_str.split("\n"):
                    lines.append(f"   |   {chain_line}")

        return "\n".join(lines)

    def _format_location(self, violation: "Violation", source_file: Optional[Path]) -> str:
        """Format the location line of the error.

        Args:
            violation: The violation
            source_file: Optional source file path

        Returns:
            Location string like "  --> file.py:10:1"
        """
        if source_file:
            file_path = source_file
        else:
            # Convert module path to file path
            file_path = Path(violation.importer.replace(".", "/") + ".py")

        line_num = violation.line_number if violation.line_number else 1
        column = 1

        return f"  --> {file_path}:{line_num}:{column}"

    def format_import_chain(self, chain: list[str], highlight_idx: int = -1) -> str:
        """Format an import chain for visualization.

        Args:
            chain: List of module names in the import chain
            highlight_idx: Index of the item to highlight (default: last item)

        Returns:
            Formatted import chain string
        """
        if not chain:
            return ""

        if highlight_idx < 0:
            highlight_idx = len(chain) - 1

        lines = []
        indent = ""

        for i, module in enumerate(chain):
            if i == highlight_idx:
                marker = " (violation!)"
            else:
                marker = ""

            if i == 0:
                lines.append(f"{module}{marker}")
            else:
                lines.append(f"{indent}  imports -> {module}{marker}")

            indent += "  "

        return "\n".join(lines)

    def format_summary(
        self,
        total_violations: int,
        analyzed_modules: int,
        duration_ms: float,
    ) -> str:
        """Format a summary of the analysis.

        Args:
            total_violations: Total number of violations found
            analyzed_modules: Number of modules analyzed
            duration_ms: Duration in milliseconds

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("")

        if total_violations == 0:
            lines.append("[OK] No violations found.")
        else:
            error_word = "error" if total_violations == 1 else "errors"
            lines.append(f"[ERROR] Found {total_violations} {error_word}.")

        lines.append(f"")
        lines.append(f"Analyzed {analyzed_modules} modules in {duration_ms:.2f}ms")

        return "\n".join(lines)

    def _format_source_snippet(
        self,
        source_line: str,
        line_number: int,
        column: int = 0,
        length: int = 0,
    ) -> str:
        """Format a source code snippet with highlighting.

        Args:
            source_line: The source code line
            line_number: Line number for display
            column: Starting column for highlight
            length: Length of highlight

        Returns:
            Formatted source snippet with underline
        """
        lines = []

        # Top border
        lines.append("   |")

        # Source line with line number
        lines.append(f"{line_number:>3} | {source_line}")

        # Underline with carets
        if length > 0:
            underline = "   |" + " " * (column + 1) + "^" * length
            lines.append(underline)

        # Bottom border
        lines.append("   |")

        return "\n".join(lines)

    def _get_source_line(self, file_path: Path, line_number: int) -> Optional[str]:
        """Read a specific line from a source file.

        Args:
            file_path: Path to the source file
            line_number: 1-based line number to read

        Returns:
            The line content if found, None otherwise
        """
        try:
            lines = file_path.read_text().split("\n")
            if 1 <= line_number <= len(lines):
                return lines[line_number - 1]
        except (IOError, OSError, UnicodeDecodeError):
            pass
        return None

    def _generate_help_notes(self, violation: "Violation") -> list[str]:
        """Generate help and note messages for a violation.

        Args:
            violation: The violation

        Returns:
            List of help/note strings
        """
        notes = []

        # Extract layer information if present in the message
        if "layer" in violation.message.lower():
            # Try to extract layer names from the violation
            importer_parts = violation.importer.split(".")
            imported_parts = violation.imported.split(".")

            # Find potential layer names (common layer names)
            common_layers = ["types", "config", "repo", "service", "runtime", "ui"]

            importer_layer = None
            imported_layer = None

            for layer in common_layers:
                if layer in importer_parts:
                    importer_layer = layer
                if layer in imported_parts:
                    imported_layer = layer

            if importer_layer and imported_layer:
                notes.append(
                    f"note: {importer_layer} cannot import from {imported_layer} "
                    "due to layer hierarchy rules"
                )
                notes.append(
                    f"help: Consider moving shared code to a common layer "
                    f"or restructuring the dependency"
                )

        # Generic help for import violations
        if not notes:
            notes.append(f"note: {violation.importer} imports {violation.imported}")
            notes.append("help: Review the import relationship and consider refactoring")

        return notes

    def _get_import_chain(self, violation: "Violation") -> list[str]:
        """Get the import chain for a violation.

        This is a placeholder that returns a simple chain.
        In a full implementation, this would trace the actual import path.

        Args:
            violation: The violation

        Returns:
            List of modules in the import chain
        """
        # For now, return a simple two-item chain
        # In a real implementation, this would use the import graph
        return [violation.importer, violation.imported]
