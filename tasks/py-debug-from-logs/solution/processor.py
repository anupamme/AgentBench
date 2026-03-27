def batch_process(items: list, batch_size: int) -> list:
    """Process items in batches, returning the sum of each batch."""
    results = []
    i = 0
    while i < len(items):
        batch = items[i:i + batch_size]
        results.append(sum(batch))
        i += batch_size
    return results
