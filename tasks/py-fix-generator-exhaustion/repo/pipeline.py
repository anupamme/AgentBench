def process(data):
    """Process data through two consumers and return both results."""
    items = (x * 2 for x in data)
    result_a = consume_sum(items)
    result_b = consume_count(items)
    return result_a, result_b


def consume_sum(items):
    return sum(items)


def consume_count(items):
    return sum(1 for _ in items)
