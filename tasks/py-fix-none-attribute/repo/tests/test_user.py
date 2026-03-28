from user import Profile, User


def test_display_name_with_profile():
    user = User("alice", Profile("Alice Smith"))
    assert user.get_display_name() == "Alice Smith"


def test_display_name_no_profile():
    user = User("bob")
    assert user.get_display_name() == "bob"
