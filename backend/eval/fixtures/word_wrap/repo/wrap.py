def wrap(words, width):
    lines, line = [], ''
    for word in words.split():
        if len(line) + len(word) + 1 > width: lines.append(line); line = word
        else: line = (line + ' ' + word).strip()
    return lines
