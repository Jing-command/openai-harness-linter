"""Provider with violations.

VIOLATION: Provider imports from Service layer (business logic).
Providers should not depend on business logic layers.
"""

# VIOLATION: Provider importing from business logic layer
from myproject.service.utils import format_name


def log_user_action(user_name: str) -> None:
    """Log user action.

    VIOLATION: Using service layer function in provider.
    """
    formatted = format_name(user_name)
    print(f"User action: {formatted}")
