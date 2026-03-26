from utils import format_role  # circular: utils imports from models


class User:
    def __init__(self, name: str, role: str = None):
        from models import DEFAULT_ROLE  # noqa — illustrates problem
        self.name = name
        self.role = role or DEFAULT_ROLE
        self.display_role = format_role(self.role)


DEFAULT_ROLE = "member"
