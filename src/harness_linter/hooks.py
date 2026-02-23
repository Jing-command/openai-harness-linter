"""Pre-commit hook integration."""

import sys
import subprocess
from pathlib import Path


def run_pre_commit(files: list[str]) -> int:
    """Run harness-lint on files staged for commit.

    This is called by pre-commit with the list of staged Python files.
    """
    # Find project root (look for pyproject.toml)
    project_root = Path.cwd()
    while not (project_root / "pyproject.toml").exists():
        parent = project_root.parent
        if parent == project_root:
            print("Error: Could not find pyproject.toml")
            return 1
        project_root = parent

    # Run harness-lint
    result = subprocess.run(
        ["harness-lint", "-v"],
        cwd=project_root,
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode


if __name__ == "__main__":
    files = sys.argv[1:]
    sys.exit(run_pre_commit(files))
