"""Layer contract implementation for harness_linter.

This module provides the LayerContract which enforces that layers can only
import from layers at their level or below in the hierarchy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from harness_linter.contracts.base import Contract, ContractResult, Violation
from harness_linter.layers import LayerRegistry

if TYPE_CHECKING:
    from grimp import ImportGraph


class LayerContract(Contract):
    """Contract enforcing layer dependency rules.

    In the Harness architecture, layers form a strict hierarchy:
    Types -> Config -> Repo -> Service -> Runtime -> UI

    Each layer can only import from:
    1. Its own layer
    2. Layers below it in the hierarchy (lower index)

    Attributes:
        registry: LayerRegistry containing layer definitions
    """

    def __init__(self, registry: LayerRegistry) -> None:
        """Initialize the layer contract.

        Args:
            registry: LayerRegistry with layer definitions
        """
        self.registry = registry

    @property
    def name(self) -> str:
        """Return the contract name."""
        return "Layer Dependency Contract"

    def check(self, graph: ImportGraph) -> ContractResult:
        """Check that layer dependencies follow the hierarchy rules.

        Args:
            graph: The import graph to check

        Returns:
            ContractResult containing any violations found
        """
        result = ContractResult(contract_name=self.name, is_valid=True)

        # Get all modules in the graph
        modules = graph.modules

        for importer_module in modules:
            # Find which layer the importing module belongs to
            importer_layer = self.registry.get_layer_for_module(importer_module)
            if importer_layer is None:
                continue  # Module not in any layer, skip

            # Get all direct imports of this module
            imported_modules = graph.find_modules_directly_imported_by(importer_module)

            for imported_module in imported_modules:
                # Find which layer the imported module belongs to
                imported_layer = self.registry.get_layer_for_module(imported_module)
                if imported_layer is None:
                    continue  # Module not in any layer, skip

                # Check if the import is allowed
                if not importer_layer.can_import_from(imported_layer):
                    violation = Violation(
                        importer=importer_module,
                        imported=imported_module,
                        message=(
                            f"Layer '{importer_layer.name}' (index {importer_layer.index}) "
                            f"cannot import from layer '{imported_layer.name}' "
                            f"(index {imported_layer.index}). "
                            f"Layers can only import from lower or equal indices."
                        ),
                    )
                    result.add_violation(violation)

        return result
