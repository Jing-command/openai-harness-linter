"""Layer definition and management system for harness_linter.

This module provides the Layer and LayerRegistry classes for defining and managing
architectural layers in the Harness pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["Layer", "LayerRegistry"]


@dataclass(frozen=True)
class Layer:
    """Represents an architectural layer.

    Layers define logical groupings of modules with specific responsibilities.
    In the Harness architecture, layers have a strict dependency order:
    Types -> Config -> Repo -> Service -> Runtime -> UI

    Attributes:
        name: The layer name (e.g., "types", "config", "repo")
        index: The layer's position in the dependency hierarchy (lower = more fundamental)
        description: Human-readable description of the layer's purpose
        modules: Tuple of module path patterns that belong to this layer
    """

    name: str
    index: int
    description: str = ""
    modules: tuple[str, ...] = field(default_factory=tuple)

    def __hash__(self) -> int:
        """Hash based on name for use in dictionaries and sets."""
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        """Equality based on name."""
        if not isinstance(other, Layer):
            return NotImplemented
        return self.name == other.name

    def can_import_from(self, other: "Layer") -> bool:
        """Check if this layer can import from another layer.

        In the Harness architecture, layers can only import from layers
        with a lower or equal index (lower layers are more fundamental).

        Args:
            other: The layer to check import permission against

        Returns:
            True if this layer can import from the other layer
        """
        return other.index <= self.index

    def add_module(self, module_pattern: str) -> "Layer":
        """Create a new layer with an additional module pattern.

        Args:
            module_pattern: Glob pattern for module paths (e.g., "myproject.types")

        Returns:
            A new Layer instance with the added module pattern
        """
        return Layer(
            name=self.name,
            index=self.index,
            description=self.description,
            modules=self.modules + (module_pattern,),
        )


class LayerRegistry:
    """Registry for managing all architectural layers.

    The LayerRegistry maintains the collection of layers for a project
    and provides lookup and validation functionality.

    Example:
        >>> registry = LayerRegistry()
        >>> registry.register(Layer("types", 0, "Core type definitions"))
        >>> registry.register(Layer("config", 1, "Configuration"))
        >>> layer = registry.get("types")
    """

    def __init__(self) -> None:
        """Initialize an empty layer registry."""
        self._layers: dict[str, Layer] = {}

    def register(self, layer: Layer) -> None:
        """Register a layer in the registry.

        Args:
            layer: The layer to register

        Raises:
            ValueError: If a layer with the same name is already registered
        """
        if layer.name in self._layers:
            raise ValueError(f"Layer '{layer.name}' is already registered")
        self._layers[layer.name] = layer

    def get(self, name: str) -> Layer | None:
        """Get a layer by name.

        Args:
            name: The layer name to look up

        Returns:
            The Layer instance if found, None otherwise
        """
        return self._layers.get(name)

    def __getitem__(self, name: str) -> Layer:
        """Get a layer by name using bracket notation.

        Args:
            name: The layer name to look up

        Returns:
            The Layer instance

        Raises:
            KeyError: If the layer is not found
        """
        if name not in self._layers:
            raise KeyError(f"Layer '{name}' not found")
        return self._layers[name]

    def __contains__(self, name: str) -> bool:
        """Check if a layer name is registered.

        Args:
            name: The layer name to check

        Returns:
            True if the layer is registered
        """
        return name in self._layers

    def __iter__(self) -> Iterator[Layer]:
        """Iterate over all registered layers in index order."""
        return iter(sorted(self._layers.values(), key=lambda l: l.index))

    def __len__(self) -> int:
        """Return the number of registered layers."""
        return len(self._layers)

    @property
    def names(self) -> list[str]:
        """Get all registered layer names in order."""
        return [layer.name for layer in self]

    def get_layer_for_module(self, module_path: str) -> Layer | None:
        """Determine which layer a module belongs to.

        Args:
            module_path: The full module path (e.g., "myproject.types.models")

        Returns:
            The matching Layer, or None if no layer matches
        """
        # Sort by specificity (longest pattern first) to get most specific match
        candidates: list[tuple[Layer, str]] = []

        for layer in self._layers.values():
            for pattern in layer.modules:
                # Convert glob-like pattern to check
                # Pattern "myproject.types" should match "myproject.types.models"
                if module_path == pattern or module_path.startswith(pattern + "."):
                    candidates.append((layer, pattern))

        if not candidates:
            return None

        # Return the layer with the most specific (longest) matching pattern
        return max(candidates, key=lambda x: len(x[1]))[0]

    def create_standard_harness_layers(self) -> None:
        """Register the standard 6-layer Harness architecture.

        Registers layers in order:
        1. types (index 0) - Core type definitions
        2. config (index 1) - Configuration
        3. repo (index 2) - Data access layer
        4. service (index 3) - Business logic
        5. runtime (index 4) - Runtime/execution
        6. ui (index 5) - User interface
        """
        layers = [
            Layer("types", 0, "Core type definitions and data models"),
            Layer("config", 1, "Configuration management"),
            Layer("repo", 2, "Data access and repository layer"),
            Layer("service", 3, "Business logic and services"),
            Layer("runtime", 4, "Runtime and execution layer"),
            Layer("ui", 5, "User interface layer"),
        ]
        for layer in layers:
            self.register(layer)
