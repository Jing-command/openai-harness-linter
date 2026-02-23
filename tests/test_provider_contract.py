"""Tests for the provider contract module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from harness_linter.contracts.provider_contract import ProviderContract
from harness_linter.layers import Layer, LayerRegistry
from harness_linter.providers import Provider, ProviderRegistry


class TestProviderContract:
    """Tests for the ProviderContract class."""

    @pytest.fixture
    def layer_registry(self) -> LayerRegistry:
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
    def provider_registry(self) -> ProviderRegistry:
        """Create a ProviderRegistry with test providers."""
        registry = ProviderRegistry()
        registry.register(
            Provider(
                name="logging",
                modules=("myproject.providers.logging",),
                allowed_layers=("service", "runtime", "ui"),
            )
        )
        registry.register(
            Provider(
                name="metrics",
                modules=("myproject.providers.metrics",),
                allowed_layers=(),  # No restrictions
            )
        )
        return registry

    @pytest.fixture
    def graph(self) -> MagicMock:
        """Create a mock ImportGraph."""
        return MagicMock()

    def test_contract_name(
        self, layer_registry: LayerRegistry, provider_registry: ProviderRegistry
    ) -> None:
        """Test contract name property."""
        contract = ProviderContract(layer_registry, provider_registry)
        assert contract.name == "Provider Usage Contract"

    def test_allowed_layer_can_import_provider(
        self,
        layer_registry: LayerRegistry,
        provider_registry: ProviderRegistry,
        graph: MagicMock,
    ) -> None:
        """Test that allowed layers can import from providers."""
        # Service is allowed to import logging
        graph.modules = {"myproject.service.users"}
        graph.find_modules_directly_imported_by.return_value = {
            "myproject.providers.logging"
        }

        contract = ProviderContract(layer_registry, provider_registry)
        result = contract.check(graph)

        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_disallowed_layer_cannot_import_provider(
        self,
        layer_registry: LayerRegistry,
        provider_registry: ProviderRegistry,
        graph: MagicMock,
    ) -> None:
        """Test that disallowed layers cannot import from providers."""
        # Types is not allowed to import logging
        graph.modules = {"myproject.types.models"}
        graph.find_modules_directly_imported_by.return_value = {
            "myproject.providers.logging"
        }

        contract = ProviderContract(layer_registry, provider_registry)
        result = contract.check(graph)

        assert result.is_valid is False
        assert len(result.violations) == 1
        violation = result.violations[0]
        assert violation.importer == "myproject.types.models"
        assert violation.imported == "myproject.providers.logging"
        assert "not allowed" in violation.message.lower()

    def test_provider_with_no_restrictions(
        self,
        layer_registry: LayerRegistry,
        provider_registry: ProviderRegistry,
        graph: MagicMock,
    ) -> None:
        """Test that providers with no restrictions can be imported by any layer."""
        # Any layer can import metrics (no restrictions)
        graph.modules = {"myproject.types.models"}
        graph.find_modules_directly_imported_by.return_value = {
            "myproject.providers.metrics"
        }

        contract = ProviderContract(layer_registry, provider_registry)
        result = contract.check(graph)

        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_provider_importing_from_business_logic_violation(
        self,
        layer_registry: LayerRegistry,
        provider_registry: ProviderRegistry,
        graph: MagicMock,
    ) -> None:
        """Test that providers importing from business logic layers is a violation."""
        # Logging provider importing from service layer
        graph.modules = {"myproject.providers.logging.handler"}
        graph.find_modules_directly_imported_by.return_value = {
            "myproject.service.users"
        }

        contract = ProviderContract(layer_registry, provider_registry)
        result = contract.check(graph)

        assert result.is_valid is False
        assert len(result.violations) == 1
        violation = result.violations[0]
        assert violation.importer == "myproject.providers.logging.handler"
        assert violation.imported == "myproject.service.users"
        assert "business logic" in violation.message.lower()

    def test_provider_importing_from_types_allowed(
        self,
        layer_registry: LayerRegistry,
        provider_registry: ProviderRegistry,
        graph: MagicMock,
    ) -> None:
        """Test that providers can import from types layer."""
        # Logging provider importing from types layer is OK
        graph.modules = {"myproject.providers.logging.handler"}
        graph.find_modules_directly_imported_by.return_value = {
            "myproject.types.models"
        }

        contract = ProviderContract(layer_registry, provider_registry)
        result = contract.check(graph)

        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_module_not_in_layer_or_provider(
        self,
        layer_registry: LayerRegistry,
        provider_registry: ProviderRegistry,
        graph: MagicMock,
    ) -> None:
        """Test that modules not in layers or providers cannot import providers."""
        graph.modules = {"myproject.unknown.module"}
        graph.find_modules_directly_imported_by.return_value = {
            "myproject.providers.logging"
        }

        contract = ProviderContract(layer_registry, provider_registry)
        result = contract.check(graph)

        assert result.is_valid is False
        assert len(result.violations) == 1
        violation = result.violations[0]
        assert "not in any layer" in violation.message.lower()

    def test_provider_importing_from_another_provider(
        self,
        layer_registry: LayerRegistry,
        provider_registry: ProviderRegistry,
        graph: MagicMock,
    ) -> None:
        """Test that providers can import from other providers."""
        # Add another provider
        provider_registry.register(
            Provider(
                name="http",
                modules=("myproject.providers.http",),
            )
        )

        graph.modules = {"myproject.providers.logging.handler"}
        graph.find_modules_directly_imported_by.return_value = {
            "myproject.providers.http.client"
        }

        contract = ProviderContract(layer_registry, provider_registry)
        result = contract.check(graph)

        # This should be valid - providers can import from providers
        assert result.is_valid is True
        assert len(result.violations) == 0

    def test_multiple_violations(
        self,
        layer_registry: LayerRegistry,
        provider_registry: ProviderRegistry,
        graph: MagicMock,
    ) -> None:
        """Test detecting multiple violations."""
        graph.modules = {
            "myproject.types.models",  # Will try to import logging
            "myproject.providers.logging.handler",  # Will try to import from service
        }

        def get_imports(module: str) -> set[str]:
            if module == "myproject.types.models":
                return {"myproject.providers.logging"}  # Violation
            elif module == "myproject.providers.logging.handler":
                return {"myproject.service.users"}  # Violation
            return set()

        graph.find_modules_directly_imported_by.side_effect = get_imports

        contract = ProviderContract(layer_registry, provider_registry)
        result = contract.check(graph)

        assert result.is_valid is False
        assert len(result.violations) == 2
