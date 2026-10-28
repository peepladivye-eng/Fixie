from pages import page
def test_full_page(): assert page(list(range(6)), 1, 3) == [0, 1, 2]
