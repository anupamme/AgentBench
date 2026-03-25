"""Database client module."""

DB_URL = "postgres://localhost:5432/mydb"


def connect():
    """Return a simulated database connection string."""
    return f"connected:{DB_URL}"


def query(conn: str, sql: str) -> list[dict]:
    """Execute a query and return rows (simulated)."""
    return [{"conn": conn, "sql": sql}]
