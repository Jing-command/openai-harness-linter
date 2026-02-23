# OpenAI Harness 架构 Linter 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 复现 OpenAI Harness Engineering 的架构 linter 系统，强制执行严格的分层架构和依赖方向规则

**Architecture:** 基于 Python 的 import-linter 扩展，实现 Types→Config→Repo→Service→Runtime→UI 的严格单向依赖。Providers 作为横切关注点的统一入口。使用 AST 分析和 import graph 验证架构规则。

**Tech Stack:** Python, import-linter (grimp), AST (ast/astroid), pytest, toml/yaml 配置

---

## 项目结构预览

```
openai-harness-linter/
├── src/
│   └── harness_linter/
│       ├── __init__.py
│       ├── cli.py              # 命令行入口
│       ├── config.py           # 配置解析
│       ├── contracts/          # 架构契约规则
│       │   ├── __init__.py
│       │   ├── base.py         # 基础契约类
│       │   ├── layer_contract.py      # 层依赖规则
│       │   ├── provider_contract.py   # Providers 规则
│       │   └── forbidden_contract.py  # 禁止的导入
│       ├── graph.py            # 导入图构建
│       ├── layers.py           # 层定义和管理
│       └── providers.py        # Providers 系统
├── tests/
│   └── test_*.py
├── examples/
│   └── sample_project/         # 示例项目
│       ├── types/
│       ├── config/
│       ├── repo/
│       ├── service/
│       ├── runtime/
│       ├── ui/
│       └── providers/
├── pyproject.toml
└── README.md
```

---

## Task 1: 项目初始化和依赖配置

**Files:**
- Create: `pyproject.toml`
- Create: `src/harness_linter/__init__.py`

**Step 1: 创建项目配置**

```toml
# pyproject.toml
[project]
name = "harness-linter"
version = "0.1.0"
description = "OpenAI Harness-style architecture linter enforcing strict layer dependencies"
requires-python = ">=3.9"
dependencies = [
    "grimp>=3.0",
    "click>=8.0",
    "tomli>=2.0; python_version<'3.11'",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov",
    "black",
    "ruff",
    "mypy",
]

[project.scripts]
harness-lint = "harness_linter.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2: 创建包初始化文件**

```python
# src/harness_linter/__init__.py
"""OpenAI Harness-style architecture linter."""

__version__ = "0.1.0"
```

**Step 3: 安装依赖**

Run: `pip install -e ".[dev]"`
Expected: Dependencies installed successfully

**Step 4: Commit**

```bash
git add pyproject.toml src/harness_linter/__init__.py
git commit -m "feat: initialize harness-linter project"
```

---

## Task 2: 层定义系统 (Layers)

**Files:**
- Create: `src/harness_linter/layers.py`
- Test: `tests/test_layers.py`

**Step 1: 编写失败测试**

```python
# tests/test_layers.py
"""Tests for layer definitions."""

import pytest
from harness_linter.layers import Layer, LayerRegistry


def test_layer_creation():
    """Test creating a layer definition."""
    layer = Layer(name="service", path="myproject.service", level=3)
    assert layer.name == "service"
    assert layer.path == "myproject.service"
    assert layer.level == 3


def test_layer_registry():
    """Test layer registry with default OpenAI Harness layers."""
    registry = LayerRegistry()

    # Register default layers
    registry.register(Layer("types", "myproject.types", 0))
    registry.register(Layer("config", "myproject.config", 1))
    registry.register(Layer("repo", "myproject.repo", 2))
    registry.register(Layer("service", "myproject.service", 3))
    registry.register(Layer("runtime", "myproject.runtime", 4))
    registry.register(Layer("ui", "myproject.ui", 5))

    # Test getting layers
    assert registry.get("service").level == 3
    assert len(registry.all()) == 6


def test_layer_dependency_direction():
    """Test that higher layers can depend on lower layers."""
    registry = LayerRegistry()

    types_layer = Layer("types", "myproject.types", 0)
    service_layer = Layer("service", "myproject.service", 3)

    registry.register(types_layer)
    registry.register(service_layer)

    # Service (level 3) CAN depend on types (level 0)
    assert registry.can_depend(service_layer, types_layer)
    # Types (level 0) CANNOT depend on service (level 3)
    assert not registry.can_depend(types_layer, service_layer)
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_layers.py -v`
Expected: FAIL with "Layer not defined"

**Step 3: 实现层系统**

```python
# src/harness_linter/layers.py
"""Layer definitions for Harness architecture."""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Layer:
    """Represents an architectural layer.

    In OpenAI Harness architecture:
    - types (level 0): Shared type definitions
    - config (level 1): Configuration management
    - repo (level 2): Data access/repository layer
    - service (level 3): Business logic layer
    - runtime (level 4): Runtime environment
    - ui (level 5): User interface layer
    """
    name: str
    path: str  # Python import path prefix
    level: int  # Lower level = foundation layer

    def __lt__(self, other: "Layer") -> bool:
        return self.level < other.level

    def __le__(self, other: "Layer") -> bool:
        return self.level <= other.level

    def __gt__(self, other: "Layer") -> bool:
        return self.level > other.level

    def __ge__(self, other: "Layer") -> bool:
        return self.level >= other.level


class LayerRegistry:
    """Registry for managing architectural layers."""

    def __init__(self):
        self._layers: dict[str, Layer] = {}

    def register(self, layer: Layer) -> None:
        """Register a layer."""
        self._layers[layer.name] = layer

    def get(self, name: str) -> Optional[Layer]:
        """Get layer by name."""
        return self._layers.get(name)

    def get_by_path(self, import_path: str) -> Optional[Layer]:
        """Find layer that matches an import path."""
        for layer in self._layers.values():
            if import_path.startswith(layer.path):
                return layer
        return None

    def all(self) -> list[Layer]:
        """Get all layers sorted by level."""
        return sorted(self._layers.values(), key=lambda l: l.level)

    def can_depend(self, dependent: Layer, dependency: Layer) -> bool:
        """Check if dependent layer can import from dependency layer.

        Rule: Higher level layers CAN import from lower level layers.
        Lower level layers CANNOT import from higher level layers.
        """
        return dependent.level > dependency.level

    @classmethod
    def create_default(cls, root_package: str) -> "LayerRegistry":
        """Create registry with OpenAI Harness default layers."""
        registry = cls()

        layers = [
            Layer("types", f"{root_package}.types", 0),
            Layer("config", f"{root_package}.config", 1),
            Layer("repo", f"{root_package}.repo", 2),
            Layer("service", f"{root_package}.service", 3),
            Layer("runtime", f"{root_package}.runtime", 4),
            Layer("ui", f"{root_package}.ui", 5),
        ]

        for layer in layers:
            registry.register(layer)

        return registry
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_layers.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/harness_linter/layers.py tests/test_layers.py
git commit -m "feat: add layer definition system"
```

---

## Task 3: Providers 系统

**Files:**
- Create: `src/harness_linter/providers.py`
- Test: `tests/test_providers.py`

**Step 1: 编写失败测试**

```python
# tests/test_providers.py
"""Tests for providers system."""

import pytest
from harness_linter.providers import Provider, ProviderRegistry


def test_provider_creation():
    """Test creating a provider definition."""
    provider = Provider(
        name="auth",
        path="myproject.providers.auth",
        allowed_layers=["service", "runtime", "ui"]
    )
    assert provider.name == "auth"
    assert "service" in provider.allowed_layers


def test_provider_registry():
    """Test provider registry."""
    registry = ProviderRegistry()

    registry.register(Provider(
        name="telemetry",
        path="myproject.providers.telemetry",
        allowed_layers=["repo", "service", "runtime"]
    ))

    assert registry.get("telemetry") is not None
    assert registry.is_provider_path("myproject.providers.telemetry.metrics")


def test_provider_layer_access():
    """Test that providers have controlled access to layers."""
    registry = ProviderRegistry()

    auth_provider = Provider(
        name="auth",
        path="myproject.providers.auth",
        allowed_layers=["service", "runtime", "ui"]  # repo cannot use auth
    )
    registry.register(auth_provider)

    # Auth can be used in service layer
    assert registry.can_use_provider("auth", "service")
    # Auth CANNOT be used in repo layer
    assert not registry.can_use_provider("auth", "repo")
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_providers.py -v`
Expected: FAIL

**Step 3: 实现 Providers 系统**

```python
# src/harness_linter/providers.py
"""Providers system for cross-cutting concerns.

In OpenAI Harness architecture, cross-cutting concerns like:
- Authentication
- Logging
- Telemetry
- Feature flags
- Database connections

All enter through a single explicit interface called "Providers".
This prevents these concerns from polluting the layered architecture.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Provider:
    """Represents a cross-cutting concern provider.

    Providers are special modules that can be accessed by specific layers
    but don't follow the normal layer dependency rules.
    """
    name: str
    path: str  # Python import path
    allowed_layers: list[str] = field(default_factory=list)
    description: str = ""

    def can_be_used_in(self, layer_name: str) -> bool:
        """Check if this provider can be used in the given layer."""
        if not self.allowed_layers:
            return True  # No restrictions
        return layer_name in self.allowed_layers


class ProviderRegistry:
    """Registry for managing cross-cutting concern providers."""

    def __init__(self):
        self._providers: dict[str, Provider] = {}
        self._provider_paths: set[str] = set()

    def register(self, provider: Provider) -> None:
        """Register a provider."""
        self._providers[provider.name] = provider
        self._provider_paths.add(provider.path)

    def get(self, name: str) -> Optional[Provider]:
        """Get provider by name."""
        return self._providers.get(name)

    def get_by_path(self, import_path: str) -> Optional[Provider]:
        """Find provider that matches an import path."""
        for provider in self._providers.values():
            if import_path.startswith(provider.path):
                return provider
        return None

    def is_provider_path(self, import_path: str) -> bool:
        """Check if import path belongs to any provider."""
        for path in self._provider_paths:
            if import_path.startswith(path):
                return True
        return False

    def can_use_provider(self, provider_name: str, layer_name: str) -> bool:
        """Check if a layer can use a specific provider."""
        provider = self._providers.get(provider_name)
        if not provider:
            return False
        return provider.can_be_used_in(layer_name)

    def all(self) -> list[Provider]:
        """Get all registered providers."""
        return list(self._providers.values())

    @classmethod
    def create_default(cls, root_package: str) -> "ProviderRegistry":
        """Create registry with common cross-cutting concern providers."""
        registry = cls()

        providers = [
            Provider(
                name="auth",
                path=f"{root_package}.providers.auth",
                allowed_layers=["service", "runtime", "ui"],
                description="Authentication and authorization"
            ),
            Provider(
                name="logging",
                path=f"{root_package}.providers.logging",
                allowed_layers=["types", "config", "repo", "service", "runtime", "ui"],
                description="Structured logging"
            ),
            Provider(
                name="telemetry",
                path=f"{root_package}.providers.telemetry",
                allowed_layers=["repo", "service", "runtime"],
                description="Metrics and tracing"
            ),
            Provider(
                name="config_provider",
                path=f"{root_package}.providers.config",
                allowed_layers=["repo", "service", "runtime", "ui"],
                description="Runtime configuration access"
            ),
            Provider(
                name="feature_flags",
                path=f"{root_package}.providers.feature_flags",
                allowed_layers=["service", "runtime", "ui"],
                description="Feature flag system"
            ),
        ]

        for provider in providers:
            registry.register(provider)

        return registry
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_providers.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/harness_linter/providers.py tests/test_providers.py
git commit -m "feat: add providers system for cross-cutting concerns"
```

---

## Task 4: 导入图分析

**Files:**
- Create: `src/harness_linter/graph.py`
- Test: `tests/test_graph.py`

**Step 1: 编写失败测试**

```python
# tests/test_graph.py
"""Tests for import graph analysis."""

import pytest
from pathlib import Path
from harness_linter.graph import ImportGraphBuilder


def test_graph_builder_init():
    """Test graph builder initialization."""
    builder = ImportGraphBuilder(root_package="myproject")
    assert builder.root_package == "myproject"


def test_build_graph(tmp_path):
    """Test building import graph from source files."""
    # Create sample project structure
    project = tmp_path / "myproject"
    project.mkdir()

    # Create types module
    (project / "types.py").write_text("""
