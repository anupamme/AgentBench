import threading


class Counter:
    def __init__(self):
        self._value = 0

    def increment(self):
        current = self._value
        self._value = current + 1

    def value(self):
        return self._value

    def reset(self):
        self._value = 0
