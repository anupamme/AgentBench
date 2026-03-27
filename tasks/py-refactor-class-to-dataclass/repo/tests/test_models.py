from models import Point


def test_equality():
    assert Point(1.0, 2.0) == Point(1.0, 2.0)


def test_inequality():
    assert Point(1.0, 2.0) != Point(3.0, 4.0)


def test_repr():
    p = Point(1.0, 2.0)
    assert "1.0" in repr(p)
    assert "2.0" in repr(p)


def test_hashable():
    p1 = Point(1.0, 2.0)
    p2 = Point(1.0, 2.0)
    s = {p1, p2}
    assert len(s) == 1


def test_immutable():
    p = Point(1.0, 2.0)
    try:
        p.x = 99.0
        assert False, "Should have raised AttributeError for frozen dataclass"
    except AttributeError:
        pass


def test_distance():
    p1 = Point(0.0, 0.0)
    p2 = Point(3.0, 4.0)
    assert abs(p1.distance_to(p2) - 5.0) < 1e-9
