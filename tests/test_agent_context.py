"""Tests for agent context formatter.

This module tests the AgentContextFormatter which formats violations
for LLM consumption with structured output and remediation steps.
"""

from __future__ import annotations

import pytest

from harness_linter.agent_context import AgentContextFormatter, ViolationContext
from harness_linter.contracts.base import Violation


class TestAgentContextFormatter:
    """Test cases for AgentContextFormatter."""

    def test_format_for_agent_backward_dependency(self) -> None:
        """Test basic formatting for backward dependency violation."""
        formatter = AgentContextFormatter()
        violation = Violation(
            importer="myproject.types",
            imported="myproject.service",
            message="Layer 'types' (index 0) cannot import from layer 'service' (index 3).",
        )
        context = ViolationContext(
            violation=violation,
            layer_importer="types",
            layer_imported="service",
            severity="error",
            architectural_principle="Dependencies flow forward through layers",
            suggested_fix="Move shared code to types or config layer",
        )

        result = formatter.format_for_agent(context)

        # Verify structure
        assert "ARCHITECTURE_VIOLATION" in result
        assert "backward_dependency" in result
        assert "error" in result
        assert "myproject.types" in result
        assert "myproject.service" in result
        assert "Dependencies flow forward through layers" in result
        assert "Move shared code to types or config layer" in result
        assert "Remediation Steps:" in result

    def test_format_for_agent_provider_misuse(self) -> None:
        """Test formatting for provider misuse violation."""
        formatter = AgentContextFormatter()
        violation = Violation(
            importer="myproject.types",
            imported="myproject.providers.cache",
            message="Layer 'types' is not allowed to import from provider 'cache'.",
        )
        context = ViolationContext(
            violation=violation,
            layer_importer="types",
            layer_imported="providers",
            severity="warning",
            architectural_principle="Providers should only be used by specific layers",
            suggested_fix="Check if layer really needs this provider",
        )

        result = formatter.format_for_agent(context)

        assert "ARCHITECTURE_VIOLATION" in result
        assert "provider_misuse" in result
        assert "warning" in result
        assert "Providers should only be used by specific layers" in result

    def test_format_with_code_example(self) -> None:
        """Test formatting includes code example when provided."""
        formatter = AgentContextFormatter()
        violation = Violation(
            importer="myproject.types",
            imported="myproject.service",
            message="Layer violation detected",
        )
        code_example = """
# Before (incorrect):
from myproject.service import UserService

# After (correct):
from myproject.types import UserProtocol
"""
        context = ViolationContext(
            violation=violation,
            layer_importer="types",
            layer_imported="service",
            severity="error",
            architectural_principle="Dependencies flow forward",
            suggested_fix="Extract interface to types layer",
            code_example=code_example,
        )

        result = formatter.format_for_agent(context)

        assert "Code Example:" in result
        assert "from myproject.service import UserService" in result
        assert "from myproject.types import UserProtocol" in result

    def test_format_with_documentation_link(self) -> None:
        """Test formatting includes documentation link when provided."""
        formatter = AgentContextFormatter()
        violation = Violation(
            importer="myproject.types",
            imported="myproject.service",
            message="Layer violation detected",
        )
        context = ViolationContext(
            violation=violation,
            layer_importer="types",
            layer_imported="service",
            severity="error",
            architectural_principle="Dependencies flow forward",
            suggested_fix="Extract interface",
            documentation_link="https://docs.example.com/architecture/layers",
        )

        result = formatter.format_for_agent(context)

        assert "Documentation:" in result
        assert "https://docs.example.com/architecture/layers" in result


class TestRemediationSteps:
    """Test cases for remediation steps generation."""

    def test_remediation_steps_backward_dependency(self) -> None:
        """Test backward dependency remediation steps."""
        formatter = AgentContextFormatter()

        steps = formatter.get_remediation_steps(
            violation_type="backward_dependency",
            importer_layer="types",
            target_layer="service",
        )

        assert len(steps) == 5
        assert "Identify what 'types' needs from 'service'" in steps[0]
        assert "Define an interface in a lower layer" in steps[1]
        assert "Move shared types to the lower layer" in steps[2]
        assert "Use dependency injection" in steps[3]
        assert "Ensure correct dependency direction" in steps[4]

    def test_remediation_steps_provider_misuse(self) -> None:
        """Test provider misuse remediation steps."""
        formatter = AgentContextFormatter()

        steps = formatter.get_remediation_steps(
            violation_type="provider_misuse",
            importer_layer="types",
            target_layer="providers",
        )

        assert len(steps) == 3
        assert "Check if layer really needs this provider" in steps[0]
        assert "add to allowed_layers" in steps[1]
        assert "refactor to avoid dependency" in steps[2]

    def test_remediation_steps_unknown_type(self) -> None:
        """Test handling of unknown violation type."""
        formatter = AgentContextFormatter()

        steps = formatter.get_remediation_steps(
            violation_type="unknown_type",
            importer_layer="types",
            target_layer="service",
        )

        assert len(steps) == 2
        assert "Review the import relationship" in steps[0]
        assert "Consider refactoring" in steps[1]


