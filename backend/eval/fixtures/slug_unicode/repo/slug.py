def slugify(value): return ''.join(c.lower() if c.isascii() and c.isalnum() else '-' for c in value).strip('-')
