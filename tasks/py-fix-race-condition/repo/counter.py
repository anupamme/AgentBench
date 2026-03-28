import time


class Counter:
    def __init__(self):
        self._value = 0

    def increment(self):
        current = self._value
        time.sleep(0)  # simulates a slow read-modify-write; exposes race condition
        self._value = current + 1

    def value(self):
        return self._value

    def reset(self):
        self._value = 0
