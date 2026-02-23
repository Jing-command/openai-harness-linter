"""Agent context formatter for LLM-friendly error messages.

This module provides the AgentContextFormatter which formats violations
in a structured format that LLMs can directly parse and consume.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from harness_linter.contracts.base import Violation


@dataclass
class ViolationContext:
    """LLM-consumable rich violation context.

    Attributes:
        violation: The base violation object
        layer_importer: The layer name of the importing module
        layer_imported: The layer name of the imported module
        severity: The severity level ("error", "warning")
        architectural_principle: Explanation of the architectural rule violated
        suggested_fix: High-level suggestion for fixing the violation
        code_example: Optional code example showing before/after
        documentation_link: Optional link to relevant documentation
    """

    violation: "Violation"
    layer_importer: str
    layer_imported: str
    severity: str
    architectural_principle: str
    suggested_fix: str
    code_example: Optional[str] = None
    documentation_link: Optional[str] = None


class AgentContextFormatter:
    """Formatter for AI Agent consumption.

    Output is designed for LLM direct parsing, including:
    - Structured format (easy to parse)
    - Specific remediation steps
    - Architectural principle explanations
    - Batch report formatting
    """

    def format_for_agent(self, context: ViolationContext) -> str:
        """Format a violation for Agent consumption.

        Args:
            context: The violation context to format

        Returns:
            Formatted string in LLM-friendly format

        Example output:
            ============================================================
            ARCHITECTURE_VIOLATION
            ============================================================

            Type: backward_dependency
            Severity: error

            Problem:
              Layer 'types' cannot import from 'service'

            Location:
              Module: myproject.types
              Layer: types
              Invalid import: myproject.service
              From layer: service

            Architectural Principle:
              Dependencies flow forward through layers

            Suggested Fix:
              Extract shared interface to types layer

            Remediation Steps:
              1. Identify what 'types' needs from 'service'
              2. Define an interface in a lower layer
              3. Move shared types to the lower layer
              4. Use dependency injection
              5. Ensure correct dependency direction
            ============================================================
        """
        lines = []
        violation_type = self._categorize_violation(context)

        # Header
        lines.append("=" * 60)
        lines.append("ARCHITECTURE_VIOLATION")
        lines.append("=" * 60)
        lines.append("")

        # Type and Severity
        lines.append(f"Type: {violation_type}")
        lines.append(f"Severity: {context.severity}")
        lines.append("")

        # Problem
        lines.append("Problem:")
        lines.append(f"  Layer '{context.layer_importer}' cannot import from '{context.layer_imported}'")
        lines.append("")

        # Location
        lines.append("Location:")
        lines.append(f"  Module: {context.violation.importer}")
        lines.append(f"  Layer: {context.layer_importer}")
        lines.append(f"  Invalid import: {context.violation.imported}")
        lines.append(f"  From layer: {context.layer_imported}")
        if context.violation.line_number:
            lines.append(f"  Line: {context.violation.line_number}")
        lines.append("")

        # Architectural Principle
        lines.append("Architectural Principle:")
        lines.append(f"  {context.architectural_principle}")
        lines.append("")

        # Suggested Fix
        lines.append("Suggested Fix:")
        lines.append(f"  {context.suggested_fix}")
        lines.append("")

        # Remediation Steps
        lines.append("Remediation Steps:")
        steps = self.get_remediation_steps(
            violation_type, context.layer_importer, context.layer_imported
        )
        for step in steps:
            lines.append(f"  {step}")

        # Optional Code Example
        if context.code_example:
            lines.append("")
            lines.append("Code Example:")
            for line in context.code_example.strip().split("\n"):
                lines.append(f"  {line}")

        # Optional Documentation Link
        if context.documentation_link:
            lines.append("")
            lines.append("Documentation:")
            lines.append(f"  {context.documentation_link}")

        # Footer
        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def get_remediation_steps(
        self,
        violation_type: str,
        importer_layer: str,
        target_layer: str,
    ) -> list[str]:
        """Get remediation steps based on violation type.

        Args:
            violation_type: The type of violation
            importer_layer: The layer doing the importing
            target_layer: The layer being imported

        Returns:
            List of remediation step strings
        """
        if violation_type == "backward_dependency":
            return [
                f"1. Identify what '{importer_layer}' needs from '{target_layer}'",
                "2. Define an interface in a lower layer",
                "3. Move shared types to the lower layer",
                "4. Use dependency injection",
                "5. Ensure correct dependency direction",
            ]
        elif violation_type == "provider_misuse":
            return [
                "1. Check if layer really needs this provider",
                "2. If yes, add to allowed_layers",
                "3. If no, refactor to avoid dependency",
            ]
        else:
            return [
                "1. Review the import relationship",
                "2. Consider refactoring to follow architecture rules",
            ]

    def format_batch_for_agent(
        self,
        contexts: list[ViolationContext],
        project_stats: dict,
    ) -> str:
        """Format multiple violations as a batch report.

        Args:
            contexts: List of violation contexts
            project_stats: Dictionary with project statistics

        Returns:
            Formatted batch report string
        """
        lines = []

        # Header
        lines.append("=" * 70)
        lines.append("ARCHITECTURE_VIOLATION_REPORT")
        lines.append("=" * 70)
        lines.append("")

        # Summary
        lines.append("Summary:")
        lines.append(f"  Total modules analyzed: {project_stats.get('total_modules', 0)}")
        lines.append(f"  Total violations: {project_stats.get('total_violations', 0)}")
        lines.append("")

        # Violation types breakdown
        violation_types = project_stats.get("violation_types", {})
        if violation_types:
            lines.append("Violations by Category:")
            for vtype, count in violation_types.items():
                lines.append(f"  - {vtype}: {count}")
            lines.append("")

        if not contexts:
            lines.append("No violations found. Architecture is compliant.")
            lines.append("")
            lines.append("=" * 70)
            return "\n".join(lines)

        # Individual violations
        lines.append(f"Found {len(contexts)} violation(s):")
        lines.append("")

        for i, context in enumerate(contexts, 1):
            lines.append(f"--- Violation #{i} ---")
            lines.append("")
            lines.append(self.format_for_agent(context))
            lines.append("")

        # Footer
        lines.append("=" * 70)
        lines.append("END OF REPORT")
        lines.append("=" * 70)

        return "\n".join(lines)

    def _categorize_violation(self, context: ViolationContext) -> str:
        """Categorize the violation type.

        Args:
            context: The violation context

        Returns:
            Category string: "backward_dependency", "provider_misuse", or "unknown"
        """
        importer = context.layer_importer.lower()
        imported = context.layer_imported.lower()
        message = context.violation.message.lower()

        # Check for provider-related violations
        if "provider" in message or importer == "providers" or imported == "providers":
            return "provider_misuse"

        # Check for backward dependency (lower layer importing from higher layer)
        # Common layer names in order: types(0) < config(1) < repo(2) < service(3) < runtime(4) < ui(5)
        layer_order = {
            "types": 0,
            "config": 1,
            "repo": 2,
            "repository": 2,
            "service": 3,
            "services": 3,
            "runtime": 4,
            "ui": 5,
            "interface": 5,
        }

        importer_idx = layer_order.get(importer, -1)
        imported_idx = layer_order.get(imported, -1)

        # If importer has lower index than imported, it's a backward dependency
        if importer_idx >= 0 and imported_idx >= 0 and importer_idx < imported_idx:
            return "backward_dependency"

        # Check message content for clues
        if "cannot import from layer" in message or "layer" in message:
            if importer_idx >= 0 and imported_idx >= 0:
                return "backward_dependency"

        return "unknown"
