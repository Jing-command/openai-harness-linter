"""UI layer - User interface layer.

This layer can import from:
- types (lower layer)
- config (lower layer)
- repo (lower layer)
- service (lower layer)
- runtime (lower layer)
- providers (cross-cutting)

This is the top layer and should not be imported by any other layer.
"""

from myproject.ui.cli import CLI

__all__ = ["CLI"]
