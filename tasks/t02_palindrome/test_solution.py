from solution import is_palindrome

def test_simple():
    assert is_palindrome("racecar")

def test_mixed_case_and_punctuation():
    assert is_palindrome("A man, a plan, a canal: Panama")

def test_not_palindrome():
    assert not is_palindrome("hello")

def test_empty():
    assert is_palindrome("")
