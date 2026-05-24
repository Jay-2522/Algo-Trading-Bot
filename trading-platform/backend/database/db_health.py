from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend.database.database import DATABASE_URL, engine


class DatabaseHealthService:
    """Report connection availability without mutating persistent state."""

    def check_database_connection(self) -> bool:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False

    def get_database_status(self) -> dict:
        connected = self.check_database_connection()
        database_type = "sqlite" if DATABASE_URL.startswith("sqlite") else DATABASE_URL.split(":", 1)[0]
        return {
            "connected": connected,
            "database_type": database_type,
            "message": "Database connection available." if connected else "Database connection unavailable.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

