from wrap import wrap
def test_multiple_lines(): assert wrap('one two three', 7) == ['one two', 'three']
