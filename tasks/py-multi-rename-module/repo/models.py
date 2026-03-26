from helpers import capitalize_words


class Article:
    def __init__(self, title: str):
        self.title = capitalize_words(title)
