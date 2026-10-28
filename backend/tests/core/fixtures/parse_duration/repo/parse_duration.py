def parse_duration(value: str) -> int:
    amount, unit = value[:-1], value[-1]
    if unit == "m":
        return int(amount) * 60
    if unit == "h":
        return int(amount) * 3600
    raise ValueError("unsupported duration unit")
