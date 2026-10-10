from solution import fizzbuzz

def test_five():
    assert fizzbuzz(5) == ["1", "2", "Fizz", "4", "Buzz"]

def test_fifteen_ends_with_fizzbuzz():
    assert fizzbuzz(15)[-1] == "FizzBuzz"

def test_zero():
    assert fizzbuzz(0) == []
