from csv_simple import parse
def test_quoted_comma(): assert parse('a,"b,c",d') == ['a','b,c','d']