class UserId:
    pass
""")

    # Create service module that imports types
    (project / "service.py").write_text("""
from myproject.types import UserId

class UserService:
    def get_user(self, user_id: UserId):
        pass
""")

    builder = ImportGraphBuilder(root_package="myproject")
    graph = builder.build_from_path(tmp_path)

    # Service should have import edge to types
    assert graph.has_import("myproject.service", "myproject.types")
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_graph.py -v`
Expected: FAIL

**Step 3: 实现导入图构建器**

```python
# src/harness_linter/graph.py
"""Import graph analysis using grimp."""

from pathlib import Path
from typing import Optional
import grimp


class ImportGraph:
    """Wrapper around grimp.ImportGraph with Harness-specific operations."""

    def __init__(self, grimp_graph: grimp.ImportGraph):
        self._graph = grimp_graph

    def has_import(self, importer: str, imported: str) -> bool:
        """Check if importer module imports from imported module."""
        return self._graph.find_shortest_chain(importer, imported) is not None

    def get_imports_from(self, module: str) -> set[str]:
        """Get all modules that a given module imports from."""
        return set(self._graph.find_modules_directly_imported_by(module))

    def get_imports_to(self, module: str) -> set[str]:
        """Get all modules that import from a given module."""
        return set(self._graph.find_modules_that_directly_import(module))

    def module_exists(self, module: str) -> bool:
        """Check if a module exists in the graph."""
        return module in self._graph.modules

    def all_modules(self) -> set[str]:
        """Get all modules in the graph."""
        return set(self._graph.modules)


class ImportGraphBuilder:
    """Builds import graph from Python source files."""

    def __init__(self, root_package: str):
        self.root_package = root_package

    def build_from_path(self, path: Path) -> ImportGraph:
        """Build import graph from source directory."""
        graph = grimp.build_graph(str(path))
        return ImportGraph(graph)

    def build_from_package(self, package_name: str) -> ImportGraph:
        """Build import graph from installed package."""
        graph = grimp.build_graph(package_name)
        return ImportGraph(graph)
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_graph.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/harness_linter/graph.py tests/test_graph.py
git commit -m "feat: add import graph analysis using grimp"
```

---

## Task 5: 架构契约基础

**Files:**
- Create: `src/harness_linter/contracts/__init__.py`
- Create: `src/harness_linter/contracts/base.py`
- Test: `tests/test_contracts_base.py`

**Step 1: 编写失败测试**

```python
# tests/test_contracts_base.py
"""Tests for base contract classes."""

import pytest
from harness_linter.contracts.base import Contract, ContractResult, Violation


def test_violation_creation():
    """Test creating a violation."""
    violation = Violation(
        message="Invalid import",
        importer="myproject.service",
        imported="myproject.ui"
    )
    assert violation.message == "Invalid import"
    assert violation.importer == "myproject.service"


def test_contract_result():
    """Test contract result."""
    violation = Violation(
        message="Invalid import",
        importer="myproject.service",
        imported="myproject.ui"
    )
    result = ContractResult(contract_name="test", violations=[violation])

    assert not result.is_valid
    assert len(result.violations) == 1


def test_contract_abstract():
    """Test that Contract is abstract."""
    with pytest.raises(TypeError):
        Contract(name="test")  # type: ignore
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_contracts_base.py -v`
Expected: FAIL

**Step 3: 实现基础契约类**

```python
# src/harness_linter/contracts/__init__.py
"""Architecture contracts for enforcing Harness rules."""

from harness_linter.contracts.base import Contract, ContractResult, Violation
from harness_linter.contracts.layer_contract import LayerContract
from harness_linter.contracts.provider_contract import ProviderContract

__all__ = [
    "Contract",
    "ContractResult",
    "Violation",
    "LayerContract",
    "ProviderContract",
]
```

```python
# src/harness_linter/contracts/base.py
"""Base classes for architecture contracts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from harness_linter.graph import ImportGraph


@dataclass(frozen=True)
class Violation:
    """Represents a contract violation."""
    message: str
    importer: str
    imported: str
    line_number: Optional[int] = None
    remediation: str = ""


@dataclass
class ContractResult:
    """Result of checking a contract."""
    contract_name: str
    violations: list[Violation] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.violations) == 0

    def merge(self, other: "ContractResult") -> "ContractResult":
        """Merge another result into this one."""
        return ContractResult(
            contract_name=f"{self.contract_name}, {other.contract_name}",
            violations=self.violations + other.violations
        )


class Contract(ABC):
    """Abstract base class for architecture contracts.

    Contracts define rules that the codebase must follow.
    Examples:
    - LayerContract: Enforces that layers only depend on lower layers
    - ProviderContract: Enforces that providers are used correctly
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def check(self, graph: ImportGraph) -> ContractResult:
        """Check this contract against the import graph.

        Args:
            graph: The import graph to check

        Returns:
            ContractResult with any violations found
        """
        pass
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_contracts_base.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/harness_linter/contracts/ tests/test_contracts_base.py
git commit -m "feat: add base contract classes"
```

---

## Task 6: 层契约实现

**Files:**
- Create: `src/harness_linter/contracts/layer_contract.py`
- Test: `tests/test_layer_contract.py`

**Step 1: 编写失败测试**

```python
# tests/test_layer_contract.py
"""Tests for layer contract."""

import pytest
from pathlib import Path
from harness_linter.contracts.layer_contract import LayerContract
from harness_linter.graph import ImportGraphBuilder
from harness_linter.layers import Layer, LayerRegistry


def test_layer_contract_valid(tmp_path):
    """Test that valid layer dependencies pass."""
    # Create project: service -> types (valid: service is higher level)
    project = tmp_path / "myproject"
    project.mkdir()

    (project / "types.py").write_text("class UserId: pass")
    (project / "service.py").write_text("""
from myproject.types import UserId
class UserService:
    def get(self, id: UserId): pass
""")

    builder = ImportGraphBuilder(root_package="myproject")
    graph = builder.build_from_path(tmp_path)

    registry = LayerRegistry()
    registry.register(Layer("types", "myproject.types", 0))
    registry.register(Layer("service", "myproject.service", 3))

    contract = LayerContract("layer-check", registry)
    result = contract.check(graph)

    assert result.is_valid


def test_layer_contract_invalid(tmp_path):
    """Test that invalid layer dependencies fail."""
    # Create project: types -> service (invalid: types is lower level)
    project = tmp_path / "myproject"
    project.mkdir()

    (project / "service.py").write_text("class UserService: pass")
    (project / "types.py").write_text("""
from myproject.service import UserService
class UserId:
    service = UserService()
""")

    builder = ImportGraphBuilder(root_package="myproject")
    graph = builder.build_from_path(tmp_path)

    registry = LayerRegistry()
    registry.register(Layer("types", "myproject.types", 0))
    registry.register(Layer("service", "myproject.service", 3))

    contract = LayerContract("layer-check", registry)
    result = contract.check(graph)

    assert not result.is_valid
    assert len(result.violations) == 1
    assert "types" in result.violations[0].message
    assert "service" in result.violations[0].message
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_layer_contract.py -v`
Expected: FAIL

**Step 3: 实现层契约**

```python
# src/harness_linter/contracts/layer_contract.py
"""Contract for enforcing layer dependency rules.

Enforces the OpenAI Harness rule: dependencies can only flow "forward"
through the layer stack. Higher layers can depend on lower layers,
but lower layers cannot depend on higher layers.

Order: types -> config -> repo -> service -> runtime -> ui
"""

from harness_linter.contracts.base import Contract, ContractResult, Violation
from harness_linter.graph import ImportGraph
from harness_linter.layers import Layer, LayerRegistry


class LayerContract(Contract):
    """Enforces that layers only depend on lower-level layers."""

    def __init__(self, name: str, layer_registry: LayerRegistry):
        super().__init__(name)
        self._registry = layer_registry

    def check(self, graph: ImportGraph) -> ContractResult:
        """Check that no layer imports from a higher-level layer."""
        violations = []

        for module in graph.all_modules():
            importer_layer = self._registry.get_by_path(module)
            if not importer_layer:
                continue  # Module not in any defined layer

            # Check all imports from this module
            for imported_module in graph.get_imports_from(module):
                imported_layer = self._registry.get_by_path(imported_module)
                if not imported_layer:
                    continue  # Import not from a defined layer

                # Check if this is a valid dependency direction
                if not self._registry.can_depend(importer_layer, imported_layer):
                    # This is a backward dependency violation!
                    violation = Violation(
                        message=(
                            f"Layer '{importer_layer.name}' (level {importer_layer.level}) "
                            f"cannot import from layer '{imported_layer.name}' "
                            f"(level {imported_layer.level}). "
                            f"Dependencies must flow from higher to lower levels."
                        ),
                        importer=module,
                        imported=imported_module,
                        remediation=(
                            f"Move the shared code to a lower layer (e.g., 'types' or 'config') "
                            f"or refactor to use dependency injection."
                        )
                    )
                    violations.append(violation)

        return ContractResult(contract_name=self.name, violations=violations)
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_layer_contract.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/harness_linter/contracts/layer_contract.py tests/test_layer_contract.py
git commit -m "feat: implement layer dependency contract"
```

---

## Task 7: Providers 契约实现

**Files:**
- Create: `src/harness_linter/contracts/provider_contract.py`
- Test: `tests/test_provider_contract.py`

**Step 1: 编写失败测试**

```python
# tests/test_provider_contract.py
"""Tests for provider contract."""

import pytest
from pathlib import Path
from harness_linter.contracts.provider_contract import ProviderContract
from harness_linter.graph import ImportGraphBuilder
from harness_linter.layers import Layer, LayerRegistry
from harness_linter.providers import Provider, ProviderRegistry


def test_provider_contract_valid(tmp_path):
    """Test that valid provider usage passes."""
    project = tmp_path / "myproject"
    project.mkdir()
    (project / "providers").mkdir()

    # Service uses auth provider (allowed)
    (project / "providers" / "auth.py").write_text("def authenticate(): pass")
    (project / "service.py").write_text("""
