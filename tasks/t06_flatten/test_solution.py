from solution import flatten

def test_flat():
    assert flatten([1, 2, 3]) == [1, 2, 3]

def test_one_level():
    assert flatten([1, [2, 3]]) == [1, 2, 3]

def test_deep():
    assert flatten([1, [2, [3, [4]]]]) == [1, 2, 3, 4]

def test_empty_inner():
    assert flatten([[], [1], []]) == [1]
