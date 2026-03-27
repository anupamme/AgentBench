def process_all(items):
    """Double every item in the list."""
    results = []
    for i in range(len(items)):
        results.append(items[i] * 2)
    return results
