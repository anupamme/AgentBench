class Profile:
    def __init__(self, name):
        self.name = name


class User:
    def __init__(self, username, profile=None):
        self.username = username
        self.profile = profile

    def get_display_name(self):
        return self.profile.name
