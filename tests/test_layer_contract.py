"""Tests for the layer contract module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from harness_linter.contracts.layer_contract import LayerContract
from harness_linter.layers import Layer, LayerRegistry


class TestLayerContract:
    """Tests for the LayerContract class."""

    @pytest.fixture
    def registry(self) -> LayerRegistry:
        """Create a LayerRegistry with standard layers."""
        registry = LayerRegistry()
        registry.register(Layer("types", 0, modules=("myproject.types",)))
        registry.register(Layer("config", 1, modules=("myproject.config",)))
        registry.register(Layer("repo", 2, modules=("myproject.repo",)))
        registry.register(Layer("service", 3, modules=("myproject.service",)))
        registry.register(Layer("runtime", 4, modules=("myproject.runtime",)))
        registry.register(Layer("ui", 5, modules=("myproject.ui",)))
        return registry

    @pytest.fixture
    def graph(self) -> MagicMock:
        """Create a mock ImportGraph."""
        return MagicMock()

    def test_contract_name(self, registry: LayerRegistry) -> None:
        """Test contract name property."""
        contract = LayerContract(registry)
        assert contract.name == "Layer Dependency Contract"

    def test_valid_import_lower_to_higher(
        self, registry: LayerRegistry, graph: MagicMock
    ) -> None:
        """Test that importing from lower to higher layer is valid."""
        # Service (3) imports from Types (0) - valid
        graph.modules = {"myproject.service.users"}
        graph.find_modules_directly_imported_by.return_value = {"myproject.types.models"}

        contract = LayerContract(registry)
        result = contract.check(graph)

        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_valid_import_same_layer(
        self, registry: LayerRegistry, graph: MagicMock
    ) -> None:
        """Test that importing within the same layer is valid."""
        # Service module imports from another Service module - valid
        graph.modules = {"myproject.service.users"}
        graph.find_modules_directly_imported_by.return_value = {"myproject.service.orders"}

        contract = LayerContract(registry)
        result = contract.check(graph)

        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_invalid_import_higher_to_lower(
        self, registry: LayerRegistry, graph: MagicMock
    ) -> None:
        """Test that importing from higher to lower layer is invalid."""
        # Types (0) imports from Service (3) - invalid
        graph.modules = {"myproject.types.models"}
        graph.find_modules_directly_imported_by.return_value = {"myproject.service.users"}

        contract = LayerContract(registry)
        result = contract.check(graph)

        assert result.is_valid is False
        assert len(result.violations) == 1
        violation = result.violations[0]
        assert violation.importer == "myproject.types.models"
        assert violation.imported == "myproject.service.users"
        assert "cannot import" in violation.message.lower()
        assert "types" in violation.message
        assert "service" in violation.message

    def test_invalid_import_types_to_ui(
        self, registry: LayerRegistry, graph: MagicMock
    ) -> None:
        """Test that Types importing from UI is invalid."""
        # Types (0) imports from UI (5) - invalid
        graph.modules = {"myproject.types.models"}
        graph.find_modules_directly_imported_by.return_value = {"myproject.ui.components"}

        contract = LayerContract(registry)
        result = contract.check(graph)

        assert result.is_valid is False
        assert len(result.violations) == 1

    def test_module_not_in_layer(self, registry: LayerRegistry, graph: MagicMock) -> None:
        """Test that modules not in any layer are skipped."""
        graph.modules = {"myproject.unknown.module"}
        graph.find_modules_directly_imported_by.return_value = {"myproject.types.models"}

        contract = LayerContract(registry)
        result = contract.check(graph)

        # No violations because the importer is not in a layer
        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_imported_not_in_layer(self, registry: LayerRegistry, graph: MagicMock) -> None:
        """Test that imports from modules not in any layer are allowed."""
        graph.modules = {"myproject.service.users"}
        graph.find_modules_directly_imported_by.return_value = {"myproject.unknown.module"}

        contract = LayerContract(registry)
        result = contract.check(graph)

        # No violations because the imported module is not in a layer
        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_multiple_violations(self, registry: LayerRegistry, graph: MagicMock) -> None:
        """Test detecting multiple violations."""
        graph.modules = {"myproject.types.models", "myproject.config.settings"}

        def get_imports(module: str) -> set[str]:
            if module == "myproject.types.models":
                return {"myproject.service.users"}  # Violation
            elif module == "myproject.config.settings":
                return {"myproject.ui.components"}  # Violation
            return set()

        graph.find_modules_directly_imported_by.side_effect = get_imports

        contract = LayerContract(registry)
        result = contract.check(graph)

        assert result.is_valid is False
        assert len(result.violations) == 2

    def test_violation_message_content(
        self, registry: LayerRegistry, graph: MagicMock
    ) -> None:
        """Test that violation messages contain useful information."""
        graph.modules = {"myproject.types.models"}
        graph.find_modules_directly_imported_by.return_value = {"myproject.service.users"}

        contract = LayerContract(registry)
        result = contract.check(graph)

        violation = result.violations[0]
        assert "types" in violation.message
        assert "service" in violation.message
        assert "0" in violation.message  # types index
        assert "3" in violation.message  # service index
