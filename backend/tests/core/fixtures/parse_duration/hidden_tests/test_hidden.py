from parse_duration import parse_duration


def test_zero_seconds_are_supported():
    assert parse_duration("0s") == 0
