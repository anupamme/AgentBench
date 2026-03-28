def batch_process(items: list, batch_size: int) -> list:
    """Process items in batches, returning the sum of each batch."""
    results = []
    i = 0
    while i < len(items):
        batch = items[i : i + batch_size]
        i += batch_size
        if i >= len(items) and len(batch) == batch_size:
            # BUG: exits before appending the final batch when it is exactly batch_size
            break
        results.append(sum(batch))
    return results