class TestBatchFormatting:
    """Test cases for batch violation formatting."""

    def test_batch_formatting(self) -> None:
        """Test formatting multiple violations as a batch."""
        formatter = AgentContextFormatter()

        violations = [
            ViolationContext(
                violation=Violation(
                    importer="myproject.types",
                    imported="myproject.service",
                    message="Layer violation",
                ),
                layer_importer="types",
                layer_imported="service",
                severity="error",
                architectural_principle="Dependencies flow forward",
                suggested_fix="Extract interface",
            ),
            ViolationContext(
                violation=Violation(
                    importer="myproject.config",
                    imported="myproject.runtime",
                    message="Layer violation",
                ),
                layer_importer="config",
                layer_imported="runtime",
                severity="error",
                architectural_principle="Dependencies flow forward",
                suggested_fix="Move to service layer",
            ),
        ]

        project_stats = {
            "total_modules": 50,
            "total_violations": 2,
            "violation_types": {"backward_dependency": 2},
        }

        result = formatter.format_batch_for_agent(violations, project_stats)

        assert "ARCHITECTURE_VIOLATION_REPORT" in result
        assert "Summary:" in result
        assert "Total modules analyzed: 50" in result
        assert "Total violations: 2" in result
        assert "Violation #1" in result
        assert "Violation #2" in result
        assert "backward_dependency" in result

    def test_batch_formatting_empty(self) -> None:
        """Test batch formatting with no violations."""
        formatter = AgentContextFormatter()

        project_stats = {
            "total_modules": 50,
            "total_violations": 0,
            "violation_types": {},
        }

        result = formatter.format_batch_for_agent([], project_stats)

        assert "ARCHITECTURE_VIOLATION_REPORT" in result
        assert "No violations found" in result

    def test_batch_formatting_with_categorization(self) -> None:
        """Test that batch formatting categorizes violations correctly."""
        formatter = AgentContextFormatter()

        violations = [
            ViolationContext(
                violation=Violation(
                    importer="myproject.types",
                    imported="myproject.service",
                    message="Layer violation",
                ),
                layer_importer="types",
                layer_imported="service",
                severity="error",
                architectural_principle="Dependencies flow forward",
                suggested_fix="Extract interface",
            ),
            ViolationContext(
                violation=Violation(
                    importer="myproject.providers.cache",
                    imported="myproject.service",
                    message="Provider imports from business logic",
                ),
                layer_importer="providers",
                layer_imported="service",
                severity="error",
                architectural_principle="Providers should not depend on business logic",
                suggested_fix="Refactor provider",
            ),
        ]

        project_stats = {
            "total_modules": 50,
            "total_violations": 2,
            "violation_types": {"backward_dependency": 1, "provider_misuse": 1},
        }

        result = formatter.format_batch_for_agent(violations, project_stats)

        # Should show categorization
        assert "by Category:" in result or "Categories:" in result


class TestViolationCategorization:
    """Test cases for violation categorization."""

    def test_categorize_backward_dependency(self) -> None:
        """Test categorization of backward dependency."""
        formatter = AgentContextFormatter()
        context = ViolationContext(
            violation=Violation(
                importer="myproject.types",
                imported="myproject.service",
                message="Layer violation",
            ),
            layer_importer="types",
            layer_imported="service",
            severity="error",
            architectural_principle="Dependencies flow forward",
            suggested_fix="Extract interface",
        )

        category = formatter._categorize_violation(context)

        assert category == "backward_dependency"

    def test_categorize_provider_misuse(self) -> None:
        """Test categorization of provider misuse."""
        formatter = AgentContextFormatter()
        context = ViolationContext(
            violation=Violation(
                importer="myproject.types",
                imported="myproject.providers.cache",
                message="Provider not allowed",
            ),
            layer_importer="types",
            layer_imported="providers",
            severity="warning",
            architectural_principle="Providers have restricted access",
            suggested_fix="Check provider usage",
        )

        category = formatter._categorize_violation(context)

        assert category == "provider_misuse"

    def test_categorize_provider_to_layer(self) -> None:
        """Test categorization of provider importing from layer."""
        formatter = AgentContextFormatter()
        context = ViolationContext(
            violation=Violation(
                importer="myproject.providers.cache",
                imported="myproject.service",
                message="Provider imports from business logic",
            ),
            layer_importer="providers",
            layer_imported="service",
            severity="error",
            architectural_principle="Providers should not depend on business logic",
            suggested_fix="Refactor provider",
        )

        category = formatter._categorize_violation(context)

        assert category == "provider_misuse"

    def test_categorize_unknown(self) -> None:
        """Test categorization of unknown violation."""
        formatter = AgentContextFormatter()
        context = ViolationContext(
            violation=Violation(
                importer="myproject.utils",
                imported="myproject.other",
                message="Some other violation",
            ),
            layer_importer="utils",
            layer_imported="other",
            severity="error",
            architectural_principle="Some principle",
            suggested_fix="Some fix",
        )

        category = formatter._categorize_violation(context)

        assert category == "unknown"