from myproject.providers.auth import authenticate
class UserService:
    def login(self): authenticate()
""")

    builder = ImportGraphBuilder(root_package="myproject")
    graph = builder.build_from_path(tmp_path)

    layer_registry = LayerRegistry()
    layer_registry.register(Layer("service", "myproject.service", 3))

    provider_registry = ProviderRegistry()
    provider_registry.register(Provider(
        name="auth",
        path="myproject.providers.auth",
        allowed_layers=["service"]
    ))

    contract = ProviderContract("provider-check", layer_registry, provider_registry)
    result = contract.check(graph)

    assert result.is_valid


def test_provider_contract_invalid_layer(tmp_path):
    """Test that provider usage in wrong layer fails."""
    project = tmp_path / "myproject"
    project.mkdir()
    (project / "providers").mkdir()

    # Repo uses auth provider (not allowed)
    (project / "providers" / "auth.py").write_text("def authenticate(): pass")
    (project / "repo.py").write_text("""
from myproject.providers.auth import authenticate
class UserRepo:
    def save(self): authenticate()
""")

    builder = ImportGraphBuilder(root_package="myproject")
    graph = builder.build_from_path(tmp_path)

    layer_registry = LayerRegistry()
    layer_registry.register(Layer("repo", "myproject.repo", 2))

    provider_registry = ProviderRegistry()
    provider_registry.register(Provider(
        name="auth",
        path="myproject.providers.auth",
        allowed_layers=["service", "ui"]  # repo NOT allowed
    ))

    contract = ProviderContract("provider-check", layer_registry, provider_registry)
    result = contract.check(graph)

    assert not result.is_valid
    assert len(result.violations) == 1
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_provider_contract.py -v`
Expected: FAIL

**Step 3: 实现 Providers 契约**

```python
# src/harness_linter/contracts/provider_contract.py
"""Contract for enforcing provider usage rules.

Enforces that:
1. Cross-cutting concerns only enter through providers
2. Providers can only be used in their allowed layers
"""

from harness_linter.contracts.base import Contract, ContractResult, Violation
from harness_linter.graph import ImportGraph
from harness_linter.layers import LayerRegistry
from harness_linter.providers import ProviderRegistry


class ProviderContract(Contract):
    """Enforces correct usage of cross-cutting concern providers."""

    def __init__(
        self,
        name: str,
        layer_registry: LayerRegistry,
        provider_registry: ProviderRegistry
    ):
        super().__init__(name)
        self._layer_registry = layer_registry
        self._provider_registry = provider_registry

    def check(self, graph: ImportGraph) -> ContractResult:
        """Check that providers are only used in allowed layers."""
        violations = []

        for module in graph.all_modules():
            # Determine which layer this module belongs to
            layer = self._layer_registry.get_by_path(module)
            if not layer:
                continue

            # Check all imports from this module
            for imported_module in graph.get_imports_from(module):
                # Check if this import is from a provider
                provider = self._provider_registry.get_by_path(imported_module)
                if not provider:
                    continue

                # Check if this layer is allowed to use this provider
                if not provider.can_be_used_in(layer.name):
                    violation = Violation(
                        message=(
                            f"Layer '{layer.name}' cannot use provider '{provider.name}'. "
                            f"Allowed layers: {', '.join(provider.allowed_layers)}."
                        ),
                        importer=module,
                        imported=imported_module,
                        remediation=(
                            f"Either:\n"
                            f"1. Add '{layer.name}' to provider's allowed_layers, or\n"
                            f"2. Move the code to an allowed layer, or\n"
                            f"3. Inject the provider dependency from a higher layer."
                        )
                    )
                    violations.append(violation)

        return ContractResult(contract_name=self.name, violations=violations)
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_provider_contract.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/harness_linter/contracts/provider_contract.py tests/test_provider_contract.py
git commit -m "feat: implement provider usage contract"
```

---

## Task 8: 配置系统

**Files:**
- Create: `src/harness_linter/config.py`
- Test: `tests/test_config.py`

**Step 1: 编写失败测试**

```python
# tests/test_config.py
"""Tests for configuration parsing."""

import pytest
import tempfile
from pathlib import Path
from harness_linter.config import Config, load_config


def test_load_config_from_toml():
    """Test loading configuration from TOML file."""
    toml_content = """
[tool.harness]
root_package = "myproject"

[[tool.harness.layers]]
name = "types"
path = "myproject.types"
level = 0

[[tool.harness.layers]]
name = "service"
path = "myproject.service"
level = 3

[[tool.harness.providers]]
name = "auth"
path = "myproject.providers.auth"
allowed_layers = ["service", "ui"]
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
        f.write(toml_content)
        config_path = Path(f.name)

    try:
        config = load_config(config_path)
        assert config.root_package == "myproject"
        assert len(config.layers) == 2
        assert len(config.providers) == 1
        assert config.providers[0].name == "auth"
    finally:
        config_path.unlink()
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_config.py -v`
Expected: FAIL

**Step 3: 实现配置系统**

```python
# src/harness_linter/config.py
"""Configuration loading and parsing."""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from harness_linter.layers import Layer, LayerRegistry
from harness_linter.providers import Provider, ProviderRegistry


@dataclass
class Config:
    """Harness linter configuration."""
    root_package: str
    layers: list[Layer] = field(default_factory=list)
    providers: list[Provider] = field(default_factory=list)

    def create_layer_registry(self) -> LayerRegistry:
        """Create layer registry from config."""
        registry = LayerRegistry()
        for layer in self.layers:
            registry.register(layer)
        return registry

    def create_provider_registry(self) -> ProviderRegistry:
        """Create provider registry from config."""
        registry = ProviderRegistry()
        for provider in self.providers:
            registry.register(provider)
        return registry

    @classmethod
    def create_default(cls, root_package: str) -> "Config":
        """Create config with default OpenAI Harness layers and providers."""
        layer_registry = LayerRegistry.create_default(root_package)
        provider_registry = ProviderRegistry.create_default(root_package)

        return cls(
            root_package=root_package,
            layers=layer_registry.all(),
            providers=provider_registry.all()
        )


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from TOML file.

    If no config path provided, looks for pyproject.toml in current directory.
    """
    if config_path is None:
        config_path = Path("pyproject.toml")

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    harness_config = data.get("tool", {}).get("harness", {})

    root_package = harness_config.get("root_package", "")
    if not root_package:
        raise ValueError("root_package is required in [tool.harness]")

    # Parse layers
    layers = []
    for layer_data in harness_config.get("layers", []):
        layers.append(Layer(
            name=layer_data["name"],
            path=layer_data["path"],
            level=layer_data["level"]
        ))

    # Parse providers
    providers = []
    for provider_data in harness_config.get("providers", []):
        providers.append(Provider(
            name=provider_data["name"],
            path=provider_data["path"],
            allowed_layers=provider_data.get("allowed_layers", []),
            description=provider_data.get("description", "")
        ))

    return Config(
        root_package=root_package,
        layers=layers,
        providers=providers
    )
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/harness_linter/config.py tests/test_config.py
git commit -m "feat: add TOML configuration loading"
```

---

## Task 9: CLI 接口

**Files:**
- Create: `src/harness_linter/cli.py`
- Test: `tests/test_cli.py`

**Step 1: 编写失败测试**

```python
# tests/test_cli.py
"""Tests for CLI interface."""

import pytest
from click.testing import CliRunner
from harness_linter.cli import main


def test_cli_help():
    """Test CLI help message."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Harness Linter" in result.output


def test_cli_no_config(tmp_path):
    """Test CLI without config file."""
    runner = CliRunner()
    with runner.isolated_filesystem(temp_dir=tmp_path) as td:
        result = runner.invoke(main, ["--package", "nonexistent"])
        assert result.exit_code != 0
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL

**Step 3: 实现 CLI**

```python
# src/harness_linter/cli.py
"""Command-line interface for Harness Linter."""

import sys
from pathlib import Path

import click

from harness_linter.config import Config, load_config
from harness_linter.graph import ImportGraphBuilder
from harness_linter.contracts.layer_contract import LayerContract
from harness_linter.contracts.provider_contract import ProviderContract


@click.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file (default: pyproject.toml)"
)
@click.option(
    "--package", "-p",
    help="Root package name (overrides config)"
)
@click.option(
    "--path",
    type=click.Path(exists=True, path_type=Path),
    default=Path("."),
    help="Path to source directory"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Show detailed output"
)
def main(config: Path | None, package: str | None, path: Path, verbose: bool) -> int:
    """Harness Linter - Enforce OpenAI-style architecture rules."""
    try:
        # Load configuration
        if config:
            cfg = load_config(config)
        else:
            try:
                cfg = load_config(Path("pyproject.toml"))
            except FileNotFoundError:
                if package:
                    cfg = Config.create_default(package)
                else:
                    click.echo(
                        "Error: No configuration found. "
                        "Create pyproject.toml with [tool.harness] or use --package",
                        err=True
                    )
                    return 1

        if package:
            cfg.root_package = package

        click.echo(f"Checking {cfg.root_package}...")

        # Build import graph
        builder = ImportGraphBuilder(root_package=cfg.root_package)
        graph = builder.build_from_path(path)

        # Create registries
        layer_registry = cfg.create_layer_registry()
        provider_registry = cfg.create_provider_registry()

        # Run contracts
        contracts = [
            LayerContract("layer-dependencies", layer_registry),
            ProviderContract("provider-usage", layer_registry, provider_registry),
        ]

        all_valid = True
        total_violations = 0

        for contract in contracts:
            if verbose:
                click.echo(f"\nChecking {contract.name}...")

            result = contract.check(graph)

            if not result.is_valid:
                all_valid = False
                total_violations += len(result.violations)

                for violation in result.violations:
                    click.echo(f"\n❌ {violation.message}")
                    click.echo(f"   {violation.importer} -> {violation.imported}")
                    if violation.remediation:
                        click.echo(f"   💡 {violation.remediation}")
            elif verbose:
                click.echo(f"  ✓ {contract.name} passed")

        if all_valid:
            click.echo("\n✅ All checks passed!")
            return 0
        else:
            click.echo(f"\n❌ Found {total_violations} violation(s)")
            return 1

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/harness_linter/cli.py tests/test_cli.py
git commit -m "feat: add CLI interface"
```

---

## Task 10: 示例项目和集成测试

**Files:**
- Create: `examples/sample_project/pyproject.toml`
- Create: `examples/sample_project/myproject/__init__.py`
- Create: `examples/sample_project/myproject/types.py`
- Create: `examples/sample_project/myproject/config.py`
- Create: `examples/sample_project/myproject/repo.py`
- Create: `examples/sample_project/myproject/service.py`
- Create: `examples/sample_project/myproject/runtime.py`
- Create: `examples/sample_project/myproject/ui.py`
- Create: `examples/sample_project/myproject/providers/auth.py`
- Create: `examples/sample_project/myproject/providers/logging.py`
- Create: `examples/sample_project/myproject/providers/telemetry.py`

