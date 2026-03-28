import asyncio


async def fetch(url: str) -> str:
    """Fetch a URL asynchronously."""
    await asyncio.sleep(0)  # simulate async I/O
    return f"content-of-{url}"


async def fetch_all(urls: list[str]) -> list[str]:
    """Fetch all URLs concurrently and return list of results."""
    return await asyncio.gather(*[fetch(url) for url in urls])
