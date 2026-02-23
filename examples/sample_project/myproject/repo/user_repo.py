"""User repository.

Repo layer imports from Types and Config layers (valid).
"""

from typing import Optional

from myproject.types.user import User


class UserRepository:
    """User data access repository."""

    def __init__(self) -> None:
        """Initialize repository with mock data."""
        self._users: dict[int, User] = {}
        self._next_id = 1

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)

    def create(self, name: str, email: str) -> User:
        """Create a new user."""
        user = User(id=self._next_id, name=name, email=email)
        self._users[user.id] = user
        self._next_id += 1
        return user

    def list_all(self) -> list[User]:
        """List all users."""
        return list(self._users.values())