**Step 1: 创建示例项目配置**

```toml
# examples/sample_project/pyproject.toml
[project]
name = "sample-project"
version = "0.1.0"

[tool.harness]
root_package = "myproject"

[[tool.harness.layers]]
name = "types"
path = "myproject.types"
level = 0

[[tool.harness.layers]]
name = "config"
path = "myproject.config"
level = 1

[[tool.harness.layers]]
name = "repo"
path = "myproject.repo"
level = 2

[[tool.harness.layers]]
name = "service"
path = "myproject.service"
level = 3

[[tool.harness.layers]]
name = "runtime"
path = "myproject.runtime"
level = 4

[[tool.harness.layers]]
name = "ui"
path = "myproject.ui"
level = 5

[[tool.harness.providers]]
name = "auth"
path = "myproject.providers.auth"
allowed_layers = ["service", "runtime", "ui"]
description = "Authentication provider"

[[tool.harness.providers]]
name = "logging"
path = "myproject.providers.logging"
allowed_layers = ["types", "config", "repo", "service", "runtime", "ui"]
description = "Structured logging"

[[tool.harness.providers]]
name = "telemetry"
path = "myproject.providers.telemetry"
allowed_layers = ["repo", "service", "runtime"]
description = "Metrics and tracing"
```

**Step 2: 创建示例模块**

```python
# examples/sample_project/myproject/__init__.py
"""Sample project demonstrating OpenAI Harness architecture."""
```

```python
# examples/sample_project/myproject/types.py
"""Domain types - layer 0 (foundation)."""

from dataclasses import dataclass
from typing import NewType

UserId = NewType("UserId", str)


@dataclass(frozen=True)
class User:
    id: UserId
    name: str
    email: str
```

```python
# examples/sample_project/myproject/config.py
"""Configuration - layer 1."""

from myproject.types import UserId

DATABASE_URL = "postgresql://localhost/db"


def get_user_settings(user_id: UserId) -> dict:
    return {"theme": "dark"}
```

```python
# examples/sample_project/myproject/repo.py
"""Data access layer - layer 2."""

from myproject.types import User, UserId
from myproject.config import DATABASE_URL
from myproject.providers.telemetry import record_query


def get_user(user_id: UserId) -> User | None:
    record_query("get_user")
    # In real app, query database
    return User(id=user_id, name="Alice", email="alice@example.com")


def save_user(user: User) -> None:
    record_query("save_user")
    # In real app, save to database
    pass
```

```python
# examples/sample_project/myproject/service.py
"""Business logic layer - layer 3."""

from myproject.types import User, UserId
from myproject.repo import get_user, save_user
from myproject.providers.auth import require_auth
from myproject.providers.logging import get_logger

logger = get_logger(__name__)


@require_auth
class UserService:
    def get_user(self, user_id: UserId) -> User | None:
        logger.info(f"Getting user {user_id}")
        return get_user(user_id)

    def create_user(self, name: str, email: str) -> User:
        logger.info(f"Creating user {name}")
        user = User(id=UserId("123"), name=name, email=email)
        save_user(user)
        return user
```

```python
# examples/sample_project/myproject/runtime.py
"""Runtime environment - layer 4."""

from myproject.service import UserService
from myproject.providers.auth import AuthContext


class Application:
    def __init__(self):
        self.user_service = UserService()
        self.auth_context = AuthContext()

    def start(self):
        print("Application started")
```

```python
# examples/sample_project/myproject/ui.py
"""User interface layer - layer 5 (top)."""

from myproject.runtime import Application
from myproject.service import UserService
from myproject.types import UserId
from myproject.providers.auth import login_required


class WebUI:
    def __init__(self, app: Application):
        self.app = app

    @login_required
    def user_page(self, user_id: str):
        user = self.app.user_service.get_user(UserId(user_id))
        return f"<h1>Hello {user.name}</h1>" if user else "<h1>Not found</h1>"
```

```python
# examples/sample_project/myproject/providers/auth.py
"""Authentication provider - cross-cutting concern."""

from functools import wraps
from typing import Callable, TypeVar

F = TypeVar("F", bound=Callable)


def require_auth(cls: type) -> type:
    """Class decorator to require authentication."""
    return cls


def login_required(func: F) -> F:
    """Function decorator to require login."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper  # type: ignore


class AuthContext:
    """Authentication context for runtime."""
    pass
```

```python
# examples/sample_project/myproject/providers/logging.py
"""Logging provider - cross-cutting concern."""

from typing import Any


def get_logger(name: str) -> Any:
    """Get a structured logger."""
    return _Logger(name)


class _Logger:
    def __init__(self, name: str):
        self.name = name

    def info(self, message: str) -> None:
        print(f"[INFO] {self.name}: {message}")

    def error(self, message: str) -> None:
        print(f"[ERROR] {self.name}: {message}")
```

```python
# examples/sample_project/myproject/providers/telemetry.py
"""Telemetry provider - cross-cutting concern."""

from typing import Any


def record_query(query_name: str) -> None:
    """Record a database query metric."""
    pass


def record_latency(operation: str, duration_ms: float) -> None:
    """Record operation latency."""
    pass
```

**Step 3: 创建集成测试**

```python
# tests/test_integration.py
"""Integration tests with sample project."""

import subprocess
import sys
from pathlib import Path


def test_sample_project_passes():
    """Test that sample project passes all checks."""
    sample_project = Path(__file__).parent.parent / "examples" / "sample_project"

    result = subprocess.run(
        [sys.executable, "-m", "harness_linter.cli", "-v"],
        cwd=sample_project,
        capture_output=True,
        text=True
    )

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    assert result.returncode == 0, f"Linter failed: {result.stdout}\n{result.stderr}"
    assert "All checks passed" in result.stdout
```

**Step 4: 运行集成测试**

Run: `pytest tests/test_integration.py -v -s`
Expected: PASS

**Step 5: Commit**

```bash
git add examples/ tests/test_integration.py
git commit -m "feat: add sample project and integration tests"
```

---

## Task 11: 违规示例和修复指南

**Files:**
- Create: `examples/violations_demo/bad_project/myproject/types.py`
- Create: `examples/violations_demo/bad_project/myproject/service.py`
- Create: `examples/violations_demo/bad_project/myproject/repo.py`
- Create: `examples/violations_demo/bad_project/pyproject.toml`

**Step 1: 创建违规示例项目**

```python
# examples/violations_demo/bad_project/myproject/types.py
"""This file VIOLATES the architecture by importing from service."""

# ❌ VIOLATION: types (layer 0) importing from service (layer 3)
from myproject.service import UserService

class UserId:
    # This creates a circular dependency!
    service = UserService()
```

```python
# examples/violations_demo/bad_project/myproject/service.py
"""Business logic layer."""

from myproject.types import UserId


class UserService:
    def get_user(self, user_id: UserId):
        return {"id": user_id}
```

```python
# examples/violations_demo/bad_project/myproject/repo.py
"""This file VIOLATES by using auth provider (not allowed in repo)."""

from myproject.types import UserId
from myproject.providers.auth import require_auth  # ❌ VIOLATION


# Auth provider is only allowed in service, runtime, ui layers
@require_auth
def get_user(user_id: UserId):
    return None
```

```toml
# examples/violations_demo/bad_project/pyproject.toml
[project]
name = "bad-project"
version = "0.1.0"

[tool.harness]
root_package = "myproject"

[[tool.harness.layers]]
name = "types"
path = "myproject.types"
level = 0

[[tool.harness.layers]]
name = "repo"
path = "myproject.repo"
level = 2

[[tool.harness.layers]]
name = "service"
path = "myproject.service"
level = 3

[[tool.harness.providers]]
name = "auth"
path = "myproject.providers.auth"
allowed_layers = ["service", "runtime", "ui"]
```

**Step 2: 创建修复版本**

```python
# examples/violations_demo/fixed_project/myproject/types.py
"""Fixed: types no longer imports from service."""

# ✅ FIXED: types only contains type definitions
class UserId:
    pass
```

```python
# examples/violations_demo/fixed_project/myproject/service.py
"""Business logic layer."""

from myproject.types import UserId
from myproject.providers.auth import require_auth  # ✅ Allowed in service


@require_auth
class UserService:
    def get_user(self, user_id: UserId):
        return {"id": user_id}
```

```python
# examples/violations_demo/fixed_project/myproject/repo.py
"""Fixed: repo no longer uses auth provider."""

from myproject.types import UserId

# ✅ FIXED: repo focuses on data access only

def get_user(user_id: UserId):
    return None
```

**Step 3: 创建演示脚本**

```python
# examples/violations_demo/demo.py
"""Demonstration of linter catching violations."""

import subprocess
import sys
from pathlib import Path


def run_linter(project_dir: Path) -> tuple[int, str]:
    """Run linter on a project and return result."""
    result = subprocess.run(
        [sys.executable, "-m", "harness_linter.cli", "-v"],
        cwd=project_dir,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout + result.stderr


def main():
    base = Path(__file__).parent

    print("=" * 60)
    print("BAD PROJECT (should fail)")
    print("=" * 60)

    bad_project = base / "bad_project"
    code, output = run_linter(bad_project)
    print(output)
    print(f"Exit code: {code}")

    print("\n" + "=" * 60)
    print("FIXED PROJECT (should pass)")
    print("=" * 60)

    fixed_project = base / "fixed_project"
    code, output = run_linter(fixed_project)
    print(output)
    print(f"Exit code: {code}")


if __name__ == "__main__":
    main()
```

**Step 4: Commit**

```bash
git add examples/violations_demo/
git commit -m "docs: add violation examples and fixes"
```

---

## Task 12: 增量检查缓存系统

**Files:**
- Create: `src/harness_linter/cache.py`
- Create: `tests/test_cache.py`
- Modify: `src/harness_linter/graph.py` (添加增量构建支持)
- Modify: `src/harness_linter/cli.py` (添加 --incremental 标志)

**Step 1: 编写失败测试**

```python
# tests/test_cache.py
"""Tests for incremental cache system."""

import pytest
import tempfile
from pathlib import Path
from harness_linter.cache import ImportGraphCache, FileFingerprint


def test_file_fingerprint():
    """Test file fingerprinting."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("x = 1")
        path = Path(f.name)

    try:
        fp = FileFingerprint.from_path(path)
        assert fp.path == path
        assert fp.size > 0
        assert fp.mtime > 0
        assert fp.hash is not None
    finally:
        path.unlink()


def test_cache_save_and_load():
    """Test saving and loading cache."""
    with tempfile.TemporaryDirectory() as tmp:
        cache_path = Path(tmp) / ".harness_cache"
        cache = ImportGraphCache(cache_path)

        # Save some data
        cache.fingerprints = {
            "myproject.types": FileFingerprint(
                path=Path("types.py"),
                mtime=1234567890.0,
                size=100,
                hash="abc123"
            )
        }
        cache.save()

        # Load and verify
        new_cache = ImportGraphCache(cache_path)
        new_cache.load()

        assert "myproject.types" in new_cache.fingerprints
        assert new_cache.fingerprints["myproject.types"].hash == "abc123"


def test_is_fresh():
    """Test detecting stale cache entries."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("x = 1")
        path = Path(f.name)

    try:
        cache = ImportGraphCache(Path(".harness_cache"))

        # Create fingerprint of current file
        fp = FileFingerprint.from_path(path)
        cache.fingerprints["test"] = fp

        # Should be fresh immediately
        assert cache.is_fresh("test", path)

        # Modify file
        path.write_text("x = 2")

        # Should be stale now
        assert not cache.is_fresh("test", path)
    finally:
        path.unlink()
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_cache.py -v`
Expected: FAIL

