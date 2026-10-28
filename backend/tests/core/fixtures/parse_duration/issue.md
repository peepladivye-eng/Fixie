# Seconds durations fail

`parse_duration("5s")` should return `5`, as the duration parser supports seconds,
minutes and hours.
