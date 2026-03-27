def format_number(n, decimals=2):
    """Format a number with the given number of decimal places."""
    return f"{n:.{decimals}f}"


def format_currency(amount, symbol="$"):
    """Format an amount as currency with 2 decimal places."""
    return f"{symbol}{format_number(amount, 2)}"


def format_percentage(ratio, decimals=1):
    """Format a ratio as a percentage."""
    return f"{ratio * 100:.{decimals}f}%"
