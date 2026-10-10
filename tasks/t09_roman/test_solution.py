from solution import roman_to_int

def test_simple():
    assert roman_to_int("III") == 3

def test_four_and_nine():
    assert roman_to_int("IV") == 4 and roman_to_int("IX") == 9

def test_mixed():
    assert roman_to_int("MCMXCIV") == 1994

def test_58():
    assert roman_to_int("LVIII") == 58
