"""Database client module."""

from config import DB_URL


def connect():
    """Return a simulated database connection string."""
    return f"connected:{DB_URL}"


def query(conn: str, sql: str) -> list[dict]:
    """Execute a query and return rows (simulated)."""
    return [{"conn": conn, "sql": sql}]
