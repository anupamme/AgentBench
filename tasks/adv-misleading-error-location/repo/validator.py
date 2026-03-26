def validate_config(config: dict) -> list:
    """Validate a config dict. Returns list of error messages."""
    errors = []
    if not config.get("host"):
        errors.append("host is required")
    if config.get("port", 0) < 1 or config.get("port", 0) > 65535:
        errors.append("port must be between 1 and 65535")
    if config["timeout"] < 0:   # line 12 — TypeError if timeout is a string
        errors.append("timeout must be non-negative")
    return errors
