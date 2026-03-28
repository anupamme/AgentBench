from app import check_default, create_user


def test_create_default_user():
    u = create_user("Alice")
    assert u.name == "Alice"
    assert u.role == "member"


def test_create_custom_role():
    u = create_user("Bob", "admin")
    assert u.role == "admin"


def test_check_default_true():
    u = create_user("Carol")
    assert check_default(u) is True


def test_check_default_false():
    u = create_user("Dave", "admin")
    assert check_default(u) is False


def test_display_role():
    u = create_user("Eve", "admin")
    assert u.display_role == "ADMIN"
