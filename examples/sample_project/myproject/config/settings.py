"""Application settings.

Config layer imports from Types layer (valid).
"""

from myproject.types.user import User


class Settings:
    """Application settings."""

    DATABASE_URL: str = "sqlite:///app.db"
    DEBUG: bool = False
    SECRET_KEY: str = "dev-secret-key"

    @classmethod
    def get_user_schema(cls) -> dict:
        """Get user schema - demonstrates types layer usage."""
        # This is valid: config can import from types
        return {
            "id": int,
            "name": str,
            "email": str,
        }