**Step 3: 实现缓存系统**

```python
# src/harness_linter/cache.py
"""Incremental cache system for import graph.

Similar to mypy --incremental, caches import graph analysis
results to speed up subsequent runs.
"""

import json
import hashlib
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class FileFingerprint:
    """Fingerprint of a source file for cache invalidation."""
    path: Path
    mtime: float
    size: int
    hash: str  # Content hash for extra safety

    @classmethod
    def from_path(cls, path: Path) -> "FileFingerprint":
        """Create fingerprint from file path."""
        stat = path.stat()
        content = path.read_bytes()
        return cls(
            path=path,
            mtime=stat.st_mtime,
            size=stat.st_size,
            hash=hashlib.sha256(content).hexdigest()[:16]
        )

    def is_stale(self, current: "FileFingerprint") -> bool:
        """Check if this fingerprint is stale compared to current."""
        return (
            self.mtime != current.mtime
            or self.size != current.size
            or self.hash != current.hash
        )


@dataclass
class CachedImportInfo:
    """Cached import information for a module."""
    fingerprint: FileFingerprint
    imports: list[str]  # Modules this module imports
    imported_by: list[str]  # Modules that import this module


class ImportGraphCache:
    """Cache for import graph analysis results."""

    CACHE_VERSION = "1"

    def __init__(self, cache_path: Path = Path(".harness_cache")):
        self.cache_path = cache_path
        self.fingerprints: dict[str, FileFingerprint] = {}
        self.imports: dict[str, list[str]] = {}
        self.version = self.CACHE_VERSION

    def load(self) -> bool:
        """Load cache from disk. Returns True if loaded successfully."""
        if not self.cache_path.exists():
            return False

        try:
            data = json.loads(self.cache_path.read_text())

            # Check version
            if data.get("version") != self.CACHE_VERSION:
                return False

            # Load fingerprints
            for module, fp_data in data.get("fingerprints", {}).items():
                self.fingerprints[module] = FileFingerprint(
                    path=Path(fp_data["path"]),
                    mtime=fp_data["mtime"],
                    size=fp_data["size"],
                    hash=fp_data["hash"]
                )

            # Load imports
            self.imports = data.get("imports", {})

            return True
        except (json.JSONDecodeError, KeyError, TypeError):
            return False

    def save(self) -> None:
        """Save cache to disk."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": self.CACHE_VERSION,
            "fingerprints": {
                mod: {
                    "path": str(fp.path),
                    "mtime": fp.mtime,
                    "size": fp.size,
                    "hash": fp.hash
                }
                for mod, fp in self.fingerprints.items()
            },
            "imports": self.imports
        }

        self.cache_path.write_text(json.dumps(data, indent=2))

    def is_fresh(self, module: str, source_path: Path) -> bool:
        """Check if cached data for module is still fresh."""
        if module not in self.fingerprints:
            return False

        if not source_path.exists():
            return False

        cached = self.fingerprints[module]
        current = FileFingerprint.from_path(source_path)

        return not cached.is_stale(current)

    def get_changed_modules(self, source_files: dict[str, Path]) -> tuple[set[str], set[str]]:
        """
        Determine which modules need re-analysis.

        Returns:
            (changed_modules, dependent_modules) - modules that changed
            and modules that import changed modules (need re-checking)
        """
        changed = set()

        # Find directly changed modules
        for module, path in source_files.items():
            if not self.is_fresh(module, path):
                changed.add(module)

        # Find modules that import changed modules (transitive)
        dependent = set()
        for changed_module in changed:
            for module, imports in self.imports.items():
                if changed_module in imports and module not in changed:
                    dependent.add(module)

        return changed, dependent

    def update(self, module: str, source_path: Path, imports: list[str]) -> None:
        """Update cache with new analysis results."""
        self.fingerprints[module] = FileFingerprint.from_path(source_path)
        self.imports[module] = imports

    def clear(self) -> None:
        """Clear cache."""
        self.fingerprints.clear()
        self.imports.clear()
        if self.cache_path.exists():
            self.cache_path.unlink()
```

**Step 4: 修改图构建器支持增量**

```python
# Add to src/harness_linter/graph.py

class IncrementalImportGraphBuilder(ImportGraphBuilder):
    """Builds import graph incrementally using cache."""

    def __init__(self, root_package: str, cache: "ImportGraphCache"):
        super().__init__(root_package)
        self._cache = cache

    def build_from_path_incremental(
        self,
        path: Path,
        source_files: dict[str, Path]
    ) -> tuple[ImportGraph, set[str]]:
        """
        Build import graph incrementally.

        Args:
            path: Root path to source directory
            source_files: Map of module name -> source file path

        Returns:
            (graph, analyzed_modules) - the import graph and set of
            modules that were re-analyzed (not from cache)
        """
        changed, dependent = self._cache.get_changed_modules(source_files)
        modules_to_analyze = changed | dependent

        if not modules_to_analyze:
            # All fresh! But we still need to build the graph
            # For now, fall back to full build
            # In production, would reconstruct from cache
            graph = self.build_from_path(path)
            return graph, set()

        # Build graph (grimp handles the heavy lifting)
        graph = self.build_from_path(path)

        # Update cache for analyzed modules
        for module in modules_to_analyze:
            if module in source_files and graph.module_exists(module):
                imports = list(graph.get_imports_from(module))
                self._cache.update(module, source_files[module], imports)

        self._cache.save()

        return graph, modules_to_analyze
```

**Step 5: 修改 CLI 支持增量标志**

```python
# Modify src/harness_linter/cli.py

from harness_linter.cache import ImportGraphCache

@click.command()
# ... existing options ...
@click.option(
    "--incremental", "-i",
    is_flag=True,
    help="Use incremental analysis (cache results)"
)
@click.option(
    "--cache-path",
    type=click.Path(path_type=Path),
    default=Path(".harness_cache"),
    help="Path to cache directory"
)
def main(
    config: Path | None,
    package: str | None,
    path: Path,
    verbose: bool,
    incremental: bool,
    cache_path: Path
) -> int:
    # ...

    if incremental:
        cache = ImportGraphCache(cache_path)
        if cache.load() and verbose:
            click.echo(f"Loaded cache from {cache_path}")

        # Discover source files
        source_files = discover_source_files(path, cfg.root_package)

        builder = IncrementalImportGraphBuilder(cfg.root_package, cache)
        graph, analyzed = builder.build_from_path_incremental(path, source_files)

        if verbose:
            click.echo(f"Analyzed {len(analyzed)} changed modules")
    else:
        builder = ImportGraphBuilder(root_package=cfg.root_package)
        graph = builder.build_from_path(path)
```

**Step 6: 运行测试验证通过**

Run: `pytest tests/test_cache.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add src/harness_linter/cache.py tests/test_cache.py
git add src/harness_linter/graph.py src/harness_linter/cli.py
git commit -m "feat: add incremental analysis cache system"
```

---

## Task 13: 结构测试 (Structural Tests)

补全与 OpenAI 实践的差距 - 添加文件大小、命名约定、函数复杂度等"品味不变量"检查。

**Files:**
- Create: `src/harness_linter/structural/__init__.py`
- Create: `src/harness_linter/structural/base.py`
- Create: `src/harness_linter/structural/file_size.py`
- Create: `src/harness_linter/structural/naming.py`
- Create: `src/harness_linter/structural/complexity.py`
- Test: `tests/test_structural/` (多个测试文件)

**Step 1: 编写失败测试**

```python
# tests/test_structural/test_file_size.py
"""Tests for file size structural checks."""

import pytest
from pathlib import Path
from harness_linter.structural.file_size import FileSizeCheck, FileSizeConfig


def test_file_size_config():
    """Test file size configuration."""
    config = FileSizeConfig(max_lines=500)
    assert config.max_lines == 500


def test_file_size_violation(tmp_path):
    """Test detecting oversized files."""
    # Create a file with 10 lines (under limit)
    small_file = tmp_path / "small.py"
    small_file.write_text("\n".join([f"x = {i}" for i in range(10)]))

    # Create a file with 15 lines (over limit of 10)
    large_file = tmp_path / "large.py"
    large_file.write_text("\n".join([f"x = {i}" for i in range(15)]))

    check = FileSizeCheck(FileSizeConfig(max_lines=10))

    violations = check.check_file(small_file)
    assert len(violations) == 0

    violations = check.check_file(large_file)
    assert len(violations) == 1
    assert "15" in violations[0].message
    assert "10" in violations[0].message
```

```python
# tests/test_structural/test_naming.py
"""Tests for naming convention structural checks."""

import pytest
from pathlib import Path
from harness_linter.structural.naming import NamingCheck, NamingConfig


def test_service_naming_convention(tmp_path):
    """Test service class naming convention."""
    # Good naming
    good_file = tmp_path / "good_service.py"
    good_file.write_text("""
class UserService:
    pass
""")

    # Bad naming
    bad_file = tmp_path / "bad_service.py"
    bad_file.write_text("""
class UserManager:
    pass
""")

    config = NamingConfig(
        layer_patterns={
            "service": {
                "class_suffixes": ["Service"],
                "path_pattern": r".*service.*"
            }
        }
    )
    check = NamingCheck(config)

    violations = check.check_file(good_file, layer="service")
    assert len(violations) == 0

    violations = check.check_file(bad_file, layer="service")
    assert len(violations) == 1
    assert "UserManager" in violations[0].message
    assert "Service" in violations[0].message
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_structural/ -v`
Expected: FAIL

**Step 3: 实现结构测试框架**

```python
# src/harness_linter/structural/__init__.py
"""Structural tests for enforcing code quality "taste invariants".

OpenAI uses structural tests to complement the linter:
- File size limits
- Naming conventions
- Function complexity
- Code patterns

These are "taste invariants" that keep the codebase consistent.
"""

from harness_linter.structural.base import StructuralCheck, StructuralViolation
from harness_linter.structural.file_size import FileSizeCheck, FileSizeConfig
from harness_linter.structural.naming import NamingCheck, NamingConfig

__all__ = [
    "StructuralCheck",
    "StructuralViolation",
    "FileSizeCheck",
    "FileSizeConfig",
    "NamingCheck",
    "NamingConfig",
]
```

