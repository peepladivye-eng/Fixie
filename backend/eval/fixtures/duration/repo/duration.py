def parse_duration(value):
    amount, unit = value.split()
    return int(amount) * (60 if unit.startswith("hour") else 1)
