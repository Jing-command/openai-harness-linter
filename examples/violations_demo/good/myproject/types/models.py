"""Type definitions - follows rules.

Types layer only defines data models, no imports from higher layers.
"""


class User:
    """User model."""

    def __init__(self, name: str) -> None:
        self.name = name

    def display_name(self) -> str:
        # Only uses built-in functions, no imports from higher layers
        return self.name.strip().title()