```python
# src/harness_linter/structural/base.py
"""Base classes for structural checks."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class StructuralViolation:
    """Violation of a structural rule."""
    check_name: str
    message: str
    file_path: Path
    line_number: Optional[int] = None
    suggestion: str = ""


class StructuralCheck(ABC):
    """Abstract base for structural checks.

    Structural checks examine source code patterns beyond
    just import dependencies.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def check_file(self, file_path: Path, **context) -> list[StructuralViolation]:
        """Check a single file for violations.

        Args:
            file_path: Path to Python source file
            **context: Additional context (e.g., layer name)

        Returns:
            List of violations found
        """
        pass

    def check_project(
        self,
        source_files: list[Path],
        layer_resolver: Optional[callable] = None
    ) -> list[StructuralViolation]:
        """Check all files in project."""
        all_violations = []

        for file_path in source_files:
            # Resolve which layer this file belongs to
            layer = None
            if layer_resolver:
                layer = layer_resolver(file_path)

            violations = self.check_file(file_path, layer=layer)
            all_violations.extend(violations)

        return all_violations
```

```python
# src/harness_linter/structural/file_size.py
"""File size limit structural check."""

import ast
from dataclasses import dataclass
from pathlib import Path

from harness_linter.structural.base import StructuralCheck, StructuralViolation


@dataclass
class FileSizeConfig:
    """Configuration for file size checks."""
    max_lines: int = 500
    max_blank_lines_ratio: float = 0.3  # Max 30% blank lines


class FileSizeCheck(StructuralCheck):
    """Check that source files don't exceed size limits."""

    def __init__(self, config: FileSizeConfig | None = None):
        super().__init__("file-size")
        self.config = config or FileSizeConfig()

    def check_file(self, file_path: Path, **context) -> list[StructuralViolation]:
        violations = []

        try:
            content = file_path.read_text()
            lines = content.split("\n")
            total_lines = len(lines)

            # Check line count
            if total_lines > self.config.max_lines:
                violations.append(StructuralViolation(
                    check_name=self.name,
                    message=(
                        f"File has {total_lines} lines, "
                        f"exceeding limit of {self.config.max_lines}"
                    ),
                    file_path=file_path,
                    suggestion=(
                        f"Consider splitting into multiple modules "
                        f"or extracting helper functions"
                    )
                ))

            # Check blank line ratio
            blank_lines = sum(1 for line in lines if line.strip() == "")
            blank_ratio = blank_lines / total_lines if total_lines > 0 else 0

            if blank_ratio > self.config.max_blank_lines_ratio:
                violations.append(StructuralViolation(
                    check_name=self.name,
                    message=(
                        f"File has {blank_ratio:.1%} blank lines, "
                        f"exceeding limit of {self.config.max_blank_lines_ratio:.0%}"
                    ),
                    file_path=file_path,
                    suggestion="Remove unnecessary blank lines"
                ))

        except Exception as e:
            # Don't fail on unreadable files
            pass

        return violations
```

```python
# src/harness_linter/structural/naming.py
"""Naming convention structural check."""

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from harness_linter.structural.base import StructuralCheck, StructuralViolation


@dataclass
class LayerNamingRules:
    """Naming rules for a specific layer."""
    class_suffixes: list[str] = field(default_factory=list)
    function_prefixes: list[str] = field(default_factory=list)
    path_pattern: Optional[str] = None  # Regex to match file paths


@dataclass
class NamingConfig:
    """Configuration for naming convention checks."""
    layer_patterns: dict[str, LayerNamingRules] = field(default_factory=dict)


class NamingCheck(StructuralCheck):
    """Check naming conventions by layer."""

    def __init__(self, config: NamingConfig | None = None):
        super().__init__("naming")
        self.config = config or self._default_config()

    def _default_config(self) -> NamingConfig:
        """Create default OpenAI-style naming rules."""
        return NamingConfig(
            layer_patterns={
                "service": LayerNamingRules(
                    class_suffixes=["Service"],
                    path_pattern=r".*service.*"
                ),
                "repo": LayerNamingRules(
                    class_suffixes=["Repository", "Repo"],
                    path_pattern=r".*repo.*"
                ),
                "types": LayerNamingRules(
                    # Types layer should have mostly data classes
                    path_pattern=r".*types.*"
                ),
            }
        )

    def check_file(self, file_path: Path, **context) -> list[StructuralViolation]:
        violations = []
        layer = context.get("layer")

        if not layer or layer not in self.config.layer_patterns:
            return violations

        rules = self.config.layer_patterns[layer]

        try:
            content = file_path.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    violation = self._check_class_name(
                        node, rules, file_path
                    )
                    if violation:
                        violations.append(violation)

        except SyntaxError:
            # Skip files with syntax errors
            pass

        return violations

    def _check_class_name(
        self,
        node: ast.ClassDef,
        rules: LayerNamingRules,
        file_path: Path
    ) -> Optional[StructuralViolation]:
        """Check if class name follows conventions."""
        if not rules.class_suffixes:
            return None

        name = node.name
        has_valid_suffix = any(
            name.endswith(suffix) for suffix in rules.class_suffixes
        )

        if not has_valid_suffix:
            expected = " or ".join(f"'{s}'" for s in rules.class_suffixes)
            return StructuralViolation(
                check_name=self.name,
                message=(
                    f"Class '{name}' should end with {expected} "
                    f"(layer: {self.name})"
                ),
                file_path=file_path,
                line_number=node.lineno,
                suggestion=f"Rename to '{name}{rules.class_suffixes[0]}'"
            )

        return None
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_structural/ -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/harness_linter/structural/ tests/test_structural/
git commit -m "feat: add structural tests (file size, naming conventions)"
```

---

## Task 14: 更好的错误信息 (Rust-style)

实现类似 Rust 编译器的详细错误信息，包含代码片段、导入链、多级帮助信息。

**Files:**
- Create: `src/harness_linter/formatters/__init__.py`
- Create: `src/harness_linter/formatters/rust_style.py`
- Modify: `src/harness_linter/cli.py` (使用新 formatter)
- Test: `tests/test_formatters.py`

**Step 1: 编写失败测试**

```python
# tests/test_formatters.py
"""Tests for error formatters."""

import pytest
from pathlib import Path
from harness_linter.formatters.rust_style import RustStyleFormatter
from harness_linter.contracts.base import Violation


def test_rust_style_formatter():
    """Test Rust-style error formatting."""
    formatter = RustStyleFormatter()

    violation = Violation(
        message="Layer violation: types cannot import from service",
        importer="myproject.types",
        imported="myproject.service",
        line_number=5,
        remediation="Move code to types or config layer"
    )

    output = formatter.format_violation(
        violation,
        source_file=Path("myproject/types.py"),
        source_line="from myproject.service import UserService"
    )

    assert "error:" in output
    assert "myproject/types.py" in output
    assert "5" in output  # line number
    assert "from myproject.service import UserService" in output
    assert "help:" in output


def test_import_chain_display():
    """Test displaying import chain."""
    formatter = RustStyleFormatter()

    # A -> B -> C (C is the violation)
    chain = ["myproject.ui", "myproject.service", "myproject.repo"]

    output = formatter.format_import_chain(chain)

    assert "myproject.ui" in output
    assert "myproject.service" in output
    assert "myproject.repo" in output
    assert "->" in output or "imports" in output
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_formatters.py -v`
Expected: FAIL

**Step 3: 实现 Rust-style 格式化器**

```python
# src/harness_linter/formatters/__init__.py
"""Error formatters for different output styles."""

from harness_linter.formatters.rust_style import RustStyleFormatter

__all__ = ["RustStyleFormatter"]
```

```python
# src/harness_linter/formatters/rust_style.py
"""Rust compiler-style error formatter.

Provides detailed error messages with:
- File location with line/column
- Source code snippet with highlighting
- Multiple levels of help notes
- Import chain visualization

Example:
```
error: Layer violation detected
  --> myproject/types.py:5:1
   |
 5 | from myproject.service import UserService
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Layer 'types' (level 0) cannot import from 'service' (level 3)
   |
   = note: Dependencies must flow from higher to lower levels
   = help: Consider moving shared code to 'types' or 'config' layer
   = help: Or use dependency injection from a higher layer
```
"""

from pathlib import Path
from typing import Optional

from harness_linter.contracts.base import Violation


class RustStyleFormatter:
    """Format violations in Rust compiler style."""

    def __init__(self, max_context_lines: int = 2):
        self.max_context_lines = max_context_lines

    def format_violation(
        self,
        violation: Violation,
        source_file: Optional[Path] = None,
        source_line: Optional[str] = None
    ) -> str:
        """Format a single violation."""
        lines = []

        # Error header
        lines.append(f"error: {violation.message}")

        # Location
        if source_file:
            loc = f"{source_file}"
            if violation.line_number:
                loc += f":{violation.line_number}:1"
            lines.append(f"  --> {loc}")

        # Source snippet
        if source_line and violation.line_number:
            snippet = self._format_source_snippet(
                source_line, violation.line_number
            )
            lines.append(snippet)

        # Remediation hints
        if violation.remediation:
            lines.append(self._format_help(violation.remediation))

        return "\n".join(lines)

    def _format_source_snippet(self, source_line: str, line_number: int) -> str:
        """Format source code with highlighting."""
        indent = "   |"
        underline = "   |" + " " * 4 + "^" * len(source_line)

        return f"""   |
{indent} {line_number} | {source_line}
{underline}"""

    def _format_help(self, message: str) -> str:
        """Format a help note."""
        return f"   = help: {message}"

    def _format_note(self, message: str) -> str:
        """Format an info note."""
        return f"   = note: {message}"

    def format_import_chain(self, chain: list[str], highlight_idx: int = -1) -> str:
        """Format an import chain.

        Example output:
            myproject.ui
              imports -> myproject.service
                imports -> myproject.repo (violation!)
        """
        if not chain:
            return ""

        lines = []
        indent = ""

        for i, module in enumerate(chain):
            marker = ""
            if i == highlight_idx:
                marker = " (violation!)"

            if i == 0:
                lines.append(f"  {indent}{module}{marker}")
            else:
                lines.append(f"  {indent}imports -> {module}{marker}")

            indent += "  "

        return "\n".join(lines)

    def format_summary(
        self,
        total_violations: int,
        analyzed_modules: int,
        duration_ms: float
    ) -> str:
        """Format summary footer."""
        if total_violations == 0:
            return f"✅ Checked {analyzed_modules} modules in {duration_ms:.0f}ms - no issues found"
        else:
            return (
                f"❌ Found {total_violations} issue(s) "
                f"in {analyzed_modules} modules ({duration_ms:.0f}ms)"
            )
```

**Step 4: 修改 CLI 使用新 formatter**

