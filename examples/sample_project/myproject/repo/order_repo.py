"""Order repository.

Repo layer imports from Types layer (valid).
"""

from datetime import datetime
from typing import Optional

from myproject.types.order import Order, OrderItem


class OrderRepository:
    """Order data access repository."""

    def __init__(self) -> None:
        """Initialize repository with mock data."""
        self._orders: dict[int, Order] = {}
        self._next_id = 1

    def get_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID."""
        return self._orders.get(order_id)

    def create(self, user_id: int, items: list[OrderItem]) -> Order:
        """Create a new order."""
        order = Order(
            id=self._next_id,
            user_id=user_id,
            items=items,
            created_at=datetime.now(),
        )
        self._orders[order.id] = order
        self._next_id += 1
        return order

    def list_by_user(self, user_id: int) -> list[Order]:
        """List all orders for a user."""
        return [o for o in self._orders.values() if o.user_id == user_id]
