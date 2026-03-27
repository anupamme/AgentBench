_REGISTRY = {}


def register(name, tags=[]):
    """Register an item with optional tags."""
    _REGISTRY[name] = {"name": name, "tags": tags}
    return _REGISTRY[name]


def get(name):
    """Retrieve a registered item."""
    return _REGISTRY.get(name)


def clear():
    """Clear all registrations."""
    _REGISTRY.clear()
