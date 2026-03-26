class StackUnderflowError(Exception):
    """Raised when popping or peeking from an empty stack."""


class Stack:
    def __init__(self):
        self._items = []

    def push(self, item) -> None:
        """Push an item onto the top of the stack."""
        self._items.append(item)

    def pop(self):
        """Remove and return the top item."""
        if self.is_empty():
            raise StackUnderflowError("pop from empty stack")
        return self._items.pop()

    def peek(self):
        """Return the top item without removing it."""
        if self.is_empty():
            raise StackUnderflowError("peek from empty stack")
        return self._items[-1]

    def is_empty(self) -> bool:
        """Return True if the stack has no items."""
        return len(self._items) == 0

    def size(self) -> int:
        """Return the number of items in the stack."""
        return len(self._items)
