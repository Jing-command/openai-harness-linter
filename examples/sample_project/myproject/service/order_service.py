"""Order service.

Service layer imports from Types, Repo, and Providers (valid).
"""

from typing import Optional

from myproject.providers.logging import get_logger
from myproject.providers.metrics import record_metric
from myproject.repo.order_repo import OrderRepository
from myproject.repo.user_repo import UserRepository
from myproject.types.order import Order, OrderItem

logger = get_logger(__name__)


class OrderService:
    """Order business logic service."""

    def __init__(
        self,
        order_repo: OrderRepository,
        user_repo: UserRepository,
    ) -> None:
        """Initialize service with repositories."""
        self._order_repo = order_repo
        self._user_repo = user_repo

    def get_order(self, order_id: int) -> Optional[Order]:
        """Get order by ID."""
        logger.info(f"Getting order {order_id}")
        return self._order_repo.get_by_id(order_id)

    def create_order(self, user_id: int, items: list[OrderItem]) -> Order:
        """Create a new order."""
        # Verify user exists
        user = self._user_repo.get_by_id(user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        logger.info(f"Creating order for user {user_id}")
        order = self._order_repo.create(user_id, items)
        record_metric("order_created", 1)
        return order

    def list_user_orders(self, user_id: int) -> list[Order]:
        """List all orders for a user."""
        logger.info(f"Listing orders for user {user_id}")
        return self._order_repo.list_by_user(user_id)
