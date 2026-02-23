"""Provider definition and management system for harness_linter.

Providers are the unified entry point for cross-cutting concerns in the Harness architecture.
All external dependencies and shared utilities must be accessed through providers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True)
class Provider:
    """Represents a provider of cross-cutting functionality.

    Providers are the only modules that can be imported by multiple layers.
    They provide a unified interface for:
    - External library wrappers (logging, metrics, HTTP clients)
    - Shared utilities that don't belong to a specific layer
    - Cross-cutting concerns that would otherwise create circular dependencies

    Attributes:
        name: The provider name (e.g., "logging", "metrics", "http")
        description: Human-readable description of what the provider offers
        modules: Tuple of module path patterns that belong to this provider
        allowed_layers: Tuple of layer names that can import this provider
    """

    name: str
    description: str = ""
    modules: tuple[str, ...] = field(default_factory=tuple)
    allowed_layers: tuple[str, ...] = field(default_factory=tuple)

    def __hash__(self) -> int:
        """Hash based on name for use in dictionaries and sets."""
        return hash(self.name)

    def __eq__(self, other: object) -> bool:
        """Equality based on name."""
        if not isinstance(other, Provider):
            return NotImplemented
        return self.name == other.name

    def contains_module(self, module_path: str) -> bool:
        """Check if a module belongs to this provider.

        Args:
            module_path: The full module path (e.g., "myproject.providers.logging")

        Returns:
            True if the module matches any of the provider's patterns
        """
        for pattern in self.modules:
            if module_path == pattern or module_path.startswith(pattern + "."):
                return True
        return False

    def can_be_imported_by(self, layer_name: str) -> bool:
        """Check if a layer can import from this provider.

        Args:
            layer_name: The name of the layer attempting to import

        Returns:
            True if the layer is allowed to import from this provider
        """
        if not self.allowed_layers:
            return True  # If no restrictions, all layers can import
        return layer_name in self.allowed_layers

    def add_module(self, module_pattern: str) -> Provider:
        """Create a new provider with an additional module pattern.

        Args:
            module_pattern: Glob pattern for module paths

        Returns:
            A new Provider instance with the added module pattern
        """
        return Provider(
            name=self.name,
            description=self.description,
            modules=self.modules + (module_pattern,),
            allowed_layers=self.allowed_layers,
        )

    def allow_layer(self, layer_name: str) -> Provider:
        """Create a new provider that allows an additional layer to import it.

        Args:
            layer_name: The layer name to allow

        Returns:
            A new Provider instance with the added layer permission
        """
        if layer_name in self.allowed_layers:
            return self
        return Provider(
            name=self.name,
            description=self.description,
            modules=self.modules,
            allowed_layers=self.allowed_layers + (layer_name,),
        )


class ProviderRegistry:
    """Registry for managing all providers.

    The ProviderRegistry maintains the collection of providers for a project
    and provides lookup and validation functionality.

    Example:
        >>> registry = ProviderRegistry()
        >>> registry.register(Provider("logging", "Logging utilities"))
        >>> provider = registry.get("logging")
    """

    def __init__(self) -> None:
        """Initialize an empty provider registry."""
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        """Register a provider in the registry.

        Args:
            provider: The provider to register

        Raises:
            ValueError: If a provider with the same name is already registered
        """
        if provider.name in self._providers:
            raise ValueError(f"Provider '{provider.name}' is already registered")
        self._providers[provider.name] = provider

    def get(self, name: str) -> Provider | None:
        """Get a provider by name.

        Args:
            name: The provider name to look up

        Returns:
            The Provider instance if found, None otherwise
        """
        return self._providers.get(name)

    def __getitem__(self, name: str) -> Provider:
        """Get a provider by name using bracket notation.

        Args:
            name: The provider name to look up

        Returns:
            The Provider instance

        Raises:
            KeyError: If the provider is not found
        """
        if name not in self._providers:
            raise KeyError(f"Provider '{name}' not found")
        return self._providers[name]

    def __contains__(self, name: str) -> bool:
        """Check if a provider name is registered.

        Args:
            name: The provider name to check

        Returns:
            True if the provider is registered
        """
        return name in self._providers

    def __iter__(self) -> Iterator[Provider]:
        """Iterate over all registered providers."""
        return iter(self._providers.values())

    def __len__(self) -> int:
        """Return the number of registered providers."""
        return len(self._providers)

    @property
    def names(self) -> list[str]:
        """Get all registered provider names."""
        return list(self._providers.keys())

    def get_provider_for_module(self, module_path: str) -> Provider | None:
        """Determine which provider a module belongs to.

        Args:
            module_path: The full module path (e.g., "myproject.providers.logging")

        Returns:
            The matching Provider, or None if no provider matches
        """
        # Sort by specificity (longest pattern first) to get most specific match
        candidates: list[tuple[Provider, str]] = []

        for provider in self._providers.values():
            for pattern in provider.modules:
                if module_path == pattern or module_path.startswith(pattern + "."):
                    candidates.append((provider, pattern))

        if not candidates:
            return None

        # Return the provider with the most specific (longest) matching pattern
        return max(candidates, key=lambda x: len(x[1]))[0]

    def is_provider_module(self, module_path: str) -> bool:
        """Check if a module path belongs to any registered provider.

        Args:
            module_path: The module path to check

        Returns:
            True if the module belongs to a provider
        """
        return self.get_provider_for_module(module_path) is not None

    def create_standard_providers(self) -> None:
        """Register standard providers commonly used in Harness projects.

        Registers providers for:
        - logging: Logging utilities
        - metrics: Metrics and monitoring
        - http: HTTP client wrappers
        - cache: Caching utilities
        - security: Security utilities
        """
        providers = [
            Provider(
                name="logging",
                description="Logging utilities and configuration",
                modules=(),
            ),
            Provider(
                name="metrics",
                description="Metrics and monitoring utilities",
                modules=(),
            ),
            Provider(
                name="http",
                description="HTTP client wrappers",
                modules=(),
            ),
            Provider(
                name="cache",
                description="Caching utilities",
                modules=(),
            ),
            Provider(
                name="security",
                description="Security utilities and authentication",
                modules=(),
            ),
        ]
        for provider in providers:
            self.register(provider)