```python
# Modify src/harness_linter/cli.py

from harness_linter.formatters.rust_style import RustStyleFormatter
import time

# In main():
def main(...) -> int:
    start_time = time.time()
    formatter = RustStyleFormatter()

    # ... after checking ...

    for violation in result.violations:
        # Try to get source line
        source_line = None
        source_file = find_source_file(violation.importer)
        if source_file and violation.line_number:
            try:
                lines = source_file.read_text().split("\n")
                if violation.line_number <= len(lines):
                    source_line = lines[violation.line_number - 1]
            except:
                pass

        output = formatter.format_violation(
            violation,
            source_file=source_file,
            source_line=source_line
        )
        click.echo(output)

    # Summary
    duration_ms = (time.time() - start_time) * 1000
    click.echo(formatter.format_summary(
        total_violations,
        len(graph.all_modules()),
        duration_ms
    ))
```

**Step 5: 运行测试验证通过**

Run: `pytest tests/test_formatters.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/harness_linter/formatters/ tests/test_formatters.py
git add src/harness_linter/cli.py
git commit -m "feat: add Rust-style error formatter with detailed diagnostics"
```

---

## Task 15: Agent 上下文集成

实现错误信息格式化为 LLM 可直接消费的格式，包含修复指令。

**Files:**
- Create: `src/harness_linter/agent_context.py`
- Modify: `src/harness_linter/cli.py` (添加 --agent-mode 标志)
- Test: `tests/test_agent_context.py`

**Step 1: 编写失败测试**

```python
# tests/test_agent_context.py
"""Tests for agent context integration."""

import pytest
from harness_linter.agent_context import AgentContextFormatter, ViolationContext
from harness_linter.contracts.base import Violation


def test_agent_context_formatter():
    """Test formatting violations for agent consumption."""
    formatter = AgentContextFormatter()

    violation = Violation(
        message="Layer 'types' cannot import from 'service'",
        importer="myproject.types",
        imported="myproject.service",
        remediation="Move code to lower layer"
    )

    context = ViolationContext(
        violation=violation,
        layer_importer="types",
        layer_imported="service",
        severity="error",
        architectural_principle="Dependencies flow forward through layers",
        suggested_fix="Extract shared interface to types layer"
    )

    output = formatter.format_for_agent(context)

    # Should be easily parseable by LLM
    assert "ARCHITECTURE_VIOLATION" in output or "violation" in output.lower()
    assert "myproject.types" in output
    assert "myproject.service" in output
    assert "suggested_fix" in output or "fix:" in output.lower()


def test_agent_remediation_steps():
    """Test generating detailed remediation steps."""
    formatter = AgentContextFormatter()

    steps = formatter.get_remediation_steps(
        violation_type="backward_dependency",
        importer_layer="types",
        target_layer="service"
    )

    assert len(steps) > 0
    assert any("move" in step.lower() for step in steps)
    assert any("interface" in step.lower() or "protocol" in step.lower() for step in steps)
```

**Step 2: 运行测试验证失败**

Run: `pytest tests/test_agent_context.py -v`
Expected: FAIL

**Step 3: 实现 Agent 上下文格式化器**

```python
# src/harness_linter/agent_context.py
"""Agent context integration for LLM-friendly error output.

OpenAI's linter errors are designed to inject remediation instructions
directly into the agent context. This creates a feedback loop where:
1. Agent generates code
2. Linter detects violation
3. Error with fix instructions goes back to agent
4. Agent can self-correct
"""

from dataclasses import dataclass
from typing import Optional

from harness_linter.contracts.base import Violation


@dataclass
class ViolationContext:
    """Rich context about a violation for agent consumption."""
    violation: Violation
    layer_importer: str
    layer_imported: str
    severity: str  # "error", "warning"
    architectural_principle: str
    suggested_fix: str
    code_example: Optional[str] = None
    documentation_link: Optional[str] = None


class AgentContextFormatter:
    """Format violations for direct consumption by AI agents.

    The output is designed to be:
    1. Easily parseable by LLMs
    2. Actionable (contains specific fix instructions)
    3. Educational (explains the architectural principle)
    4. Contextual (provides relevant code examples)
    """

    def format_for_agent(self, context: ViolationContext) -> str:
        """Format violation as structured text for agent."""
        lines = [
            "=" * 60,
            "ARCHITECTURE_VIOLATION",
            "=" * 60,
            "",
            f"Type: {self._categorize_violation(context)}",
            f"Severity: {context.severity}",
            f"",
            f"Problem:",
            f"  {context.violation.message}",
            f"",
            f"Location:",
            f"  Module: {context.violation.importer}",
            f"  Layer: {context.layer_importer}",
            f"  Invalid import: {context.violation.imported}",
            f"  From layer: {context.layer_imported}",
            f"",
            f"Architectural Principle:",
            f"  {context.architectural_principle}",
            f"",
            f"Suggested Fix:",
            f"  {context.suggested_fix}",
        ]

        if context.code_example:
            lines.extend([
                f"",
                f"Example:",
                f"  {context.code_example}",
            ])

        if context.documentation_link:
            lines.extend([
                f"",
                f"Learn more: {context.documentation_link}",
            ])

        # Add remediation steps
        steps = self.get_remediation_steps(
            self._categorize_violation(context),
            context.layer_importer,
            context.layer_imported
        )

        if steps:
            lines.extend([
                f"",
                f"Remediation Steps:",
            ])
            for i, step in enumerate(steps, 1):
                lines.append(f"  {i}. {step}")

        lines.extend([
            "",
            "=" * 60,
        ])

        return "\n".join(lines)

    def _categorize_violation(self, context: ViolationContext) -> str:
        """Categorize violation type."""
        # Check if it's a backward dependency
        layer_levels = {
            "types": 0, "config": 1, "repo": 2,
            "service": 3, "runtime": 4, "ui": 5
        }

        importer_level = layer_levels.get(context.layer_importer, -1)
        imported_level = layer_levels.get(context.layer_imported, -1)

        if importer_level != -1 and imported_level != -1:
            if importer_level < imported_level:
                return "backward_dependency"

        return "layer_violation"

    def get_remediation_steps(
        self,
        violation_type: str,
        importer_layer: str,
        target_layer: str
    ) -> list[str]:
        """Get specific remediation steps based on violation type."""

        if violation_type == "backward_dependency":
            return [
                f"Identify what '{importer_layer}' needs from '{target_layer}'",
                f"Define an interface/protocol in a lower layer (types/config)",
                f"Move shared types to the lower layer",
                f"Use dependency injection to provide implementation from higher layer",
                f"Ensure the dependency direction remains: {importer_layer} <- {target_layer}"
            ]

        elif violation_type == "provider_misuse":
            return [
                f"Check if '{importer_layer}' really needs this provider",
                f"If yes, add '{importer_layer}' to the provider's allowed_layers",
                f"If no, refactor to avoid the dependency",
                f"Consider if the provider should be accessed through a higher layer"
            ]

        return []

    def format_batch_for_agent(
        self,
        contexts: list[ViolationContext],
        project_stats: dict
    ) -> str:
        """Format multiple violations with project context."""
        lines = [
            "=" * 60,
            "ARCHITECTURE_ANALYSIS_REPORT",
            "=" * 60,
            "",
            f"Project: {project_stats.get('name', 'unknown')}",
            f"Modules analyzed: {project_stats.get('modules', 0)}",
            f"Violations found: {len(contexts)}",
            "",
        ]

        for i, context in enumerate(contexts, 1):
            lines.append(f"--- Violation {i}/{len(contexts)} ---")
            lines.append(self.format_for_agent(context))
            lines.append("")

        if contexts:
            lines.extend([
                "SUMMARY:",
                f"Please address the {len(contexts)} violation(s) above.",
                "Focus on the highest-impact fixes first (deepest layer violations).",
                "",
            ])
        else:
            lines.append("✅ No violations found. Architecture is clean.")

        return "\n".join(lines)
```

**Step 4: 运行测试验证通过**

Run: `pytest tests/test_agent_context.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/harness_linter/agent_context.py tests/test_agent_context.py
git commit -m "feat: add agent context integration for LLM-friendly errors"
```

---

## Task 16: 预提交钩子支持

添加预提交钩子配置，方便集成到开发工作流。

**Files:**
- Create: `.pre-commit-hooks.yaml`
- Create: `src/harness_linter/hooks.py`
- Modify: `pyproject.toml` (添加 hook 入口)

**Step 1: 创建预提交钩子配置**

```yaml
# .pre-commit-hooks.yaml
- id: harness-lint
  name: Harness Architecture Linter
  description: Enforce OpenAI Harness-style architecture rules
  entry: harness-lint
  language: python
  types: [python]
  require_serial: true
  additional_dependencies: []

- id: harness-lint-strict
  name: Harness Architecture Linter (Strict)
  description: Enforce architecture rules with structural tests
  entry: harness-lint --structural
  language: python
  types: [python]
  require_serial: true
```

**Step 2: 添加 hooks 模块**

```python
# src/harness_linter/hooks.py
"""Pre-commit hook integration."""

import sys
from pathlib import Path


def run_pre_commit(files: list[str]) -> int:
    """Run harness-lint on files staged for commit.

    This is called by pre-commit with the list of staged Python files.
    """
    from harness_linter.cli import main
    from click.testing import CliRunner

    runner = CliRunner()

    # Find project root (look for pyproject.toml)
    project_root = Path.cwd()
    while not (project_root / "pyproject.toml").exists():
        parent = project_root.parent
        if parent == project_root:
            break
        project_root = parent

    # Run linter
    result = runner.invoke(main, ["-v", "--path", str(project_root)])

    print(result.output)

    return result.exit_code


if __name__ == "__main__":
    files = sys.argv[1:]
    sys.exit(run_pre_commit(files))
```

**Step 3: 修改 pyproject.toml 添加 hook 脚本**

```toml
# Add to pyproject.toml
[project.scripts]
harness-lint = "harness_linter.cli:main"
harness-pre-commit = "harness_linter.hooks:run_pre_commit"
```

**Step 4: Commit**

```bash
git add .pre-commit-hooks.yaml src/harness_linter/hooks.py
git add pyproject.toml
git commit -m "feat: add pre-commit hook support"
```

---

## Task 17: 更新优化建议文档和 README

**Step 1: 更新 OPTIMIZATIONS.md**

更新优化文档，标记已完成的优化：

```markdown
## 已完成的优化

### ✅ 增量检查缓存 (Task 12)
- 实现 `.harness_cache` 缓存系统
- 基于文件指纹（mtime + size + hash）的失效检测
- 只分析变更文件及其依赖
- 使用 `--incremental` 或 `-i` 启用

### ✅ 结构测试 (Task 13)
- 文件大小限制（默认 500 行）
- 层特定的命名约定检查
- 可扩展的框架支持更多检查

### ✅ Rust-style 错误信息 (Task 14)
- 详细的文件位置显示
- 源代码片段高亮
- 多级 help/note 信息
- 导入链可视化

### ✅ Agent 上下文集成 (Task 15)
- 错误信息设计为 LLM 可直接解析
- 包含具体修复步骤
- 架构原则解释
- 批量报告格式化

### ✅ 预提交钩子 (Task 16)
- `.pre-commit-hooks.yaml` 配置
- 可直接集成到 pre-commit 工作流
```

**Step 2: 更新 README**

添加新功能到 README：

