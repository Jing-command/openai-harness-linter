# Harness Linter

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

OpenAI Harness-style architecture linter enforcing strict layer dependencies.

## Overview

Harness Linter is a Python architecture linter that enforces a strict 6-layer dependency model inspired by OpenAI's Harness Engineering practices. It ensures your codebase maintains clean architecture boundaries and prevents circular dependencies.

## Features

- **6-Layer Architecture Enforcement**: Types → Config → Repo → Service → Runtime → UI
- **Providers System**: Managed cross-cutting concerns (auth, logging, telemetry, etc.)
- **Import Graph Analysis**: AST-based dependency validation
- **Configurable Rules**: TOML/YAML configuration support
- **CI/CD Ready**: Pre-commit hooks and GitHub Actions support

## Installation

### As a Python Package

```bash
pip install harness-linter
```

Or install from source:

```bash
git clone https://github.com/your-org/harness-linter.git
cd harness-linter
pip install -e ".[dev]"
```

### Using with Claude Code

This linter works well with Claude Code. Add custom commands to your project's `CLAUDE.md`:

```markdown
## Commands

- `/check` - Run `harness-linter check` on current project
- `/init-linter` - Initialize linter config for new project
- `/batch-lint` - Batch check multiple projects

## Commands

- `/check`: Run `harness-linter check` on the current project
- `/init-linter`: Initialize linter configuration for a new project
- `/batch-lint`: Batch check multiple projects in a directory
```

Or use the CLI directly:

```bash
# Check current project
harness-linter check

# Initialize config for new project
harness-linter init

# Batch check multiple projects
harness-linter batch ~/Projects
```

## Quick Start

### 1. Create Configuration

Create `harness-linter.toml` in your project root:

```toml
[tool.harness-linter]
root_package = "myproject"

[tool.harness-linter.layers]
types = { path = "myproject.types", level = 0 }
config = { path = "myproject.config", level = 1 }
repo = { path = "myproject.repo", level = 2 }
service = { path = "myproject.service", level = 3 }
runtime = { path = "myproject.runtime", level = 4 }
ui = { path = "myproject.ui", level = 5 }

[tool.harness-linter.providers]
auth = { path = "myproject.providers.auth", allowed_layers = ["service", "runtime", "ui"] }
logging = { path = "myproject.providers.logging", allowed_layers = ["*"] }
telemetry = { path = "myproject.providers.telemetry", allowed_layers = ["repo", "service", "runtime"] }
```

### 2. Run Linter

```bash
# Basic check
harness-lint

# With all features
harness-lint --incremental --structural --format rust
```

## Advanced Features

### Incremental Checking

Speed up subsequent checks with file fingerprint-based caching:

```bash
harness-lint --incremental  # Use cache to accelerate subsequent checks
harness-lint -i             # Short form
```

Cache is stored in `.harness_cache/` directory and automatically invalidates when files change.

### Structural Testing

Enable file-level architecture checks:

```bash
harness-lint --structural   # Enable file size and naming convention checks
harness-lint -s             # Short form
```

**Configuration:**
```toml
[tool.harness-linter.structural]
max_lines = 500
naming_conventions = [
    { layer = "repo", pattern = "^.*_repository\.py$" },
    { layer = "service", pattern = "^.*_service\.py$" },
]
```

### Rust-style Error Output

Get detailed diagnostic messages similar to Rust compiler:

```bash
harness-lint --format rust  # Detailed diagnostic output
```

**Example output:**
```
error[E1001]: Layer violation detected
  --> myproject/service/user_service.py:12:8
   |
12 | from myproject.ui import user_interface
   |        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   |        |
   |        Service layer cannot depend on UI layer
   |
   = help: Service layer (level 3) can only depend on lower layers
   = note: UI layer is at level 5
```

### Agent Mode

Output format optimized for LLM consumption:

```bash
harness-lint --agent-mode   # LLM-consumable format
```

This produces structured JSON output with fix steps that can be directly consumed by AI assistants.

### Pre-commit Hooks

Integrate into your Git workflow:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/your-org/harness-linter
    rev: v0.1.0
    hooks:
      - id: harness-lint
        args: ['--incremental', '--structural']
