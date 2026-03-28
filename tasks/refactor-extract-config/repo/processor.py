"""Data processor that combines database and API data."""

from api_client import fetch
from db import connect, query

BATCH_SIZE = 100


def process(sql: str, endpoint: str) -> dict:
    """Fetch data from DB and API and combine into a batch result."""
    conn = connect()
    rows = query(conn, sql)
    api_data = fetch(endpoint)

    batch = rows[:BATCH_SIZE]
    return {
        "batch_size": BATCH_SIZE,
        "rows_fetched": len(batch),
        "api_endpoint": api_data["endpoint"],
        "api_key_prefix": api_data["api_key"][:7],
    }
