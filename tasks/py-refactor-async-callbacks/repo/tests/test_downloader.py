import pytest
import pytest_asyncio
from downloader import fetch, fetch_all


@pytest.mark.asyncio
async def test_fetch_single():
    result = await fetch("http://example.com/page")
    assert result == "content-of-http://example.com/page"


@pytest.mark.asyncio
async def test_fetch_all():
    urls = ["http://a.com", "http://b.com", "http://c.com"]
    results = await fetch_all(urls)
    assert len(results) == 3
    assert all(r.startswith("content-of-") for r in results)
