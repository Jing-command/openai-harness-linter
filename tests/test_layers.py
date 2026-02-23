"""Tests for the layers module."""

from __future__ import annotations

import pytest

from harness_linter.layers import Layer, LayerRegistry


class TestLayer:
    """Tests for the Layer class."""

    def test_layer_creation(self) -> None:
        """Test basic layer creation."""
        layer = Layer(
            name="service",
            index=3,
            description="Business logic layer",
            modules=("myproject.service",),
        )
        assert layer.name == "service"
        assert layer.index == 3
        assert layer.description == "Business logic layer"
        assert layer.modules == ("myproject.service",)

    def test_layer_default_values(self) -> None:
        """Test layer creation with default values."""
        layer = Layer(name="types", index=0)
        assert layer.description == ""
        assert layer.modules == ()

    def test_layer_hash_and_equality(self) -> None:
        """Test layer hashing and equality based on name."""
        layer1 = Layer(name="service", index=3)
        layer2 = Layer(name="service", index=3, description="Different desc")
        layer3 = Layer(name="repo", index=2)

        assert layer1 == layer2
        assert hash(layer1) == hash(layer2)
        assert layer1 != layer3
        assert layer1 != "service"

    def test_can_import_from_lower_index(self) -> None:
        """Test that layers can import from lower-indexed layers."""
        types_layer = Layer(name="types", index=0)
        config_layer = Layer(name="config", index=1)
        service_layer = Layer(name="service", index=3)

        # Service can import from types and config
        assert service_layer.can_import_from(types_layer)
        assert service_layer.can_import_from(config_layer)

        # Types cannot import from service
        assert not types_layer.can_import_from(service_layer)

        # Same layer is allowed
        assert service_layer.can_import_from(Layer(name="service", index=3))

    def test_add_module(self) -> None:
        """Test adding a module pattern to a layer."""
        layer = Layer(name="service", index=3, modules=("myproject.service",))
        new_layer = layer.add_module("myproject.services")

        # Original unchanged
        assert layer.modules == ("myproject.service",)
        # New layer has both patterns
        assert new_layer.modules == ("myproject.service", "myproject.services")


class TestLayerRegistry:
    """Tests for the LayerRegistry class."""

    def test_register_and_get(self) -> None:
        """Test registering and retrieving layers."""
        registry = LayerRegistry()
        layer = Layer(name="service", index=3)

        registry.register(layer)
        assert registry.get("service") == layer
        assert registry["service"] == layer

    def test_get_nonexistent(self) -> None:
        """Test getting a non-existent layer."""
        registry = LayerRegistry()
        assert registry.get("nonexistent") is None

    def test_getitem_nonexistent(self) -> None:
        """Test bracket access to non-existent layer raises KeyError."""
        registry = LayerRegistry()
        with pytest.raises(KeyError, match="Layer 'nonexistent' not found"):
            _ = registry["nonexistent"]

    def test_register_duplicate(self) -> None:
        """Test registering a duplicate layer raises ValueError."""
        registry = LayerRegistry()
        registry.register(Layer(name="service", index=3))

        with pytest.raises(ValueError, match="Layer 'service' is already registered"):
            registry.register(Layer(name="service", index=4))

    def test_contains(self) -> None:
        """Test checking if a layer is registered."""
        registry = LayerRegistry()
        registry.register(Layer(name="service", index=3))

        assert "service" in registry
        assert "nonexistent" not in registry

    def test_iteration_order(self) -> None:
        """Test that layers are iterated in index order."""
        registry = LayerRegistry()
        registry.register(Layer(name="service", index=3))
        registry.register(Layer(name="types", index=0))
        registry.register(Layer(name="config", index=1))

        names = [layer.name for layer in registry]
        assert names == ["types", "config", "service"]

    def test_len(self) -> None:
        """Test getting the number of registered layers."""
        registry = LayerRegistry()
        assert len(registry) == 0

        registry.register(Layer(name="types", index=0))
        assert len(registry) == 1

        registry.register(Layer(name="service", index=3))
        assert len(registry) == 2

    def test_names_property(self) -> None:
        """Test getting layer names in order."""
        registry = LayerRegistry()
        registry.register(Layer(name="service", index=3))
        registry.register(Layer(name="types", index=0))

        assert registry.names == ["types", "service"]

    def test_get_layer_for_module(self) -> None:
        """Test finding which layer a module belongs to."""
        registry = LayerRegistry()
        registry.register(
            Layer(name="types", index=0, modules=("myproject.types",))
        )
        registry.register(
            Layer(name="service", index=3, modules=("myproject.service",))
        )

        assert registry.get_layer_for_module("myproject.types.models") == registry.get("types")
        assert registry.get_layer_for_module("myproject.service.users") == registry.get("service")
        assert registry.get_layer_for_module("myproject.unknown") is None

    def test_get_layer_for_module_specificity(self) -> None:
        """Test that most specific pattern wins."""
        registry = LayerRegistry()
        registry.register(
            Layer(name="types", index=0, modules=("myproject.types", "myproject.types.core"))
        )
        registry.register(
            Layer(name="core", index=1, modules=("myproject.types.core.special",))
        )

        # Most specific pattern wins
        result = registry.get_layer_for_module("myproject.types.core.special.module")
        assert result is not None
        assert result.name == "core"

    def test_create_standard_harness_layers(self) -> None:
        """Test creating standard 6-layer architecture."""
        registry = LayerRegistry()
        registry.create_standard_harness_layers()

        assert len(registry) == 6
        assert registry.names == ["types", "config", "repo", "service", "runtime", "ui"]

        # Check each layer exists with correct index
        assert registry["types"].index == 0
        assert registry["config"].index == 1
        assert registry["repo"].index == 2
        assert registry["service"].index == 3
        assert registry["runtime"].index == 4
        assert registry["ui"].index == 5
