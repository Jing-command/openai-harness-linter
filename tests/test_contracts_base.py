"""Tests for the contracts base module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from harness_linter.contracts.base import Contract, ContractResult, Violation

if TYPE_CHECKING:
    from grimp import ImportGraph


class TestViolation:
    """Tests for the Violation class."""

    def test_violation_creation(self) -> None:
        """Test basic violation creation."""
        violation = Violation(
            importer="myproject.service.users",
            imported="myproject.ui.components",
            message="Service cannot import from UI",
        )
        assert violation.importer == "myproject.service.users"
        assert violation.imported == "myproject.ui.components"
        assert violation.message == "Service cannot import from UI"
        assert violation.line_number is None

    def test_violation_with_line_number(self) -> None:
        """Test violation creation with line number."""
        violation = Violation(
            importer="myproject.service.users",
            imported="myproject.ui.components",
            message="Service cannot import from UI",
            line_number=42,
        )
        assert violation.line_number == 42

    def test_violation_str_without_line(self) -> None:
        """Test string representation without line number."""
        violation = Violation(
            importer="myproject.service.users",
            imported="myproject.ui.components",
            message="Service cannot import from UI",
        )
        str_repr = str(violation)
        assert "myproject.service.users" in str_repr
        assert "myproject.ui.components" in str_repr
        assert "Service cannot import from UI" in str_repr

    def test_violation_str_with_line(self) -> None:
        """Test string representation with line number."""
        violation = Violation(
            importer="myproject.service.users",
            imported="myproject.ui.components",
            message="Service cannot import from UI",
            line_number=42,
        )
        str_repr = str(violation)
        assert ":42" in str_repr

    def test_violation_is_frozen(self) -> None:
        """Test that violations are immutable."""
        violation = Violation(
            importer="myproject.service.users",
            imported="myproject.ui.components",
            message="Service cannot import from UI",
        )
        with pytest.raises(AttributeError):
            violation.importer = "other"  # type: ignore[misc]


class TestContractResult:
    """Tests for the ContractResult class."""

    def test_result_creation_valid(self) -> None:
        """Test creating a valid result."""
        result = ContractResult(contract_name="Test Contract", is_valid=True)
        assert result.contract_name == "Test Contract"
        assert result.is_valid is True
        assert result.violations == []

    def test_result_creation_invalid(self) -> None:
        """Test creating an invalid result with violations."""
        violation = Violation(
            importer="a",
            imported="b",
            message="test",
        )
        result = ContractResult(
            contract_name="Test Contract",
            is_valid=False,
            violations=[violation],
        )
        assert result.is_valid is False
        assert len(result.violations) == 1

    def test_add_violation(self) -> None:
        """Test adding a violation updates is_valid."""
        result = ContractResult(contract_name="Test Contract", is_valid=True)
        violation = Violation(
            importer="a",
            imported="b",
            message="test",
        )
        result.add_violation(violation)
        assert result.is_valid is False
        assert len(result.violations) == 1
        assert result.violations[0] == violation

    def test_add_multiple_violations(self) -> None:
        """Test adding multiple violations."""
        result = ContractResult(contract_name="Test Contract", is_valid=True)
        violation1 = Violation(importer="a", imported="b", message="test1")
        violation2 = Violation(importer="c", imported="d", message="test2")

        result.add_violation(violation1)
        result.add_violation(violation2)

        assert result.is_valid is False
        assert len(result.violations) == 2


class TestContract:
    """Tests for the Contract abstract base class."""

    def test_contract_is_abstract(self) -> None:
        """Test that Contract cannot be instantiated directly."""

        class IncompleteContract(Contract):
            pass

        with pytest.raises(TypeError):
            IncompleteContract()  # type: ignore[abstract]

    def test_contract_name_property(self) -> None:
        """Test that name property must be implemented."""

        class NoNameContract(Contract):
            def check(self, graph: ImportGraph) -> ContractResult:
                return ContractResult("test", True)

        with pytest.raises(TypeError):
            NoNameContract()  # type: ignore[abstract]

    def test_contract_check_method(self) -> None:
        """Test that check method must be implemented."""

        class NoCheckContract(Contract):
            @property
            def name(self) -> str:
                return "No Check"

        with pytest.raises(TypeError):
            NoCheckContract()  # type: ignore[abstract]

    def test_complete_contract(self) -> None:
        """Test a complete contract implementation."""

        class TestContract(Contract):
            @property
            def name(self) -> str:
                return "Test Contract"

            def check(self, graph: ImportGraph) -> ContractResult:
                return ContractResult(self.name, True)

        contract = TestContract()
        assert contract.name == "Test Contract"
        assert str(contract) == "Test Contract"
