"""Service utilities.

Service layer can import from Types layer (lower layer).
"""

from myproject.types.models import User


def format_user_name(user: User) -> str:
    """Format user name.

    Valid: Service layer imports from Types layer.
    """
    return user.display_name()
