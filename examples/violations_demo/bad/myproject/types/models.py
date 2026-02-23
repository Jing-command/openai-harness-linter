"""Type definitions with violations.

VIOLATION: Types layer (index 0) imports from Service layer (index 3).
This violates the layer dependency rule.
"""

# VIOLATION: Importing from higher layer
from myproject.service.utils import format_name


class User:
    """User model."""

    def __init__(self, name: str) -> None:
        self.name = name

    def display_name(self) -> str:
        # VIOLATION: Using service layer function
        return format_name(self.name)
