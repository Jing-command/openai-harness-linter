"""User type definitions."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """User data model."""

    id: int
    name: str
    email: str
    is_active: bool = True

    def to_dict(self) -> dict:
        """Convert user to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_active": self.is_active,
        }
