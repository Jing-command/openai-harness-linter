"""Tests for the providers module."""

from __future__ import annotations

import pytest

from harness_linter.providers import Provider, ProviderRegistry


class TestProvider:
    """Tests for the Provider class."""

    def test_provider_creation(self) -> None:
        """Test basic provider creation."""
        provider = Provider(
            name="logging",
            description="Logging utilities",
            modules=("myproject.providers.logging",),
            allowed_layers=("service", "runtime"),
        )
        assert provider.name == "logging"
        assert provider.description == "Logging utilities"
        assert provider.modules == ("myproject.providers.logging",)
        assert provider.allowed_layers == ("service", "runtime")

    def test_provider_default_values(self) -> None:
        """Test provider creation with default values."""
        provider = Provider(name="logging")
        assert provider.description == ""
        assert provider.modules == ()
        assert provider.allowed_layers == ()

    def test_provider_hash_and_equality(self) -> None:
        """Test provider hashing and equality based on name."""
        provider1 = Provider(name="logging", description="Original")
        provider2 = Provider(name="logging", description="Different")
        provider3 = Provider(name="metrics")

        assert provider1 == provider2
        assert hash(provider1) == hash(provider2)
        assert provider1 != provider3
        assert provider1 != "logging"

    def test_contains_module(self) -> None:
        """Test checking if a module belongs to a provider."""
        provider = Provider(
            name="logging",
            modules=("myproject.providers.logging",),
        )

        assert provider.contains_module("myproject.providers.logging")
        assert provider.contains_module("myproject.providers.logging.handlers")
        assert not provider.contains_module("myproject.service.users")

    def test_can_be_imported_by(self) -> None:
        """Test layer import permissions."""
        provider = Provider(
            name="logging",
            allowed_layers=("service", "runtime"),
        )

        assert provider.can_be_imported_by("service")
        assert provider.can_be_imported_by("runtime")
        assert not provider.can_be_imported_by("types")
        assert not provider.can_be_imported_by("ui")

    def test_can_be_imported_by_no_restrictions(self) -> None:
        """Test that empty allowed_layers means all layers can import."""
        provider = Provider(name="logging")

        assert provider.can_be_imported_by("service")
        assert provider.can_be_imported_by("types")
        assert provider.can_be_imported_by("any_layer")

    def test_add_module(self) -> None:
        """Test adding a module pattern to a provider."""
        provider = Provider(
            name="logging",
            modules=("myproject.providers.logging",),
        )
        new_provider = provider.add_module("myproject.providers.log_config")

        # Original unchanged
        assert provider.modules == ("myproject.providers.logging",)
        # New provider has both patterns
        assert new_provider.modules == (
            "myproject.providers.logging",
            "myproject.providers.log_config",
        )

    def test_allow_layer(self) -> None:
        """Test allowing an additional layer to import a provider."""
        provider = Provider(
            name="logging",
            allowed_layers=("service",),
        )
        new_provider = provider.allow_layer("runtime")

        # Original unchanged
        assert provider.allowed_layers == ("service",)
        # New provider has both layers
        assert new_provider.allowed_layers == ("service", "runtime")

    def test_allow_layer_duplicate(self) -> None:
        """Test allowing a layer that's already allowed returns same provider."""
        provider = Provider(
            name="logging",
            allowed_layers=("service",),
        )
        new_provider = provider.allow_layer("service")

        # Same object returned since no change needed
        assert new_provider is provider


class TestProviderRegistry:
    """Tests for the ProviderRegistry class."""

    def test_register_and_get(self) -> None:
        """Test registering and retrieving providers."""
        registry = ProviderRegistry()
        provider = Provider(name="logging")

        registry.register(provider)
        assert registry.get("logging") == provider
        assert registry["logging"] == provider

    def test_get_nonexistent(self) -> None:
        """Test getting a non-existent provider."""
        registry = ProviderRegistry()
        assert registry.get("nonexistent") is None

    def test_getitem_nonexistent(self) -> None:
        """Test bracket access to non-existent provider raises KeyError."""
        registry = ProviderRegistry()
        with pytest.raises(KeyError, match="Provider 'nonexistent' not found"):
            _ = registry["nonexistent"]

    def test_register_duplicate(self) -> None:
        """Test registering a duplicate provider raises ValueError."""
        registry = ProviderRegistry()
        registry.register(Provider(name="logging"))

        with pytest.raises(ValueError, match="Provider 'logging' is already registered"):
            registry.register(Provider(name="logging"))

    def test_contains(self) -> None:
        """Test checking if a provider is registered."""
        registry = ProviderRegistry()
        registry.register(Provider(name="logging"))

        assert "logging" in registry
        assert "nonexistent" not in registry

    def test_iteration(self) -> None:
        """Test iterating over registered providers."""
        registry = ProviderRegistry()
        registry.register(Provider(name="logging"))
        registry.register(Provider(name="metrics"))

        names = {provider.name for provider in registry}
        assert names == {"logging", "metrics"}

    def test_len(self) -> None:
        """Test getting the number of registered providers."""
        registry = ProviderRegistry()
        assert len(registry) == 0

        registry.register(Provider(name="logging"))
        assert len(registry) == 1

        registry.register(Provider(name="metrics"))
        assert len(registry) == 2

    def test_names_property(self) -> None:
        """Test getting provider names."""
        registry = ProviderRegistry()
        registry.register(Provider(name="logging"))
        registry.register(Provider(name="metrics"))

        assert set(registry.names) == {"logging", "metrics"}

    def test_get_provider_for_module(self) -> None:
        """Test finding which provider a module belongs to."""
        registry = ProviderRegistry()
        registry.register(
            Provider(name="logging", modules=("myproject.providers.logging",))
        )
        registry.register(
            Provider(name="metrics", modules=("myproject.providers.metrics",))
        )

        assert (
            registry.get_provider_for_module("myproject.providers.logging.handlers")
            == registry.get("logging")
        )
        assert (
            registry.get_provider_for_module("myproject.providers.metrics")
            == registry.get("metrics")
        )
        assert registry.get_provider_for_module("myproject.service.users") is None

    def test_get_provider_for_module_specificity(self) -> None:
        """Test that most specific pattern wins."""
        registry = ProviderRegistry()
        registry.register(
            Provider(name="logging", modules=("myproject.providers.logging",))
        )
        registry.register(
            Provider(name="special", modules=("myproject.providers.logging.special",))
        )

        # Most specific pattern wins
        result = registry.get_provider_for_module(
            "myproject.providers.logging.special.handler"
        )
        assert result is not None
        assert result.name == "special"

    def test_is_provider_module(self) -> None:
        """Test checking if a module path belongs to any provider."""
        registry = ProviderRegistry()
        registry.register(
            Provider(name="logging", modules=("myproject.providers.logging",))
        )

        assert registry.is_provider_module("myproject.providers.logging")
        assert registry.is_provider_module("myproject.providers.logging.handlers")
        assert not registry.is_provider_module("myproject.service.users")

    def test_create_standard_providers(self) -> None:
        """Test creating standard providers."""
        registry = ProviderRegistry()
        registry.create_standard_providers()

        assert len(registry) == 5
        expected_names = {"logging", "metrics", "http", "cache", "security"}
        assert set(registry.names) == expected_names

        # Check each provider exists
        for name in expected_names:
            assert registry.get(name) is not None
            assert name in registry