```

Install the hook:
```bash
pre-commit install
```

## Architecture

### Layer System

The linter enforces a strict 6-layer architecture where each layer can only depend on lower layers:

```
Level 5: UI Layer          (web interfaces, CLI, API endpoints)
Level 4: Runtime Layer     (app initialization, middleware)
Level 3: Service Layer     (business logic, use cases)
Level 2: Repo Layer        (data access, repositories)
Level 1: Config Layer      (configuration management)
Level 0: Types Layer       (shared type definitions)
```

**Dependency Rule**: Higher layers can import from lower layers, but not vice versa.

### Providers System

Cross-cutting concerns enter through explicit Providers:

- **Auth**: Authentication and authorization
- **Logging**: Structured logging
- **Telemetry**: Metrics and tracing
- **Feature Flags**: Feature toggle system

Each provider declares which layers can access it.

## CLI Reference

```
Usage: harness-lint [OPTIONS] [PATH]

Options:
  -c, --config PATH         Configuration file path
  -f, --format [text|json|rust]  Output format
  --agent-mode              Enable agent-friendly output
  -i, --incremental         Enable incremental checking with cache
  -s, --structural          Enable structural tests
  --max-lines INTEGER       Maximum lines per file (structural test)
  --cache-dir PATH          Cache directory path
  --clear-cache             Clear the cache before running
  -v, --verbose             Verbose output
  --version                 Show version
  --help                    Show this message and exit
```

## Configuration Reference

### Full Configuration Example

```toml
[tool.harness-linter]
root_package = "myproject"

# Layer definitions
[tool.harness-linter.layers]
types = { path = "myproject.types", level = 0 }
config = { path = "myproject.config", level = 1 }
repo = { path = "myproject.repo", level = 2 }
service = { path = "myproject.service", level = 3 }
runtime = { path = "myproject.runtime", level = 4 }
ui = { path = "myproject.ui", level = 5 }

# Provider definitions
[tool.harness-linter.providers]
auth = { path = "myproject.providers.auth", allowed_layers = ["service", "runtime", "ui"] }
logging = { path = "myproject.providers.logging", allowed_layers = ["*"] }
telemetry = { path = "myproject.providers.telemetry", allowed_layers = ["repo", "service", "runtime"] }
config_provider = { path = "myproject.providers.config", allowed_layers = ["repo", "service", "runtime", "ui"] }
feature_flags = { path = "myproject.providers.feature_flags", allowed_layers = ["service", "runtime", "ui"] }

# Structural test settings
[tool.harness-linter.structural]
max_lines = 500
naming_conventions = [
    { layer = "repo", pattern = "^.*_repository\.py$" },
    { layer = "service", pattern = "^.*_service\.py$" },
    { layer = "runtime", pattern = "^.*_runtime\.py$" },
]

# Forbidden imports
[[tool.harness-linter.forbidden]]
importer = "myproject.repo"
imported = "myproject.ui"
message = "Repository layer should not depend on UI layer"
```

## Comparison with OpenAI Practices

| Feature | OpenAI Harness | Harness Linter |
|---------|---------------|----------------|
| Layer Architecture | 6 layers | 6 layers |
| Providers System | ✅ | ✅ |
| Import Graph Analysis | ✅ | ✅ |
| Incremental Checking | ✅ | ✅ |
| Structural Tests | ✅ | ✅ |
| Rust-style Errors | ✅ | ✅ |
| Agent Context Integration | ✅ | ✅ |
| Garbage Collection Agent | ⏳ | ⏳ (Future Work) |

## Development

### Setup

```bash
git clone https://github.com/your-org/harness-linter.git
cd harness-linter
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
pytest --cov=harness_linter
```

### Project Structure

```
openai-harness-linter/
├── src/
│   └── harness_linter/
│       ├── __init__.py
│       ├── cli.py              # Command line interface
│       ├── config.py           # Configuration parsing
│       ├── cache.py            # Incremental cache system
│       ├── structural.py       # Structural tests
│       ├── formatters/         # Output formatters
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── text_formatter.py
│       │   ├── json_formatter.py
│       │   ├── rust_formatter.py
│       │   └── agent_formatter.py
│       ├── contracts/          # Architecture contracts
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── layer_contract.py
│       │   ├── provider_contract.py
│       │   └── forbidden_contract.py
│       ├── graph.py            # Import graph analysis
│       ├── layers.py           # Layer definitions
│       └── providers.py        # Providers system
├── tests/
│   └── test_*.py
├── examples/
│   └── sample_project/         # Example project
├── docs/
│   └── OPTIMIZATIONS.md        # Optimization documentation
├── pyproject.toml
├── README.md
└── .pre-commit-hooks.yaml
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

## Acknowledgments

This project is inspired by the architecture practices at OpenAI's Harness Engineering team.
