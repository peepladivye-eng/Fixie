from parse_duration import parse_duration


def test_minutes_are_supported():
    assert parse_duration("2m") == 120


def test_seconds_are_supported():
    assert parse_duration("5s") == 5
