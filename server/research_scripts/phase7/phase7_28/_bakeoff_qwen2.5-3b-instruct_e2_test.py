def is_count_at_least(actual, minimum):
    return actual >= minimum

def test_is_count_at_least():
    assert is_count_at_least(5, 3) == True
    assert is_count_at_least(2, 3) == False
    assert is_count_at_least(3, 3) == True
    print('OK')