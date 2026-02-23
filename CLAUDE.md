# CLAUDE.md - OpenAI Harness Linter

## Project Overview

**OpenAI Harness Linter** - A performance-focused import graph analyzer for enforcing 6-layer architecture in Python projects.

- **Root Package**: `harness_linter`
- **Version**: 0.1.0
- **Repository**: `https://github.com/Jing-command/openai-harness-linter`

## Architecture

### Core Components

```
src/harness_linter/
├── __init__.py          # Package entry point
├── cli.py               # Command-line interface
├── config.py            # Configuration parsing (pyproject.toml)
├── graph.py             # Import graph construction & cycle detection
├── cache.py             # Incremental caching for changed files
├── layers.py            # 6-layer architecture enforcement
├── providers.py         # Provider pattern validation
├── hooks.py             # Pre-commit hook integration
├── agent_context.py     # Agent SDK context management
├── contracts/           # Contract definitions
│   ├── base.py          # Base contract interface
│   ├── layer_contract.py    # Layer validation logic
│   └── provider_contract.py # Provider validation logic
├── formatters/          # Output formatters
│   └── rust_style.py    # Rust-style diagnostic output
└── structural/          # Structural checks
    ├── base.py          # Base structural check
    ├── file_size.py     # File size limits
    └── naming.py        # Naming convention checks
```

### Six-Layer Architecture

Projects using this linter enforce these layers (low to high index):

1. **types** - Pure data types and domain models (index 0)
2. **config** - Configuration management (index 1)
3. **repo** - Data access and persistence (index 2)
4. **service** - Business logic (index 3)
5. **runtime** - Application runtime (index 4)
6. **ui** - User interface layer (index 5)

**Note**: The `providers` system is a separate cross-cutting concern mechanism, not a layer. Providers are explicitly allowed to be used by specific layers.

**Rule**: Higher-index layers can import from lower-index layers, never reverse.

## Configuration

Projects configure the linter in `pyproject.toml`:

```toml
[tool.harness-linter]
root-package = "myproject"
contracts = ["layer", "provider"]
cache-path = ".harness_cache"

[[tool.harness-linter.layers]]
name = "types"
index = 0
modules = ["myproject.types"]

[[tool.harness-linter.providers]]
name = "logging"
modules = ["myproject.providers.logging"]
allowed_layers = ["service", "runtime"]
```

## Development Commands

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=harness_linter

# Run specific test file
pytest tests/test_graph.py -v

# Run linter on example project
cd examples/sample_project && python -m harness_linter check

# Install in development mode
pip install -e .
```

## Key Implementation Details

### Import Graph Construction
- Uses `grimp.build_graph()` to analyze import relationships
- Caches parsed graph to `.harness_cache/` for incremental runs
- Tracks file modification times to invalidate stale cache entries

### Contract System
- `LayerContract`: Validates layer import rules using dependency graph
- `ProviderContract`: Ensures providers only used by allowed layers
- Extensible base class for custom contracts

### Performance Optimizations
- Incremental caching (only re-analyze changed files)
- Graph persistence between runs
- Layer index pre-computation

## Testing Structure

```
tests/
├── test_graph.py          # Import graph & cycle detection
├── test_layers.py         # Layer rule enforcement
├── test_providers.py      # Provider validation
├── test_cache.py          # Caching mechanism
├── test_config.py         # Configuration parsing
├── test_hooks.py          # Pre-commit hook
├── test_hooks.py          # Pre-commit hook
├── test_formatters.py     # Output formatting
├── test_contracts_base.py # Base contract tests
├── test_layer_contract.py # Layer contract tests
├── test_provider_contract.py # Provider contract tests
├── test_agent_context.py  # Agent context tests
└── test_structural/       # Structural checks
    ├── test_file_size.py
    └── test_naming.py
```

## Common Tasks

### Adding a New Contract
1. Create class inheriting from `Contract` in `contracts/`
2. Implement `check(graph, config)` method
3. Add to `CONTRACT_REGISTRY` in `contracts/__init__.py`
4. Add tests in `tests/test_<name>_contract.py`

### Adding a New Formatter
1. Create module in `formatters/`
2. Implement format function accepting `List[Violation]`
3. Register in `formatters/__init__.py`
4. Add CLI option in `cli.py`

### Running on Example Projects
```bash
# Good example (should pass)
cd examples/violations_demo/good
harness-linter check

# Bad example (should fail with violations)
cd examples/violations_demo/bad
harness-linter check
```

## Pre-commit Hook

Projects can add to `.pre-commit-config.yaml`:

```yaml
- repo: local
  hooks:
    - id: harness-linter
      name: Harness Linter
      entry: harness-linter check
      language: system
      types: [python]
      pass_filenames: false
```

## Project Memory

- **Recent Work**: Added `__all__` exports, extracted `_run_contracts` helper for CLI code deduplication
- **Architecture Decisions**: Derive business logic layers from index instead of hardcoding
- **Known Limitations**: Incremental cache optimizes file parsing but full graph still built each run
- **Performance**: Uses `time.perf_counter()` for accurate duration tracking

## Related Projects

See `D:/Projects/` for projects using this linter:
- `final-test/`, `testv2/`, `testnew/` - Test projects with full 6-layer config
- `scan-test/` - Multi-project workspace example
