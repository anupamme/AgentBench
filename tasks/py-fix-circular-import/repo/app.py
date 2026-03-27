from models import User
from utils import is_default_role


def create_user(name: str, role: str = None) -> User:
    return User(name, role)


def check_default(user: User) -> bool:
    return is_default_role(user.role)
