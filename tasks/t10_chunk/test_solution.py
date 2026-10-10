from solution import chunk

def test_even():
    assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

def test_remainder_kept():
    assert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]

def test_bigger_than_list():
    assert chunk([1, 2], 5) == [[1, 2]]

def test_empty():
    assert chunk([], 3) == []
