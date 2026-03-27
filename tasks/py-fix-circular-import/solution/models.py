from utils import format_role
from constants import DEFAULT_ROLE


class User:
    def __init__(self, name: str, role: str = None):
        self.name = name
        self.role = role or DEFAULT_ROLE
        self.display_role = format_role(self.role)
