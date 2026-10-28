from csv_simple import parse
def test_quotes(): assert parse('"a,b",c') == ['a,b','c']
