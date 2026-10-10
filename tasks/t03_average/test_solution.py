from solution import average

def test_basic():
    assert average([1, 2, 3]) == 2

def test_single():
    assert average([5]) == 5

def test_empty_is_zero():
    assert average([]) == 0.0
