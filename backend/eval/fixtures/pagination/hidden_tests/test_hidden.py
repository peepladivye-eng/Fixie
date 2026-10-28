from pages import page
def test_last_page(): assert page(list(range(5)), 2, 3) == [3, 4]
