"""Runtime layer - Runtime and execution layer.

This layer can import from:
- types (lower layer)
- config (lower layer)
- repo (lower layer)
- service (lower layer)
- providers (cross-cutting)
"""

from myproject.runtime.app import Application

__all__ = ["Application"]
