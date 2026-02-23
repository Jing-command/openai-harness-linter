"""User service.

Service layer imports from Types, Repo, and Providers (valid).
"""

from typing import Optional

from myproject.providers.logging import get_logger
from myproject.repo.user_repo import UserRepository
from myproject.types.user import User

logger = get_logger(__name__)


class UserService:
    """User business logic service."""

    def __init__(self, repository: UserRepository) -> None:
        """Initialize service with repository."""
        self._repo = repository

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        logger.info(f"Getting user {user_id}")
        return self._repo.get_by_id(user_id)

    def create_user(self, name: str, email: str) -> User:
        """Create a new user."""
        logger.info(f"Creating user: {name}")
        return self._repo.create(name, email)

    def list_users(self) -> list[User]:
        """List all users."""
        logger.info("Listing all users")
        return self._repo.list_all()
