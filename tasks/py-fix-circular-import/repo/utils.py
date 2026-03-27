from models import DEFAULT_ROLE  # circular: models imports from utils


def format_role(role: str) -> str:
    return role.upper()


def is_default_role(role: str) -> bool:
    return role == DEFAULT_ROLE
