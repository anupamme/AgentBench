import pytest
from stack import Stack, StackUnderflowError


def test_new_stack_is_empty():
    s = Stack()
    assert s.is_empty() is True


def test_push_makes_nonempty():
    s = Stack()
    s.push(1)
    assert s.is_empty() is False


def test_push_pop_single():
    s = Stack()
    s.push(42)
    assert s.pop() == 42


def test_push_pop_lifo_order():
    s = Stack()
    s.push(1)
    s.push(2)
    s.push(3)
    assert s.pop() == 3
    assert s.pop() == 2
    assert s.pop() == 1


def test_pop_empty_raises():
    s = Stack()
    with pytest.raises(StackUnderflowError):
        s.pop()


def test_peek_returns_top():
    s = Stack()
    s.push(10)
    s.push(20)
    assert s.peek() == 20
    assert s.size() == 2  # peek does not remove


def test_peek_empty_raises():
    s = Stack()
    with pytest.raises(StackUnderflowError):
        s.peek()


def test_size():
    s = Stack()
    assert s.size() == 0
    s.push("a")
    assert s.size() == 1
    s.push("b")
    assert s.size() == 2
    s.pop()
    assert s.size() == 1


def test_push_various_types():
    s = Stack()
    s.push(None)
    s.push([1, 2, 3])
    s.push({"key": "value"})
    assert s.size() == 3
