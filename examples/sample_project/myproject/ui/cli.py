"""Command-line interface.

UI layer imports from Runtime, Service, Types, and Providers (valid).
"""

from myproject.providers.logging import get_logger
from myproject.runtime.app import Application
from myproject.types.order import OrderItem

logger = get_logger(__name__)


class CLI:
    """Command-line interface."""

    def __init__(self, app: Application) -> None:
        """Initialize CLI with application."""
        self._app = app

    def create_user(self, name: str, email: str) -> None:
        """Create a new user."""
        user = self._app.user_service.create_user(name, email)
        print(f"Created user: {user}")

    def create_order(self, user_id: int, product_id: int, quantity: int, price: float) -> None:
        """Create a new order."""
        items = [OrderItem(product_id, quantity, price)]
        order = self._app.order_service.create_order(user_id, items)
        print(f"Created order: {order}")

    def list_users(self) -> None:
        """List all users."""
        users = self._app.user_service.list_users()
        for user in users:
            print(f"  - {user}")

    def list_orders(self, user_id: int) -> None:
        """List orders for a user."""
        orders = self._app.order_service.list_user_orders(user_id)
        for order in orders:
            print(f"  - {order}")
