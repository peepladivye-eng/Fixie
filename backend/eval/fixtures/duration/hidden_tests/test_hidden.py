from duration import parse_duration
def test_minutes_and_hours(): assert (parse_duration("1 hour"), parse_duration("5 minutes")) == (3600, 300)
