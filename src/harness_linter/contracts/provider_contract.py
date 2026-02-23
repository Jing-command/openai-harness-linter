"""Provider contract implementation for harness_linter.

This module provides the ProviderContract which enforces that:
1. Only modules in allowed layers can import from providers
2. Providers cannot import from business logic layers (to avoid circular dependencies)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from harness_linter.contracts.base import Contract, ContractResult, Violation
from harness_linter.layers import LayerRegistry
from harness_linter.providers import ProviderRegistry

if TYPE_CHECKING:
    from grimp import ImportGraph


class ProviderContract(Contract):
    """Contract enforcing provider usage rules.

    Providers are the unified entry point for cross-cutting concerns.
    This contract ensures:
    1. Providers can only be imported by explicitly allowed layers
    2. Providers cannot import from business logic layers (repo, service, etc.)

    Attributes:
        layer_registry: LayerRegistry containing layer definitions
        provider_registry: ProviderRegistry containing provider definitions
    """

    def __init__(
        self,
        layer_registry: LayerRegistry,
        provider_registry: ProviderRegistry,
    ) -> None:
        """Initialize the provider contract.

        Args:
            layer_registry: LayerRegistry with layer definitions
            provider_registry: ProviderRegistry with provider definitions
        """
        self.layer_registry = layer_registry
        self.provider_registry = provider_registry

    @property
    def name(self) -> str:
        """Return the contract name."""
        return "Provider Usage Contract"

    def check(self, graph: ImportGraph) -> ContractResult:
        """Check that provider usage follows the architecture rules.

        Args:
            graph: The import graph to check

        Returns:
            ContractResult containing any violations found
        """
        result = ContractResult(contract_name=self.name, is_valid=True)

        # Get all modules in the graph
        modules = graph.modules

        for importer_module in modules:
            # Get all direct imports of this module
            imported_modules = graph.find_modules_directly_imported_by(importer_module)

            for imported_module in imported_modules:
                # Check if the imported module is a provider
                provider = self.provider_registry.get_provider_for_module(imported_module)
                if provider is not None:
                    # This is a provider import - check if allowed
                    self._check_provider_import(
                        importer_module, imported_module, provider, result
                    )

                # Check if the importer is a provider
                importer_provider = self.provider_registry.get_provider_for_module(
                    importer_module
                )
                if importer_provider is not None:
                    # This is a provider doing the importing - check restrictions
                    self._check_provider_to_layer_import(
                        importer_module, imported_module, result
                    )

        return result

    def _check_provider_import(
        self,
        importer_module: str,
        imported_module: str,
        provider: "Provider",
        result: ContractResult,
    ) -> None:
        """Check if a layer is allowed to import from a provider.

        Args:
            importer_module: The module importing from the provider
            imported_module: The provider module being imported
            provider: The provider being imported
            result: ContractResult to add violations to
        """
        # Find which layer the importer belongs to
        importer_layer = self.layer_registry.get_layer_for_module(importer_module)

        if importer_layer is None:
            # Module not in any layer - check if it's a provider
            if not self.provider_registry.is_provider_module(importer_module):
                # Neither in a layer nor a provider - violation
                violation = Violation(
                    importer=importer_module,
                    imported=imported_module,
                    message=(
                        f"Module '{importer_module}' is not in any layer "
                        f"and cannot import from provider '{provider.name}'"
                    ),
                )
                result.add_violation(violation)
            return

        # Check if the layer is allowed to import this provider
        if not provider.can_be_imported_by(importer_layer.name):
            violation = Violation(
                importer=importer_module,
                imported=imported_module,
                message=(
                    f"Layer '{importer_layer.name}' is not allowed to import "
                    f"from provider '{provider.name}'. "
                    f"Allowed layers: {list(provider.allowed_layers)}"
                ),
            )
            result.add_violation(violation)

    def _check_provider_to_layer_import(
        self,
        importer_module: str,
        imported_module: str,
        result: ContractResult,
    ) -> None:
        """Check if a provider is importing from a business logic layer.

        Providers should not import from business logic layers to avoid
        circular dependencies.

        Args:
            importer_module: The provider module doing the importing
            imported_module: The module being imported
            result: ContractResult to add violations to
        """
        # Find which layer the imported module belongs to
        imported_layer = self.layer_registry.get_layer_for_module(imported_module)

        if imported_layer is None:
            return  # Not importing from a layer, no violation

        # Providers should not import from business logic layers
        # Business logic layers are those with index >= 2
        # (typically repo, service, runtime, ui)
        if imported_layer.index >= 2:
            violation = Violation(
                importer=importer_module,
                imported=imported_module,
                message=(
                    f"Provider '{importer_module}' imports from business logic "
                    f"layer '{imported_layer.name}'. Providers should not depend "
                    f"on business logic layers to avoid circular dependencies."
                ),
            )
            result.add_violation(violation)
