"""Application runtime.

Runtime layer imports from Service, Repo, Types, and Providers (valid).
"""

from myproject.providers.logging import get_logger
from myproject.repo.order_repo import OrderRepository
from myproject.repo.user_repo import UserRepository
from myproject.service.order_service import OrderService
from myproject.service.user_service import UserService

logger = get_logger(__name__)


class Application:
    """Application runtime."""

    def __init__(self) -> None:
        """Initialize application."""
        # Initialize repositories
        user_repo = UserRepository()
        order_repo = OrderRepository()

        # Initialize services
        self._user_service = UserService(user_repo)
        self._order_service = OrderService(order_repo, user_repo)

        logger.info("Application initialized")

    @property
    def user_service(self) -> UserService:
        """Get user service."""
        return self._user_service

    @property
    def order_service(self) -> OrderService:
        """Get order service."""
        return self._order_service

    def run(self) -> None:
        """Run the application."""
        logger.info("Application running")
