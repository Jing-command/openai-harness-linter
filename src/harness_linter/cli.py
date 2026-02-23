"""Command-line interface for harness_linter."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from harness_linter.cache import ImportGraphCache
from harness_linter.config import Config, find_project_root, load_config
from harness_linter.contracts.layer_contract import LayerContract
from harness_linter.contracts.provider_contract import ProviderContract
from harness_linter.graph import ImportGraphBuilder, IncrementalImportGraphBuilder
from harness_linter.layers import Layer, LayerRegistry
from harness_linter.providers import Provider, ProviderRegistry
from harness_linter.formatters.rust_style import RustStyleFormatter
from harness_linter.agent_context import AgentContextFormatter, ViolationContext
from harness_linter.structural.base import StructuralViolation
from harness_linter.structural.file_size import FileSizeCheck, FileSizeConfig
from harness_linter.structural.naming import NamingCheck, NamingConfig


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), required=False)
@click.option("--package", "-p", help="Root package name (overrides config)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option(
    "--incremental", "-i", is_flag=True, help="Enable incremental checking using cache"
)
@click.option(
    "--cache-path",
    type=click.Path(path_type=Path),
    default=None,
    help="Path to cache file (default: .harness_cache)",
)
@click.option("--config", "-c", type=click.Path(path_type=Path), help="Config file path")
@click.option(
    "--structural", "-s",
    is_flag=True,
    help="Enable structural tests (file size, naming conventions)"
)
@click.option(
    "--format",
    "format_style",
    type=click.Choice(["default", "rust"]),
    default="default",
    help="Output format style"
)
@click.option(
    "--agent-mode",
    is_flag=True,
    help="Output in LLM-friendly format for AI agents"
)
def main(
    path: Path | None,
    package: str | None,
    verbose: bool,
    incremental: bool,
    cache_path: Path | None,
    config: Path | None,
    structural: bool,
    format_style: str,
    agent_mode: bool,
) -> int:
    """Analyze import graph for a Python package.

    If PATH is not provided, the current directory is used.
    Configuration is loaded from pyproject.toml if available.
    """
    try:
        # Determine the path to analyze
        if path is None:
            path = Path.cwd()

        # Load configuration
        cfg = _load_configuration(config, path, package)
        if cfg is None:
            click.echo(
                "Error: Could not load configuration. "
                "Please specify --package or create a pyproject.toml with [tool.harness-linter] section.",
                err=True,
            )
            return 1

        # Determine cache path
        if cache_path is None:
            cache_path = Path(cfg.cache_path)

        if incremental:
            return _run_incremental(path, cfg, verbose, cache_path, structural, format_style, agent_mode)
        else:
            return _run_full(path, cfg, verbose, structural, format_style, agent_mode)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return 1


def _load_configuration(
    config_path: Path | None, project_path: Path, package: str | None
) -> Config | None:
    """Load configuration from file or create default.

    Args:
        config_path: Explicit config file path, or None to search
        project_path: Path to the project
        package: Explicit package name, or None to use config

    Returns:
        Config if successful, None otherwise
    """
    # Try to load from explicit config path
    if config_path:
        cfg = load_config(config_path)
        if cfg and package:
            cfg.root_package = package
        return cfg

    # Try to load from project path
    cfg = load_config(project_path / "pyproject.toml")
    if cfg:
        if package:
            cfg.root_package = package
        return cfg

    # Try to find project root
    root = find_project_root(project_path)
    if root:
        cfg = load_config(root / "pyproject.toml")
        if cfg:
            if package:
                cfg.root_package = package
            return cfg

    # If package is specified, create default config
    if package:
        return Config.default(package)

    return None


def _run_full(path: Path, config: Config, verbose: bool, structural: bool = False, format_style: str = "default", agent_mode: bool = False) -> int:
    """Run full analysis without caching."""
    builder = ImportGraphBuilder(config.root_package)

    if verbose and not agent_mode:
        click.echo(f"Building import graph for {config.root_package} from {path}")

    graph = builder.build_from_path(path)
    modules = graph.modules

    if verbose and not agent_mode:
        click.echo(f"Found {len(modules)} modules")

    # Set up registries from config
    layer_registry = _build_layer_registry(config)
    provider_registry = _build_provider_registry(config)

    # Initialize formatter if needed
    formatter = RustStyleFormatter() if format_style == "rust" and not agent_mode else None

    # Run contracts
    violations_found = False
    all_violations = []

    if "layer" in config.contracts:
        if verbose and not agent_mode:
            click.echo("Checking layer dependencies...")
        layer_contract = LayerContract(layer_registry)
        result = layer_contract.check(graph)
        if not agent_mode:
            _print_contract_result(result, verbose, formatter, path)
        if not result.is_valid:
            violations_found = True
            all_violations.extend(result.violations)

    if "provider" in config.contracts:
        if verbose and not agent_mode:
            click.echo("Checking provider usage...")
        provider_contract = ProviderContract(layer_registry, provider_registry)
        result = provider_contract.check(graph)
        if not agent_mode:
            _print_contract_result(result, verbose, formatter, path)
        if not result.is_valid:
            violations_found = True
            all_violations.extend(result.violations)

    # Run structural tests if enabled
    structural_violations: list[StructuralViolation] = []
    if structural:
        if verbose and not agent_mode:
            click.echo("Running structural tests...")
        structural_violations = _run_structural_tests(path, layer_registry, verbose, formatter)
        if structural_violations:
            violations_found = True

    # Output results
    if agent_mode:
        # Format for agent consumption
        _print_agent_mode_output(all_violations, layer_registry, provider_registry, len(modules))
    elif format_style == "rust":
        # Calculate duration (placeholder since we don't track it yet)
        duration_ms = 0.0
        summary = formatter.format_summary(
            total_violations=len(all_violations) + len(structural_violations),
            analyzed_modules=len(modules),
            duration_ms=duration_ms,
        )
        click.echo(summary)
    else:
        click.echo(f"\nTotal modules: {len(modules)}")

        if violations_found:
            click.echo("Violations found!")
        else:
            click.echo("No violations found.")

    return 1 if violations_found else 0


def _build_layer_registry(config: Config) -> LayerRegistry:
    """Build a LayerRegistry from configuration.

    Args:
        config: The configuration

    Returns:
        LayerRegistry with configured layers
    """
    registry = LayerRegistry()

    if config.layers:
        for layer_config in config.layers:
            layer = Layer(
                name=layer_config["name"],
                index=layer_config["index"],
                description=layer_config.get("description", ""),
                modules=tuple(layer_config.get("modules", [])),
            )
            registry.register(layer)
    else:
        # Use default layers
        registry.create_standard_harness_layers()

    return registry


def _build_provider_registry(config: Config) -> ProviderRegistry:
    """Build a ProviderRegistry from configuration.

    Args:
        config: The configuration

    Returns:
        ProviderRegistry with configured providers
    """
    registry = ProviderRegistry()

    for provider_config in config.providers:
        provider = Provider(
            name=provider_config["name"],
            description=provider_config.get("description", ""),
            modules=tuple(provider_config.get("modules", [])),
            allowed_layers=tuple(provider_config.get("allowed_layers", [])),
        )
        registry.register(provider)

    return registry


def _print_contract_result(result, verbose: bool, formatter: RustStyleFormatter | None = None, base_path: Path | None = None) -> None:
    """Print contract check results.

    Args:
        result: The ContractResult to print
        verbose: Whether to show verbose output
        formatter: Optional RustStyleFormatter for rust-style output
        base_path: Base path for resolving source files
    """
    if result.is_valid:
        if verbose:
            click.echo(f"  {result.contract_name}: OK")
        return

    if formatter is None:
        # Default format
        click.echo(f"  {result.contract_name}: FAILED")
        for violation in result.violations:
            click.echo(f"    - {violation}")
    else:
        # Rust-style format
        for violation in result.violations:
            # Try to find source file
            source_file = None
            if base_path:
                # Convert module path to file path
                module_path = violation.importer.replace(".", "/") + ".py"
                potential_file = base_path / module_path
                if potential_file.exists():
                    source_file = potential_file

            formatted = formatter.format_violation(violation, source_file=source_file)
            click.echo(formatted)
            click.echo()  # Empty line between violations


def _run_incremental(
    path: Path, config: Config, verbose: bool, cache_path: Path, structural: bool = False, format_style: str = "default", agent_mode: bool = False
) -> int:
    """Run incremental analysis using cache."""
    cache = ImportGraphCache(cache_path)

    # Load existing cache if available
    cache_loaded = cache.load()

    if verbose and not agent_mode:
        click.echo(f"Building import graph for {config.root_package} from {path}")
        if cache_loaded:
            click.echo(f"Loaded cache from {cache_path}")
        else:
            click.echo("No existing cache found, will create new cache")

    # Find all source files
    builder = IncrementalImportGraphBuilder(config.root_package, cache)
    source_files = builder.find_source_files(path)

    if verbose and not agent_mode:
        click.echo(f"Found {len(source_files)} source files")

    # Build graph incrementally
    graph, reanalyzed = builder.build_from_path_incremental(path, source_files)
    modules = graph.modules

    if verbose and not agent_mode:
        click.echo(f"Found {len(modules)} modules")
        click.echo(f"Re-analyzed {len(reanalyzed)} modules")

    # Save cache
    cache.save()

    if verbose and not agent_mode:
        click.echo(f"Saved cache to {cache_path}")

    # Set up registries from config
    layer_registry = _build_layer_registry(config)
    provider_registry = _build_provider_registry(config)

    # Initialize formatter if needed
    formatter = RustStyleFormatter() if format_style == "rust" and not agent_mode else None

    # Run contracts
    violations_found = False
    all_violations = []

    if "layer" in config.contracts:
        if verbose and not agent_mode:
            click.echo("Checking layer dependencies...")
        layer_contract = LayerContract(layer_registry)
        result = layer_contract.check(graph)
        if not agent_mode:
            _print_contract_result(result, verbose, formatter, path)
        if not result.is_valid:
            violations_found = True
            all_violations.extend(result.violations)

    if "provider" in config.contracts:
        if verbose and not agent_mode:
            click.echo("Checking provider usage...")
        provider_contract = ProviderContract(layer_registry, provider_registry)
        result = provider_contract.check(graph)
        if not agent_mode:
            _print_contract_result(result, verbose, formatter, path)
        if not result.is_valid:
            violations_found = True
            all_violations.extend(result.violations)

    # Run structural tests if enabled
    structural_violations: list[StructuralViolation] = []
    if structural:
        if verbose and not agent_mode:
            click.echo("Running structural tests...")
        structural_violations = _run_structural_tests(path, layer_registry, verbose, formatter)
        if structural_violations:
            violations_found = True

    # Output results
    if agent_mode:
        # Format for agent consumption
        _print_agent_mode_output(all_violations, layer_registry, provider_registry, len(modules))
    elif format_style == "rust":
        # Calculate duration (placeholder since we don't track it yet)
        duration_ms = 0.0
        summary = formatter.format_summary(
            total_violations=len(all_violations) + len(structural_violations),
            analyzed_modules=len(modules),
            duration_ms=duration_ms,
        )
        click.echo(summary)
    else:
        click.echo(f"\nTotal modules: {len(modules)}")

        if violations_found:
            click.echo("Violations found!")
        else:
            click.echo("No violations found.")

    return 1 if violations_found else 0


def _print_agent_mode_output(
    violations: list,
    layer_registry: LayerRegistry,
    provider_registry: ProviderRegistry,
    total_modules: int,
) -> None:
    """Print violations in agent-friendly format.

    Args:
        violations: List of violations to format
        layer_registry: Layer registry for layer lookup
        provider_registry: Provider registry for provider lookup
        total_modules: Total number of modules analyzed
    """
    formatter = AgentContextFormatter()
    contexts = []

    # Categorize violations
    violation_types: dict[str, int] = {}

    for violation in violations:
        # Determine layers
        importer_layer = layer_registry.get_layer_for_module(violation.importer)
        imported_layer = layer_registry.get_layer_for_module(violation.imported)

        layer_importer = importer_layer.name if importer_layer else "unknown"
        layer_imported = imported_layer.name if imported_layer else "unknown"

        # Check if it's a provider-related violation
        is_provider_violation = (
            provider_registry.is_provider_module(violation.imported)
            or provider_registry.is_provider_module(violation.importer)
            or "provider" in violation.message.lower()
        )

        if is_provider_violation:
            severity = "warning"
            principle = "Providers should only be used by specific layers to avoid coupling"
            suggested_fix = "Check if layer really needs this provider, or refactor to avoid the dependency"
            violation_type = "provider_misuse"
        else:
            severity = "error"
            principle = "Dependencies flow forward through layers (lower layers are more fundamental)"
            suggested_fix = f"Extract shared interface to {layer_importer} layer or move code to a common lower layer"
            violation_type = "backward_dependency"

        # Count violation types
        violation_types[violation_type] = violation_types.get(violation_type, 0) + 1

        context = ViolationContext(
            violation=violation,
            layer_importer=layer_importer,
            layer_imported=layer_imported,
            severity=severity,
            architectural_principle=principle,
            suggested_fix=suggested_fix,
        )
        contexts.append(context)

    # Build project stats
    project_stats = {
        "total_modules": total_modules,
        "total_violations": len(violations),
        "violation_types": violation_types,
    }

    # Format and print
    output = formatter.format_batch_for_agent(contexts, project_stats)
    click.echo(output)


def _run_structural_tests(
    path: Path, layer_registry: LayerRegistry, verbose: bool, formatter: RustStyleFormatter | None = None
) -> list[StructuralViolation]:
    """Run structural tests on source files.

    Args:
        path: Path to the project
        layer_registry: Layer registry for layer resolution
        verbose: Whether to show verbose output
        formatter: Optional RustStyleFormatter for rust-style output

    Returns:
        List of structural violations found
    """
    all_violations: list[StructuralViolation] = []

    # Find all Python files
    source_files = list(path.rglob("*.py"))

    # Create structural checks
    file_size_check = FileSizeCheck()
    naming_check = NamingCheck()

    # Define layer resolver
    def resolve_layer(file_path: Path) -> str | None:
        """Resolve layer from file path."""
        path_str = str(file_path)
        for layer in layer_registry:
            if layer.name in path_str:
                return layer.name
        return None

    # Run file size checks
    if verbose:
        click.echo("  Checking file sizes...")
    for file_path in source_files:
        violations = file_size_check.check_file(file_path)
        all_violations.extend(violations)

    # Run naming convention checks
    if verbose:
        click.echo("  Checking naming conventions...")
    for file_path in source_files:
        layer = resolve_layer(file_path)
        violations = naming_check.check_file(file_path, layer=layer)
        all_violations.extend(violations)

    # Print violations
    if all_violations:
        if formatter is None:
            # Default format
            click.echo("  Structural: FAILED")
            for violation in all_violations:
                line_info = f":{violation.line_number}" if violation.line_number else ""
                click.echo(f"    - {violation.file_path}{line_info}: {violation.message}")
                if violation.suggestion:
                    click.echo(f"      Suggestion: {violation.suggestion}")
        else:
            # Rust-style format for structural violations
            for violation in all_violations:
                # Convert structural violation to a format compatible with RustStyleFormatter
                from harness_linter.contracts.base import Violation
                sv = Violation(
                    importer=str(violation.file_path),
                    imported="structural",
                    message=violation.message,
                    line_number=violation.line_number,
                )
                formatted = formatter.format_violation(sv, source_file=violation.file_path)
                click.echo(formatted)
                if violation.suggestion:
                    click.echo(f"   = suggestion: {violation.suggestion}")
                click.echo()
    else:
        if verbose:
            click.echo("  Structural: OK")

    return all_violations


if __name__ == "__main__":
    sys.exit(main())
