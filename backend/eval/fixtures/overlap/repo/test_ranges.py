from ranges import overlaps
def test_touching_is_not_overlap(): assert overlaps((1, 3), (3, 5)) is False
