"""Base classes for architecture contracts.

This module provides the foundation for all architectural contracts in the
harness_linter system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grimp import ImportGraph


@dataclass(frozen=True)
class Violation:
    """Represents a single contract violation.

    A violation occurs when an import relationship breaks an architectural rule.

    Attributes:
        importer: The module that is importing (the one breaking the rule)
        imported: The module being imported (the one that shouldn't be imported)
        message: Human-readable description of the violation
        line_number: Optional line number where the import occurs
    """

    importer: str
    imported: str
    message: str
    line_number: int | None = None

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        if self.line_number:
            return f"{self.importer}:{self.line_number} imports {self.imported} - {self.message}"
        return f"{self.importer} imports {self.imported} - {self.message}"


@dataclass
class ContractResult:
    """Result of checking a contract against an import graph.

    Attributes:
        contract_name: Name of the contract that was checked
        is_valid: True if no violations were found
        violations: List of violations found
    """

    contract_name: str
    is_valid: bool
    violations: list[Violation] = field(default_factory=list)

    def add_violation(self, violation: Violation) -> None:
        """Add a violation to this result.

        Args:
            violation: The violation to add
        """
        self.violations.append(violation)
        self.is_valid = False


class Contract(ABC):
    """Abstract base class for all architectural contracts.

    A contract defines a rule about what imports are allowed or forbidden
    in the codebase. Contracts are checked against an import graph to
    detect violations.

    Example:
        class MyContract(Contract):
            @property
            def name(self) -> str:
                return "My Contract"

            def check(self, graph: ImportGraph) -> ContractResult:
                # Check logic here
                pass
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the contract name."""
        ...

    @abstractmethod
    def check(self, graph: ImportGraph) -> ContractResult:
        """Check this contract against an import graph.

        Args:
            graph: The import graph to check

        Returns:
            ContractResult containing any violations found
        """
        ...

    def __str__(self) -> str:
        """Return the contract name."""
        return self.name
