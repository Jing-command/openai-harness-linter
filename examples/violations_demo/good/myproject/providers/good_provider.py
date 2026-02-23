"""Provider following rules.

Providers should only import from types/config, not business logic.
"""

from myproject.types.models import User


def log_user_action(user: User) -> None:
    """Log user action.

    Valid: Provider imports from Types layer only.
    """
    print(f"User action: {user.display_name()}")
