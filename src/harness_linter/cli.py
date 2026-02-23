"""Command-line interface for harness_linter."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from harness_linter.cache import ImportGraphCache
from harness_linter.graph import ImportGraphBuilder, IncrementalImportGraphBuilder


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--package", "-p", required=True, help="Root package name")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option(
    "--incremental", "-i", is_flag=True, help="Enable incremental checking using cache"
)
@click.option(
    "--cache-path",
    type=click.Path(path_type=Path),
    default=Path(".harness_cache"),
    help="Path to cache file (default: .harness_cache)",
)
def main(
    path: Path, package: str, verbose: bool, incremental: bool, cache_path: Path
) -> int:
    """Analyze import graph for a Python package."""
    try:
        if incremental:
            return _run_incremental(path, package, verbose, cache_path)
        else:
            return _run_full(path, package, verbose)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        return 1


def _run_full(path: Path, package: str, verbose: bool) -> int:
    """Run full analysis without caching."""
    builder = ImportGraphBuilder(package)

    if verbose:
        click.echo(f"Building import graph for {package} from {path}")

    graph = builder.build_from_path(path)
    modules = graph.modules

    if verbose:
        click.echo(f"Found {len(modules)} modules")

    # Basic analysis - just count imports
    total_imports = 0
    for module in modules:
        total_imports += len(graph.find_modules_directly_imported_by(module))

    click.echo(f"Total modules: {len(modules)}")
    click.echo(f"Total imports: {total_imports}")

    return 0


def _run_incremental(
    path: Path, package: str, verbose: bool, cache_path: Path
) -> int:
    """Run incremental analysis using cache."""
    cache = ImportGraphCache(cache_path)

    # Load existing cache if available
    cache_loaded = cache.load()

    if verbose:
        click.echo(f"Building import graph for {package} from {path}")
        if cache_loaded:
            click.echo(f"Loaded cache from {cache_path}")
        else:
            click.echo("No existing cache found, will create new cache")

    # Find all source files
    builder = IncrementalImportGraphBuilder(package, cache)
    source_files = builder.find_source_files(path)

    if verbose:
        click.echo(f"Found {len(source_files)} source files")

    # Build graph incrementally
    graph, reanalyzed = builder.build_from_path_incremental(path, source_files)
    modules = graph.modules

    if verbose:
        click.echo(f"Found {len(modules)} modules")
        click.echo(f"Re-analyzed {len(reanalyzed)} modules")

    # Save cache
    cache.save()

    if verbose:
        click.echo(f"Saved cache to {cache_path}")

    # Basic analysis - just count imports
    total_imports = 0
    for module in modules:
        total_imports += len(graph.find_modules_directly_imported_by(module))

    click.echo(f"Total modules: {len(modules)}")
    click.echo(f"Total imports: {total_imports}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
