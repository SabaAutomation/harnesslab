from solution import fib

def test_base_cases():
    assert fib(0) == 0 and fib(1) == 1

def test_small():
    assert [fib(i) for i in range(8)] == [0, 1, 1, 2, 3, 5, 8, 13]

def test_larger():
    assert fib(20) == 6765