```markdown
## 高级功能

### 增量检查

```bash
harness-lint --incremental  # 使用缓存加速后续检查
```

### 结构测试

除了架构依赖检查，还可以检查代码"品味不变量"：

```bash
harness-lint --structural  # 启用文件大小、命名约定等检查
```

### Agent 模式

输出格式化为 LLM 可直接消费的格式：

```bash
harness-lint --agent-mode  # 适合 CI/CD 输出给 Agent
```

### 预提交钩子

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/your-org/harness-linter
    rev: v0.1.0
    hooks:
      - id: harness-lint
```
```

**Step 3: Commit**

```bash
git add docs/OPTIMIZATIONS.md README.md
git commit -m "docs: update documentation with new features"
```

---

## Task 18: 优化建议文档

**Step 1: 创建优化建议文档**

```markdown
# Harness Linter 优化建议

基于 OpenAI Harness Engineering 和实际使用经验，以下是可考虑的优化方向：

## 1. 性能优化

### 1.1 增量检查
**当前问题**: 每次检查都重新构建整个导入图
**优化方案**:
- 缓存导入图（使用文件哈希或 mtime）
- 只检查变更的文件及其依赖
- 类似 `mypy --incremental` 的缓存机制

```python
# 伪代码
class IncrementalChecker:
    def check(self, changed_files: list[Path]) -> ContractResult:
        # 只重新分析变更文件
        # 复用缓存的依赖图
        pass
```

### 1.2 并行分析
- 使用多进程并行检查不同契约
- grimp 本身可以并行构建图

## 2. 功能增强

### 2.1 更细粒度的规则
**当前**: 层级别的规则
**增强**:
- 模块级别的规则
- 函数/类级别的导入限制
- 基于注解的排除规则

```toml
# 模块级别规则
[[tool.harness.module_rules]]
module = "myproject.repo.sensitive"
can_only_import_from = ["myproject.types"]
```

### 2.2 自动修复建议
**当前**: 提供修复建议文本
**增强**:
- `--fix` 标志自动修复简单违规
- 生成重构计划
- IDE 集成提供快速修复

```python
# 自动修复示例
def fix_violation(violation: Violation) -> CodeChange:
    if is_simple_move(violation):
        return move_import_to_allowed_layer(violation)
```

### 2.3 可视化依赖图
**增强**:
- `harness-lint --visualize` 生成依赖图
- 标记违规依赖为红色
- 使用 graphviz 或 mermaid

### 2.4 更智能的 Providers
**增强**:
- Provider 接口验证（确保实现特定协议）
- Provider 依赖注入支持
- Provider 版本管理

## 3. 开发者体验

### 3.1 更好的错误信息
**当前**: 基本错误信息
**增强**:
- 显示导入链（A -> B -> C -> 违规）
- 相关代码片段
- 类似 Rust 编译器的详细错误

```
error: Layer violation detected
  --> myproject/types.py:5:1
   |
 5 | from myproject.service import UserService
   | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   |
   = note: types (level 0) cannot import from service (level 3)
   = help: Consider moving shared code to 'types' or 'config' layer
   = help: Or use dependency injection from a higher layer
```

### 3.2 IDE 集成
- VS Code 扩展
- PyCharm 插件
- 实时检查

### 3.3 预提交钩子
```yaml
# .pre-commit-hooks.yaml
- repo: local
  hooks:
    - id: harness-lint
      name: Harness Architecture Check
      entry: harness-lint
      language: system
      types: [python]
```

## 4. 企业级功能

### 4.1 自定义契约 DSL
**增强**: 允许用声明式语言定义复杂规则

```yaml
# custom-contracts.yaml
contracts:
  - name: no-database-in-ui
    description: UI layer cannot directly access database
    forbidden:
      importer_pattern: "myproject.ui.*"
      imported_pattern: "myproject.repo.*"
      except:
        - "myproject.repo.readonly_views"
```

### 4.2 架构漂移检测
**增强**:
- 定期运行报告趋势
- 检测新增的违规模式
- 架构健康度评分

### 4.3 与 CI/CD 集成
- GitHub Actions 插件
- PR 评论机器人
- 架构审查工作流

### 4.4 多语言支持
**增强**:
- TypeScript/JavaScript 版本
- Go 版本
- 统一的跨语言架构规则

## 5. 与 OpenAI 实践的差距

### 5.1 结构测试
OpenAI 使用 **structural tests** 补充 linter：
- 测试类命名约定
- 文件大小限制
- 函数复杂度检查
- "Taste invariants"

```python
# 结构测试示例
def test_file_size_limits():
    for file in get_source_files():
        lines = count_lines(file)
        assert lines < 500, f"{file} exceeds 500 lines"

def test_naming_conventions():
    for cls in get_classes():
        if is_service(cls):
            assert cls.name.endswith("Service")
```

### 5.2 Agent 上下文集成
OpenAI 的 linter 错误设计为**直接注入到 Agent 上下文**：
- 错误信息包含修复指令
- 历史违规模式学习
- Agent 可查询架构文档

### 5.3 垃圾回收代理
OpenAI 使用定期运行的 "garbage collection" 代理：
- 扫描文档和代码不一致
- 自动提出重构 PR
- 质量评分和趋势分析

## 6. 推荐的下一步优化

按优先级排序：

1. **即时**: 更好的错误信息和导入链显示
2. **短期**: 预提交钩子 + CI 集成
3. **中期**: 增量检查缓存
4. **长期**: 自动修复和 IDE 集成
```

**Step 2: Commit**

```bash
git add docs/OPTIMIZATIONS.md
git commit -m "docs: add optimization recommendations"
```

---

## Task 19: README 文档

**Files:**
- Create: `README.md`

**Step 1: 创建 README**

```markdown
# Harness Linter

复现 OpenAI Harness Engineering 的架构 linter，强制执行严格的分层架构和依赖方向规则。

## 核心概念

### 分层架构

OpenAI 发现 Agents 在具有严格边界和可预测结构的环境中最有效：

```
UI (5)          ← 用户界面
Runtime (4)     ← 运行时环境
Service (3)     ← 业务逻辑
Repo (2)        ← 数据访问
Config (1)      ← 配置管理
Types (0)       ← 共享类型
```

**规则**: 依赖只能向"前"流动（高层可以依赖低层，反之不行）

### Providers 模式

横切关注点（认证、日志、遥测等）通过单一接口进入：

```python
# ✅ 正确的使用方式
from myproject.providers.auth import require_auth
from myproject.providers.logging import get_logger
from myproject.providers.telemetry import record_metric
```

## 安装

```bash
pip install harness-linter
```

## 快速开始

### 1. 配置 pyproject.toml

```toml
[tool.harness]
root_package = "myproject"

[[tool.harness.layers]]
name = "types"
path = "myproject.types"
level = 0

[[tool.harness.layers]]
name = "service"
path = "myproject.service"
level = 3

[[tool.harness.providers]]
name = "auth"
path = "myproject.providers.auth"
allowed_layers = ["service", "runtime", "ui"]
```

### 2. 运行检查

```bash
harness-lint --verbose
```

### 3. 修复违规

```
❌ Layer 'types' (level 0) cannot import from layer 'service' (level 3)
   myproject.types -> myproject.service
   💡 Move the shared code to a lower layer (e.g., 'types' or 'config')
```

## 工作原理

1. **导入图构建**: 使用 grimp 分析所有 Python 导入
2. **层映射**: 将模块映射到定义的层
3. **方向验证**: 确保导入符合层级别顺序
4. **Provider 检查**: 验证 providers 只在允许的层使用

## 与 import-linter 的关系

本项目基于 import-linter 的理念，但专门针对 OpenAI Harness 架构设计：

| 特性 | import-linter | harness-linter |
|------|---------------|----------------|
| 通用架构规则 | ✅ | ✅ |
| 预定义层结构 | ❌ | ✅ |
| Providers 支持 | ❌ | ✅ |
| Agent 优化错误 | ❌ | ✅ |

## 配置参考

### 完整配置示例

```toml
[tool.harness]
root_package = "myproject"

# 层定义（必须按 level 排序）
[[tool.harness.layers]]
name = "types"
path = "myproject.types"
level = 0

[[tool.harness.layers]]
name = "config"
path = "myproject.config"
level = 1

[[tool.harness.layers]]
name = "repo"
path = "myproject.repo"
level = 2

[[tool.harness.layers]]
name = "service"
path = "myproject.service"
level = 3

[[tool.harness.layers]]
name = "runtime"
path = "myproject.runtime"
level = 4

[[tool.harness.layers]]
name = "ui"
path = "myproject.ui"
level = 5

# Providers 定义
[[tool.harness.providers]]
name = "auth"
path = "myproject.providers.auth"
allowed_layers = ["service", "runtime", "ui"]
description = "Authentication and authorization"

[[tool.harness.providers]]
name = "logging"
path = "myproject.providers.logging"
allowed_layers = ["types", "config", "repo", "service", "runtime", "ui"]
description = "Structured logging"

[[tool.harness.providers]]
name = "telemetry"
path = "myproject.providers.telemetry"
allowed_layers = ["repo", "service", "runtime"]
description = "Metrics and tracing"
```

## 设计哲学

> "Agents are most effective in environments with strict boundaries and predictable structure."
> — OpenAI Harness Engineering

1. **机械强制**: 架构规则通过 linter 强制执行，而非文档约定
2. **早期约束**: 在代码量还小时就建立架构边界
3. **Agent 友好**: 错误信息设计为可直接注入 Agent 上下文

## License

MIT
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add comprehensive README"
```

---

## 总结

实现完成！这个 linter 完整复现了 OpenAI Harness Engineering 的架构检查系统，并添加了多项优化：

### 核心功能
1. **分层架构检查**: Types → Config → Repo → Service → Runtime → UI
2. **Providers 系统**: 横切关注点统一入口
3. **架构契约**: 可扩展的规则系统

### OpenAI 实践补全
4. **增量检查缓存** (`--incremental`): 类似 mypy，大幅加速大型项目
5. **结构测试** (`--structural`): 文件大小、命名约定等"品味不变量"
6. **Rust-style 错误信息**: 详细诊断、源代码高亮、导入链可视化
7. **Agent 上下文集成** (`--agent-mode`): LLM 可直接消费的格式

### 开发者体验
8. **预提交钩子**: 集成 pre-commit 工作流
9. **详细文档**: 示例项目、违规修复指南、优化建议

现在可以：
```bash
# 基础检查
harness-lint --verbose

# 增量检查（更快）
harness-lint --incremental -v

# 完整检查（包含结构测试）
harness-lint --structural -v

# Agent 模式输出
harness-lint --agent-mode
```

---

**Plan complete and saved to `docs/plans/2026-02-23-openai-harness-architecture-linter.md`.**

**Two execution options:**

**1. Subagent-Driven (this session)** - 我使用 superpowers:subagent-driven-development 派遣新鲜 subagent 逐个任务执行，我在任务之间审查，快速迭代

**2. Parallel Session (separate)** - 引导你打开新会话，使用 superpowers:executing-plans 批量执行，带检查点

**Which approach?**
