"""Order type definitions."""

from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class OrderItem:
    """Order item data model."""

    product_id: int
    quantity: int
    price: float


@dataclass
class Order:
    """Order data model."""

    id: int
    user_id: int
    items: List[OrderItem]
    created_at: datetime
    status: str = "pending"

    def total_amount(self) -> float:
        """Calculate total order amount."""
        return sum(item.price * item.quantity for item in self.items)
