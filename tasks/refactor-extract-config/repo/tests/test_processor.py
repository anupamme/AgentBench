"""Integration tests for the processor module."""
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from processor import process


def test_process_returns_batch_result():
    result = process(sql="SELECT * FROM items", endpoint="/api/items")
    assert "batch_size" in result
    assert "rows_fetched" in result
    assert "api_endpoint" in result
    assert "api_key_prefix" in result


def test_process_batch_size():
    result = process(sql="SELECT 1", endpoint="/api/ping")
    assert result["batch_size"] == 100


def test_process_api_endpoint():
    result = process(sql="SELECT 1", endpoint="/api/v2/data")
    assert result["api_endpoint"] == "/api/v2/data"


def test_process_api_key_prefix():
    result = process(sql="SELECT 1", endpoint="/api/ping")
    assert result["api_key_prefix"] == "sk-test"
